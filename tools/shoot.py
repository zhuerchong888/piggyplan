"""截图夹具：以固定窗口几何渲染每个页面，再抓客户区存 PNG。

用于重构前后逐张肉眼比对。

两个坑，都是这里的做法必须绕开的原因：
1. 不用 CopyFromScreen——它依赖 SetForegroundWindow，而 Windows 前台锁会静默
   拒绝非前台进程的调用，结果截到的是桌面上碰巧在上的任意窗口。
2. PrintWindow 是同步的，会给目标窗口发 WM_PRINT，要求目标的消息循环正在跑。
   因此这里用常驻 PowerShell 进程 + 从 stdin 读指令，Python 发完指令后必须持续
   app.update() 泵消息直到文件出现；若改成 subprocess.run() 阻塞等待，就是死锁。

第三个坑是 PrintWindow 与消息泵之间的偶发死锁：阻塞发生在 app.update() 内部，
Python 侧任何超时检查都不会被走到。对策是双保险——
- 每个页面挂一个看门狗线程，超时直接 os._exit(97)；
- supervise() 以子进程方式重跑自己（最多 4 次），已成功的页面按 PNG 签名
  校验后跳过，因此重试只补缺失的页。
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CAPTURES = ["today", "upcoming", "all", "goals", "archive", "settings", "settings-backup", "settings-local", "board", "goal-detail", "goal-board", "search", "empty-today"]
DIALOG_CAPTURES = ["task", "task-more", "goal", "filter", "quick-add", "batch-date", "batch-goal", "goal-decision"]

PAGE_TIMEOUT = 40.0  # 正常每页 1-2s；看门狗只该在死锁时触发
WATCHDOG_EXIT = 97

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


def looks_valid(path: Path) -> bool:
    """半截 PNG 也满足 exists()；用签名 + 最小体积排除，避免重试时错跳过。"""
    try:
        if path.stat().st_size < 5_000:
            return False
        return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    except OSError:
        return False


def quiesce(app, ms: int = 300) -> None:
    """持续泵消息一小段时间，让防抖重渲染（_window_resized 的 after(80, render)、
    搜索防抖）先跑完。否则它们会在抓图的泵消息间隙触发，PrintWindow 截到
    “已清空、重建中”的半成品页面。同时 focus_force 统一窗口激活态，避免
    原生标题栏按钮的渲染随焦点漂移。"""
    app.lift()
    app.focus_force()
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.update()


def _bail_out() -> None:
    print(f"watchdog: {PAGE_TIMEOUT}s 内未完成，疑似 PrintWindow 死锁，退出码 {WATCHDOG_EXIT}", flush=True)
    os._exit(WATCHDOG_EXIT)


def watchdog() -> threading.Timer:
    timer = threading.Timer(PAGE_TIMEOUT, _bail_out)
    timer.start()
    return timer


def worker(label: str) -> None:
    """一次尝试：补齐 label 目录下缺失的页面。卡死由看门狗以 97 退出。

    用种子临时库而非用户的实时库：截图必须确定性，否则隔天数据一变，
    前后基线就失去可比性。种子数据带逾期/今天/未来/已完成/目标/模板，
    覆盖六个页面的全部状态分支。
    """
    import tempfile

    import piggyplan_desktop

    try:
        from piggyplan.database import Database  # 拆包后的来源
    except ImportError:  # 单文件时代：Database 定义在根模块里
        Database = piggyplan_desktop.Database

    out = ROOT / "shots" / label
    out.mkdir(parents=True, exist_ok=True)
    folder = tempfile.TemporaryDirectory()
    database = Database(Path(folder.name) / "shots.db", seed=True)
    app = piggyplan_desktop.PiggyPlanApp(database=database)
    geometry = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--geometry=")), "1160x760+60+40")
    app.geometry(geometry)
    grabber = Grabber()
    try:
        for name in CAPTURES:
            target = out / f"{name}.png"
            if looks_valid(target):
                print(f"  {name}.png (cached)", flush=True)
                continue
            guard = watchdog()
            try:
                if name == "board":
                    app.navigate("all")
                    app.all_mode = "board"
                    app.render()
                elif name == "goal-detail":
                    app.open_goal_detail(database.list_goals(status="active")[0]["id"])
                elif name == "goal-board":
                    app.goal_mode = "board"
                    app.open_goal_detail(database.list_goals(status="active")[0]["id"])
                elif name in ("settings-backup", "settings-local"):
                    app.navigate("settings")
                elif name == "search":
                    app.search_var.set("复盘")
                    app.render()
                elif name == "empty-today":
                    database.clear_all()
                    app.navigate("today")
                else:
                    app.navigate(name)
                quiesce(app)
                if name == "settings-backup":
                    def descendants(widget):
                        for child in widget.winfo_children():
                            yield child
                            yield from descendants(child)
                    import tkinter as tk_tk
                    heading = next(widget for widget in descendants(app.center)
                                   if isinstance(widget, tk_tk.Label) and widget.cget("text") == "数据与备份")
                    region = app.canvas.bbox("all")
                    app.canvas.yview_moveto(max(0, heading.winfo_rooty() - app.page.winfo_rooty() - 18) / region[3])
                    quiesce(app)
                elif name == "settings-local":
                    app.canvas.yview_moveto(1)
                    quiesce(app)
                grabber.grab(app, target)
                print(f"  {name}.png", flush=True)
            finally:
                guard.cancel()
        for name in DIALOG_CAPTURES:
            target = out / f"dialog-{name}.png"
            if looks_valid(target):
                continue
            guard = watchdog()
            try:
                if name in ("batch-date", "batch-goal", "goal-decision"):
                    if not database.list_tasks():
                        database.create_task("整理下周安排")
                    if name in ("batch-goal", "goal-decision") and not database.list_goals():
                        database.create_goal("完成季度复盘")
                        database.create_goal("建立每周阅读习惯", category="life")
                    app.navigate("all")
                    task_id = database.list_tasks()[0]["id"]
                    app.selected_task_ids.add(task_id)
                    if name == "goal-decision":
                        goal_id = database.list_goals()[0]["id"]
                        database.update_task(task_id, {"goal_id": goal_id})
                        app.goal_decision_dialog(goal_id, "achieve")
                    else:
                        (app.batch_set_date if name == "batch-date" else app.batch_attach_goal)()
                else:
                    {"task": app.open_task_dialog, "task-more": app.open_task_dialog, "goal": app.open_goal_dialog,
                     "filter": app.open_filter_dialog, "quick-add": app.open_quick_add}[name]()
                quiesce(app)
                # 对话框是独立 Toplevel，PrintWindow 抓主窗口抓不到它；直接抓对话框 hwnd。
                import tkinter as tk_tk
                dialog = next(child for child in app.winfo_children() if isinstance(child, tk_tk.Toplevel))
                if name == "task-more":
                    from piggyplan.ui.widgets import PillButton
                    def dialog_descendants(widget):
                        for child in widget.winfo_children():
                            yield child
                            yield from dialog_descendants(child)
                    more = next(widget for widget in dialog_descendants(dialog)
                                if isinstance(widget, PillButton)
                                and widget.itemcget(widget._text, "text") == "更多选项")
                    more.invoke()
                    quiesce(app)
                grabber.grab(dialog, target)
                print(f"  dialog-{name}.png", flush=True)
                app.destroy_top_level()
            finally:
                guard.cancel()
    finally:
        grabber.close()
        app.destroy()
        database.close()
        folder.cleanup()


def supervise(label: str) -> int:
    for attempt in range(1, 5):
        result = subprocess.run(
            [sys.executable, "-u", str(Path(__file__).resolve()), label, "--worker"]
            + [arg for arg in sys.argv if arg.startswith("--geometry=")])
        if result.returncode == 0:
            print(f"shots/{label}: {len(CAPTURES) + len(DIALOG_CAPTURES)} images")
            return 0
        if result.returncode != WATCHDOG_EXIT:
            return result.returncode
        print(f"attempt {attempt} wedged in PrintWindow deadlock; retrying", flush=True)
    print("所有重试均失败", flush=True)
    return 1


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "before"
    if "--worker" in sys.argv:
        worker(label)
    else:
        raise SystemExit(supervise(label))
