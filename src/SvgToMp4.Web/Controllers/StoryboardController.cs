using Microsoft.AspNetCore.Mvc;

namespace SvgToMp4.Web.Controllers;
public sealed class StoryboardController : Controller
{
    [HttpGet("/")] public IActionResult Index() => View();
}
