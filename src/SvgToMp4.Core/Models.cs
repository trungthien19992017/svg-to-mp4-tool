namespace SvgToMp4.Core;

public sealed record RenderSettings(double Duration = 10, double Hold = 1, string Aspect = "portrait", string Hand = "asian", double HandScale = 0.65, string Effect = "whiteboard");
public sealed record CreateRender(string Svg, string Name, string Mode, RenderSettings Settings);
public sealed record Job(string Id, string Name, string Mode, string State, string Stage, int FramesDone, int FramesTotal,
    string? Error, string CreatedAt, string UpdatedAt, RenderSettings Settings, int Width, int Height, int Fps,
    string? Warning = null, string? ProjectId = null, string? Revision = null, string Kind = "svg", string? StartedAt = null, string? CompletedAt = null, string? OutputPath = null);

public static class JobStates
{
    public static bool Terminal(string state) => state is "Succeeded" or "Completed" or "Failed" or "Cancelled";
}

public sealed class AppPaths
{
    public string Root { get; }
    public string Data => Path.Combine(Root, "data");
    public string Jobs => Path.Combine(Data, "jobs");
    public string Adapter => Path.Combine(Root, "engine", "render.py");
    public AppPaths(string root)
    {
        Root = Path.GetFullPath(root);
        Directory.CreateDirectory(Jobs);
    }
    public string JobDirectory(string id)
    {
        if (!Guid.TryParseExact(id, "N", out _)) throw new ArgumentException("Mã tác vụ không hợp lệ.");
        return Path.Combine(Jobs, id);
    }
}
