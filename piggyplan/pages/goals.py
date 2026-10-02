"""长期目标页：卡片、详情与列表/看板模式。"""

from __future__ import annotations

import tkinter as tk
from typing import Any
from ..ui.widgets import Card
from ..util import category_label, date_text


class GoalsMixin:
    def render_goals(self, parent: tk.Misc) -> None:
        goals = self.db.list_goals(status="active")
        active_count = len(goals)
        average = round(sum(goal["progress"] for goal in goals) / active_count) if active_count else 0
        self.page_header(parent, "长期方向", "长期目标", "把长期方向拆成一步步可以完成的待办。", (f"{active_count} 个", f"进行中目标 · 平均 {average}%"))
        toolbar = tk.Frame(parent, bg=self.colors["bg"])
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 17))
        self._label(toolbar, "选择一个目标，查看进度与下一步。", 9, self.colors["text_soft"], False, bg=self.colors["bg"]).pack(side="left")
        filter_bar = tk.Frame(parent, bg=self.colors["bg"])
        filter_bar.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self._label(filter_bar, "状态", 8, self.colors["text_faint"], True, bg=self.colors["bg"]).pack(side="left", padx=(0, 6))
        for value, title in (("active", "进行中"), ("all", "全部"), ("achieved", "已达成")):
            self._button(filter_bar, title, lambda value=value: self._set_goal_status(value), "primary" if getattr(self, "goal_status", "active") == value else "ghost").pack(side="left", padx=(0, 3))
        self._label(filter_bar, "分类", 8, self.colors["text_faint"], True, bg=self.colors["bg"]).pack(side="left", padx=(19, 6))
        for value, title in (("all", "全部"), ("work", category_label("work")), ("life", category_label("life"))):
            self._button(filter_bar, title, lambda value=value: self._set_goal_category(value), "primary" if getattr(self, "goal_category", "all") == value else "ghost").pack(side="left", padx=(0, 3))
        selected_status = getattr(self, "goal_status", "active")
        selected_category = getattr(self, "goal_category", "all")
        goals = self.db.list_goals(status=selected_status, category=selected_category)
        grid = tk.Frame(parent, bg=self.colors["bg"])
        grid.grid(row=3, column=0, sticky="ew")
        grid.grid_columnconfigure(0, weight=1)
        if not goals:
            self.empty_state(grid, "还没有符合条件的目标", "设定一个长期目标，把它拆成具体待办。", self.open_new_goal)
            return
        for index, goal in enumerate(goals):
            self.goal_card(grid, goal).grid(row=index, column=0, sticky="ew")

    def goal_card(self, parent: tk.Misc, goal: dict[str, Any]) -> tk.Frame:
        c = self.colors
        bg = parent.cget("bg")
        outer = tk.Frame(parent, bg=bg, cursor="hand2")
        outer.grid_columnconfigure(0, weight=1, minsize=0)
        body = tk.Frame(outer, bg=bg)
        body.grid(row=0, column=0, sticky="ew", pady=(22, 18), padx=(0, 22))
        title = self._label(body, goal["title"], 13, c["text"], True, bg=bg, anchor="w", justify="left", width=1)
        title.pack(fill="x")
        title.bind("<Configure>", lambda e: title.configure(wraplength=max(160, e.width)))
        note = self._label(body, goal["note"] or "添加关联待办，开始推进这个目标。", 10, c["text_soft"], bg=bg, justify="left", anchor="w", width=1)
        note.pack(fill="x", pady=(8, 10))
        note.bind("<Configure>", lambda e: note.configure(wraplength=max(160, e.width)))
        values = [category_label(goal["category"]), "已达成" if goal["status"] == "achieved" else "进行中"]
        if goal["priority"] == "high":
            values.append("高优先级")
        if goal.get("planned_finish_date"):
            values.append(date_text(goal["planned_finish_date"]))
        self._label(body, "   ".join(values), 9, c["text_soft"], bg=bg, anchor="w", width=1).pack(fill="x")
        progress = tk.Frame(outer, bg=bg)
        progress.grid(row=0, column=1, sticky="ne", pady=22)
        self._label(progress, f"{goal['progress']}%", 20, c["strong"], True, bg=bg).pack(anchor="e")
        self._label(progress, f"{goal['completed']}/{goal['total']} 待办完成", 9, c["text_soft"], bg=bg).pack(anchor="e", pady=(5, 8))
        edit = self._button(progress, "编辑", lambda gid=goal["id"]: self.open_goal_dialog(gid), "ghost")
        edit.pack(anchor="e")
        track = tk.Frame(outer, bg=c["line"], height=3)
        track.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        tk.Frame(track, bg=c["accentDeep"], height=3).place(relwidth=goal["progress"] / 100, relheight=1)
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
        bg = self.colors["bg"]
        self._button(parent, "‹ 返回长期目标", lambda: self.navigate("goals"), "link").grid(row=0, column=0, sticky="w", pady=(0, 18))
        header = self.page_header(parent, "", goal["title"], goal["note"] or "通过关联待办推进这个目标。", (f"{goal['progress']}%", f"{goal['completed']}/{goal['total']} 待办完成"))
        header.grid_configure(row=1)
        meta = tk.Frame(parent, bg=bg)
        meta.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        values = [category_label(goal["category"]), "已达成" if goal["status"] == "achieved" else "进行中"]
        if goal["priority"] == "high":
            values.append("高优先级")
        if goal.get("planned_finish_date"):
            values.append("计划完成 " + date_text(goal["planned_finish_date"]))
        self._label(meta, "   ".join(values), 9, self.colors["text_soft"], bg=bg).pack(side="left")
        self._button(meta, "编辑", lambda: self.open_goal_dialog(goal_id), "outline").pack(side="right")
        if goal["status"] == "active":
            self._button(meta, "达成目标", lambda: self.confirm_goal_achieve(goal_id), "soft").pack(side="right", padx=(0, 9))
        else:
            self._button(meta, "恢复进行中", lambda: self.db.restore_goal(goal_id) or self.render(), "soft").pack(side="right", padx=(0, 9))
        track = tk.Frame(parent, bg=self.colors["line"], height=3)
        track.grid(row=3, column=0, sticky="ew", pady=(0, 24))
        tk.Frame(track, bg=self.colors["accentDeep"], height=3).place(relwidth=goal["progress"] / 100, relheight=1)
        toolbar = tk.Frame(parent, bg=bg)
        toolbar.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        self._label(toolbar, f"关联待办  {goal['total']}", 11, self.colors["text"], True, bg=bg).pack(side="left")
        for mode, text in (("board", "看板"), ("list", "列表")):
            self._button(toolbar, text, lambda mode=mode: self._set_goal_mode(mode), "soft" if self.goal_mode == mode else "ghost").pack(side="right", padx=(4, 0))
        tasks = self.db.list_tasks(goal_id=goal_id, include_completed=True, status="all")
        todo = [task for task in tasks if task["status"] == "todo"]
        done = [task for task in tasks if task["status"] == "completed"]
        if self.goal_mode == "board":
            self.render_board(parent, tasks, 5, goal_id)
        else:
            body = tk.Frame(parent, bg=bg)
            body.grid(row=5, column=0, sticky="ew")
            for task in todo:
                self.task_row(body, task)
            if not todo:
                self.empty_state(body, "这个目标还没有未完成待办", "添加一个具体动作，让目标开始向前。", lambda: self.open_new_task(goal_id=goal_id))
            completed = tk.Frame(body, bg=bg)
            completed.pack(fill="x", pady=(22, 0))
            self._button(completed, f"{'▾' if self.completed_open else '›'} 已完成 {len(done)}", self.toggle_completed, "ghost").pack(anchor="w", pady=(0, 7))
            if self.completed_open:
                for task in done:
                    self.task_row(completed, task, compact=True)
        delete_row = tk.Frame(parent, bg=bg)
        delete_row.grid(row=6, column=0, sticky="w", pady=(30, 0))
        self._button(delete_row, "删除目标", lambda: self.confirm_goal_delete(goal_id), "danger").pack(side="left")
