using Microsoft.AspNetCore.Mvc;

namespace SvgToMp4.Web.Controllers;

public sealed class StudioController : Controller
{
    [HttpGet("/whiteboard")] public IActionResult Index() => View();
}
