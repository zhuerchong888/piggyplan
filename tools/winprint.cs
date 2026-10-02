using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class WinPrint
{
    [StructLayout(LayoutKind.Sequential)]
    private struct NativeRect
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll")]
    private static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);

    [DllImport("user32.dll")]
    private static extern bool GetClientRect(IntPtr hwnd, out NativeRect rect);

    // PW_RENDERFULLCONTENT = 2：让 DWM 组合的窗口也能画出内容。
    private const uint RenderFullContent = 2;

    public static string Capture(IntPtr hwnd, string outputPath)
    {
        NativeRect rect;
        if (!GetClientRect(hwnd, out rect) || rect.Right <= 0 || rect.Bottom <= 0)
        {
            throw new InvalidOperationException("窗口客户区尺寸非法");
        }

        using (var bitmap = new Bitmap(rect.Right, rect.Bottom))
        {
            using (var graphics = Graphics.FromImage(bitmap))
            {
                IntPtr hdc = graphics.GetHdc();
                if (!PrintWindow(hwnd, hdc, RenderFullContent))
                {
                    throw new InvalidOperationException("PrintWindow 调用失败");
                }
                graphics.ReleaseHdc(hdc);
            }
            bitmap.Save(outputPath, ImageFormat.Png);
        }
        return rect.Right + "x" + rect.Bottom;
    }
}
