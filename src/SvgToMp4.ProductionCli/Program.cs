using System.IO.Compression;
using System.Text;
using System.Text.Json.Nodes;
using SvgToMp4.Core;

try
{
    if (args.Length == 2 && args[0] == "validate")
    {
        var kit = ProductionKitStore.Parse(File.ReadAllBytes(args[1]));
        Console.WriteLine($"PASS structural/syntax: {kit.Id} v{kit.Version}; {kit.Files.Count} files. Browser/visual QA is separate.");
    }
    else if (args.Length == 4 && args[0] == "compile")
    {
        var kit = ProductionKitStore.Parse(File.ReadAllBytes(args[1]));
        var result = EpisodeCompiler.Compile(kit, JsonNode.Parse(File.ReadAllText(args[2]))!.AsObject());
        foreach (var (path, source) in result.Files.Where(f => f.Key.EndsWith(".js"))) StorySyntax.Check(path, source);
        // Validate before opening the destination; never overwrite an existing release.
        using var output = new FileStream(args[3], FileMode.CreateNew);
        using var zip = new ZipArchive(output, ZipArchiveMode.Create);
        foreach (var (path, bytes) in result.Files.Append(new("story.json", Encoding.UTF8.GetBytes(result.Manifest.ToJsonString()))))
        { using var entry = zip.CreateEntry(path).Open(); entry.Write(bytes); }
        Console.WriteLine("Created " + Path.GetFullPath(args[3]));
    }
    else if (args.Length == 2 && args[0] == "smoke") Smoke(Path.GetFullPath(args[1]));
    else { Console.Error.WriteLine("validate KIT.zip | compile KIT.zip EPISODE.json NEW.zip | smoke SOURCE_ROOT"); return 2; }
    return 0;
}
catch (Exception error) when (error is ArgumentException or InvalidDataException or InvalidOperationException or IOException or System.Text.Json.JsonException or System.Xml.XmlException)
{ Console.Error.WriteLine(error.Message); return 1; }

static void Smoke(string root)
{
    var scratch = Path.Combine(root, "work", "production-smoke-" + Guid.NewGuid().ToString("N"));
    var paths = new AppPaths(scratch); var registry = new ProductionKitStore(paths); var stories = new StoryStore(paths);
    var sample = File.ReadAllBytes(Path.Combine(root, "src/SvgToMp4.Web/wwwroot/episodes/production-kit-demo.zip"));
    var kit = registry.Import(sample);
    if (registry.Import(sample).Digest != kit.Digest) throw new Exception("Idempotent import failed");
    var spec = JsonNode.Parse(File.ReadAllText(Path.Combine(root, "samples/production-episode.json")))!.AsObject();
    var compiled = EpisodeCompiler.Compile(kit, spec); var project = stories.Save(null, compiled.Manifest, compiled.Files);
    using var roundtrip = new MemoryStream(stories.Export(project)); var imported = stories.Import(roundtrip);
    if (imported.Manifest["scenes"]!.AsArray().Count != 3 || imported.Manifest["duration"]!.GetValue<double>() != 12) throw new Exception("Story v1 integration failed");
    Console.WriteLine("PASS kit import, immutable duplicate, 3-scene compile, real StoryStore validation/export/re-import");
    foreach (var name in new[] { "A-expression", "B-pose", "C-motion" })
    {
        var original = ProductionKitStore.Parse(File.ReadAllBytes(Path.Combine(root, "demo/episode-generator/generated", name, "production-kit.zip")), false);
        var oldSpec = JsonNode.Parse(File.ReadAllText(Path.Combine(root, "demo/episode-generator/generated", name, "episode.json")))!.AsObject();
        var testSpec = new JsonObject { ["schemaVersion"] = "episode-1", ["kitId"] = original.Id, ["kitVersion"] = original.Version, ["id"] = "acceptance", ["title"] = name,
            ["scenes"] = new JsonArray(new JsonObject { ["id"] = "scene-001", ["duration"] = 4,
                ["actors"] = new JsonArray(new JsonObject { ["id"] = "hero", ["character"] = oldSpec["character"]!.DeepClone(), ["expression"] = oldSpec["expression"]!.DeepClone(), ["pose"] = oldSpec["pose"]!.DeepClone(), ["motion"] = oldSpec["motion"]!.DeepClone() }) }) };
        var result = EpisodeCompiler.Compile(original, testSpec);
        if (!result.Files.ContainsKey("metadata/production-lock.json")) throw new Exception("Missing lock");
        Console.WriteLine("PASS catalog extension " + name + " (compiler checks; visual QA not run)");
    }
    var bad = (JsonObject)spec.DeepClone(); bad["scenes"]![0]!["actors"]![0]!["motion"] = "does-not-exist";
    try { EpisodeCompiler.Compile(kit, bad); throw new Exception("Unknown capability was accepted"); }
    catch (ArgumentException) { Console.WriteLine("PASS reject unsupported capability"); }
    Console.WriteLine("Smoke artifacts (isolated): " + scratch);
}
