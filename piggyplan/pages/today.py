"""Today: a continuous, quiet execution list."""
from __future__ import annotations
import tkinter as tk
from ..util import today_key, today_text


class TodayMixin:
    def render_today(self, parent: tk.Misc) -> None:
        tasks = self.db.list_tasks(mode="default")
        overdue = [t for t in tasks if t.get("planned_date") and t["planned_date"] < today_key()]
        planned = [t for t in tasks if t.get("planned_date") == today_key()]
        completed = self.db.completed_on(today_key())
        done_planned = sum(t.get("planned_date") == today_key() for t in completed)
        total = len(planned) + done_planned
        stats = self.db.weekly_stats()
        self.page_header(parent, "", "今天", today_text())
        summary = tk.Frame(parent, bg=self.colors["bg"])
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        for col, (label, value) in enumerate((("今日计划", total), ("今日完成", len(completed)), ("逾期待处理", len(overdue)), ("本周完成", stats["actual"]))):
            summary.grid_columnconfigure(col, weight=1)
            item = tk.Frame(summary, bg=self.colors["bg"])
            item.grid(row=0, column=col, sticky="w")
            self._label(item, str(value), 20, self.colors["strong"] if col == 1 else self.colors["text"], True).pack(anchor="w")
            self._label(item, label, 9, self.colors["text_soft"]).pack(anchor="w", pady=(5, 0))
        progress = tk.Frame(summary, bg=self.colors["line"], height=3)
        progress.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(20, 0))
        if total:
            tk.Frame(progress, bg=self.colors["accentDeep"], height=3).place(relwidth=done_planned / total, relheight=1)
        row = 2
        if overdue:
            self.section_title(parent, "逾期待处理", len(overdue), color=self.colors["high_ink"]).grid(row=row, column=0, sticky="ew")
            row += 1
            block = tk.Frame(parent, bg=self.colors["bg"])
            block.grid(row=row, column=0, sticky="ew", pady=(0, 20))
            for task in overdue:
                self.task_row(block, task)
            row += 1
        self.section_title(parent, "今日待办", len(planned), "添加到今天", lambda: self.open_new_task(date_key=today_key())).grid(row=row, column=0, sticky="ew")
        row += 1
        block = tk.Frame(parent, bg=self.colors["bg"])
        block.grid(row=row, column=0, sticky="ew")
        if planned:
            for task in planned:
                self.task_row(block, task, show_date=False)
        else:
            self.empty_state(block, "今天还没有安排", "记录一件要做的事，或从之后的安排中选择。", lambda: self.open_new_task(date_key=today_key()))
        row += 1
        completed_box = tk.Frame(parent, bg=self.colors["bg"])
        completed_box.grid(row=row, column=0, sticky="ew", pady=(24, 0))
        header = tk.Frame(completed_box, bg=self.colors["bg"])
        header.pack(fill="x")
        self._button(header, f"{'▾' if self.completed_open else '›'}  今天已完成  {len(completed)}", self.toggle_completed, "ghost").pack(side="left")
        if self.completed_open:
            for task in completed:
                self.task_row(completed_box, task, compact=True)
            if not completed:
                self._label(completed_box, "完成的事项会保留在这里。", 10, self.colors["text_soft"]).pack(anchor="w", pady=16)
