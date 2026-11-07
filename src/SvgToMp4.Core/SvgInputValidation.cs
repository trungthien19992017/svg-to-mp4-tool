using System.Xml;
using System.Xml.Linq;

namespace SvgToMp4.Core;

public static class SvgInputValidation
{
    public static string? ValidateMode(string source, string effect)
    {
        XDocument document;
        try
        {
            using var text = new StringReader(source);
            using var reader = XmlReader.Create(text, new XmlReaderSettings
            {
                DtdProcessing = DtdProcessing.Prohibit,
                XmlResolver = null,
                MaxCharactersInDocument = 20_000_000
            });
            document = XDocument.Load(reader);
        }
        catch (XmlException)
        {
            return "Mã SVG không hợp lệ hoặc chứa DTD. Vui lòng kiểm tra lại file trước khi render.";
        }
        var root = document.Root;
        if (root is null || root.Name.LocalName != "svg" || root.Name.NamespaceName is not ("" or "http://www.w3.org/2000/svg"))
            return "File cần có phần tử gốc SVG hợp lệ.";
        if (effect != "doodle") return null;
        var groups = root.Descendants().Where(e => e.Name == root.Name.Namespace + "g" && (string?)e.Attribute("id") == "doodles").ToArray();
        if (groups.Length == 0)
            return "SVG này chưa có lớp nét doodle. Hãy chọn “Nét trước, màu sau” cho file này, hoặc mở “Mẫu doodle” để thử vẽ trên ảnh nền.";
        if (groups.Length != 1 || groups[0].Parent != root || root.Elements().LastOrDefault() != groups[0])
            return "Lớp nét doodle cần nằm riêng ở cuối SVG. Hãy chuyển group có id=\"doodles\" thành phần tử con cuối cùng của SVG, hoặc dùng “Nét trước, màu sau”.";
        return null;
    }
}
