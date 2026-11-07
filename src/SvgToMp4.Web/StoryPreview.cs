using SvgToMp4.Core;

namespace SvgToMp4.Web;

public static class StoryPreview
{
    public static async Task Serve(HttpContext context, AppPaths paths, IWebHostEnvironment environment, StoryStore stories)
    {
        if (context.Request.Method is not ("GET" or "HEAD")) { context.Response.StatusCode = 405; return; }
        context.Response.Headers["Content-Security-Policy"] = "sandbox allow-scripts; default-src 'none'; script-src http://127.0.0.1:5189 blob:; style-src http://127.0.0.1:5189 'unsafe-inline'; img-src http://127.0.0.1:5189 data: blob:; font-src http://127.0.0.1:5189 blob: data:; media-src http://127.0.0.1:5189 blob:; connect-src http://127.0.0.1:5189; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors http://127.0.0.1:5188";
        context.Response.Headers["Access-Control-Allow-Origin"] = "*";
        context.Response.Headers["X-Content-Type-Options"] = "nosniff";
        context.Response.Headers["Cache-Control"] = "no-store";
        string file;
        try
        {
            var parts = context.Request.Path.Value!.Split('/', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length >= 5 && parts[0] == "story" && parts[1] == "bundle")
            {
                var name = StoryValidation.SafePath(string.Join('/', parts.Skip(4)));
                file = Path.Combine(stories.RevisionPath(parts[2], parts[3]), name);
            }
            else if (context.Request.Path.StartsWithSegments("/story") && parts.Length >= 2)
            {
                var name = string.Join('/', parts.Skip(1));
                var allowed = new[] { "runtime.html", "runtime.js", "runtime.css", "timeline.mjs", "vendor/gsap.min.js", "vendor/MotionPathPlugin.min.js", "vendor/MorphSVGPlugin.min.js" };
                if (!allowed.Contains(name)) { context.Response.StatusCode = 404; return; }
                file = Path.Combine(environment.WebRootPath, "story", name);
            }
            else { context.Response.StatusCode = 404; return; }
            if (!System.IO.File.Exists(file)) { context.Response.StatusCode = 404; return; }
        }
        catch (ArgumentException) { context.Response.StatusCode = 400; return; }
        context.Response.ContentType = Path.GetExtension(file).ToLowerInvariant() switch
        {
            ".html" => "text/html; charset=utf-8", ".js" or ".mjs" => "text/javascript; charset=utf-8", ".css" => "text/css; charset=utf-8", ".json" => "application/json",
            ".svg" => "image/svg+xml", ".png" => "image/png", ".jpg" or ".jpeg" => "image/jpeg", ".webp" => "image/webp", ".woff2" => "font/woff2", ".ttf" => "font/ttf",
            ".wav" => "audio/wav", ".mp3" => "audio/mpeg", ".ogg" => "audio/ogg", ".m4a" => "audio/mp4", _ => "application/octet-stream"
        };
        await context.Response.SendFileAsync(file);
    }
}
