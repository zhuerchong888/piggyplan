"""Toast 轻提示：右下角浮层，可携带撤销动作。"""

from __future__ import annotations

import tkinter as tk


class ToastMixin:
    def show_toast(self, message: str, undo_id: str | None = None, undo_status: str | None = None, undo_callback=None) -> None:
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.toast_undo_callback = undo_callback
        toast = tk.Toplevel(self)
        self.toast = toast
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=self.SURFACE)
        width, height = 340, 56
        self.update_idletasks()
        x = self.winfo_x() + max(20, self.winfo_width() - width - 25)
        y = self.winfo_y() + max(20, self.winfo_height() - height - 30)
        toast.geometry(f"{width}x{height}+{x}+{y}")
        outer = tk.Frame(toast, bg=self.SURFACE, highlightthickness=0)
        outer.pack(fill="both", expand=True)
        self._label(outer, "🐾", 13, self.colors["strong"], True, bg=self.SURFACE).pack(side="left", padx=(14, 8))
        self._label(outer, message, 9, self.TEXT_SOFT, False, bg=self.SURFACE).pack(side="left", fill="x", expand=True)
        if undo_id:
            self._button(outer, "撤回", lambda: self._undo_task(undo_id, undo_status), "link").pack(side="right", padx=10)
        elif undo_callback:
            self._button(outer, "撤回", undo_callback, "link").pack(side="right", padx=10)
        toast.after(5200, lambda: toast.destroy() if toast.winfo_exists() else None)
