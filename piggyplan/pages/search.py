"""搜索结果页：按标题、备注、目标与标签匹配。"""

from __future__ import annotations

import tkinter as tk


class SearchMixin:
    def render_search(self, parent: tk.Misc, query: str) -> None:
        result_tasks = self.db.list_tasks(include_completed=True, status="all", query=query)
        result_goals = self.db.list_goals(status="all", query=query)
        self.page_header(parent, "全局搜索", f"搜索「{query}」", "搜索标题、备注、标签、目标名称和目标说明。", (str(len(result_tasks) + len(result_goals)), "条结果"))
        row = 1
        if self.selected_task_ids:
            self.render_batch_bar(parent, row)
            row += 1
        self._label(parent, f"待办  {len(result_tasks)}", 10, self.colors["text"], True, bg=self.colors["bg"]).grid(row=row, column=0, sticky="w", pady=(0, 9))
        row += 1
        if result_tasks:
            task_block = tk.Frame(parent, bg=self.colors["bg"])
            task_block.grid(row=row, column=0, sticky="ew")
            for task in result_tasks:
                self.task_row(task_block, task, selectable=True)
            row += 1
        else:
            self._label(parent, "没有匹配的待办。", 9, self.colors["text_soft"], False, bg=self.colors["bg"]).grid(row=row, column=0, sticky="w", padx=7, pady=(0, 18))
            row += 1
        self._label(parent, f"目标  {len(result_goals)}", 10, self.colors["text"], True, bg=self.colors["bg"]).grid(row=row, column=0, sticky="w", pady=(7, 9))
        row += 1
        if result_goals:
            for goal in result_goals:
                self.goal_card(parent, goal).grid(row=row, column=0, sticky="ew", pady=(0, 8))
                row += 1
        else:
            self._label(parent, "没有匹配的目标。", 9, self.colors["text_soft"], False, bg=self.colors["bg"]).grid(row=row, column=0, sticky="w", padx=7)
