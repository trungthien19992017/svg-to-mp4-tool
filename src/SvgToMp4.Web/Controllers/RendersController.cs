using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Mvc;
using SvgToMp4.Core;
using SvgToMp4.Worker;

namespace SvgToMp4.Web.Controllers;

[ApiController, Route("api")]
public sealed class RendersController(JobStore store, AppPaths paths, RenderWorker worker) : ControllerBase
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    [HttpGet("session")]
    public object Session([FromServices] IAntiforgery antiforgery) => new { token = antiforgery.GetAndStoreTokens(HttpContext).RequestToken };
    [HttpGet("renders")] public object List() => store.List();
    [HttpGet("renders/{id}")] public IActionResult Get(string id) => store.Get(id) is { } job ? Ok(job) : NotFound();

    [HttpPost("renders"), ValidateAntiForgeryToken]
    public async Task<IActionResult> Create(CreateRender request)
    {
        if (string.IsNullOrWhiteSpace(request.Svg) || Encoding.UTF8.GetByteCount(request.Svg) > 20_000_000) return BadRequest(new { error = "SVG phải có nội dung và không quá 20 MB, gồm cả ảnh nền nhúng." });
        if (request.Mode is not ("preview" or "export")) return BadRequest(new { error = "Loại render không hợp lệ." });
        var s = request.Settings;
        if (s is not null && s.Effect is not ("whiteboard" or "doodle")) return BadRequest(new { error = "Hiệu ứng không hợp lệ." });
        if (s is null || !double.IsFinite(s.Duration) || s.Duration is < 3 or > 120 || !double.IsFinite(s.Hold) || s.Hold < 0.5 || s.Hold > s.Duration - 1.5 || s.Aspect is not ("portrait" or "landscape") || s.Hand is not ("asian" or "black" or "children" or "white" or "none") || !double.IsFinite(s.HandScale) || s.HandScale is < 0.2 or > 1.5)
            return BadRequest(new { error = "Thiết lập không hợp lệ: thời lượng 3–120 giây, giữ hình ≥0,5 giây và còn ít nhất 1,5 giây cho phần vẽ/tô màu." });
        if (SvgInputValidation.ValidateMode(request.Svg, s.Effect) is { } modeError)
            return BadRequest(new { error = modeError });
        if (store.List().Count(j => !JobStates.Terminal(j.State)) >= 5) return BadRequest(new { error = "Đang có 5 tác vụ chờ. Vui lòng đợi hoặc hủy bớt." });
        var id = Guid.NewGuid().ToString("N"); var dir = paths.JobDirectory(id); Directory.CreateDirectory(dir);
        var preview = request.Mode == "preview"; var shortSide = preview ? 540 : 1080; var longSide = preview ? 960 : 1920;
        var width = s.Aspect == "portrait" ? shortSide : longSide; var height = s.Aspect == "portrait" ? longSide : shortSide; var fps = preview ? 15 : 30;
        var name = Path.GetFileNameWithoutExtension(request.Name ?? "Bản vẽ").Trim();
        if (string.IsNullOrEmpty(name)) name = "Bản vẽ";
        name = name[..Math.Min(80, name.Length)];
        var now = DateTimeOffset.UtcNow.ToString("O");
        var job = new Job(id, name, request.Mode, "Queued", "Đang chờ", 0, (int)Math.Round(s.Duration * fps), null, now, now, s, width, height, fps);
        await System.IO.File.WriteAllTextAsync(Path.Combine(dir, "input.svg"), request.Svg, new UTF8Encoding(false));
        await System.IO.File.WriteAllTextAsync(Path.Combine(dir, "request.json"), JsonSerializer.Serialize(new { schemaVersion = 1, jobId = id, width, height, fps, settings = s }, Json));
        store.Add(job); return Accepted($"/api/renders/{id}", job);
    }
    [HttpPost("renders/{id}/cancel"), ValidateAntiForgeryToken]
    public IActionResult Cancel(string id) => worker.Cancel(id) is { } job ? Ok(job) : NotFound();

    [HttpGet("renders/{id}/video")]
    public IActionResult Video(string id, [FromQuery] bool download = false)
    {
        var job = store.Get(id); if (job?.State is not ("Succeeded" or "Completed")) return NotFound();
        var file = Path.Combine(paths.JobDirectory(id), "output.mp4"); if (!System.IO.File.Exists(file)) return NotFound();
        return PhysicalFile(file, "video/mp4", download ? $"{job.Name}-{job.Mode}.mp4" : null, enableRangeProcessing: true);
    }
    [HttpGet("renders/{id}/source")]
    public IActionResult Source(string id)
    {
        var job = store.Get(id); if (job is null || job.Kind == "story") return NotFound();
        return PhysicalFile(Path.Combine(paths.JobDirectory(id), "input.svg"), "text/plain; charset=utf-8");
    }
}
