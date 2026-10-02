"""对话框壳：Card(stroke=True) 圆角主体 + 页脚按钮区。

六个对话框统一从这里拿壳：墨线只画在壳上（"墨线只在壳上"的落点之一），
页脚用 line 分隔，Escape 关闭。内容放进 .content（可任意 grid/pack），
页脚按钮放进 .footer_actions，错误提示放 .footer_actions 左侧。
"""
from __future__ import annotations

import tkinter as tk

from .widgets import Card


class Dialog(tk.Toplevel):
    def __init__(self, app, title: str, geometry: str, topmost: bool = False) -> None:
        super().__init__(app)
        self.app = app
        self.title(title)
        colors = app.colors
        self.configure(bg=colors["wash"])
        self.transient(app)
        self.grab_set()
        if topmost:
            self.attributes("-topmost", True)
        self.geometry(geometry)
        self._min_width, self._min_height = (int(part) for part in geometry.split("+")[0].split("x"))
        self.bind("<Escape>", lambda _event: self.destroy())
        shell = Card(self, app=app, tone="surface", stroke=True, fixed=True)
        shell.pack(fill="both", expand=True)
        self.body = shell.body
        body_bg = self.body.cget("bg")
        self.footer = tk.Frame(self.body, bg=body_bg)
        self.footer.pack(fill="x", side="bottom")
        tk.Frame(self.footer, bg=colors["line"], height=1).pack(fill="x")
        self.footer_actions = tk.Frame(self.footer, bg=body_bg)
        self.footer_actions.pack(fill="x", padx=20, pady=11)
        self.content = tk.Frame(self.body, bg=body_bg)
        self.content.pack(fill="both", expand=True)
        self.after_idle(self._fit_height)

    def _fit_height(self) -> None:
        """geometry 里的高度只是下限：按 body 的需求高度加高窗口，页脚永不裁剪。"""
        self.update_idletasks()
        shell = self.body.master
        needed = self.body.winfo_reqheight() + 2 * shell.padding_y
        width = max(self._min_width, self.winfo_width())
        self.geometry(f"{width}x{max(self._min_height, needed)}")
