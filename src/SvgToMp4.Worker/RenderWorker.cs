using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using SvgToMp4.Core;

namespace SvgToMp4.Worker;

public sealed class RenderWorker(JobStore store, AppPaths paths, IConfiguration config, ILogger<RenderWorker> logger) : BackgroundService
{
    private readonly object gate = new();
    private string? activeId;
    private CancellationTokenSource? activeCancel;
    public Job? Cancel(string id)
    {
        lock (gate)
        {
            var job = store.Update(id, j => JobStates.Terminal(j.State) ? j : j with { State = "Cancelled", Stage = "Đã hủy", CompletedAt = DateTimeOffset.UtcNow.ToString("O") });
            if (activeId == id) activeCancel?.Cancel();
            return job;
        }
    }
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            var job = store.List().Where(j => j.State == "Queued").OrderBy(j => j.CreatedAt).FirstOrDefault();
            if (job is null) { await Task.Delay(500, stoppingToken); continue; }
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(stoppingToken);
            cts.CancelAfter(TimeSpan.FromSeconds(job.Kind == "story" ? Math.Clamp(job.Settings.Duration * 20, 900, 7200) : 900));
            lock (gate)
            {
                if (store.Get(job.Id)?.State != "Queued") continue;
                activeId = job.Id; activeCancel = cts;
                store.Update(job.Id, j => j with { State = "Preparing", Stage = job.Kind == "story" ? "Đang chuẩn bị câu chuyện" : "Đang kiểm tra SVG", StartedAt = DateTimeOffset.UtcNow.ToString("O") });
            }
            try { await Run(job, cts.Token); }
            catch (OperationCanceledException)
            {
                store.Update(job.Id, j => JobStates.Terminal(j.State) ? j : j with { State = "Failed", Stage = "Đã dừng", Error = stoppingToken.IsCancellationRequested ? "Ứng dụng đã dừng." : "Tác vụ vượt quá thời gian xử lý cho phép.", CompletedAt = DateTimeOffset.UtcNow.ToString("O") });
            }
            catch (Exception e)
            {
                logger.LogWarning(e, "Render {JobId} failed", job.Id);
                store.Update(job.Id, j => JobStates.Terminal(j.State) ? j : j with { State = "Failed", Stage = "Không thể render", Error = e.Message, CompletedAt = DateTimeOffset.UtcNow.ToString("O") });
            }
            finally
            {
                lock (gate) { activeCancel = null; activeId = null; }
                if (store.Get(job.Id)?.State is not ("Succeeded" or "Completed"))
                    foreach (var name in new[] { "output.partial.mp4", "silent.partial.mp4", "output.mp4" })
                    {
                        try { File.Delete(Path.Combine(paths.JobDirectory(job.Id), name)); } catch (IOException) { }
                    }
            }
        }
    }
    private async Task Run(Job job, CancellationToken token)
    {
        if (job.Kind == "story" && (!OperatingSystem.IsWindows() || !Environment.Is64BitProcess)) throw new InvalidOperationException("Story render cần Windows 64-bit với OS Job Object trong bản này.");
        var dir = paths.JobDirectory(job.Id);
        var start = new ProcessStartInfo(config["Renderer:Python"] ?? "python")
        {
            WorkingDirectory = paths.Root, UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
        };
        start.ArgumentList.Add(job.Kind == "story" ? Path.Combine(paths.Root, "engine", "story_render.py") : paths.Adapter); start.ArgumentList.Add("--job"); start.ArgumentList.Add(Path.Combine(dir, "request.json"));
        start.Environment["PYTHONUTF8"] = "1";
        start.Environment["PYTHONDONTWRITEBYTECODE"] = "1";
        if (job.Kind == "story") start.Environment["STORY_RESOURCE_GUARD"] = "windows-job-v1";
        // Render jobs never need credentials from the web host.
        foreach (var key in start.Environment.Keys.Where(k => k.Contains("TOKEN", StringComparison.OrdinalIgnoreCase) || k.Contains("SECRET", StringComparison.OrdinalIgnoreCase) || k.Contains("API_KEY", StringComparison.OrdinalIgnoreCase)).ToArray()) start.Environment.Remove(key);
        using var process = Process.Start(start) ?? throw new InvalidOperationException("Không khởi động được Python.");
        using var boundary = job.Kind == "story" ? new StoryProcessBoundary(process) : null;
        using var registration = token.Register(() => { try { if (!process.HasExited) process.Kill(entireProcessTree: true); } catch (InvalidOperationException) { } });
        // Drain stderr even for verbose encoders; keep diagnostics bounded.
        var errors = new Queue<string>();
        var stderr = Task.Run(async () =>
        {
            while (await process.StandardError.ReadLineAsync() is { } line)
            {
                errors.Enqueue(line.Length > 1000 ? line[..1000] : line);
                while (errors.Count > 30) errors.Dequeue();
            }
        });
        string? engineError = null;
        while (await process.StandardOutput.ReadLineAsync(token) is { } line)
        {
            try
            {
                using var doc = JsonDocument.Parse(line); var e = doc.RootElement;
                var type = e.GetProperty("type").GetString();
                if (type == "error") engineError = e.GetProperty("message").GetString();
                if (type == "progress")
                {
                    var state = e.GetProperty("state").GetString()!;
                    var stage = e.GetProperty("stage").GetString()!;
                    var done = e.TryGetProperty("done", out var d) ? d.GetInt32() : 0;
                    var total = e.TryGetProperty("total", out var t) ? t.GetInt32() : job.FramesTotal;
                    var warning = e.TryGetProperty("warning", out var w) ? w.GetString() : null;
                    store.Update(job.Id, j => JobStates.Terminal(j.State) ? j : j with { State = state, Stage = stage, FramesDone = done, FramesTotal = total, Warning = warning ?? j.Warning });
                }
            }
            catch (JsonException) { logger.LogDebug("Non-JSON renderer output ignored"); }
        }
        await process.WaitForExitAsync(token); await stderr; token.ThrowIfCancellationRequested();
        if (process.ExitCode != 0) throw new InvalidOperationException(engineError ?? "Engine không xuất được video. Kiểm tra cài đặt Python, Chrome và FFmpeg.");
        var output = Path.Combine(dir, "output.mp4");
        if (!File.Exists(output) || !File.Exists(Path.Combine(dir, "result.json"))) throw new InvalidOperationException("Engine chưa tạo đủ kết quả kiểm chứng.");
        lock (gate)
        {
            token.ThrowIfCancellationRequested();
            store.Update(job.Id, j => JobStates.Terminal(j.State) ? j : j with { State = job.Kind == "story" ? "Completed" : "Succeeded", Stage = "Hoàn tất", FramesDone = j.FramesTotal, CompletedAt = DateTimeOffset.UtcNow.ToString("O"), OutputPath = output });
        }
    }
}
