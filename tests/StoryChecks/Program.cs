using System.IO.Compression;
using System.Text;
using System.Text.Json.Nodes;
using SvgToMp4.Core;

var root = Path.GetFullPath(args.Length > 0 ? args[0] : ".");
var testRoot = Path.Combine(root, "work", "story-tests-" + Guid.NewGuid().ToString("N"));
var store = new StoryStore(new AppPaths(testRoot)); var checks = 0;
void Check(bool value, string label) { if (!value) throw new Exception(label); checks++; Console.WriteLine("PASS " + label); }
void Reject(Action action, string label) { try { action(); } catch (Exception e) when (e is ArgumentException or System.Xml.XmlException or InvalidDataException) { checks++; Console.WriteLine("PASS reject " + label); return; } throw new Exception("Expected rejection: " + label); }
try
{
    using var sample = File.OpenRead(Path.Combine(root, "samples", "lost-star.zip"));
    var project = store.Import(sample);
    Check(project.Manifest["duration"]!.GetValue<double>() == 34.5, "four-scene overlap duration");
    Check(project.Manifest["scenes"]!.AsArray().Count == 4 && project.Manifest["characters"]!.AsArray().Count == 1, "shared character and scenes");
    var files = store.ReadFiles(project); var oldPath = store.RevisionPath(project.Id, project.Revision);
    using var exported = new MemoryStream(store.Export(project)); var roundTrip = store.Import(exported);
    Check(store.ReadFiles(roundTrip)["assets/characters/may.svg"].SequenceEqual(files["assets/characters/may.svg"]), "ZIP round-trip preserves assets");
    var save = new StorySave((JsonObject)project.Manifest.DeepClone(), new() { ["scenes/scene-001.js"] = Encoding.UTF8.GetString(files["scenes/scene-001.js"]) + "\n// edited" });
    var next = store.SaveRevision(project.Id, project.Revision, save);
    Check(next.Revision != project.Revision && File.ReadAllText(Path.Combine(oldPath, "scenes/scene-001.js")).EndsWith("\n"), "immutable revisions");
    try { store.SaveRevision(project.Id, project.Revision, save); throw new Exception("Expected conflict"); } catch (StoryConflictException) { checks++; }
    foreach (var path in new[] { "../evil.js", "/evil.js", "C:/evil.js", "x\\evil.js", "assets/../x.svg", "CON.js", "x%2f.js", "evil.exe" }) Reject(() => StoryValidation.SafePath(path), path);
    foreach (var kind in new[] { "version", "missing", "transition", "duplicate", "timer", "mime" })
    {
        var manifest = (JsonObject)project.Manifest.DeepClone(); var copy = files.ToDictionary(x => x.Key, x => x.Value);
        if (kind == "version") manifest["schemaVersion"] = "2";
        if (kind == "missing") copy.Remove("assets/characters/may.svg");
        if (kind == "transition") manifest["scenes"]![0]!["transition"]!["duration"] = 8;
        if (kind == "duplicate") manifest["scenes"]![1]!["id"] = "scene-001";
        if (kind == "timer") copy["scenes/scene-001.js"] = Encoding.UTF8.GetBytes("export function createScene(context){setInterval(()=>{},1);}");
        if (kind == "mime") copy["audio/sfx/chime.wav"] = Encoding.UTF8.GetBytes("fake wav");
        Reject(() => StoryValidation.Validate(manifest, copy), kind);
    }
    using var attack = new MemoryStream();
    using (var zip = new ZipArchive(attack, ZipArchiveMode.Create, true))
    {
        foreach (var (name, bytes) in files) { using var entry = zip.CreateEntry(name).Open(); entry.Write(bytes); }
        using var bad = zip.CreateEntry("../evil.js").Open(); bad.WriteByte(1);
    }
    attack.Position = 0; Reject(() => store.Import(attack), "ZIP traversal");
    Reject(() => StorySyntax.Check("invalid.js", Encoding.UTF8.GetBytes("export function createScene(context) { ??? }")), "JavaScript syntax without execution");
    Console.WriteLine($"Story core: {checks} checks passed.");
}
finally
{
    var work = Path.GetFullPath(Path.Combine(root, "work")) + Path.DirectorySeparatorChar;
    if (Path.GetFullPath(testRoot).StartsWith(work, StringComparison.OrdinalIgnoreCase) && Directory.Exists(testRoot)) Directory.Delete(testRoot, true);
}
