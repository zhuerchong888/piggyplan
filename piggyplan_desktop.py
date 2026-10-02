"""PiggyPlan 桌面版入口。

保留此文件与这些 re-export 是硬要求：启动 .bat、开机自启注册表值、
PyInstaller spec 和 tools/shoot.py 都按 `piggyplan_desktop` 这个名字引用它。
"""
from __future__ import annotations

import sys

from piggyplan.runtime.tcl import prepare as _prepare_tcl

_prepare_tcl()

import tkinter as tk
from tkinter import messagebox

from piggyplan.app import PiggyPlanApp  # noqa: E402  (re-export：见模块 docstring)
from piggyplan.runtime.paths import log_event  # noqa: E402
from piggyplan.runtime.single_instance import SingleInstance, activate_existing_window  # noqa: E402
from piggyplan.selftest import run_gui_smoke_test, run_self_test  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    if "--self-test" in arguments:
        run_self_test()
        return 0
    if "--gui-smoke" in arguments:
        run_gui_smoke_test()
        return 0

    instance = SingleInstance()
    if not instance.acquire():
        activate_existing_window()
        return 0
    try:
        app = PiggyPlanApp(start_minimized="--minimized" in arguments)
        app.mainloop()
        return 0
    except Exception as error:
        log_event("application startup failed", error)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("PiggyPlan 启动失败", "软件没有成功启动。请查看日志目录中的 piggyplan.log。", parent=root)
            root.destroy()
        except Exception:
            print("PiggyPlan startup failed; see the application log for details.")
        return 1
    finally:
        instance.release()


if __name__ == "__main__":
    raise SystemExit(main())
