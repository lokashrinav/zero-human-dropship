Add-Type @"
using System;
using System.Runtime.InteropServices;
public class KeySender {
    [DllImport("user32.dll")] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")] public static extern IntPtr FindWindowEx(IntPtr hWndParent, IntPtr hWndChildAfter, string lpszClass, string lpszWindow);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();

    public const uint WM_KEYDOWN = 0x0100;
    public const uint WM_KEYUP = 0x0101;
    public const int VK_RETURN = 0x0D;
}
"@

Write-Host "=== Auto-Accept for Claude Code ==="
Write-Host "Sends Enter to this terminal every 0.8s"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# Find Windows Terminal
$wt = Get-Process -Name WindowsTerminal -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $wt) {
    $wt = Get-Process -Name cmd, powershell, pwsh -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
}

if (-not $wt) {
    Write-Host "ERROR: No terminal window found"
    exit 1
}

$hwnd = $wt.MainWindowHandle
Write-Host "Found terminal: $($wt.ProcessName) (PID $($wt.Id), HWND $hwnd)"
Write-Host "Sending Enter every 0.8 seconds..."

while ($true) {
    [KeySender]::PostMessage($hwnd, [KeySender]::WM_KEYDOWN, [IntPtr][KeySender]::VK_RETURN, [IntPtr]::Zero) | Out-Null
    [KeySender]::PostMessage($hwnd, [KeySender]::WM_KEYUP, [IntPtr][KeySender]::VK_RETURN, [IntPtr]::Zero) | Out-Null
    Start-Sleep -Milliseconds 800
}
