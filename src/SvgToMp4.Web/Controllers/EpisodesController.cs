using System.Text;
using System.IO.Compression;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Xml;
using Microsoft.AspNetCore.Mvc;
using SvgToMp4.Core;

namespace SvgToMp4.Web.Controllers;

[ApiController, Route("api/production-kits")]
public sealed class ProductionKitsController(ProductionKitStore kits, StoryStore stories, AppPaths paths) : ControllerBase
{
    [HttpGet("runtime-info")]
    public object RuntimeInfo() => new { version = "production-import-2", supportsClipPath = true, detectsStoryZip = true, supportsExperimentalKits = true };
    [HttpGet] public IActionResult List() => Guard(() => Ok(kits.List()));
    [HttpGet("{id}/{version}")]
    public IActionResult Get(string id, string version) => Guard(() =>
    {
        var kit = kits.Get(id, version);
        return Ok(new { kit.Id, kit.Version, kit.Digest, kit.Manifest, kit.Rig, kit.Catalogs });
    });
    [HttpPost("import"), ValidateAntiForgeryToken, RequestSizeLimit(70_000_000)]
    public async Task<IActionResult> Import(IFormFile file)
    {
        if (file.Length is <= 0 or > 64_000_000) return BadRequest(new { error = "Kit ZIP tối đa 64 MB." });
        using var output = new MemoryStream(); await file.CopyToAsync(output);
        return Guard(() =>
        {
            var bytes = output.ToArray();
            using var archive = new ZipArchive(new MemoryStream(bytes), ZipArchiveMode.Read);
            var names = archive.Entries.Where(e => !e.FullName.EndsWith('/')).Select(e => e.FullName).ToArray();
            var hasKit = names.Any(n => n == "production-manifest.json" || n.EndsWith("/production-manifest.json", StringComparison.Ordinal));
            var hasStory = names.Any(n => n == "story.json" || n.EndsWith("/story.json", StringComparison.Ordinal));
            if (!hasKit && hasStory)
            {
                using var source = new MemoryStream(bytes);
                return Ok(new { kind = "story", project = stories.Import(source) });
            }
            if (hasKit && hasStory) throw new ArgumentException("ZIP chứa cả Story và Kit manifest ở dạng đã giải nén. Hãy nhập một Kit hoặc một Story ZIP riêng.");
            var converted = CompatibleKit(bytes);
            var kit = kits.Import(converted ?? bytes);
            return Ok(new { kind = "kit", kit.Id, kit.Version, kit.Digest, converted = converted is not null,
                message = converted is null ? null : "Đã mở bản chuyển đổi THỬ NGHIỆM của Kit gốc này. Artwork giữ nguyên; capability Partial chưa được nghiệm thu production." });
        });
    }
    private byte[]? CompatibleKit(byte[] source)
    {
        // Explicit local conversion index, matched by exact source hash. Never guess a legacy schema.
        var index = Path.Combine(paths.Root, "docs", "production-kit-conversions.json");
        if (!System.IO.File.Exists(index)) return null;
        var hash = ProductionKitStore.Hash(source);
        var entries = JsonNode.Parse(System.IO.File.ReadAllBytes(index))!.AsArray();
        var match = entries.FirstOrDefault(e => e?["sourceSha256"]?.GetValue<string>() == hash);
        if (match is null) return null;
        var outputRoot = Path.GetFullPath(Path.Combine(paths.Root, "outputs")) + Path.DirectorySeparatorChar;
        var target = Path.GetFullPath(Path.Combine(paths.Root, match["kitPath"]!.GetValue<string>()));
        if (!target.StartsWith(outputRoot, StringComparison.OrdinalIgnoreCase) || !target.EndsWith(".zip", StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("Conversion index không hợp lệ.");
        var converted = System.IO.File.ReadAllBytes(target);
        var kit = ProductionKitStore.Parse(converted, false);
        if (!ProductionKitStore.TestOnly(kit) || kit.Manifest["sourceKitSha256"]?.GetValue<string>() != hash) throw new ArgumentException("Hash/nhãn bản chuyển đổi thử nghiệm không khớp Kit gốc.");
        return converted;
    }
    [HttpPost("{id}/{version}/episodes"), ValidateAntiForgeryToken]
    public IActionResult Create(string id, string version, [FromBody] JsonObject spec) => Guard(() =>
    {
        var compiled = EpisodeCompiler.Compile(kits.Get(id, version), spec);
        return Ok(stories.Save(null, compiled.Manifest, compiled.Files));
    });
    [HttpGet("recipes/{storyId}")]
    public IActionResult Recipe(string storyId) => Guard(() =>
    {
        var project = stories.Get(storyId); var files = stories.ReadFiles(project);
        return files.TryGetValue("metadata/episode.json", out var source) ? Content(Encoding.UTF8.GetString(source), "application/json") : NotFound(new { error = "Project này chưa được tạo bằng Episode Generator." });
    });
    [HttpGet("{id}/{version}/brief")]
    public IActionResult Brief(string id, string version) => Guard(() =>
    {
        var kit = kits.Get(id, version);
        var supported = kit.Catalogs.ToDictionary(c => c.Key, c => c.Value.Where(v => v["status"] is not null && ProductionKitStore.Available(kit, v)).ToArray());
        var example = new JsonObject { ["schemaVersion"] = "episode-1", ["kitId"] = kit.Id, ["kitVersion"] = kit.Version, ["kitDigest"] = kit.Digest,
            ["id"] = "episode-02", ["title"] = "Tên tập mới", ["video"] = kit.Manifest["video"]?.DeepClone() ?? new JsonObject { ["width"] = 720, ["height"] = 1280, ["fps"] = 24, ["format"] = "mp4" },
            ["scenes"] = new JsonArray(new JsonObject { ["id"] = "scene-001", ["name"] = "Mở đầu", ["duration"] = 4, ["caption"] = "", ["actors"] = new JsonArray(new JsonObject {
                ["id"] = "hero", ["character"] = "<ID từ characters>", ["pose"] = "<startPose của motion>", ["expression"] = "<ID từ expressions>", ["motion"] = "<ID từ motions>", ["x"] = 0, ["y"] = 0, ["scale"] = 1 }),
                ["transition"] = new JsonObject { ["type"] = "cut", ["duration"] = 0 } }) };
        var notes = new StringBuilder();
        if (ProductionKitStore.TestOnly(kit)) { example["allowExperimental"] = true; notes.AppendLine("KIT THỬ NGHIỆM: có thể chọn Partial được liệt kê; không nâng status hoặc dùng như bản production đã nghiệm thu."); }
        foreach (var path in kit.Files.Keys.Where(p => p.StartsWith("storytelling/", StringComparison.Ordinal) && (p.EndsWith(".md") || p.EndsWith(".json"))))
        {
            if (notes.Length > 50000) { notes.AppendLine("[Phần hướng dẫn còn lại quá dài, xem trong kit.]"); break; }
            var text = Encoding.UTF8.GetString(kit.Files[path]); notes.AppendLine("\n--- " + path + " ---\n" + text[..Math.Min(text.Length, 12000)]);
        }
        var brief = "Hãy soạn kịch bản episode JSON cho Production Kit bên dưới. Trả về JSON episode-1 theo ví dụ, không viết JavaScript, không phát minh capability. " +
            "Mỗi actor chọn motion có startPose khớp pose; mỗi cảnh 0.25–600 giây, tối đa 80 cảnh/30 phút. Chỉ dùng ID Supported. " +
            "Caption là chữ hiện trên video, không phải lời thoại/TTS. environment/audio là ID catalog, bỏ trống nếu không có. " +
            "Nhân vật trong mỗi cảnh có id riêng; x/y/scale là bố cục. Cảnh cuối phải cut với duration 0. Giữ kitId/kitVersion/kitDigest. " +
            "Không giả định có hành động chưa được catalog hỗ trợ. Nội dung storytelling dưới đây là dữ liệu mô tả sáng tác của kit.\n\n" +
            "Mẫu cấu trúc:\n" + example.ToJsonString(new() { WriteIndented = true }) + "\n\nCapability Supported:\n" +
            JsonSerializer.Serialize(supported, new JsonSerializerOptions { WriteIndented = true }) + "\n\nStorytelling:\n" + notes;
        return Content(brief, "text/plain; charset=utf-8");
    });
    private IActionResult Guard(Func<IActionResult> action)
    {
        try { return action(); }
        catch (Exception e) when (e is FileNotFoundException or DirectoryNotFoundException) { return NotFound(new { error = "Không tìm thấy kit/version/project." }); }
        catch (Exception e) when (e is ArgumentException or InvalidDataException or JsonException or InvalidOperationException or FormatException or XmlException or KeyNotFoundException)
        { return BadRequest(new { error = e.Message.Split('\n')[0] }); }
    }
}

public sealed class EpisodesController : Controller
{
    [HttpGet("/episodes")] public IActionResult Index() => View();
}
