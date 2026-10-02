"""今日清单页：逾期、今天、已完成三段。

页面只负责排布与调用，绘制一律走 PrimitivesMixin 的原语，数据一律走 self.db。"""

from __future__ import annotations

import tkinter as tk
from ..util import today_key


class TodayMixin:
    def render_today(self, parent: tk.Misc) -> None:
        tasks = self.db.list_tasks()
        overdue = [task for task in tasks if task.get("planned_date") and task["planned_date"] < today_key()]
        planned_today = [task for task in tasks if task.get("planned_date") == today_key()]
        completed_today = self.db.completed_on(today_key())
        planned_total = len(planned_today) + len([task for task in completed_today if task.get("planned_date") == today_key()])
        done_today = len([task for task in completed_today if task.get("planned_date") == today_key()])
        percent = round(done_today / planned_total * 100) if planned_total else 0
        self.page_header(parent, "执行焦点", "今天要做的事", "逾期不会自动消失，今天只保留真正需要你决定的下一步。", (f"{len(planned_today)} 项", f"今天待办 · {percent}% 已按计划完成"))
        if overdue:
            notice = tk.Frame(parent, bg="#FFF0F1", highlightthickness=0)
            notice.grid(row=1, column=0, sticky="ew", pady=(0, 18))
            self._label(notice, f"🐷  有 {len(overdue)} 项逾期，原计划日期会保留。先处理最重要的一件。", 9, self.HIGH, True, bg="#FFF0EE").pack(side="left", padx=13, pady=11)
            self._button(notice, "查看逾期", lambda: self.canvas.yview_moveto(0.15), "link").pack(side="right", padx=10)
        row = 2
        if overdue:
            self.section_title(parent, "逾期", len(overdue), color=self.HIGH).grid(row=row, column=0, sticky="ew")
            row += 1
            block = tk.Frame(parent, bg=self.BG)
            block.grid(row=row, column=0, sticky="ew", pady=(0, 20))
            for task in overdue:
                self.task_row(block, task)
            row += 1
        self.section_title(parent, "今天", len(planned_today), "添加到今天", lambda: self.open_new_task(date_key=today_key())).grid(row=row, column=0, sticky="ew")
        row += 1
        today_block = tk.Frame(parent, bg=self.BG)
        today_block.grid(row=row, column=0, sticky="ew")
        high = [task for task in planned_today if task["priority"] == "high"]
        normal = [task for task in planned_today if task["priority"] != "high"]
        if high:
            self._label(today_block, "高优先级", 9, self.TEXT_SOFT, True, bg=self.BG).pack(anchor="w", pady=(0, 7))
            for task in high:
                self.task_row(today_block, task, show_date=False)
        if normal:
            self._label(today_block, "普通优先级", 9, self.TEXT_SOFT, True, bg=self.BG).pack(anchor="w", pady=(11, 7) if high else (0, 7))
            for task in normal:
                self.task_row(today_block, task, show_date=False)
        if not planned_today:
            self.empty_state(today_block, "今天没有安排事项", "需要做的事可以先放到之后或未安排。", self.open_new_task)
        row += 1
        completed_box = tk.Frame(parent, bg=self.SURFACE_SOFT, highlightthickness=0)
        completed_box.grid(row=row, column=0, sticky="ew", pady=(20, 0))
        header = tk.Frame(completed_box, bg=self.SURFACE_SOFT)
        header.pack(fill="x")
        arrow = "▾" if self.completed_open else "›"
        self._button(header, f"{arrow}  已完成  {len(completed_today)}", self.toggle_completed, "ghost").pack(side="left", padx=9, pady=6)
        self._label(header, "今天实际完成", 8, self.TEXT_FAINT, False, bg=self.SURFACE_SOFT).pack(side="right", padx=12)
        if self.completed_open:
            for task in completed_today:
                self.task_row(completed_box, task, compact=True)
            if not completed_today:
                self.empty_state(completed_box, "今天还没有完成记录", "完成的事项会在这里留下痕迹。")
