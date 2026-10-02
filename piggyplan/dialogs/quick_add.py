"""全局快速添加浮层：由全局热键唤起。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from ..ui.dialog import Dialog
from ..ui.widgets import PillButton
from ..util import category_label, offset_date, parse_date, today_key


class QuickAddMixin:
    def open_quick_add(self) -> None:
        existing = getattr(self, "quick_add_dialog", None)
        if existing and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_force()
            return
        dialog = Dialog(self, "+ 快速添加待办", "500x286", topmost=True)
        self.quick_add_dialog = dialog
        dialog.resizable(False, False)
        container = dialog.content
        container.columnconfigure(0, weight=1)
        self._label(container, "+  快速添加待办", 15, self.colors["text"], True).grid(row=0, column=0, sticky="w", padx=2, pady=(0, 2))
        self._label(container, "只记录一个想法也可以，默认不会计入今天的计划。", 9, self.colors["text_soft"], False).grid(row=1, column=0, sticky="w", padx=2, pady=(0, 14))
        title_var = tk.StringVar()
        title_entry = ttk.Entry(container, textvariable=title_var, font=("Microsoft YaHei UI", 12))
        title_entry.grid(row=2, column=0, sticky="ew", padx=2, pady=(0, 14), ipady=5)
        options = tk.Frame(container, bg=self.colors["surface"])
        options.grid(row=3, column=0, sticky="ew", padx=2)
        options.grid_columnconfigure(1, weight=1)
        self._label(options, "计划日期", 8, self.colors["text_soft"], True, bg=self.colors["surface"]).grid(row=0, column=0, sticky="w", padx=(0, 8))
        date_var = tk.StringVar(value="")
        date_entry = ttk.Entry(options, textvariable=date_var, width=13)
        date_entry.grid(row=0, column=1, sticky="w")
        for label, value in (("未安排", ""), ("今天", today_key()), ("明天", offset_date(1))):
            self._button(options, label, lambda value=value: date_var.set(value), "ghost").grid(row=0, column=2 + ((0 if label == "未安排" else 1) if label != "明天" else 2), padx=(5, 0))
        self._label(options, "格式 YYYY-MM-DD", 8, self.colors["text_faint"], False, bg=self.colors["surface"]).grid(row=1, column=1, sticky="w", pady=(3, 0))
        properties = tk.Frame(container, bg=self.colors["surface"])
        properties.grid(row=4, column=0, sticky="ew", padx=2, pady=(14, 14))
        self._label(properties, "分类", 8, self.colors["text_soft"], True, bg=self.colors["surface"]).pack(side="left")
        category_var = tk.StringVar(value=category_label(self.settings.get("default_category", "work")))
        ttk.Combobox(properties, textvariable=category_var, values=["工作", "生活"], state="readonly", width=8).pack(side="left", padx=(7, 20))
        self._label(properties, "优先级", 8, self.colors["text_soft"], True, bg=self.colors["surface"]).pack(side="left")
        priority_var = tk.StringVar(value="普通")
        ttk.Combobox(properties, textvariable=priority_var, values=["普通", "高"], state="readonly", width=8).pack(side="left", padx=(7, 0))
        footer = dialog.footer_actions
        error = self._label(footer, "", 8, self.colors["high_ink"], False)
        error.pack(side="left", padx=2)

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

        PillButton(footer, app=self, text="取消", command=close, kind="ghost").pack(side="right", padx=(0, 7))
        PillButton(footer, app=self, text="保存待办", command=save, kind="primary").pack(side="right", padx=(0, 2))
        dialog.bind("<Return>", lambda _event: save())
        dialog.bind("<Escape>", lambda _event: close())
        title_entry.focus_set()
