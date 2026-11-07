using System.Diagnostics;
using System.Runtime.InteropServices;

namespace SvgToMp4.Worker;

/// <summary>OS limits around the worker and inherited Chromium/FFmpeg children.</summary>
public sealed class StoryProcessBoundary : IDisposable
{
    private IntPtr handle;
    public StoryProcessBoundary(Process process)
    {
        if (!OperatingSystem.IsWindows() || !Environment.Is64BitProcess) throw new InvalidOperationException("Story JavaScript rendering cần Windows 64-bit Job Object trong bản này. Chưa cấu hình isolation tương đương trên môi trường hiện tại.");
        handle = CreateJobObject(IntPtr.Zero, null);
        if (handle == IntPtr.Zero) { try { process.Kill(true); } catch (InvalidOperationException) { } throw new InvalidOperationException("Không tạo được giới hạn tài nguyên cho Story worker."); }
        var limits = new ExtendedLimits
        {
            Basic = new BasicLimits { LimitFlags = 0x2000 | 0x400 | 0x100 | 0x200 | 0x8 | 0x2, ActiveProcessLimit = 32, PerProcessUserTimeLimit = TimeSpan.FromMinutes(30).Ticks },
            ProcessMemoryLimit = new UIntPtr(2UL * 1024 * 1024 * 1024), JobMemoryLimit = new UIntPtr(4UL * 1024 * 1024 * 1024)
        };
        var size = Marshal.SizeOf<ExtendedLimits>(); var memory = Marshal.AllocHGlobal(size);
        try
        {
            Marshal.StructureToPtr(limits, memory, false);
            if (!SetInformationJobObject(handle, 9, memory, (uint)size) || !AssignProcessToJobObject(handle, process.Handle))
                throw new InvalidOperationException("Không áp dụng được giới hạn process/CPU/RAM. Story render đã dừng để không chạy code ngoài ranh giới được cấu hình.");
        }
        catch { Dispose(); try { process.Kill(true); } catch (InvalidOperationException) { } throw; }
        finally { Marshal.FreeHGlobal(memory); }
    }
    public void Dispose() { if (handle != IntPtr.Zero) { CloseHandle(handle); handle = IntPtr.Zero; } }
    [StructLayout(LayoutKind.Sequential)] private struct BasicLimits { public long PerProcessUserTimeLimit, PerJobUserTimeLimit; public uint LimitFlags; public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize; public uint ActiveProcessLimit; public UIntPtr Affinity; public uint PriorityClass, SchedulingClass; }
    [StructLayout(LayoutKind.Sequential)] private struct IoCounters { public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
    [StructLayout(LayoutKind.Sequential)] private struct ExtendedLimits { public BasicLimits Basic; public IoCounters Io; public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed; }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr CreateJobObject(IntPtr attributes, string? name);
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool SetInformationJobObject(IntPtr job, int infoClass, IntPtr information, uint length);
    [DllImport("kernel32.dll", SetLastError = true)] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll")] [return: MarshalAs(UnmanagedType.Bool)] private static extern bool CloseHandle(IntPtr handle);
}
