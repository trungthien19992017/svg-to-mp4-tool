using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.AspNetCore.Mvc;
using SvgToMp4.Core;

namespace SvgToMp4.Web.Controllers;

[ApiController, Route("api/stories")]
public sealed class StoriesController(StoryStore stories, JobStore jobs, AppPaths paths) : ControllerBase
{
    [HttpGet] public object List() => stories.List();
    [HttpGet("{id}")] public IActionResult Get(string id) => Guard(() => Ok(stories.Get(id)));
    [HttpPost("import"), ValidateAntiForgeryToken, RequestSizeLimit(70_000_000)]
    public async Task<IActionResult> Import(IFormFile file)
    {
        if (file.Length is <= 0 or > 64_000_000) return BadRequest(new { error = "ZIP tối đa 64 MB." });
        using var buffer = new MemoryStream(); await file.CopyToAsync(buffer); buffer.Position = 0;
        return Guard(() => Ok(stories.Import(buffer)));
    }
    [HttpPost, ValidateAntiForgeryToken]
    public IActionResult Create(StorySave request) => Guard(() => Ok(stories.Save(null, request.Manifest, request.Files.ToDictionary(f => f.Key, f => Encoding.UTF8.GetBytes(f.Value), StringComparer.OrdinalIgnoreCase))));
    [HttpPut("{id}"), ValidateAntiForgeryToken]
    public IActionResult Save(string id, StorySave request, [FromQuery] string revision) => Guard(() =>
    {
        return Ok(stories.SaveRevision(id, revision, request));
    });
    [HttpGet("{id}/export")]
    public IActionResult Export(string id) => Guard(() => File(stories.Export(stories.Get(id)), "application/zip", $"story-{id}.zip"));
    [HttpGet("{id}/files/{**name}")]
    public IActionResult Read(string id, string name, [FromQuery] string? revision) => Guard(() =>
    {
        var project = stories.Get(id); var file = Path.Combine(stories.RevisionPath(id, revision ?? project.Revision), StoryValidation.SafePath(name));
        var ext = Path.GetExtension(name).ToLowerInvariant();
        var mime = ext switch { ".wav" => "audio/wav", ".mp3" => "audio/mpeg", ".m4a" => "audio/mp4", ".ogg" => "audio/ogg", ".png" => "image/png", ".jpg" or ".jpeg" => "image/jpeg", ".webp" => "image/webp", _ => "text/plain; charset=utf-8" };
        return PhysicalFile(file, mime, enableRangeProcessing: true);
    });
    [HttpPost("{id}/render"), ValidateAntiForgeryToken]
    public IActionResult Render(string id, StoryRenderOptions options) => Guard(() =>
    {
        StoryValidation.ValidateVideo(options.Width, options.Height, options.Fps);
        if (options.Crf is < 10 or > 35 || options.Preset is not ("ultrafast" or "veryfast" or "medium")) throw new ArgumentException("CRF 10–35, preset ultrafast/veryfast/medium.");
        if (jobs.List().Count(j => !JobStates.Terminal(j.State)) >= 5) return BadRequest(new { error = "Đang có 5 tác vụ chờ." });
        var project = stories.Get(id); var jobId = Guid.NewGuid().ToString("N"); var dir = paths.JobDirectory(jobId); Directory.CreateDirectory(dir);
        var snapshot = stories.RevisionPath(id, project.Revision); var seconds = project.Manifest["duration"]!.GetValue<double>();
        var settings = new RenderSettings(seconds, 0, options.Width < options.Height ? "portrait" : "landscape", "none");
        var now = DateTimeOffset.UtcNow.ToString("O");
        var job = new Job(jobId, project.Title, "export", "Queued", "Đang chờ", 0, (int)Math.Ceiling(seconds * options.Fps), null, now, now, settings, options.Width, options.Height, options.Fps, ProjectId: id, Revision: project.Revision, Kind: "story");
        FileWrite(Path.Combine(dir, "request.json"), new { schemaVersion = 1, kind = "story", snapshot, width = options.Width, height = options.Height, fps = options.Fps, crf = options.Crf, preset = options.Preset });
        jobs.Add(job); return Accepted($"/api/renders/{jobId}", job);
    });
    private static void FileWrite(string path, object value) => System.IO.File.WriteAllText(path, JsonSerializer.Serialize(value, new JsonSerializerOptions(JsonSerializerDefaults.Web)));
    private IActionResult Guard(Func<IActionResult> action)
    {
        try { return action(); }
        catch (StoryConflictException e) { return Conflict(new { error = e.Message }); }
        catch (FileNotFoundException) { return NotFound(new { error = "Không tìm thấy project/file." }); }
        catch (DirectoryNotFoundException) { return NotFound(new { error = "Không tìm thấy project/revision." }); }
        catch (Exception e) when (e is ArgumentException or InvalidDataException or JsonException or System.Xml.XmlException or InvalidOperationException or FormatException)
        { return BadRequest(new { error = e.Message.Split('\n')[0] }); }
    }
}
