"""Toast 轻提示：右下角浮层，可携带撤销动作。"""

from __future__ import annotations

import tkinter as tk

from ..tokens import RADIUS
from .mascot import PigMark
from .shape import soft_round_rect


class ToastMixin:
    def show_toast(self, message: str, undo_id: str | None = None, undo_status: str | None = None, undo_callback=None) -> None:
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.toast_undo_callback = undo_callback
        colors = self.colors
        toast = tk.Toplevel(self)
        self.toast = toast
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=colors["wash"])
        width, height = 340, 60
        self.update_idletasks()
        x = self.winfo_x() + max(20, self.winfo_width() - width - 25)
        y = self.winfo_y() + max(20, self.winfo_height() - height - 30)
        toast.geometry(f"{width}x{height}+{x}+{y}")
        canvas = tk.Canvas(toast, bg=colors["wash"], width=width, height=height,
                           highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)
        soft_round_rect(canvas, 2, 2, width - 2, height - 2, RADIUS["control"],
                        colors["surface"], backdrop=colors["wash"],
                        stroke=colors["shell"], stroke_width=2)
        inner = tk.Frame(canvas, bg=colors["surface"])
        canvas.create_window(16, height // 2, window=inner, anchor="w")
        PigMark(inner, app=self, variant="tray").pack(side="left", padx=(0, 8))
        self._label(inner, message, 9, colors["text_soft"], False, bg=colors["surface"]).pack(side="left", fill="x", expand=True)
        if undo_id:
            self._button(inner, "撤回", lambda: self._undo_task(undo_id, undo_status), "link").pack(side="right", padx=10)
        elif undo_callback:
            self._button(inner, "撤回", undo_callback, "link").pack(side="right", padx=10)
        toast.after(5200, lambda: toast.destroy() if toast.winfo_exists() else None)
