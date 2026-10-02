"""之后安排页：未安排 / 今天 / 明天 / 未来七天的分组视图。"""

from __future__ import annotations

import tkinter as tk
from typing import Any
from ..util import date_text, offset_date, today_key


class UpcomingMixin:
    def render_upcoming(self, parent: tk.Misc) -> None:
        self.page_header(parent, "轻量规划", "之后", "未来按日期展开，未安排的想法留在最底部，不占用计划完成率。", (str(len(self.db.list_tasks())), "项未来安排"))
        toolbar = tk.Frame(parent, bg=self.colors["bg"])
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        self._label(toolbar, "把未来安排放在合适的日期，今天只看今天。", 9, self.colors["text_soft"], False, bg=self.colors["bg"]).pack(side="left")
        self._button(toolbar, "+ 添加到明天", lambda: self.open_new_task(date_key=offset_date(1)), "outline").pack(side="right")
        tasks = self.db.list_tasks()
        groups: dict[str, list[dict[str, Any]]] = {}
        for task in tasks:
            if task.get("planned_date") and task["planned_date"] > today_key() or not task.get("planned_date"):
                groups.setdefault(task.get("planned_date") or "unplanned", []).append(task)
        keys = sorted((key for key in groups if key != "unplanned")) + (["unplanned"] if "unplanned" in groups else [])
        row = 2
        if not keys:
            self.empty_state(parent, "之后还没有安排", "把想法记录下来，或为待办选一个未来日期。", self.open_new_task)
            return
        for key in keys:
            title = "未安排" if key == "unplanned" else date_text(key)
            subtitle = "先记录，之后再决定" if key == "unplanned" else key
            self.section_title(parent, f"{title}  ·  {subtitle}", len(groups[key]), "添加", lambda value=None, key=key: self.open_new_task(date_key=None if key == "unplanned" else key)).grid(row=row, column=0, sticky="ew")
            row += 1
            block = tk.Frame(parent, bg=self.colors["bg"])
            block.grid(row=row, column=0, sticky="ew", pady=(0, 17))
            for task in sorted(groups[key], key=lambda item: self.db._task_sort_key(item, "upcoming")):
                self.task_row(block, task, show_date=False)
            row += 1
