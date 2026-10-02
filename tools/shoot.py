"""截图夹具：以固定窗口几何渲染每个页面，再抓客户区存 PNG。

用于重构前后逐张肉眼比对。

两个坑，都是这里的做法必须绕开的原因：
1. 不用 CopyFromScreen——它依赖 SetForegroundWindow，而 Windows 前台锁会静默
   拒绝非前台进程的调用，结果截到的是桌面上碰巧在上的任意窗口。
2. PrintWindow 是同步的，会给目标窗口发 WM_PRINT，要求目标的消息循环正在跑。
   因此这里用常驻 PowerShell 进程 + 从 stdin 读指令，Python 发完指令后必须持续
   app.update() 泵消息直到文件出现；若改成 subprocess.run() 阻塞等待，就是死锁。
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CAPTURES = ["today", "upcoming", "all", "goals", "archive", "settings"]

REPL = r"""
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Drawing
Add-Type -Path '%s' -ReferencedAssemblies System.Drawing
while ($null -ne ($line = [Console]::In.ReadLine())) {
    if ($line.Length -eq 0) { continue }
    $parts = $line -split '\|', 2
    try { [void][WinPrint]::Capture([IntPtr]([int]$parts[0]), $parts[1]) } catch { }
}
""" % (ROOT / "tools" / "winprint.cs").as_posix()


class Grabber:
    def __init__(self) -> None:
        self.process = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", REPL],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )

    def grab(self, app, destination: Path, timeout: float = 25.0) -> None:
        app.update_idletasks()
        app.update()
        destination.unlink(missing_ok=True)
        assert self.process.stdin
        self.process.stdin.write(f"{int(app.frame(), 16)}|{destination.as_posix()}\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + timeout
        while not destination.exists():
            if self.process.poll() is not None:
                raise RuntimeError("PowerShell 抓取进程已退出")
            if time.monotonic() > deadline:
                raise RuntimeError(f"{destination.name} 抓取超时")
            app.update()              # 关键：泵消息，否则 PrintWindow 永不返回
            time.sleep(0.01)
        time.sleep(0.05)              # 等 PNG 写完

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        self.process.wait(timeout=5)


def run(label: str) -> None:
    import piggyplan_desktop

    out = ROOT / "shots" / label
    out.mkdir(parents=True, exist_ok=True)
    app = piggyplan_desktop.PiggyPlanApp()
    app.geometry("1160x760+60+40")
    grabber = Grabber()
    try:
        for name in CAPTURES:
            app.navigate(name)
            grabber.grab(app, out / f"{name}.png")
            print(f"  {name}.png")
        app.open_task_dialog()
        grabber.grab(app, out / "dialog-task.png")
        print("  dialog-task.png")
        app.destroy_top_level()
    finally:
        grabber.close()
        app.destroy()
    print(f"shots/{label}: {len(CAPTURES) + 1} images")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "before")
