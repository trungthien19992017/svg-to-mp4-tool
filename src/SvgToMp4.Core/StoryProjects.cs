using System.IO.Compression;
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using System.Xml;
using System.Xml.Linq;
using System.Globalization;

namespace SvgToMp4.Core;

public sealed record StoryProject(string Id, string Revision, string Title, string UpdatedAt, JsonObject Manifest, string[] Files);
public sealed record StorySave(JsonObject Manifest, Dictionary<string, string> Files);
public sealed record StoryRenderOptions(int Width, int Height, int Fps, int Crf = 18, string Preset = "veryfast");

public static class StoryValidation
{
    public const long MaxTotal = 128_000_000;
    public static readonly HashSet<string> Extensions = new(StringComparer.OrdinalIgnoreCase) { ".json", ".js", ".svg", ".html", ".css", ".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".m4a", ".ogg", ".ttf", ".woff2" };
    public static string SafePath(string value)
    {
        if (string.IsNullOrWhiteSpace(value) || value.Length > 200 || value.Contains('\\') || value.Contains(':') || value.Contains('%') || value.Contains('?') || value.Contains('#') || value.StartsWith('/') || value.Split('/').Any(s => s is "" or "." or ".." || s.EndsWith('.') || s.EndsWith(' ') || Regex.IsMatch(s, @"^(CON|PRN|AUX|NUL|COM\d|LPT\d)(\.|$)", RegexOptions.IgnoreCase)))
            throw new ArgumentException($"Đường dẫn không an toàn: {value}");
        if (!Regex.IsMatch(value, @"^[\p{L}\p{N}_ .\-/]+$") || !Extensions.Contains(Path.GetExtension(value))) throw new ArgumentException($"Loại file không được hỗ trợ: {value}");
        return value;
    }
    public static JsonObject Validate(JsonObject input, IReadOnlyDictionary<string, byte[]> files)
    {
        var m = (JsonObject)input.DeepClone();
        if ((string?)m["schemaVersion"] != "1.0") throw new ArgumentException("Chỉ hỗ trợ Story Project schemaVersion 1.0.");
        if (!Regex.IsMatch((string?)m["projectId"] ?? "", @"^[A-Za-z0-9_-]{1,80}$")) throw new ArgumentException("projectId cần 1–80 chữ, số, dấu gạch ngang hoặc gạch dưới.");
        if (string.IsNullOrWhiteSpace((string?)m["title"]) || ((string)m["title"]!).Length > 160) throw new ArgumentException("Story cần title, tối đa 160 ký tự.");
        var v = m["video"] as JsonObject ?? throw new ArgumentException("Thiếu video settings.");
        ValidateVideo(v["width"]?.GetValue<int>() ?? 0, v["height"]?.GetValue<int>() ?? 0, v["fps"]?.GetValue<int>() ?? 0);
        if ((string?)v["format"] is not (null or "mp4")) throw new ArgumentException("Chỉ hỗ trợ MP4.");
        if (m["render"] is JsonObject render)
        {
            var rw = Number(render, "width", 64, 3840, v["width"]!.GetValue<int>());
            var rh = Number(render, "height", 64, 3840, v["height"]!.GetValue<int>());
            var rf = Number(render, "fps", 24, 60, v["fps"]!.GetValue<int>());
            if (rw % 1 != 0 || rh % 1 != 0 || rf % 1 != 0) throw new ArgumentException("Render width/height/fps phải là số nguyên.");
            ValidateVideo((int)rw, (int)rh, (int)rf); Number(render, "crf", 10, 35, 18);
            if ((string?)render["preset"] is not (null or "ultrafast" or "veryfast" or "medium")) throw new ArgumentException("Render preset không hợp lệ.");
        }
        var scenes = m["scenes"] as JsonArray ?? throw new ArgumentException("Thiếu danh sách scenes.");
        if (scenes.Count is < 1 or > 80) throw new ArgumentException("Story cần 1–80 cảnh.");
        var assets = m["assets"] as JsonArray ?? new JsonArray();
        var ids = new HashSet<string>(StringComparer.Ordinal); var assetIds = new HashSet<string>(StringComparer.Ordinal);
        void Ref(string? path) { if (path is null || !files.ContainsKey(SafePath(path))) throw new ArgumentException($"Thiếu file được tham chiếu: {path}"); }
        foreach (var a in assets)
        {
            var id = (string?)a?["id"] ?? "";
            if (!Regex.IsMatch(id, @"^[A-Za-z0-9_-]{1,80}$") || !assetIds.Add(id)) throw new ArgumentException($"Asset ID không hợp lệ hoặc trùng: {id}");
            Ref((string?)a?["path"]);
        }
        double start = 0;
        for (var index = 0; index < scenes.Count; index++)
        {
            var s = scenes[index] as JsonObject ?? throw new ArgumentException("Scene phải là object.");
            var id = (string?)s["id"] ?? "";
            if (!Regex.IsMatch(id, @"^[A-Za-z0-9_-]{1,80}$") || !ids.Add(id)) throw new ArgumentException($"Scene ID không hợp lệ hoặc trùng: {id}");
            var duration = Number(s, "duration", .25, 600);
            var source = (string?)s["source"]; Ref(source);
            if (Path.GetExtension(source) is not ".js") throw new ArgumentException($"{id}: source phải là module .js export createScene(context).");
            var code = Encoding.UTF8.GetString(files[source!]);
            if (!Regex.IsMatch(code, @"export\s+(?:async\s+)?function\s+createScene\s*\(")) throw new ArgumentException($"{id}: thiếu export function createScene(context).");
            if (Regex.IsMatch(code, @"\b(?:Date\s*\.\s*now|Math\s*\.\s*random|setTimeout|setInterval|requestAnimationFrame|fetch|WebSocket|XMLHttpRequest|Worker|SharedWorker|eval)\s*\(")) throw new ArgumentException($"{id}: dùng thời gian, random, network hoặc code động ngoài contract. Dùng context.random() và timeline được seek.");
            if (Regex.IsMatch(code, @"\brepeat\s*:\s*-1\b")) throw new ArgumentException($"{id}: repeat phải hữu hạn.");
            foreach (var field in new[] { "html", "css" }) if (s[field] is not null) Ref((string?)s[field]);
            s["start"] = start;
            var transition = s["transition"] as JsonObject;
            var kind = (string?)transition?["type"] ?? "cut";
            if (kind is not ("cut" or "fade" or "slide")) throw new ArgumentException($"{id}: transition chỉ hỗ trợ cut, fade hoặc slide.");
            var overlap = kind == "cut" ? 0 : transition is null ? .5 : Number(transition, "duration", 0, 600, .5);
            if (!double.IsFinite(overlap) || overlap < 0 || overlap > duration / 2 || (index < scenes.Count - 1 && overlap > Number(scenes[index + 1]!.AsObject(), "duration", .25, 600) / 2)) throw new ArgumentException($"{id}: transition quá dài (tối đa nửa thời lượng của mỗi cảnh kề nhau).");
            if (index == scenes.Count - 1 && overlap != 0) throw new ArgumentException($"{id}: cảnh cuối không có transition đi ra.");
            start += duration - overlap;
        }
        if (start > 1800) throw new ArgumentException("Story tối đa 30 phút.");
        m["duration"] = start;
        var characters = m["characters"] as JsonArray ?? new JsonArray(); var characterIds = new HashSet<string>();
        foreach (var character in characters)
        {
            var id = (string?)character?["id"] ?? "";
            if (!Regex.IsMatch(id, @"^[A-Za-z0-9_-]{1,80}$") || !characterIds.Add(id) || !assetIds.Contains((string?)character?["assetId"] ?? "")) throw new ArgumentException($"Nhân vật {id}: ID trùng hoặc assetId chưa được khai báo.");
        }
        foreach (var scene in scenes)
        {
            foreach (var character in scene?["characters"] as JsonArray ?? new JsonArray()) if (!characterIds.Contains((string?)character ?? "")) throw new ArgumentException($"{scene?["id"]}: tham chiếu nhân vật chưa khai báo.");
            if (scene?["background"] is { } background && !assetIds.Contains((string?)background ?? "")) throw new ArgumentException($"{scene["id"]}: tham chiếu background chưa khai báo.");
        }
        foreach (var track in m["audio"] as JsonArray ?? new JsonArray())
        {
            var a = track as JsonObject ?? throw new ArgumentException("Audio track phải là object.");
            var asset = assets.FirstOrDefault(x => (string?)x?["id"] == (string?)a["assetId"]);
            if (asset is null || !new[] { ".wav", ".mp3", ".m4a", ".ogg" }.Contains(Path.GetExtension((string?)asset["path"]))) throw new ArgumentException("Audio track cần asset âm thanh local hợp lệ.");
            Number(a, "start", 0, 1800, 0); Number(a, "offset", 0, 1800, 0); var length = Number(a, "duration", .01, 1800);
            Number(a, "volume", 0, 1, 1); Number(a, "fadeIn", 0, length, 0); Number(a, "fadeOut", 0, length, 0);
            if (a["sceneId"] is not null && !ids.Contains((string)a["sceneId"]!)) throw new ArgumentException("Audio tham chiếu scene không tồn tại.");
        }
        foreach (var (path, content) in files)
        {
            SafePath(path);
            if (content.LongLength > 16_000_000) throw new ArgumentException($"File quá lớn: {path}");
            var extension = Path.GetExtension(path).ToLowerInvariant();
            if (extension == ".svg") ValidateSvg(content, path);
            if (extension == ".json") JsonNode.Parse(content);
            if (extension is ".js" or ".css" or ".html" or ".svg") _ = new UTF8Encoding(false, true).GetString(content);
            if (extension == ".js")
            {
                var code = Encoding.UTF8.GetString(content);
                foreach (Match match in Regex.Matches(code, """(?:from\s*|import\s*\(\s*|import\s*)['"]([^'"]+)['"]"""))
                {
                    var relative = match.Groups[1].Value;
                    if (!relative.StartsWith('.')) throw new ArgumentException($"{path}: chỉ import module local tương đối; GSAP có sẵn trong context.");
                    var basis = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "story-module-root"));
                    var resolved = Path.GetFullPath(Path.Combine(basis, Path.GetDirectoryName(path)!, relative));
                    if (!resolved.StartsWith(basis + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) || !files.ContainsKey(Path.GetRelativePath(basis, resolved).Replace('\\', '/'))) throw new ArgumentException($"{path}: thiếu hoặc không cho phép import {relative}.");
                }
            }
            bool Starts(params byte[] prefix) => content.AsSpan().StartsWith(prefix);
            bool At(int offset, string text) => content.Length >= offset + text.Length && Encoding.ASCII.GetString(content, offset, text.Length) == text;
            var signature = extension switch
            {
                ".png" => Starts(137, 80, 78, 71, 13, 10, 26, 10), ".jpg" or ".jpeg" => Starts(255, 216, 255),
                ".webp" => At(0, "RIFF") && At(8, "WEBP"), ".wav" => At(0, "RIFF") && At(8, "WAVE"),
                ".mp3" => At(0, "ID3") || (content.Length > 2 && content[0] == 255 && (content[1] & 224) == 224),
                ".ogg" => At(0, "OggS"), ".m4a" => At(4, "ftyp"), ".woff2" => At(0, "wOF2"),
                ".ttf" => Starts(0, 1, 0, 0) || At(0, "OTTO"), _ => true
            };
            if (!signature) throw new ArgumentException($"{path}: nội dung không khớp phần mở rộng.");
        }
        return m;
    }
    public static void ValidateVideo(int width, int height, int fps)
    {
        if (width is < 64 or > 3840 || height is < 64 or > 3840 || width % 2 != 0 || height % 2 != 0 || (long)width * height > 8_294_400 || fps is not (24 or 30 or 60)) throw new ArgumentException("Video cần kích thước chẵn từ 64 đến 3840 pixel, tối đa 4K, FPS 24/30/60.");
    }
    public static double Number(JsonObject o, string key, double min, double max, double? fallback = null)
    {
        double n;
        if (o[key] is null) n = fallback ?? throw new ArgumentException($"Thiếu {key}.");
        else if (!double.TryParse(o[key]!.ToJsonString(), NumberStyles.Float, CultureInfo.InvariantCulture, out n)) throw new ArgumentException($"{key} phải là số.");
        if (!double.IsFinite(n) || n < min || n > max) throw new ArgumentException($"{key} cần nằm trong [{min}, {max}]."); return n;
    }
    private static void ValidateSvg(byte[] bytes, string path)
    {
        using var text = new MemoryStream(bytes);
        using var reader = XmlReader.Create(text, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null, MaxCharactersInDocument = 16_000_000 });
        var svg = XDocument.Load(reader);
        if (svg.Root?.Name.LocalName != "svg") throw new ArgumentException($"{path}: không phải SVG.");
        foreach (var e in svg.Descendants())
        {
            if (e.Name.LocalName is "script" or "foreignObject" || e.Attributes().Where(a => !a.IsNamespaceDeclaration).Any(a => a.Name.LocalName.StartsWith("on", StringComparison.OrdinalIgnoreCase) || Regex.IsMatch(a.Value, @"(?:https?|file|javascript):|@import", RegexOptions.IgnoreCase) || (a.Name.LocalName == "href" && !a.Value.StartsWith('#')))) throw new ArgumentException($"{path}: SVG chứa script hoặc tài nguyên ngoài. Đặt animation trong scene .js và khai báo asset local.");
        }
    }
}

