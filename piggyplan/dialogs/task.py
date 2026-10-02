"""待办新建/编辑对话框：字段、子步骤、标签与模板。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any
from ..ui.dialog import Dialog
from ..ui.widgets import PillButton
from ..util import category_label, goal_choice_labels, parse_date, split_tags, today_key


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
        self.selected_task_ids.clear()
        self.search_var.set("")
        self.render()

    def open_task_dialog(self, task_id: str | None = None, preset_date: str | None = None, goal_id: str | None = None, template: dict[str, Any] | None = None) -> None:
        task = self.db.get_task(task_id) if task_id else None
        template = template or {}
        dialog = Dialog(self, "编辑待办" if task else "新建待办", "500x350")
        container = dialog.content
        container.columnconfigure(0, weight=1)
        form = tk.Frame(container, bg=self.colors["surface"])
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)
        title_var = tk.StringVar(value=task["title"] if task else template.get("title", ""))
        note_default = task["note"] if task else template.get("note", "")
        category_value = task["category"] if task else template.get("category", self.settings.get("default_category", "work"))
        priority_value = task["priority"] if task else template.get("priority", "normal")
        category_var = tk.StringVar(value=category_label(category_value))
        priority_var = tk.StringVar(value="高" if priority_value == "high" else "普通")
        date_var = tk.StringVar(value=task["planned_date"] if task and task.get("planned_date") else preset_date or "")
        goal_values = goal_choice_labels(self.db.list_goals(status="all"), include_standalone=True)
        goal_current = task.get("goal_id") if task else goal_id
        goal_display = next((name for name, value in goal_values.items() if value == goal_current), "独立待办")
        goal_var = tk.StringVar(value=goal_display)
        tags_var = tk.StringVar(value="、".join(task.get("tags", [])) if task else "、".join(template.get("tags", [])))
        self._form_label(form, "要做什么？", row=0)
        title_entry = ttk.Entry(form, textvariable=title_var, font=self.font("body"))
        title_entry.grid(row=1, column=0, sticky="ew", pady=(5, 18), ipady=3)
        properties = tk.Frame(form, bg=self.colors["surface"])
        properties.grid(row=2, column=0, sticky="ew", pady=(0, 17))
        for col in range(2): properties.columnconfigure(col, weight=1, uniform="properties")
        self._form_label(properties, "分类", 0, 0)
        self._form_label(properties, "计划日期（可留空）", 0, 1)
        category = ttk.Combobox(properties, textvariable=category_var, values=[category_label("work"), category_label("life")], state="readonly", width=1)
        category.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(5, 0))
        date_entry = ttk.Entry(properties, textvariable=date_var, width=1)
        date_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(5, 0))
        self._form_label(form, "所属目标", row=3)
        goal_combo = ttk.Combobox(form, textvariable=goal_var, values=list(goal_values), state="readonly", width=1)
        goal_combo.grid(row=4, column=0, sticky="ew", pady=(5, 12))

        more_button = PillButton(form, app=self, text="更多选项", command=lambda: toggle_details(), kind="link", size="sm")
        more_button.grid(row=5, column=0, sticky="w")
        details = tk.Frame(form, bg=self.colors["surface"])
        details.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        for col in range(2): details.columnconfigure(col, weight=1, uniform="details")
        self._form_label(details, "备注（可选）", row=0)
        note = tk.Text(details, width=1, height=3, wrap="word", bg=self.colors["surface_soft"], fg=self.colors["text"], relief="flat", bd=0, highlightbackground=self.colors["surface_soft"], highlightcolor=self.colors["strong"], highlightthickness=1, font=self.font("meta"))
        note.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 13))
        note.insert("1.0", note_default)
        self._form_label(details, "优先级", 2, 0)
        self._form_label(details, "标签", 2, 1)
        priority = ttk.Combobox(details, textvariable=priority_var, values=["普通", "高"], state="readonly", width=1)
        priority.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(5, 13))
        ttk.Entry(details, textvariable=tags_var, width=1).grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(5, 13))
        self._form_label(details, "子步骤（每行一个）", row=4)
        step_completion: dict[str, tk.BooleanVar] = {}
        if task and task.get("subtasks"):
            checklist = tk.Frame(details, bg=self.colors["surface_soft"], highlightthickness=0)
            checklist.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 7))
            self._label(checklist, "逐项勾选（不会自动完成主待办）", 8, self.colors["text_faint"], False, bg=self.colors["surface"]).pack(anchor="w", padx=9, pady=(7, 3))
            for step in task["subtasks"]:
                var = tk.BooleanVar(value=bool(step["completed"]))
                step_completion[step["id"]] = var
                tk.Checkbutton(checklist, text=step["title"], variable=var, anchor="w", bg=self.colors["surface"], fg=self.colors["text"], activebackground=self.colors["surface"], selectcolor=self.colors["surface"], highlightthickness=0, font=self.font("meta")).pack(fill="x", padx=7, pady=1)
        steps = tk.Text(details, width=1, height=3, wrap="word", bg=self.colors["surface_soft"], fg=self.colors["text"], relief="flat", bd=0, highlightbackground=self.colors["surface_soft"], highlightcolor=self.colors["strong"], highlightthickness=1, font=self.font("meta"))
        steps.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        if task:
            steps.insert("1.0", "\n".join(step["title"] for step in task.get("subtasks", [])))
        elif template.get("subtasks"):
            steps.insert("1.0", "\n".join(template["subtasks"]))
        details.grid_remove()

        def toggle_details() -> None:
            if details.winfo_manager():
                details.grid_remove()
                more_button.set_text("更多选项")
            else:
                details.grid()
                more_button.set_text("收起选项")
            dialog.fit_to_content()

        footer = dialog.footer_actions
        error = tk.Label(footer, text="", bg=footer.cget("bg"), fg=self.colors["high_ink"], font=self.font("meta"))
        error.pack(side="left", padx=2)
        PillButton(footer, app=self, text="取消", command=dialog.destroy, kind="ghost").pack(side="right", padx=(0, 10))

        def save() -> None:
            title_value = title_var.get().strip()
            if not title_value:
                error.configure(text="标题不能为空")
                title_entry.focus_set()
                return
            step_lines = [item.strip() for item in steps.get("1.0", tk.END).splitlines() if item.strip()]
            old_steps = task.get("subtasks", []) if task else []
            # Match unchanged titles first so reordering or inserting text cannot
            # erase completed flags. With an unchanged count, unmatched lines
            # are edits of the remaining old lines, in their original order.
            remaining = list(range(len(old_steps)))
            matches: dict[int, int] = {}
            for index, item in enumerate(step_lines):
                match = next((old_index for old_index in remaining if old_steps[old_index]["title"] == item), None)
                if match is not None:
                    matches[index] = match
                    remaining.remove(match)
            if len(step_lines) == len(old_steps):
                unmatched = [index for index in range(len(step_lines)) if index not in matches]
                matches.update(zip(unmatched, remaining))
            steps_value = []
            for index, item in enumerate(step_lines):
                previous = old_steps[matches[index]] if index in matches else None
                variable = step_completion.get(previous["id"]) if previous else None
                completed = variable.get() if variable is not None else bool(previous and previous["completed"])
                steps_value.append({"title": item, "completed": completed})
            goal_id_value = goal_values.get(goal_var.get()) or None
            values = {"title": title_value, "note": note.get("1.0", tk.END).strip(), "category": "life" if category_var.get() == category_label("life") else "work", "priority": "high" if priority_var.get() == "高" else "normal", "planned_date": date_var.get().strip() or None, "goal_id": goal_id_value, "tags": split_tags(tags_var.get()), "subtasks": steps_value}
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

        PillButton(footer, app=self, text="保存待办", command=save, kind="primary").pack(side="right", padx=(0, 2))
        title_entry.focus_set()

    def _form_label(self, parent: tk.Misc, text: str, row: int | None = None, col: int = 0, color: str | None = None) -> None:
        label = self._label(parent, text, 8, color or self.colors["text_soft"], True, bg=parent.cget("bg"))
        if row is None:
            label.pack(anchor="w", pady=(0, 5))
        else:
            label.grid(row=row, column=col, sticky="w")
