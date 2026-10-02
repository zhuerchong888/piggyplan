"""全局快速添加浮层：由全局热键唤起。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from ..util import category_label, offset_date, parse_date, today_key


class QuickAddMixin:
    def open_quick_add(self) -> None:
        existing = getattr(self, "quick_add_dialog", None)
        if existing and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_force()
            return
        dialog = tk.Toplevel(self)
        self.quick_add_dialog = dialog
        dialog.title("+ 快速添加待办")
        dialog.configure(bg=self.colors["bg"])
        dialog.transient(self)
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)
        dialog.geometry("500x286")
        dialog.columnconfigure(0, weight=1)
        self._label(dialog, "+  快速添加待办", 15, self.colors["text"], True, bg=self.colors["bg"]).grid(row=0, column=0, sticky="w", padx=22, pady=(19, 2))
        self._label(dialog, "只记录一个想法也可以，默认不会计入今天的计划。", 9, self.colors["text_soft"], False, bg=self.colors["bg"]).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 14))
        title_var = tk.StringVar()
        title_entry = ttk.Entry(dialog, textvariable=title_var, font=("Microsoft YaHei UI", 12))
        title_entry.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 14), ipady=5)
        options = tk.Frame(dialog, bg=self.colors["bg"])
        options.grid(row=3, column=0, sticky="ew", padx=22)
        options.grid_columnconfigure(1, weight=1)
        self._label(options, "计划日期", 8, self.colors["text_soft"], True, bg=self.colors["bg"]).grid(row=0, column=0, sticky="w", padx=(0, 8))
        date_var = tk.StringVar(value="")
        date_entry = ttk.Entry(options, textvariable=date_var, width=13)
        date_entry.grid(row=0, column=1, sticky="w")
        for label, value in (("未安排", ""), ("今天", today_key()), ("明天", offset_date(1))):
            self._button(options, label, lambda value=value: date_var.set(value), "ghost").grid(row=0, column=2 + ((0 if label == "未安排" else 1) if label != "明天" else 2), padx=(5, 0))
        self._label(options, "格式 YYYY-MM-DD", 8, self.colors["text_faint"], False, bg=self.colors["bg"]).grid(row=1, column=1, sticky="w", pady=(3, 0))
        properties = tk.Frame(dialog, bg=self.colors["bg"])
        properties.grid(row=4, column=0, sticky="ew", padx=22, pady=(14, 14))
        self._label(properties, "分类", 8, self.colors["text_soft"], True, bg=self.colors["bg"]).pack(side="left")
        category_var = tk.StringVar(value=category_label(self.settings.get("default_category", "work")))
        ttk.Combobox(properties, textvariable=category_var, values=["工作", "生活"], state="readonly", width=8).pack(side="left", padx=(7, 20))
        self._label(properties, "优先级", 8, self.colors["text_soft"], True, bg=self.colors["bg"]).pack(side="left")
        priority_var = tk.StringVar(value="普通")
        ttk.Combobox(properties, textvariable=priority_var, values=["普通", "高"], state="readonly", width=8).pack(side="left", padx=(7, 0))
        footer = tk.Frame(dialog, bg=self.colors["surface_soft"], highlightthickness=0)
        footer.grid(row=5, column=0, sticky="ew")
        error = self._label(footer, "", 8, self.colors["high"], False, bg=self.colors["surface"])
        error.pack(side="left", padx=22)

        def close() -> None:
            if dialog.winfo_exists():
                dialog.destroy()

        def save() -> None:
            title = title_var.get().strip()
            planned = date_var.get().strip() or None
            if not title:
                error.configure(text="标题不能为空")
                title_entry.focus_set()
                return
            if planned and not parse_date(planned):
                error.configure(text="日期格式应为 YYYY-MM-DD")
                date_entry.focus_set()
                return
            self.db.create_task(title, category="life" if category_var.get() == "生活" else "work", priority="high" if priority_var.get() == "高" else "normal", planned_date=planned)
            close()
            if self.state() != "withdrawn":
                self.render()
                self.show_toast("待办已快速添加")

        self._button(footer, "取消", close, "ghost").pack(side="right", padx=(0, 7), pady=10)
        self._button(footer, "保存待办", save, "primary").pack(side="right", padx=(0, 20), pady=10)
        dialog.bind("<Return>", lambda _event: save())
        dialog.bind("<Escape>", lambda _event: close())
        title_entry.focus_set()
