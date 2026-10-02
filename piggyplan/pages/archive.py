"""完成归档页：已完成待办与已达成目标两个页签。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any
from ..util import category_label


class ArchiveMixin:
    def render_archive(self, parent: tk.Misc) -> None:
        self.page_header(parent, "保留痕迹", "归档", "完成不是删除。把已经做过的事情留在这里，之后仍然可以回看。", (str(len(self.db.list_tasks(include_completed=True, status="completed"))), "完成记录"))
        tabs = tk.Frame(parent, bg=self.colors["bg"])
        tabs.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        for value, title in (("tasks", "已完成待办"), ("goals", "已达成目标")):
            self._button(tabs, title, lambda value=value: self._set_archive_tab(value), "primary" if self.archive_tab == value else "ghost").pack(side="left", padx=(0, 4))
        controls = tk.Frame(parent, bg=self.colors["bg"])
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        query_var = tk.StringVar(value=self.archive_query)
        query_var.trace_add("write", lambda *_args: self._refresh_archive_query(query_var.get()))
        self._archive_entry = ttk.Entry(controls, textvariable=query_var, width=30)
        self._archive_entry.pack(side="left")
        category_choices = {"全部分类": "all", category_label("work"): "work", category_label("life"): "life"}
        category_name = next((label for label, value in category_choices.items() if value == getattr(self, "archive_category", "all")), "全部分类")
        category_var = tk.StringVar(value=category_name)
        category = ttk.Combobox(controls, textvariable=category_var, values=list(category_choices), state="readonly", width=10)
        category.pack(side="right")
        category.bind("<<ComboboxSelected>>", lambda _event: self._set_archive_category(category_choices.get(category_var.get(), "all")))
        self._label(controls, "筛选", 8, self.colors["text_faint"], True, bg=self.colors["bg"]).pack(side="right", padx=(0, 7))
        self._archive_results = tk.Frame(parent, bg=self.colors["bg"])
        self._archive_results.grid(row=3, column=0, sticky="ew")
        self._archive_results.columnconfigure(0, weight=1)
        self._render_archive_results()

    def _refresh_archive_query(self, value: str) -> None:
        """Update only results, keeping the active search widget and its cursor."""

        self.archive_query = value
        pending = getattr(self, "_archive_search_after", None)
        if pending:
            self.after_cancel(pending)
        self._archive_search_after = self.after(150, self._render_archive_results)

    def _render_archive_results(self) -> None:
        self._archive_search_after = None
        parent = getattr(self, "_archive_results", None)
        if parent is None or not parent.winfo_exists():
            return
        for child in parent.winfo_children():
            child.destroy()
        if self.archive_tab == "tasks":
            tasks = self.db.list_tasks(include_completed=True, status="completed", category=getattr(self, "archive_category", "all"), query=self.archive_query)
            if not tasks:
                self.empty_state(parent, "还没有已完成待办", "完成的事项会按实际完成日期出现在这里。")
                return
            for task in tasks:
                self.archive_task_row(parent, task)
        else:
            goals = self.db.list_goals(status="achieved", category=getattr(self, "archive_category", "all"), query=self.archive_query)
            if not goals:
                self.empty_state(parent, "还没有已达成目标", "目标达成后会永久保留在这里。")
                return
            for goal in goals:
                self.archive_goal_row(parent, goal)

    def archive_task_row(self, parent: tk.Misc, task: dict[str, Any]) -> None:
        row = tk.Frame(parent, bg=self.colors["surface"], highlightthickness=0)
        row.grid(sticky="ew", pady=(0, 8))
        body = tk.Frame(row, bg=self.colors["surface"])
        body.pack(fill="x", padx=14, pady=11)
        left = tk.Frame(body, bg=self.colors["surface"])
        left.pack(side="left", fill="x", expand=True)
        self._label(left, task["title"], 10, self.colors["text"], True, bg=self.colors["surface"], anchor="w").pack(fill="x")
        goal_label = f"  ·  {task['goal_title']}" if task.get("goal_title") else "  ·  独立待办"
        self._label(left, f"✓  实际完成 {task['completed_at'][:10] if task.get('completed_at') else '未知日期'}   {goal_label}", 8, self.colors["text_faint"], False, bg=self.colors["surface"], anchor="w").pack(fill="x", pady=(4, 0))
        self.badge(body, "已完成", "#E8F5EE", self.colors["success_ink"]).pack(side="right", padx=(10, 0))
        self._button(body, "查看", lambda tid=task["id"]: self.open_task_dialog(tid), "ghost").pack(side="right")

    def archive_goal_row(self, parent: tk.Misc, goal: dict[str, Any]) -> None:
        row = tk.Frame(parent, bg=self.colors["surface"], highlightthickness=0)
        row.grid(sticky="ew", pady=(0, 8))
        body = tk.Frame(row, bg=self.colors["surface"])
        body.pack(fill="x", padx=14, pady=11)
        left = tk.Frame(body, bg=self.colors["surface"])
        left.pack(side="left", fill="x", expand=True)
        self._label(left, goal["title"], 10, self.colors["text"], True, bg=self.colors["surface"], anchor="w").pack(fill="x")
        self._label(left, f"✓  达成于 {goal['achieved_at'][:10] if goal.get('achieved_at') else '未知日期'}   ·   {goal['completed']} / {goal['total']} 个待办", 8, self.colors["text_faint"], False, bg=self.colors["surface"], anchor="w").pack(fill="x", pady=(4, 0))
        self.badge(body, "已达成", "#E8F5EE", self.colors["success_ink"]).pack(side="right")
        self._button(body, "查看", lambda gid=goal["id"]: self.open_goal_detail(gid), "ghost").pack(side="right", padx=(0, 8))
