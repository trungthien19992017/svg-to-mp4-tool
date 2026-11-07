using System.Diagnostics;
using System.Text;

namespace SvgToMp4.Core;

public static class StorySyntax
{
    // --check parses module syntax. It does not evaluate code or resolve imports.
    public static void Check(string path, byte[] source)
    {
        var start = new ProcessStartInfo("node") { UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true, RedirectStandardError = true, RedirectStandardOutput = true, StandardInputEncoding = new UTF8Encoding(false) };
        foreach (var arg in new[] { "--max-old-space-size=128", "--input-type=module", "--check" }) start.ArgumentList.Add(arg);
        using var process = Process.Start(start) ?? throw new ArgumentException("Cần Node.js để kiểm tra cú pháp scene. Chạy setup.ps1.");
        var errors = process.StandardError.ReadToEndAsync(); var output = process.StandardOutput.ReadToEndAsync();
        process.StandardInput.Write(Encoding.UTF8.GetString(source)); process.StandardInput.Close();
        if (!process.WaitForExit(5000)) { process.Kill(true); throw new ArgumentException($"{path}: kiểm tra cú pháp vượt thời gian cho phép."); }
        var stderr = errors.GetAwaiter().GetResult(); _ = output.GetAwaiter().GetResult();
        if (process.ExitCode != 0)
        {
            var detail = stderr.Split('\n').FirstOrDefault(line => line.StartsWith("SyntaxError:")) ?? "JavaScript module không hợp lệ.";
            throw new ArgumentException($"{path}: {detail.Trim()}");
        }
    }
}
