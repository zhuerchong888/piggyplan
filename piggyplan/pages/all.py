"""全部待办页：筛选、批量操作栏、列表与看板两种模式。"""

from __future__ import annotations

import tkinter as tk
from typing import Any


class AllMixin:
    def render_all(self, parent: tk.Misc) -> None:
        tasks = self.db.list_tasks(include_completed=self.filter_values["status"] != "todo", mode="all", category=self.filter_values["category"], priority=self.filter_values["priority"], status=self.filter_values["status"])
        tasks = self._apply_task_filters(tasks)
        self.page_header(parent, "全局掌握", "全部待办", "工作与生活放在同一条执行线上，日期通过显式操作调整。", (str(len(tasks)), "符合当前筛选"))
        toolbar = tk.Frame(parent, bg=self.BG)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 13))
        self._button(toolbar, "筛选", self.open_filter_dialog, "outline").pack(side="left")
        self._label(toolbar, self._filter_summary(), 8, self.TEXT_SOFT, False, bg=self.BG).pack(side="left", padx=9)
        modes = tk.Frame(toolbar, bg=self.SURFACE_SOFT, highlightthickness=0)
        modes.pack(side="right")
        self._button(modes, "列表", lambda: self._set_all_mode("list"), "primary" if self.all_mode == "list" else "ghost").pack(side="left", padx=3, pady=3)
        self._button(modes, "看板", lambda: self._set_all_mode("board"), "primary" if self.all_mode == "board" else "ghost").pack(side="left", padx=3, pady=3)
        if self.selected_task_ids:
            self.render_batch_bar(parent, 2)
            row = 3
        else:
            row = 2
        if self.all_mode == "board":
            self.render_board(parent, tasks, row)
            return
        if not tasks:
            self.empty_state(parent, "没有符合条件的待办", "试试清除筛选，或者新建一条待办。", self.open_new_task)
            return
        for priority, title in (("high", "高优先级"), ("normal", "普通优先级")):
            subset = [task for task in tasks if task["priority"] == priority]
            self.section_title(parent, title, len(subset), color=self.HIGH if priority == "high" else self.TEXT_SOFT).grid(row=row, column=0, sticky="ew")
            row += 1
            block = tk.Frame(parent, bg=self.BG)
            block.grid(row=row, column=0, sticky="ew", pady=(0, 18))
            for task in subset:
                self.task_row(block, task, selectable=True)
            if not subset:
                self._label(block, "这一组暂时是空的。", 8, self.TEXT_FAINT, False, bg=self.BG).pack(anchor="w", padx=12, pady=8)
            row += 1

    def _apply_task_filters(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        relation = self.filter_values.get("goal", "all")
        if relation == "linked":
            tasks = [task for task in tasks if task.get("goal_id")]
        elif relation == "standalone":
            tasks = [task for task in tasks if not task.get("goal_id")]
        tag = self.filter_values.get("tag", "all")
        if tag != "all":
            tasks = [task for task in tasks if tag in task.get("tags", [])]
        return tasks

    def _filter_summary(self) -> str:
        values = []
        if self.filter_values["category"] != "all": values.append("生活" if self.filter_values["category"] == "life" else "工作")
        if self.filter_values["priority"] != "all": values.append("高优" if self.filter_values["priority"] == "high" else "普通")
        if self.filter_values["goal"] != "all": values.append("已关联" if self.filter_values["goal"] == "linked" else "独立")
        if self.filter_values["status"] != "todo": values.append("已完成" if self.filter_values["status"] == "completed" else "全部状态")
        if self.filter_values.get("tag", "all") != "all": values.append(f"#{self.filter_values['tag']}")
        return " · ".join(values) if values else "待办 · 全部分类 · 高优先级置顶"

    def render_batch_bar(self, parent: tk.Misc, row: int) -> None:
        bar = tk.Frame(parent, bg=self.colors["soft"], highlightthickness=0)
        bar.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        self._label(bar, f"已选择 {len(self.selected_task_ids)} 项", 9, "#A04868", True, bg=self.colors["soft"]).pack(side="left", padx=12, pady=9)
        for text, callback in (("清除", lambda: (self.selected_task_ids.clear(), self.render())), ("删除", self.batch_delete), ("设置日期", self.batch_set_date), ("完成", self.batch_complete)):
            self._button(bar, text, callback, "ghost").pack(side="right", padx=(0, 4), pady=4)
        more = tk.Menubutton(bar, text="更多操作 ▾", relief="flat", bd=0, bg=self.SURFACE, fg=self.TEXT_SOFT, activebackground=self.colors["accent"], font=("Microsoft YaHei UI", 9), cursor="hand2", padx=10, pady=7)
        menu = tk.Menu(more, tearoff=0, bg=self.SURFACE, fg=self.TEXT, activebackground=self.colors["soft"], activeforeground=self.TEXT, bd=0)
        menu.add_command(label="分类：工作", command=lambda: self.batch_set("category", "work"))
        menu.add_command(label="分类：生活", command=lambda: self.batch_set("category", "life"))
        menu.add_separator()
        menu.add_command(label="优先级：高", command=lambda: self.batch_set("priority", "high"))
        menu.add_command(label="优先级：普通", command=lambda: self.batch_set("priority", "normal"))
        menu.add_separator()
        menu.add_command(label="挂载到目标", command=self.batch_attach_goal)
        menu.add_command(label="解除目标关联", command=lambda: self._batch_set_goal(None))
        more.configure(menu=menu)
        more.pack(side="right", padx=(0, 4), pady=4)

    def render_board(self, parent: tk.Misc, tasks: list[dict[str, Any]], row: int, goal_id: str | None = None) -> None:
        board = tk.Frame(parent, bg=self.BG)
        board.grid(row=row, column=0, sticky="ew")
        todo = [task for task in tasks if task["status"] == "todo"]
        completed = self.db.list_tasks(include_completed=True, status="completed", category=self.filter_values["category"], priority=self.filter_values["priority"], goal_id=goal_id)
        completed = self._apply_task_filters(completed)
        for col, (title, values, status) in enumerate((("待办", todo, "todo"), ("已完成", completed, "completed"))):
            column = tk.Frame(board, bg=self.SURFACE_SOFT, highlightthickness=0)
            column.grid(row=0, column=col, sticky="nsew", padx=(0, 10) if col == 0 else (10, 0))
            board.grid_columnconfigure(col, weight=1)
            head = tk.Frame(column, bg=self.SURFACE_SOFT)
            head.pack(fill="x", padx=14, pady=12)
            self._label(head, title, 10, self.TEXT, True, bg=self.SURFACE_SOFT).pack(side="left")
            self.badge(head, str(len(values)), self.SURFACE, self.TEXT_SOFT).pack(side="right")
            body = tk.Frame(column, bg=self.SURFACE_SOFT)
            body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            if values:
                for task in values:
                    self.task_row(body, task, compact=True, selectable=True)
            else:
                self._label(body, "这一栏暂时是空的。", 8, self.TEXT_FAINT, False, bg=self.SURFACE_SOFT).pack(anchor="w", padx=8, pady=14)
