"""目标新建/编辑对话框。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from ..util import category_label, parse_date


class GoalDialogMixin:
    def open_goal_dialog(self, goal_id: str | None = None) -> None:
        goal = self.db.get_goal(goal_id) if goal_id else None
        dialog = tk.Toplevel(self)
        dialog.title("编辑长期目标" if goal else "新建长期目标")
        dialog.configure(bg=self.BG)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("500x470")
        dialog.columnconfigure(0, weight=1)
        head = tk.Frame(dialog, bg=self.SURFACE)
        head.grid(row=0, column=0, sticky="ew")
        self._label(head, "编辑长期目标" if goal else "新建长期目标", 17, self.TEXT, True, bg=self.SURFACE).pack(anchor="w", padx=22, pady=(19, 3))
        self._label(head, "目标进度由关联待办自动计算，不需要手动维护百分比。", 9, self.TEXT_SOFT, False, bg=self.SURFACE).pack(anchor="w", padx=22, pady=(0, 16))
        form = tk.Frame(dialog, bg=self.BG)
        form.grid(row=1, column=0, sticky="nsew", padx=20, pady=17)
        form.columnconfigure(0, weight=1)
        title_var = tk.StringVar(value=goal["title"] if goal else "")
        category_var = tk.StringVar(value=category_label(goal["category"] if goal else self.settings.get("default_category", "work")))
        priority_var = tk.StringVar(value="高" if goal and goal["priority"] == "high" else "普通")
        date_var = tk.StringVar(value=goal["planned_finish_date"] if goal and goal.get("planned_finish_date") else "")
        self._form_label(form, "目标是什么？", row=0)
        title_entry = ttk.Entry(form, textvariable=title_var, font=("Microsoft YaHei UI", 12))
        title_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15), ipady=3)
        self._form_label(form, "目标说明（可选）", row=2)
        note = tk.Text(form, height=5, wrap="word", bg=self.SURFACE_SOFT, fg=self.TEXT, relief="flat", bd=0, highlightbackground=self.SURFACE_SOFT, highlightcolor=self.colors["strong"], highlightthickness=1, font=("Microsoft YaHei UI", 9))
        note.grid(row=3, column=0, sticky="ew", pady=(4, 14))
        if goal:
            note.insert("1.0", goal.get("note", ""))
        properties = tk.Frame(form, bg=self.BG)
        properties.grid(row=4, column=0, sticky="ew")
        properties.grid_columnconfigure(0, weight=1)
        properties.grid_columnconfigure(1, weight=1)
        self._form_label(properties, "分类", 0, 0)
        self._form_label(properties, "优先级", 0, 1)
        ttk.Combobox(properties, textvariable=category_var, values=["工作", "生活"], state="readonly").grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        ttk.Combobox(properties, textvariable=priority_var, values=["普通", "高"], state="readonly").grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self._form_label(form, "计划完成日期（可留空）", row=5)
        date_entry = ttk.Entry(form, textvariable=date_var)
        date_entry.grid(row=6, column=0, sticky="ew", pady=(4, 1))
        self._label(form, "只做方向提醒，不会产生强提醒。格式 YYYY-MM-DD。", 8, self.TEXT_FAINT, False, bg=self.BG).grid(row=7, column=0, sticky="w")
        footer = tk.Frame(dialog, bg=self.SURFACE_SOFT, highlightthickness=0)
        footer.grid(row=2, column=0, sticky="ew")
        error = tk.Label(footer, text="", bg=self.SURFACE, fg=self.HIGH, font=("Microsoft YaHei UI", 9))
        error.pack(side="left", padx=22)
        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=(0, 10), pady=13)

        def save() -> None:
            title_value = title_var.get().strip()
            if not title_value:
                error.configure(text="目标标题不能为空")
                title_entry.focus_set()
                return
            if date_var.get().strip() and not parse_date(date_var.get().strip()):
                error.configure(text="日期格式应为 YYYY-MM-DD")
                date_entry.focus_set()
                return
            values = {"title": title_value, "note": note.get("1.0", tk.END).strip(), "category": "life" if category_var.get() == "生活" else "work", "priority": "high" if priority_var.get() == "高" else "normal", "planned_finish_date": date_var.get().strip() or None}
            if goal:
                self.db.update_goal(goal["id"], values)
            else:
                self.db.create_goal(**values)
            dialog.destroy()
            self.render()
            self.show_toast("长期目标已保存")

        self._button(footer, "保存目标", save, "primary").pack(side="right", padx=(0, 22), pady=13)
        title_entry.focus_set()
