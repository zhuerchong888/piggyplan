"""待办新建/编辑对话框：字段、子步骤、标签与模板。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any
from ..util import category_label, parse_date, split_tags, today_key


class TaskDialogMixin:
    def open_new_task(self, date_key: str | None = None, goal_id: str | None = None, template: dict[str, Any] | None = None) -> None:
        if date_key is None and self.view == "today":
            date_key = today_key()
        self.open_task_dialog(None, preset_date=date_key, goal_id=goal_id, template=template)

    def open_new_goal(self) -> None:
        self.open_goal_dialog()

    def open_goal_detail(self, goal_id: str) -> None:
        self.selected_goal_id = goal_id
        self.view = "goals"
        self.render()

    def open_task_dialog(self, task_id: str | None = None, preset_date: str | None = None, goal_id: str | None = None, template: dict[str, Any] | None = None) -> None:
        task = self.db.get_task(task_id) if task_id else None
        template = template or {}
        dialog = tk.Toplevel(self)
        dialog.title("编辑待办" if task else "新建待办")
        dialog.configure(bg=self.BG)
        dialog.transient(self)
        dialog.grab_set()
        dialog.minsize(470, 520)
        dialog.geometry("540x730")
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        head = tk.Frame(dialog, bg=self.SURFACE)
        head.grid(row=0, column=0, sticky="ew")
        self._label(head, "编辑待办" if task else "新建待办", 17, self.TEXT, True, bg=self.SURFACE).pack(anchor="w", padx=22, pady=(19, 3))
        self._label(head, "标题先行，其他信息之后再补也可以。", 9, self.TEXT_SOFT, False, bg=self.SURFACE).pack(anchor="w", padx=22, pady=(0, 16))
        form = tk.Frame(dialog, bg=self.BG)
        form.grid(row=1, column=0, sticky="nsew", padx=20, pady=16)
        form.columnconfigure(0, weight=1)
        title_var = tk.StringVar(value=task["title"] if task else template.get("title", ""))
        note_default = task["note"] if task else template.get("note", "")
        category_value = task["category"] if task else template.get("category", self.settings.get("default_category", "work"))
        priority_value = task["priority"] if task else template.get("priority", "normal")
        category_var = tk.StringVar(value=category_label(category_value))
        priority_var = tk.StringVar(value="高" if priority_value == "high" else "普通")
        date_var = tk.StringVar(value=task["planned_date"] if task and task.get("planned_date") else preset_date or "")
        goal_values = {"独立待办": ""}
        for goal in self.db.list_goals(status="all"):
            goal_values[f"{goal['title']}{'（已达成）' if goal['status'] == 'achieved' else ''}"] = goal["id"]
        goal_current = task.get("goal_id") if task else goal_id
        goal_display = next((name for name, value in goal_values.items() if value == goal_current), "独立待办")
        goal_var = tk.StringVar(value=goal_display)
        tags_var = tk.StringVar(value="、".join(task.get("tags", [])) if task else "、".join(template.get("tags", [])))
        self._form_label(form, "要做什么？", row=0)
        title_entry = ttk.Entry(form, textvariable=title_var, font=("Microsoft YaHei UI", 12))
        title_entry.grid(row=1, column=0, sticky="ew", pady=(0, 14), ipady=3)
        self._form_label(form, "备注详情（可选）", row=2)
        note = tk.Text(form, height=4, wrap="word", bg=self.SURFACE_SOFT, fg=self.TEXT, relief="flat", bd=0, highlightbackground=self.SURFACE_SOFT, highlightcolor=self.colors["strong"], highlightthickness=1, font=("Microsoft YaHei UI", 9))
        note.grid(row=3, column=0, sticky="ew", pady=(0, 13))
        note.insert("1.0", note_default)
        properties = tk.Frame(form, bg=self.BG)
        properties.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        for col in range(2): properties.columnconfigure(col, weight=1)
        self._form_label(properties, "分类", 0, 0)
        self._form_label(properties, "优先级", 0, 1)
        category = ttk.Combobox(properties, textvariable=category_var, values=["工作", "生活"], state="readonly")
        category.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        priority = ttk.Combobox(properties, textvariable=priority_var, values=["普通", "高"], state="readonly")
        priority.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self._form_label(form, "计划日期（可留空）", row=5)
        date_entry = ttk.Entry(form, textvariable=date_var)
        date_entry.grid(row=6, column=0, sticky="ew", pady=(4, 1))
        self._label(form, "格式 YYYY-MM-DD；只保存自然日，不设置截止时刻。", 8, self.TEXT_FAINT, False, bg=self.BG).grid(row=7, column=0, sticky="w", pady=(0, 11))
        self._form_label(form, "所属长期目标", row=8)
        goal_combo = ttk.Combobox(form, textvariable=goal_var, values=list(goal_values), state="readonly")
        goal_combo.grid(row=9, column=0, sticky="ew", pady=(4, 11))
        self._form_label(form, "标签（用逗号或顿号分隔）", row=10)
        ttk.Entry(form, textvariable=tags_var).grid(row=11, column=0, sticky="ew", pady=(4, 11))
        self._form_label(form, "子步骤（每行一个，可选）", row=12)
        step_completion: dict[str, tk.BooleanVar] = {}
        if task and task.get("subtasks"):
            checklist = tk.Frame(form, bg=self.SURFACE_SOFT, highlightthickness=0)
            checklist.grid(row=13, column=0, sticky="ew", pady=(4, 7))
            self._label(checklist, "逐项勾选（不会自动完成主待办）", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(anchor="w", padx=9, pady=(7, 3))
            for step in task["subtasks"][:6]:
                var = tk.BooleanVar(value=bool(step["completed"]))
                step_completion[step["id"]] = var
                tk.Checkbutton(checklist, text=step["title"], variable=var, command=lambda sid=step["id"], current=var: self.db.update_subtask(sid, completed=current.get()), anchor="w", bg=self.SURFACE, fg=self.TEXT, activebackground=self.SURFACE, selectcolor=self.SURFACE, highlightthickness=0, font=("Microsoft YaHei UI", 9)).pack(fill="x", padx=7, pady=1)
            if len(task["subtasks"]) > 6:
                self._label(checklist, f"其余 {len(task['subtasks']) - 6} 项可在下方文本中编辑。", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(anchor="w", padx=9, pady=(3, 7))
        steps = tk.Text(form, height=5, wrap="word", bg=self.SURFACE_SOFT, fg=self.TEXT, relief="flat", bd=0, highlightbackground=self.SURFACE_SOFT, highlightcolor=self.colors["strong"], highlightthickness=1, font=("Microsoft YaHei UI", 9))
        steps.grid(row=14, column=0, sticky="ew", pady=(4, 0))
        if task:
            steps.insert("1.0", "\n".join(step["title"] for step in task.get("subtasks", [])))
        elif template.get("subtasks"):
            steps.insert("1.0", "\n".join(template["subtasks"]))
        footer = tk.Frame(dialog, bg=self.SURFACE_SOFT, highlightthickness=0)
        footer.grid(row=2, column=0, sticky="ew")
        error = tk.Label(footer, text="", bg=self.SURFACE, fg=self.HIGH, font=("Microsoft YaHei UI", 9))
        error.pack(side="left", padx=22)
        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=(0, 10), pady=13)

        def save() -> None:
            title_value = title_var.get().strip()
            if not title_value:
                error.configure(text="标题不能为空")
                title_entry.focus_set()
                return
            step_lines = [item.strip() for item in steps.get("1.0", tk.END).splitlines() if item.strip()]
            old_steps = task.get("subtasks", []) if task else []
            steps_value = []
            for index, item in enumerate(step_lines):
                completed = False
                if index < len(old_steps) and old_steps[index]["title"] == item:
                    variable = step_completion.get(old_steps[index]["id"])
                    completed = variable.get() if variable else bool(old_steps[index]["completed"])
                steps_value.append({"title": item, "completed": completed})
            goal_id_value = goal_values.get(goal_var.get()) or None
            values = {"title": title_value, "note": note.get("1.0", tk.END).strip(), "category": "life" if category_var.get() == "生活" else "work", "priority": "high" if priority_var.get() == "高" else "normal", "planned_date": date_var.get().strip() or None, "goal_id": goal_id_value, "tags": split_tags(tags_var.get()), "subtasks": steps_value}
            if values["planned_date"] and not parse_date(values["planned_date"]):
                error.configure(text="计划日期格式应为 YYYY-MM-DD")
                date_entry.focus_set()
                return
            if task:
                self.db.update_task(task["id"], values)
            else:
                self.db.create_task(**values)
            dialog.destroy()
            self.render()
            self.show_toast("待办已保存")

        self._button(footer, "保存待办", save, "primary").pack(side="right", padx=(0, 22), pady=13)
        title_entry.focus_set()

    def _form_label(self, parent: tk.Misc, text: str, row: int | None = None, col: int = 0, color: str | None = None) -> None:
        label = self._label(parent, text, 8, color or self.TEXT_SOFT, True, bg=parent.cget("bg"))
        if row is None:
            label.pack(anchor="w", pady=(0, 5))
        else:
            label.grid(row=row, column=col, sticky="w")