public sealed class StoryStore(AppPaths paths)
{
    private readonly object gate = new();
    private string Root => Path.Combine(paths.Data, "stories");
    public IReadOnlyList<StoryProject> List()
    {
        Directory.CreateDirectory(Root);
        return Directory.GetDirectories(Root).Select(p => { try { return Get(Path.GetFileName(p)); } catch { return null; } }).OfType<StoryProject>().OrderByDescending(p => p.UpdatedAt).ToArray();
    }
    public string RevisionPath(string id, string revision)
    {
        if (!Guid.TryParseExact(id, "N", out _) || !Guid.TryParseExact(revision, "N", out _)) throw new ArgumentException("Mã project/revision không hợp lệ.");
        return Path.Combine(Root, id, "revisions", revision);
    }
    public StoryProject Get(string id)
    {
        if (!Guid.TryParseExact(id, "N", out _)) throw new ArgumentException("Mã project không hợp lệ.");
        var p = JsonNode.Parse(File.ReadAllText(Path.Combine(Root, id, "project.json")))!.AsObject();
        var revision = (string)p["revision"]!; var dir = RevisionPath(id, revision);
        var manifest = JsonNode.Parse(File.ReadAllText(Path.Combine(dir, "story.json")))!.AsObject();
        return new(id, revision, (string)manifest["title"]!, (string)p["updatedAt"]!, manifest, Directory.GetFiles(dir, "*", SearchOption.AllDirectories).Select(f => Path.GetRelativePath(dir, f).Replace('\\', '/')).Order().ToArray());
    }
    public StoryProject Save(string? id, JsonObject manifest, Dictionary<string, byte[]> files)
    {
        lock (gate)
        {
            var normalized = StoryValidation.Validate(manifest, files);
            foreach (var (name, source) in files.Where(f => Path.GetExtension(f.Key).Equals(".js", StringComparison.OrdinalIgnoreCase))) StorySyntax.Check(name, source);
            if (files.Count > 512 || files.Values.Sum(b => (long)b.Length) > StoryValidation.MaxTotal) throw new ArgumentException("Project vượt quá 512 file hoặc 128 MB.");
            id ??= Guid.NewGuid().ToString("N"); var revision = Guid.NewGuid().ToString("N"); var directory = RevisionPath(id, revision);
            Directory.CreateDirectory(directory);
            foreach (var (name, bytes) in files)
            {
                if (name == "story.json") continue;
                var file = Path.Combine(directory, StoryValidation.SafePath(name)); Directory.CreateDirectory(Path.GetDirectoryName(file)!); File.WriteAllBytes(file, bytes);
            }
            File.WriteAllText(Path.Combine(directory, "story.json"), normalized.ToJsonString(new() { WriteIndented = true }));
            var pointer = Path.Combine(Root, id, "project.json");
            File.WriteAllText(pointer + ".tmp", new JsonObject { ["revision"] = revision, ["updatedAt"] = DateTimeOffset.UtcNow.ToString("O") }.ToJsonString());
            File.Move(pointer + ".tmp", pointer, true); return Get(id);
        }
    }
    public Dictionary<string, byte[]> ReadFiles(StoryProject project) => project.Files.ToDictionary(f => f, f => File.ReadAllBytes(Path.Combine(RevisionPath(project.Id, project.Revision), StoryValidation.SafePath(f))), StringComparer.OrdinalIgnoreCase);
    public StoryProject SaveRevision(string id, string revision, StorySave request)
    {
        lock (gate)
        {
            var current = Get(id);
            if (current.Revision != revision) throw new StoryConflictException();
            var files = ReadFiles(current);
            foreach (var (name, text) in request.Files) files[StoryValidation.SafePath(name)] = Encoding.UTF8.GetBytes(text);
            return Save(id, request.Manifest, files);
        }
    }
    public StoryProject Import(Stream stream)
    {
        using var archive = new ZipArchive(stream, ZipArchiveMode.Read, true);
        if (archive.Entries.Count > 600) throw new ArgumentException("ZIP có quá nhiều file.");
        var entries = archive.Entries.Where(e => !e.FullName.EndsWith('/')).ToArray();
        var manifestName = entries.Where(e => e.FullName == "story.json" || e.FullName.EndsWith("/story.json")).Select(e => e.FullName).ToArray();
        if (manifestName.Length != 1) throw new ArgumentException("ZIP cần đúng một story.json.");
        var prefix = manifestName[0][..^"story.json".Length]; var files = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase); long total = 0;
        foreach (var entry in entries)
        {
            if (!entry.FullName.StartsWith(prefix, StringComparison.Ordinal) || ((entry.ExternalAttributes >> 16) & 0xF000) == 0xA000) throw new ArgumentException("ZIP có đường dẫn ngoài project hoặc symlink.");
            var name = StoryValidation.SafePath(entry.FullName[prefix.Length..]);
            total += entry.Length;
            if (entry.Length > 16_000_000 || total > StoryValidation.MaxTotal || entry.Length / Math.Max(1.0, entry.CompressedLength) > 200) throw new ArgumentException("ZIP quá lớn hoặc tỷ lệ nén không an toàn.");
            using var input = entry.Open(); using var output = new MemoryStream();
            var buffer = new byte[65536]; int read;
            while ((read = input.Read(buffer)) > 0) { if (output.Length + read > entry.Length || output.Length + read > 16_000_000) throw new ArgumentException("ZIP vượt kích thước khai báo."); output.Write(buffer, 0, read); }
            if (output.Length != entry.Length || !files.TryAdd(name, output.ToArray())) throw new ArgumentException("ZIP trùng đường dẫn hoặc kích thước file sai.");
        }
        return Save(null, JsonNode.Parse(files["story.json"])!.AsObject(), files);
    }
    public byte[] Export(StoryProject project)
    {
        using var output = new MemoryStream();
        using (var zip = new ZipArchive(output, ZipArchiveMode.Create, true))
            foreach (var (name, bytes) in ReadFiles(project)) { using var file = zip.CreateEntry(name, CompressionLevel.Fastest).Open(); file.Write(bytes); }
        return output.ToArray();
    }
}

public sealed class StoryConflictException() : Exception("Project đã thay đổi ở cửa sổ khác. Mở lại trước khi lưu để tránh ghi đè.");
