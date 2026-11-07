using System.Net;
using Microsoft.AspNetCore.DataProtection;
using SvgToMp4.Core;
using SvgToMp4.Worker;
using SvgToMp4.Web;

var builder = WebApplication.CreateBuilder(args);
var root = Path.GetFullPath(Path.Combine(builder.Environment.ContentRootPath, "../.."));
builder.Services.AddSingleton(new AppPaths(root));
builder.Services.AddDataProtection().PersistKeysToFileSystem(new DirectoryInfo(Path.Combine(root, "data", "keys")));
builder.Services.AddSingleton<JobStore>();
builder.Services.AddSingleton<StoryStore>();
builder.Services.AddSingleton<RenderWorker>();
builder.Services.AddHostedService(s => s.GetRequiredService<RenderWorker>());
builder.Services.AddControllersWithViews();
builder.Services.AddAntiforgery(o => o.HeaderName = "X-CSRF-TOKEN");
builder.WebHost.UseUrls("http://127.0.0.1:5188", "http://127.0.0.1:5189");
builder.WebHost.ConfigureKestrel(o => o.Limits.MaxRequestBodySize = 75_000_000);
var app = builder.Build();
app.Use(async (context, next) =>
{
    if (context.Connection.RemoteIpAddress is { } remote && !IPAddress.IsLoopback(remote))
    { context.Response.StatusCode = 403; return; }
    if (context.Connection.LocalPort == 5189)
    {
        await StoryPreview.Serve(context, context.RequestServices.GetRequiredService<AppPaths>(), app.Environment, context.RequestServices.GetRequiredService<StoryStore>());
        return;
    }
    if (context.Request.Path == "/story/runtime.html" || context.Request.Path.StartsWithSegments("/story/bundle")) { context.Response.StatusCode = 404; return; }
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    context.Response.Headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; media-src 'self'; connect-src 'self'; frame-src http://127.0.0.1:5189; object-src 'none'; frame-ancestors 'none'; base-uri 'none'";
    await next();
});
app.UseStaticFiles();
app.MapControllers();
app.MapControllerRoute("default", "{controller=Studio}/{action=Index}/{id?}");
app.Run();
