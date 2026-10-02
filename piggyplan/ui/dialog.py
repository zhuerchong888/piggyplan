"""统一白色弹窗：可滚动表单与始终可见的操作页脚。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Dialog(tk.Toplevel):
    """内容放 .content，按钮放 .footer_actions；.body 保留为原生容器。"""

    def __init__(self, app, title: str, geometry: str, topmost: bool = False) -> None:
        super().__init__(app)
        self.app = app
        self.title(title)
        colors = app.colors
        self.configure(bg=colors["surface"])
        self.transient(app)
        self.grab_set()
        if topmost:
            self.attributes("-topmost", True)
        self.geometry(geometry)
        self._min_width, self._min_height = (int(part) for part in geometry.split("+")[0].split("x"))
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<MouseWheel>", self.scroll, add="+")
        self.bind("<Button-4>", self.scroll, add="+")
        self.bind("<Button-5>", self.scroll, add="+")
        self.bind("<FocusIn>", self._reveal_focus, add="+")
        self._fit_after = None

        self.body = tk.Frame(self, bg=colors["surface"])
        self.body.pack(fill="both", expand=True)
        self.footer = tk.Frame(self.body, bg=colors["surface"])
        self.footer.pack(fill="x", side="bottom")
        tk.Frame(self.footer, bg=colors["line"], height=1).pack(fill="x")
        self.footer_actions = tk.Frame(self.footer, bg=colors["surface"])
        self.footer_actions.pack(fill="x", padx=22, pady=14)

        viewport = tk.Frame(self.body, bg=colors["surface"])
        viewport.pack(fill="both", expand=True)
        self.content_canvas = tk.Canvas(viewport, bg=colors["surface"], bd=0,
                                        highlightthickness=0, width=1, height=1)
        self.canvas = self.content_canvas
        style = ttk.Style(self)
        style.configure("Dialog.Vertical.TScrollbar", width=9, borderwidth=0,
                        relief="flat", background=colors["line_strong"],
                        troughcolor=colors["surface"], arrowcolor=colors["ink_soft"])
        style.map("Dialog.Vertical.TScrollbar", background=[("active", colors["accentDeep"])])
        self.content_scrollbar = ttk.Scrollbar(viewport, orient="vertical",
                                               command=self.content_canvas.yview,
                                               style="Dialog.Vertical.TScrollbar")
        self.content_canvas.pack(side="left", fill="both", expand=True)
        self.content_canvas.configure(yscrollcommand=self.content_scrollbar.set)
        self.content = tk.Frame(self.content_canvas, bg=colors["surface"], padx=22, pady=20)
        self._content_window = self.content_canvas.create_window(0, 0, anchor="nw", window=self.content)
        self.content.bind("<Configure>", self._sync_content)
        self.content_canvas.bind("<Configure>", self._resize_content)
        self.fit_to_content()

    def fit_to_content(self) -> None:
        """展开或收起字段后调整窗口，关闭时一并取消待执行的调整。"""
        if self._fit_after is not None:
            self.after_cancel(self._fit_after)
        self._fit_after = self.after_idle(self._fit_height)

    def _resize_content(self, event) -> None:
        self.content_canvas.itemconfigure(self._content_window, width=max(1, event.width),
                                          height=max(event.height, self.content.winfo_reqheight()))
        self._sync_content()

    def _sync_content(self, _event=None) -> None:
        canvas = self.content_canvas
        content_height = self.content.winfo_reqheight()
        canvas.itemconfigure(self._content_window, height=max(canvas.winfo_height(), content_height))
        canvas.configure(scrollregion=canvas.bbox("all"))
        overflow = content_height > canvas.winfo_height() + 1
        if overflow and not self.content_scrollbar.winfo_manager():
            self.content_scrollbar.pack(side="right", fill="y")
        elif not overflow and self.content_scrollbar.winfo_manager():
            self.content_scrollbar.pack_forget()
            canvas.yview_moveto(0)

    def _fit_height(self) -> None:
        """按内容增长至屏幕上限，长表单只滚动内容，页脚留在窗口内。"""
        self._fit_after = None
        self.update_idletasks()
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        maximum_height = max(160, screen_height - 100)
        width = min(max(self._min_width, self.winfo_width()), max(240, screen_width - 60))
        needed = self.content.winfo_reqheight() + self.footer.winfo_reqheight()
        height = min(max(self._min_height, needed), maximum_height)
        self.minsize(min(width, self._min_width), min(220, maximum_height))
        self.maxsize(max(240, screen_width - 60), maximum_height)
        if self.app.winfo_ismapped():
            x = self.app.winfo_rootx() + (self.app.winfo_width() - width) // 2
            y = self.app.winfo_rooty() + (self.app.winfo_height() - height) // 2
        else:
            x, y = (screen_width - width) // 2, (screen_height - height) // 2
        x = max(12, min(x, screen_width - width - 12))
        y = max(40, min(y, screen_height - height - 60))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def scroll(self, event) -> str:
        """供主窗口滚轮分发使用；弹窗内的原生文本框保留自身滚动。"""
        widget = getattr(event, "widget", None)
        if widget is not None and widget.winfo_class() in ("Text", "Listbox", "TCombobox"):
            return "break"
        if getattr(event, "num", None) in (4, 5):
            units = -1 if event.num == 4 else 1
        else:
            delta = getattr(event, "delta", 0)
            units = int(-delta / 120) or (-1 if delta > 0 else 1 if delta < 0 else 0)
        if units and self.content_canvas.yview() != (0.0, 1.0):
            self.content_canvas.yview_scroll(units * 3, "units")
        return "break"

    def _reveal_focus(self, event) -> None:
        widget = event.widget
        ancestor = widget
        while ancestor is not None and ancestor is not self.content:
            ancestor = getattr(ancestor, "master", None)
        if ancestor is None:
            return
        canvas = self.content_canvas
        region = canvas.bbox("all")
        if not region or region[3] <= canvas.winfo_height():
            return
        top = widget.winfo_rooty() - self.content.winfo_rooty()
        bottom = top + widget.winfo_height()
        visible_top = canvas.canvasy(0)
        height = canvas.winfo_height()
        if top < visible_top:
            canvas.yview_moveto(max(0, top - 8) / region[3])
        elif bottom > visible_top + height:
            canvas.yview_moveto((bottom - height + 8) / region[3])

    def destroy(self) -> None:
        if self._fit_after is not None:
            self.after_cancel(self._fit_after)
            self._fit_after = None
        super().destroy()
