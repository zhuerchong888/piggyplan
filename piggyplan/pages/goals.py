"""长期目标页：卡片、详情与列表/看板模式。"""

from __future__ import annotations

import tkinter as tk
from typing import Any
from ..util import date_text


class GoalsMixin:
    def render_goals(self, parent: tk.Misc) -> None:
        goals = self.db.list_goals(status="active")
        active_count = len(goals)
        average = round(sum(goal["progress"] for goal in goals) / active_count) if active_count else 0
        self.page_header(parent, "长期方向", "长期目标", "目标只负责承载成果，真正推进它的，是一件件进入待办的具体动作。", (f"{active_count} 个", f"进行中目标 · 平均 {average}%"))
        toolbar = tk.Frame(parent, bg=self.colors["bg"])
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 17))
        self._label(toolbar, "所有目标共用工作 / 生活与高 / 普通两套简单规则。", 9, self.colors["text_soft"], False, bg=self.colors["bg"]).pack(side="left")
        self._button(toolbar, "+ 新建目标", self.open_new_goal, "primary").pack(side="right")
        filter_bar = tk.Frame(parent, bg=self.colors["bg"])
        filter_bar.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self._label(filter_bar, "状态", 8, self.colors["text_faint"], True, bg=self.colors["bg"]).pack(side="left", padx=(0, 6))
        for value, title in (("active", "进行中"), ("all", "全部"), ("achieved", "已达成")):
            self._button(filter_bar, title, lambda value=value: self._set_goal_status(value), "primary" if getattr(self, "goal_status", "active") == value else "ghost").pack(side="left", padx=(0, 3))
        self._label(filter_bar, "分类", 8, self.colors["text_faint"], True, bg=self.colors["bg"]).pack(side="left", padx=(19, 6))
        for value, title in (("all", "全部"), ("work", "工作"), ("life", "生活")):
            self._button(filter_bar, title, lambda value=value: self._set_goal_category(value), "primary" if getattr(self, "goal_category", "all") == value else "ghost").pack(side="left", padx=(0, 3))
        selected_status = getattr(self, "goal_status", "active")
        selected_category = getattr(self, "goal_category", "all")
        goals = self.db.list_goals(status=selected_status, category=selected_category)
        grid = tk.Frame(parent, bg=self.colors["bg"])
        grid.grid(row=3, column=0, sticky="ew")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        if not goals:
            self.empty_state(grid, "还没有符合条件的目标", "设定一个长期目标，把它拆成具体待办。", self.open_new_goal)
            return
        for index, goal in enumerate(goals):
            self.goal_card(grid, goal).grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0, 7) if index % 2 == 0 else (7, 0), pady=(0, 13))

    def goal_card(self, parent: tk.Misc, goal: dict[str, Any]) -> tk.Frame:
        colors = self.colors
        outer = tk.Frame(parent, bg=self.colors["surface"], highlightthickness=0, cursor="hand2")
        stripe = tk.Frame(outer, bg=self.colors["high"] if goal["priority"] == "high" else colors["accent"], height=4)
        stripe.pack(fill="x")
        body = tk.Frame(outer, bg=self.colors["surface"])
        body.pack(fill="both", expand=True, padx=15, pady=13)
        top = tk.Frame(body, bg=self.colors["surface"])
        top.pack(fill="x")
        title = self._label(top, goal["title"], 11, self.colors["text"], True, bg=self.colors["surface"], anchor="w")
        title.pack(side="left", fill="x", expand=True)
        self.badge(top, "已达成" if goal["status"] == "achieved" else "进行中", "#E8F5EE" if goal["status"] == "achieved" else colors["soft"], "#4A9B72" if goal["status"] == "achieved" else "#A04868").pack(side="right")
        badges = tk.Frame(body, bg=self.colors["surface"])
        badges.pack(fill="x", pady=(8, 0))
        self.badge(badges, "生活" if goal["category"] == "life" else "工作", "#FDF2E4" if goal["category"] == "life" else colors["soft"], "#A06830" if goal["category"] == "life" else "#A04868").pack(side="left", padx=(0, 6))
        if goal["priority"] == "high":
            self.badge(badges, "高优先级", "#FFF0F0", "#C95D61").pack(side="left")
        self._label(body, goal["note"] or "还没有目标说明，把它拆成下一步就好。", 8, self.colors["text_soft"], False, bg=self.colors["surface"], anchor="w", wraplength=330, justify="left").pack(fill="x", pady=(13, 14))
        progress_row = tk.Frame(body, bg=self.colors["surface"])
        progress_row.pack(fill="x")
        self._label(progress_row, f"{goal['progress']}%", 18, colors["strong"], True, bg=self.colors["surface"]).pack(side="left")
        self._label(progress_row, f"{goal['completed']} / {goal['total']} 个待办完成", 8, self.colors["text_soft"], False, bg=self.colors["surface"]).pack(side="right", pady=5)
        track = tk.Frame(body, bg=self.colors["surface_soft"], height=8)
        track.pack(fill="x", pady=(8, 0))
        fill = tk.Frame(track, bg=self.colors["success"] if goal["status"] == "achieved" else colors["accent"], height=8)
        fill.place(relwidth=max(0, min(1, goal["progress"] / 100)), relheight=1)
        footer = tk.Frame(body, bg=self.colors["surface"])
        footer.pack(fill="x", pady=(13, 0))
        self._label(footer, f"◷  {date_text(goal['planned_finish_date']) if goal.get('planned_finish_date') else '暂无计划完成日期'}", 8, self.colors["text_faint"], False, bg=self.colors["surface"]).pack(side="left")
        edit = self._button(footer, "编辑", lambda gid=goal["id"]: self.open_goal_dialog(gid), "ghost")
        edit.pack(side="right")
        self._bind_click_recursive(outer, lambda gid=goal["id"]: self.open_goal_detail(gid), skip=(edit,))
        return outer

    def _bind_click_recursive(self, widget: tk.Misc, callback, skip: tuple[tk.Misc, ...] = ()) -> None:
        if widget not in skip:
            widget.bind("<Button-1>", lambda _event: callback())
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback, skip)

    def render_goal_detail(self, parent: tk.Misc, goal_id: str) -> None:
        goal = self.db.get_goal(goal_id)
        if not goal:
            self.selected_goal_id = None
            self.render_goals(parent)
            return
        back = self._button(parent, "‹  返回长期目标", lambda: self.navigate("goals"), "link")
        back.grid(row=0, column=0, sticky="w", pady=(0, 15))
        summary = tk.Frame(parent, bg=self.colors["surface"], highlightthickness=0)
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 22))
        summary.grid_columnconfigure(0, weight=1)
        info = tk.Frame(summary, bg=self.colors["surface"])
        info.grid(row=0, column=0, sticky="ew", padx=18, pady=17)
        self._label(info, goal["title"], 18, self.colors["text"], True, bg=self.colors["surface"]).pack(anchor="w")
        badges = tk.Frame(info, bg=self.colors["surface"])
        badges.pack(anchor="w", pady=(8, 0))
        self.badge(badges, "生活" if goal["category"] == "life" else "工作", "#FDF2E4" if goal["category"] == "life" else self.colors["soft"], "#A06830" if goal["category"] == "life" else "#A04868").pack(side="left", padx=(0, 6))
        if goal["priority"] == "high": self.badge(badges, "高优先级", "#FFF0F0", "#C95D61").pack(side="left", padx=(0, 6))
        self.badge(badges, "已达成" if goal["status"] == "achieved" else "进行中", "#E8F5EE" if goal["status"] == "achieved" else self.colors["soft"], "#4A9B72" if goal["status"] == "achieved" else "#A04868").pack(side="left")
        self._label(info, goal["note"] or "这个目标还没有说明。", 9, self.colors["text_soft"], False, bg=self.colors["surface"], wraplength=610, justify="left").pack(anchor="w", pady=(10, 10))
        self._label(info, f"◷  {('计划完成 ' + date_text(goal['planned_finish_date'])) if goal.get('planned_finish_date') else '暂未设置计划完成日期'}     ✓  {goal['completed']} / {goal['total']} 个待办", 8, self.colors["text_faint"], False, bg=self.colors["surface"]).pack(anchor="w")
        progress = tk.Frame(summary, bg=self.colors["surface"])
        progress.grid(row=0, column=1, sticky="e", padx=22, pady=17)
        self._label(progress, f"{goal['progress']}%", 28, self.colors["strong"], True, bg=self.colors["surface"]).pack(anchor="e")
        self._label(progress, "自动进度", 8, self.colors["text_soft"], False, bg=self.colors["surface"]).pack(anchor="e")
        buttons = tk.Frame(progress, bg=self.colors["surface"])
        buttons.pack(anchor="e", pady=(9, 0))
        self._button(buttons, "编辑", lambda gid=goal_id: self.open_goal_dialog(gid), "outline").pack(side="left", padx=(0, 5))
        if goal["status"] == "active": self._button(buttons, "达成目标", lambda gid=goal_id: self.confirm_goal_achieve(gid), "primary").pack(side="left")
        else: self._button(buttons, "恢复进行中", lambda gid=goal_id: self.db.restore_goal(gid) or self.render(), "outline").pack(side="left")
        toolbar = tk.Frame(parent, bg=self.colors["bg"])
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 13))
        self._label(toolbar, f"关联待办 · {goal['total']} 项", 9, self.colors["text_soft"], True, bg=self.colors["bg"]).pack(side="left")
        self._button(toolbar, "+ 新增关联待办", lambda gid=goal_id: self.open_new_task(goal_id=gid), "outline").pack(side="right")
        self._button(toolbar, "看板", lambda: self._set_goal_mode("board"), "primary" if self.goal_mode == "board" else "ghost").pack(side="right", padx=(0, 4))
        self._button(toolbar, "列表", lambda: self._set_goal_mode("list"), "primary" if self.goal_mode == "list" else "ghost").pack(side="right", padx=(0, 3))
        tasks = self.db.list_tasks(goal_id=goal_id, include_completed=True, status="all")
        todo = [task for task in tasks if task["status"] == "todo"]
        done = [task for task in tasks if task["status"] == "completed"]
        if self.goal_mode == "board":
            self.render_board(parent, tasks, 3, goal_id)
        else:
            body = tk.Frame(parent, bg=self.colors["bg"])
            body.grid(row=3, column=0, sticky="ew")
            self._label(body, f"待办  {len(todo)}", 10, self.colors["text"], True, bg=self.colors["bg"]).pack(anchor="w", pady=(0, 8))
            if todo:
                for task in todo:
                    self.task_row(body, task)
            else:
                self.empty_state(body, "这个目标还没有未完成待办", "新增一个具体动作，让目标开始向前。", lambda gid=goal_id: self.open_new_task(goal_id=gid))
            completed = tk.Frame(body, bg=self.colors["surface_soft"], highlightthickness=0)
            completed.pack(fill="x", pady=(17, 0))
            self._button(completed, f"{'▾' if self.completed_open else '›'}  已完成  {len(done)}", self.toggle_completed, "ghost").pack(side="left", padx=8, pady=6)
            if self.completed_open:
                for task in done:
                    self.task_row(completed, task, compact=True)
        delete_row = tk.Frame(parent, bg=self.colors["bg"])
        delete_row.grid(row=4, column=0, sticky="w", pady=(22, 0))
        self._button(delete_row, "删除目标", lambda gid=goal_id: self.confirm_goal_delete(gid), "danger").pack(side="left")
        self._label(delete_row, "删除前会让你选择如何处理关联待办。", 8, self.colors["text_faint"], False, bg=self.colors["bg"]).pack(side="left", padx=9)
