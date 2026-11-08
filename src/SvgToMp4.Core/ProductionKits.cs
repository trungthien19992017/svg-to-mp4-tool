using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using System.Xml;
using System.Xml.Linq;

namespace SvgToMp4.Core;

public sealed record ProductionKit(string Id, string Version, string Digest, JsonObject Manifest,
    JsonObject Rig, Dictionary<string, JsonObject[]> Catalogs, Dictionary<string, byte[]> Files);

/// <summary>Immutable, local Production Kit registry. Independent of the Story renderer.</summary>
public sealed class ProductionKitStore(AppPaths paths)
{
    private readonly object gate = new();
    private string Root => Path.Combine(paths.Data, "production-kits");
    public static string Hash(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
    public static string Identifier(string value)
    {
        if (!Regex.IsMatch(value, "^[A-Za-z0-9_-]{1,80}$")) throw new ArgumentException("ID cần 1–80 chữ, số, _ hoặc -.");
        return value;
    }
    public static string Version(string value)
    {
        if (!Regex.IsMatch(value, @"^\d{1,8}\.\d{1,8}\.\d{1,8}$")) throw new ArgumentException("Version phải có dạng major.minor.patch.");
        return value;
    }
    private string KitPath(string id, string version) => Path.Combine(Root, Identifier(id), Version(version) + ".zip");
    public IEnumerable<object> List()
    {
        if (!Directory.Exists(Root)) return [];
        return Directory.GetFiles(Root, "*.zip", SearchOption.AllDirectories).Select(path =>
        {
            var kit = Parse(File.ReadAllBytes(path), false);
            return (object)new { kit.Id, kit.Version, kit.Digest, title = kit.Manifest["title"]?.GetValue<string>() ?? kit.Id,
                demo = kit.Manifest["demo"]?.GetValue<bool>() ?? kit.Manifest["schemaVersion"]?.GetValue<string>() == "demo-1" };
        }).ToArray();
    }
    public ProductionKit Get(string id, string version) => Parse(File.ReadAllBytes(KitPath(id, version)), false);
    public ProductionKit Import(byte[] bytes)
    {
        var kit = Parse(bytes);
        lock (gate)
        {
            var path = KitPath(kit.Id, kit.Version);
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            if (File.Exists(path))
            {
                if (Hash(File.ReadAllBytes(path)) == kit.Digest) return kit;
                throw new ArgumentException("Kit/version đã phát hành có nội dung khác. Hãy tăng version, không ghi đè.");
            }
            foreach (var older in Directory.GetFiles(Path.GetDirectoryName(path)!, "*.zip"))
            {
                var previous = Parse(File.ReadAllBytes(older), false);
                if (Text(previous.Rig, "version") == Text(kit.Rig, "version") && previous.Rig.ToJsonString() != kit.Rig.ToJsonString())
                    throw new ArgumentException("Rig thay đổi nhưng giữ nguyên rig version. Cần tăng rig version và migration capability.");
            }
            var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try { File.WriteAllBytes(temporary, bytes); File.Move(temporary, path); }
            finally { if (File.Exists(temporary)) File.Delete(temporary); }
        }
        return kit;
    }
    public static string Text(JsonObject value, string key) => value[key]?.GetValue<string>() ?? throw new ArgumentException("Thiếu " + key);
    public static bool TestOnly(ProductionKit kit) => kit.Manifest["testOnly"]?.GetValue<bool>() == true;
    public static bool Available(ProductionKit kit, JsonObject capability) => Text(capability, "status") == "Supported" || (TestOnly(kit) && Text(capability, "status") == "Partial");
    public static string ExpressionNode(JsonObject expression, string characterId) => Identifier(expression["bindings"]?[characterId]?.GetValue<string>() ?? Text(expression, "nodeId"));
    public static JsonObject Object(JsonNode? node, string label) => node as JsonObject ?? throw new ArgumentException(label + " phải là object.");
    public static JsonArray Array(JsonNode? node, string label) => node as JsonArray ?? throw new ArgumentException(label + " phải là array.");
    public static ProductionKit Parse(byte[] bytes, bool checkSyntax = true)
    {
        if (bytes.Length is < 1 or > 64_000_000) throw new ArgumentException("Kit ZIP tối đa 64 MB.");
        using var stream = new MemoryStream(bytes);
        using var archive = new ZipArchive(stream, ZipArchiveMode.Read);
        if (archive.Entries.Count > 600) throw new ArgumentException("Kit tối đa 600 ZIP entries.");
        var entries = archive.Entries.Where(e => !e.FullName.EndsWith('/')).ToArray();
        var roots = entries.Where(e => e.FullName == "production-manifest.json" || e.FullName.EndsWith("/production-manifest.json", StringComparison.Ordinal)).ToArray();
        if (roots.Length != 1) throw new ArgumentException("ZIP Kit cần đúng một production-manifest.json. Nếu đây là tập đã biên dịch, nhập bằng Import ZIP trong Storyboard.");
        var prefix = roots[0].FullName[..^"production-manifest.json".Length];
        var files = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase); long total = 0;
        foreach (var entry in entries)
        {
            if (!entry.FullName.StartsWith(prefix, StringComparison.Ordinal) || ((entry.ExternalAttributes >> 16) & 0xF000) == 0xA000)
                throw new ArgumentException("ZIP chứa symlink hoặc file ngoài kit root.");
            var name = SafeKitPath(entry.FullName[prefix.Length..]); total += entry.Length;
            if (entry.Length > 16_000_000 || total > 128_000_000 || entry.Length / Math.Max(1.0, entry.CompressedLength) > 200)
                throw new ArgumentException("Kit vượt giới hạn kích thước/tỷ lệ nén.");
            using var input = entry.Open(); using var output = new MemoryStream(); var buffer = new byte[65536]; int read;
            while ((read = input.Read(buffer)) > 0)
            {
                if (output.Length + read > entry.Length || output.Length + read > 16_000_000) throw new ArgumentException("ZIP vượt kích thước khai báo.");
                output.Write(buffer, 0, read);
            }
            if (output.Length != entry.Length || !files.TryAdd(name, output.ToArray())) throw new ArgumentException("ZIP trùng đường dẫn/kích thước sai.");
        }
        JsonObject Read(string path) => Object(JsonNode.Parse(ReadFile(files, path)), path);
        var manifest = Read("production-manifest.json");
        if (Text(manifest, "schemaVersion") is not ("production-1" or "demo-1")) throw new ArgumentException("Đây là Kit nguồn chưa được chuyển sang profile production-1. Dùng Kit chuyển đổi tương ứng; không đổi riêng schemaVersion vì rig/catalog cũng cần ánh xạ.");
        var id = Identifier(Text(manifest, "kitId")); var version = Version(Text(manifest, "version"));
        var rig = Read(Text(manifest, "rig")); var rigVersion = Identifier(Text(rig, "version"));
        if (Text(manifest, "rigVersion") != rigVersion) throw new ArgumentException("Rig version không khớp; cần migration.");
        var joints = Object(rig["joints"], "rig.joints");
        if (joints.Count is < 1 or > 100) throw new ArgumentException("Rig cần 1–100 joints.");
        var jointIds = new HashSet<string>();
        foreach (var (joint, node) in joints)
        {
            Identifier(joint); var binding = Object(node, joint); var nodeId = Identifier(Text(binding, "nodeId"));
            if (!jointIds.Add(nodeId)) throw new ArgumentException("Hai joints không được ghi đè cùng SVG node.");
            Point(binding["pivot"], joint + ".pivot");
            if (binding["parent"] is { } parent && (!joints.ContainsKey(parent.GetValue<string>()) || parent.GetValue<string>() == joint)) throw new ArgumentException("Rig parent không tồn tại hoặc tự tham chiếu.");
        }
        foreach (var joint in joints.Select(x => x.Key))
        {
            var chain = new HashSet<string>(); string? current = joint;
            while (current is not null)
            {
                if (!chain.Add(current)) throw new ArgumentException("Rig parent tạo chu trình.");
                current = joints[current]?["parent"]?.GetValue<string>();
            }
        }
        var anchors = Object(rig["anchors"] ?? new JsonObject(), "anchors");
        foreach (var (name, point) in anchors) { Identifier(name); Point(point, name); }
        var catalogs = new Dictionary<string, JsonObject[]>(); var bindings = Object(manifest["catalogs"], "catalogs");
        foreach (var kind in new[] { "characters", "poses", "expressions", "motions", "environments", "audio", "templates" })
        {
            if (bindings[kind] is null)
            {
                if (kind is "characters" or "poses" or "expressions" or "motions") throw new ArgumentException("Thiếu catalog " + kind);
                catalogs[kind] = []; continue;
            }
            var records = Array(JsonNode.Parse(ReadFile(files, Text(bindings, kind))), kind).Select(n => Object(n, kind)).ToArray();
            var ids = new HashSet<string>();
            foreach (var record in records)
            {
                var name = Identifier(Text(record, "id")); if (!ids.Add(name)) throw new ArgumentException("Catalog trùng ID " + name);
                if (kind != "templates" && Text(record, "status") is not ("Supported" or "Partial" or "Unavailable" or "Unsupported")) throw new ArgumentException("QA status không hợp lệ: " + name);
                if (kind is "poses" or "expressions" or "motions")
                    if (Text(record, "rigVersion") != rigVersion) throw new ArgumentException("Capability " + name + " thay đổi rig: cần migration.");
            }
            catalogs[kind] = records;
        }
        foreach (var pose in catalogs["poses"])
            foreach (var (joint, angle) in Object(pose["rotations"], "pose.rotations"))
            {
                if (!joints.ContainsKey(joint)) throw new ArgumentException("Pose yêu cầu joint không tồn tại: " + joint);
                Finite(angle, -360, 360, "pose rotation");
            }
        var svgDocuments = new Dictionary<string, XDocument>();
        foreach (var expression in catalogs["expressions"])
        {
            if (expression["nodeId"] is not null) Identifier(Text(expression, "nodeId"));
            if (expression["bindings"] is JsonObject expressionBindings) foreach (var (character, value) in expressionBindings) { Identifier(character); Identifier(value!.GetValue<string>()); }
        }
        foreach (var (path, data) in files)
        {
            var ext = Path.GetExtension(path).ToLowerInvariant();
            if (ext == ".json") JsonNode.Parse(data);
            if (ext is ".js" or ".json" or ".md" or ".svg") _ = new UTF8Encoding(false, true).GetString(data);
            if (ext == ".svg") svgDocuments[path] = Svg(data, path);
            if (ext == ".js" && checkSyntax) StorySyntax.Check(path, data);
            if (ext == ".js")
            {
                var code = Encoding.UTF8.GetString(data);
                if (Regex.IsMatch(code, @"\b(?:Date\s*\.\s*now|Math\s*\.\s*random|setTimeout|setInterval|requestAnimationFrame|fetch|WebSocket|XMLHttpRequest|Worker|SharedWorker|eval)\s*\(") || Regex.IsMatch(code, @"\brepeat\s*:\s*-1\b"))
                    throw new ArgumentException(path + ": adapter vi phạm deterministic contract.");
                foreach (Match match in Regex.Matches(code, """(?:from\s*|import\s*\(\s*|import\s*)['"]([^'"]+)['"]"""))
                {
                    var relative = match.Groups[1].Value;
                    if (!relative.StartsWith('.')) throw new ArgumentException("Adapter chỉ import module tương đối trong kit.");
                    var basis = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "production-kit-module-root"));
                    var target = Path.GetFullPath(Path.Combine(basis, Path.GetDirectoryName(path)!, relative));
                    if (!target.StartsWith(basis + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) || !files.ContainsKey(Path.GetRelativePath(basis, target).Replace('\\', '/')))
                        throw new ArgumentException("Thiếu module dependency: " + relative);
                }
            }
        }
        foreach (var character in catalogs["characters"])
        {
            var path = Text(character, "artwork");
            if (!svgDocuments.TryGetValue(path, out var svg)) throw new ArgumentException("Artwork phải là SVG có trong kit.");
            var nodes = svg.Descendants().Where(n => n.Attribute("id") is not null).ToDictionary(n => n.Attribute("id")!.Value);
            foreach (var (joint, binding) in joints)
            {
                if (!nodes.TryGetValue(Text(binding!.AsObject(), "nodeId"), out var node)) throw new ArgumentException(path + ": thiếu joint " + joint);
                if (binding["parent"] is { } parent)
                {
                    var parentId = Text(joints[parent.GetValue<string>()]!.AsObject(), "nodeId");
                    if (!node.Ancestors().Any(n => (string?)n.Attribute("id") == parentId)) throw new ArgumentException(path + ": rig hierarchy không tương thích.");
                }
            }
            foreach (var expression in catalogs["expressions"].Where(e => Text(e, "status") == "Supported" || (manifest["testOnly"]?.GetValue<bool>() == true && Text(e, "status") == "Partial")))
                if (!nodes.ContainsKey(ExpressionNode(expression, Text(character, "id")))) throw new ArgumentException(path + ": thiếu expression node " + Text(expression, "id"));
        }
        foreach (var motion in catalogs["motions"])
        {
            var module = Text(motion, "module"); if (!module.EndsWith(".js", StringComparison.Ordinal)) throw new ArgumentException("Motion module cần đuôi .js.");
            var adapterCode = Encoding.UTF8.GetString(ReadFile(files, module));
            if (!Regex.IsMatch(adapterCode, @"export\s+function\s+evaluate\s*\(")) throw new ArgumentException(module + ": cần export function evaluate(t, duration) đồng bộ.");
            Finite(motion["duration"], .25, 600, "motion.duration");
            foreach (var key in new[] { "startPose", "endPose" })
                if (!catalogs["poses"].Any(p => Text(p, "id") == Text(motion, key))) throw new ArgumentException("Motion thiếu " + key);
            foreach (var joint in Array(motion["requiredJoints"], "requiredJoints")) if (!joints.ContainsKey(joint!.GetValue<string>())) throw new ArgumentException("Motion thiếu joint.");
            foreach (var anchor in Array(motion["anchors"], "anchors")) if (!anchors.ContainsKey(anchor!.GetValue<string>())) throw new ArgumentException("Motion thiếu anchor.");
        }
        foreach (var environment in catalogs["environments"])
        {
            if (!svgDocuments.ContainsKey(Text(environment, "artwork"))) throw new ArgumentException("Environment cần SVG local.");
            if (environment["foregroundArtwork"] is not null && !svgDocuments.ContainsKey(Text(environment, "foregroundArtwork"))) throw new ArgumentException("Environment foreground cần SVG local.");
        }
        foreach (var audio in catalogs["audio"])
        {
            var path = Text(audio, "path"); ReadFile(files, path);
            if (Path.GetExtension(path) is not (".wav" or ".mp3" or ".m4a" or ".ogg")) throw new ArgumentException("Audio extension không hỗ trợ.");
            Finite(audio["duration"], .01, 1800, "audio.duration");
        }
        return new(id, version, Hash(bytes), manifest, rig, catalogs, files);
    }
    public static byte[] ReadFile(IReadOnlyDictionary<string, byte[]> files, string path)
    {
        SafeKitPath(path); return files.TryGetValue(path, out var data) ? data : throw new ArgumentException("Thiếu dependency: " + path);
    }
    private static string SafeKitPath(string path)
    {
        // Kit documentation/approved examples stay in the registry; only Story files enter episodes.
        var ext = Path.GetExtension(path).ToLowerInvariant();
        if (ext is ".md" or ".zip") StoryValidation.SafePath(path + ".json");
        else StoryValidation.SafePath(path);
        return path;
    }
    public static double Finite(JsonNode? node, double min, double max, string label)
    {
        if (node is null || !double.TryParse(node.ToJsonString(), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var n) || !double.IsFinite(n) || n < min || n > max)
            throw new ArgumentException(label + $" cần nằm trong [{min}, {max}].");
        return n;
    }
    private static void Point(JsonNode? node, string label)
    {
        var values = Array(node, label); if (values.Count != 2) throw new ArgumentException(label + " cần hai tọa độ.");
        foreach (var value in values) Finite(value, -100000, 100000, label);
    }
    private static XDocument Svg(byte[] bytes, string path)
    {
        using var stream = new MemoryStream(bytes);
        using var reader = XmlReader.Create(stream, new() { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null, MaxCharactersInDocument = 16_000_000 });
        var doc = XDocument.Load(reader);
        if (doc.Root?.Name != XName.Get("svg", "http://www.w3.org/2000/svg")) throw new ArgumentException(path + ": SVG root không hợp lệ.");
        var ids = new HashSet<string>(); var references = new List<string>();
        foreach (var node in doc.Descendants())
        {
            if (node.Name.NamespaceName != "http://www.w3.org/2000/svg" || node.Name.LocalName is not ("svg" or "g" or "path" or "rect" or "circle" or "ellipse" or "line" or "polyline" or "polygon" or "defs" or "clipPath" or "linearGradient" or "radialGradient" or "stop" or "title" or "desc"))
                throw new ArgumentException(path + ": SVG element chưa hỗ trợ: " + node.Name.LocalName + ".");
            if (node.Attribute("id") is { } id && !ids.Add(Identifier(id.Value))) throw new ArgumentException(path + ": trùng SVG ID.");
            foreach (var attribute in node.Attributes().Where(a => !a.IsNamespaceDeclaration))
            {
                var value = attribute.Value;
                if (attribute.Name.LocalName.StartsWith("on", StringComparison.OrdinalIgnoreCase) || Regex.IsMatch(value, @"(?:https?|data|file|javascript):|@import|\\", RegexOptions.IgnoreCase)) throw new ArgumentException(path + ": active/external SVG attribute.");
                if (attribute.Name.LocalName == "href")
                {
                    if (!value.StartsWith('#')) throw new ArgumentException(path + ": external href.");
                    references.Add(value[1..]);
                }
                var matches = Regex.Matches(value, @"url\(#([A-Za-z0-9_-]+)\)");
                if (Regex.Matches(value, @"url\s*\(", RegexOptions.IgnoreCase).Count != matches.Count) throw new ArgumentException(path + ": SVG URL chưa hỗ trợ.");
                references.AddRange(matches.Select(m => m.Groups[1].Value));
            }
        }
        if (references.Any(r => !ids.Contains(r))) throw new ArgumentException(path + ": SVG fragment dependency không tồn tại.");
        return doc;
    }
}
