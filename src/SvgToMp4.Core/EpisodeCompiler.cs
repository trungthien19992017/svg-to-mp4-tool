using System.Reflection;
using System.Text;
using System.Text.Json.Nodes;
using static SvgToMp4.Core.ProductionKitStore;

namespace SvgToMp4.Core;

public sealed record CompiledEpisode(JsonObject Manifest, Dictionary<string, byte[]> Files);

/// <summary>Catalog-driven compiler. Emits ordinary self-contained Story v1 projects.</summary>
public static class EpisodeCompiler
{
    public static byte[] Runtime()
    {
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("SvgToMp4.Core.ProductionRuntime.js")!;
        using var output = new MemoryStream(); stream.CopyTo(output); return output.ToArray();
    }
    public static JsonObject Capability(ProductionKit kit, string kind, string id)
    {
        var record = kit.Catalogs[kind].SingleOrDefault(p => Text(p, "id") == id);
        if (record is null || !Available(kit, record)) throw new ArgumentException(kind + "/" + id + " chưa Supported. Không tự thay bằng capability khác.");
        return record;
    }
    public static CompiledEpisode Compile(ProductionKit kit, JsonObject input)
    {
        var spec = (JsonObject)input.DeepClone();
        if (Text(spec, "schemaVersion") != "episode-1") throw new ArgumentException("Kịch bản cần schemaVersion episode-1.");
        if (TestOnly(kit) && spec["allowExperimental"]?.GetValue<bool>() != true) throw new ArgumentException("Kit thử nghiệm cần allowExperimental=true; không dùng như kit production đã nghiệm thu.");
        if (Text(spec, "kitId") != kit.Id || Text(spec, "kitVersion") != kit.Version) throw new ArgumentException("Kit khóa trong kịch bản không khớp.");
        if (spec["kitDigest"] is not null && Text(spec, "kitDigest") != kit.Digest) throw new ArgumentException("Hash kit thay đổi; hãy chọn lại kit.");
        spec["kitDigest"] = kit.Digest;
        var id = Identifier(Text(spec, "id")); var title = Text(spec, "title");
        if (string.IsNullOrWhiteSpace(title) || title.Length > 160) throw new ArgumentException("Tên tập cần 1–160 ký tự.");
        var video = Object(spec["video"] ?? kit.Manifest["video"]?.DeepClone() ?? new JsonObject { ["width"] = 720, ["height"] = 1280, ["fps"] = 24, ["format"] = "mp4" }, "video");
        StoryValidation.ValidateVideo(video["width"]!.GetValue<int>(), video["height"]!.GetValue<int>(), video["fps"]!.GetValue<int>());
        var sourceScenes = Array(spec["scenes"], "scenes");
        if (sourceScenes.Count is < 1 or > 80) throw new ArgumentException("Kịch bản cần 1–80 cảnh.");
        var files = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase) { ["modules/production-runtime.js"] = Runtime() };
        // Preserve adapter-relative imports inside a private kit subtree.
        foreach (var (path, bytes) in kit.Files.Where(f => f.Key.EndsWith(".js", StringComparison.Ordinal))) files["kit/" + path] = bytes;
        var assets = new JsonArray(); var scenes = new JsonArray(); var tracks = new JsonArray();
        var assetPaths = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        string Asset(string path)
        {
            if (assetPaths.TryGetValue(path, out var existing)) return existing;
            var assetId = "asset-" + assetPaths.Count; assetPaths[path] = assetId;
            var target = "kit/" + path; files[target] = ReadFile(kit.Files, path);
            assets.Add(new JsonObject { ["id"] = assetId, ["path"] = target }); return assetId;
        }
        var sceneIds = new HashSet<string>();
        foreach (var item in sourceScenes)
        {
            var scene = Object(item, "scene"); var sceneId = Identifier(Text(scene, "id"));
            if (!sceneIds.Add(sceneId)) throw new ArgumentException("Trùng scene ID.");
            var duration = Finite(scene["duration"], .25, 600, "scene.duration");
            var actors = Array(scene["actors"], "scene.actors");
            if (actors.Count is < 1 or > 8) throw new ArgumentException("Mỗi cảnh cần 1–8 nhân vật.");
            var configs = new JsonArray(); var imports = new StringBuilder(); var adapters = new List<string>(); var actorIds = new HashSet<string>();
            foreach (var actorNode in actors)
            {
                var actor = Object(actorNode, "actor"); var actorId = Identifier(Text(actor, "id"));
                if (!actorIds.Add(actorId)) throw new ArgumentException("Trùng actor ID trong cảnh.");
                var character = Capability(kit, "characters", Text(actor, "character"));
                var pose = Capability(kit, "poses", Text(actor, "pose"));
                var expression = Capability(kit, "expressions", Text(actor, "expression"));
                var boundExpression = (JsonObject)expression.DeepClone();
                boundExpression["nodeId"] = ExpressionNode(expression, Text(character, "id"));
                var motionId = actor["motion"]?.GetValue<string>() ?? "";
                var motion = motionId.Length == 0 ? null : Capability(kit, "motions", motionId);
                if (motion is not null && Text(motion, "startPose") != Text(pose, "id")) throw new ArgumentException("Motion " + Text(motion, "id") + " cần start pose " + Text(motion, "startPose"));
                if (motion is not null) Capability(kit, "poses", Text(motion, "endPose"));
                var name = "adapter" + adapters.Count; adapters.Add(name);
                if (motion is null) imports.Append("const ").Append(name).AppendLine(" = holdPose;");
                else imports.Append("import {evaluate as ").Append(name).Append("} from ").Append(System.Text.Json.JsonSerializer.Serialize("../kit/" + Text(motion, "module"))).AppendLine(";");
                configs.Add(new JsonObject { ["id"] = actorId, ["assetId"] = Asset(Text(character, "artwork")),
                    ["pose"] = pose.DeepClone(), ["expression"] = boundExpression,
                    ["expressionNodes"] = new JsonArray(kit.Catalogs["expressions"].Where(e => e["nodeId"] is not null || e["bindings"]?[Text(character, "id")] is not null).Select(e => (JsonNode?)JsonValue.Create(ExpressionNode(e, Text(character, "id")))).DistinctBy(n => n!.GetValue<string>()).ToArray()),
                    ["motionDuration"] = motion?["duration"]?.DeepClone() ?? JsonValue.Create(duration),
                    ["x"] = Finite(actor["x"] ?? JsonValue.Create(0), -10000, 10000, "actor.x"),
                    ["y"] = Finite(actor["y"] ?? JsonValue.Create(0), -10000, 10000, "actor.y"),
                    ["scale"] = Finite(actor["scale"] ?? JsonValue.Create(1), .05, 8, "actor.scale") });
            }
            string? background = null, foreground = null;
            if (scene["environment"] is { } environment && !string.IsNullOrEmpty(environment.GetValue<string>()))
            {
                var environmentRecord = Capability(kit, "environments", environment.GetValue<string>());
                background = Asset(Text(environmentRecord, "artwork"));
                if (environmentRecord["foregroundArtwork"] is not null) foreground = Asset(Text(environmentRecord, "foregroundArtwork"));
            }
            var caption = scene["caption"]?.GetValue<string>() ?? "";
            if (caption.Length > 500) throw new ArgumentException("Caption tối đa 500 ký tự.");
            var config = new JsonObject { ["duration"] = duration, ["rig"] = kit.Rig.DeepClone(), ["actors"] = configs,
                ["expressionNodes"] = new JsonArray(kit.Catalogs["expressions"].Where(e => e["nodeId"] is not null).Select(e => (JsonNode?)JsonValue.Create(Text(e, "nodeId"))).DistinctBy(n => n!.GetValue<string>()).ToArray()),
                ["background"] = background, ["foreground"] = foreground, ["caption"] = caption };
            var source = "scenes/" + sceneId + ".js";
            files[source] = Encoding.UTF8.GetBytes("import {createEpisodeScene,holdPose} from '../modules/production-runtime.js';\n" + imports +
                "export function createScene(context) {return createEpisodeScene(context," + config.ToJsonString() + ",[" + string.Join(',', adapters) + "]);}\n");
            scenes.Add(new JsonObject { ["id"] = sceneId, ["name"] = scene["name"]?.DeepClone() ?? JsonValue.Create(sceneId), ["source"] = source,
                ["duration"] = duration, ["transition"] = scene["transition"]?.DeepClone() ?? new JsonObject { ["type"] = "cut", ["duration"] = 0 } });
            if (scene["audio"] is { } audioNode && !string.IsNullOrEmpty(audioNode.GetValue<string>()))
            {
                var audio = Capability(kit, "audio", audioNode.GetValue<string>());
                tracks.Add(new JsonObject { ["assetId"] = Asset(Text(audio, "path")), ["sceneId"] = sceneId, ["start"] = 0,
                    ["duration"] = Math.Min(duration, audio["duration"]!.GetValue<double>()),
                    ["volume"] = Finite(scene["volume"] ?? JsonValue.Create(.4), 0, 1, "audio.volume") });
            }
        }
        files["metadata/episode.json"] = Encoding.UTF8.GetBytes(spec.ToJsonString(new() { WriteIndented = true }));
        var hashes = new JsonObject(); foreach (var (path, data) in kit.Files.OrderBy(f => f.Key)) hashes[path] = Hash(data);
        var lockFile = new JsonObject { ["kitId"] = kit.Id, ["version"] = kit.Version, ["sha256"] = kit.Digest,
            ["rigVersion"] = kit.Rig["version"]!.DeepClone(), ["rigSha256"] = Hash(Encoding.UTF8.GetBytes(kit.Rig.ToJsonString())),
            ["compilerVersion"] = "1.0.0", ["runtimeSha256"] = Hash(Runtime()), ["dependencies"] = hashes,
            ["testOnly"] = TestOnly(kit),
            ["qaPolicy"] = TestOnly(kit) ? "EXPERIMENTAL: Partial capabilities used for user testing only; no production approval or status promotion." : "Only catalog Supported capabilities selected. This is the pack author's QA declaration; episode visual acceptance is separate." };
        files["metadata/production-lock.json"] = Encoding.UTF8.GetBytes(lockFile.ToJsonString(new() { WriteIndented = true }));
        var manifest = new JsonObject { ["schemaVersion"] = "1.0", ["projectId"] = id, ["title"] = title,
            ["video"] = video.DeepClone(), ["assets"] = assets, ["scenes"] = scenes, ["audio"] = tracks };
        if (files.Count + 1 > 512 || files.Values.Sum(b => (long)b.Length) > StoryValidation.MaxTotal) throw new ArgumentException("Episode vượt giới hạn Story v1: 512 files / 128 MB.");
        var normalized = StoryValidation.Validate(manifest, files);
        return new(normalized, files);
    }
}
