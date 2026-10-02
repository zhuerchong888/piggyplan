"""UI 原语：页头 / 分节标题 / 卡片 / 徽章 / 任务行 / 空状态，以及拖拽、右键、圈选绑定。

页面只消费这些原语，不直接拼 Frame；颜色与字号经 self.colors 与类常量获取
（Task 5 起改走 tokens）。"""

from __future__ import annotations

import tkinter as tk
from typing import Any
from ..tokens import RADIUS, SPACE
from ..util import date_text, offset_date, today_key
from .mascot import PigMark
from .widgets import Card, CheckCircle, Chip, HeartIcon, PillButton, SnoutIcon


class PrimitivesMixin:
    def page_header(self, parent: tk.Misc, eyebrow: str, title: str, description: str, stat: tuple[str, str] | None = None) -> tk.Frame:
        header = tk.Frame(parent, bg=self.colors["bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 22))
        header.grid_columnconfigure(0, weight=1)
        label = self._label(header, f"PIGGY MOMENT · {eyebrow.upper()}", 8, self.colors["strong"], True)
        label.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self._label(header, title, 22, self.colors["text"], True).grid(row=1, column=0, sticky="w")
        self._label(header, description, 9, self.colors["text_soft"], False, wraplength=610, justify="left").grid(row=2, column=0, sticky="w", pady=(6, 0))
        if stat:
            stat_box = tk.Frame(header, bg=self.colors["soft"], highlightthickness=0)
            stat_box.grid(row=0, column=1, rowspan=3, sticky="e", padx=(18, 0))
            self._label(stat_box, stat[0], 19, self.colors["strong"], True, bg=self.colors["soft"]).pack(anchor="e", padx=18, pady=(13, 0))
            self._label(stat_box, stat[1], 8, self.colors["text_soft"], False, bg=self.colors["soft"]).pack(anchor="e", padx=18, pady=(0, 13))
        return header

    def section_title(self, parent: tk.Misc, title: str, count: int | None = None, action_text: str | None = None, command=None, color: str | None = None) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.colors["bg"])
        left = tk.Frame(frame, bg=self.colors["bg"])
        left.pack(side="left")
        SnoutIcon(left, app=self, size=14).pack(side="left", padx=(0, 9))
        self._label(left, title, 10, color or self.colors["text"], True).pack(side="left")
        if count is not None:
            self._label(left, str(count), 8, self.colors["text_faint"], False).pack(side="left", padx=8)
        if action_text and command:
            self._button(frame, f"+ {action_text}", command, "link").pack(side="right")
        return frame

    _card_tone = "surface"
    _card_stroke = False
    _card_hover = True

    def card(self, parent: tk.Misc, padx: int = 16, pady: int = 14) -> tk.Frame:
        box = Card(parent, app=self, tone=self._card_tone, radius=RADIUS["card"],
                   padding=(padx, pady), stroke=self._card_stroke, hoverable=self._card_hover)
        box.pack(fill="x", pady=(0, SPACE["2"]))
        return box.body

    def badge(self, parent: tk.Misc, text: str, bg: str | None = None, fg: str | None = None):
        return Chip(parent, app=self, text=text, fill=bg, foreground=fg)

    def _scrollable_task_holder(self, parent: tk.Misc) -> tk.Frame:
        holder = tk.Frame(parent, bg=self.colors["bg"])
        holder.pack(fill="both", expand=True)
        return holder

    def task_row(self, parent: tk.Misc, task: dict[str, Any], show_date: bool = True, compact: bool = False, selectable: bool = False) -> tk.Frame:
        colors = self.colors
        frame = Card(parent, app=self, tone="surface", hoverable=True, padding=(12, 11))
        frame.pack(fill="x", pady=(0, 9))
        frame.body.configure(cursor="hand2")
        body = frame.body
        if selectable:
            chosen = tk.BooleanVar(value=task["id"] in self.selected_task_ids)
            selector = tk.Checkbutton(body, variable=chosen, command=lambda tid=task["id"], var=chosen: self._toggle_selection(tid, var.get()), bg=self.colors["surface"], activebackground=self.colors["surface"], selectcolor=self.colors["surface"], bd=0, highlightthickness=0)
            selector.pack(side="left", padx=(0, 6))
        check = CheckCircle(body, app=self, completed=task["status"] == "completed", command=lambda tid=task["id"]: self.toggle_task(tid))
        check.pack(side="left", padx=(0, 11))
        middle = tk.Frame(body, bg=self.colors["surface"])
        middle.pack(side="left", fill="x", expand=True)
        title_row = tk.Frame(middle, bg=self.colors["surface"])
        title_row.pack(fill="x")
        if task["priority"] == "high" and task["status"] != "completed":
            HeartIcon(title_row, app=self, size=12).pack(side="left", padx=(0, 5))
        title = self._label(title_row, task["title"], 10, self.colors["text_soft"] if task["status"] == "completed" else self.colors["text"], True, bg=self.colors["surface"], anchor="w")
        title.pack(side="left", fill="x", expand=True)
        if task.get("note") and not compact:
            self._label(middle, task["note"], 8, self.colors["text_soft"], False, bg=self.colors["surface"], anchor="w").pack(fill="x", pady=(3, 0))
        meta = tk.Frame(middle, bg=self.colors["surface"])
        meta.pack(fill="x", pady=(6, 0))
        if show_date:
            planned = task.get("planned_date")
            overdue = planned and planned < today_key() and task["status"] == "todo"
            date_color = colors["high_ink"] if overdue else colors["strong"] if planned == today_key() else colors["warning_ink"] if planned == offset_date(1) else colors["text_faint"]
            self._label(meta, f"◷  {date_text(planned)}", 8, date_color, bool(overdue), bg=self.colors["surface"]).pack(side="left", padx=(0, 11))
        self.badge(meta, "生活" if task["category"] == "life" else "工作", "#FDF2E4" if task["category"] == "life" else colors["soft"], "#A06830" if task["category"] == "life" else "#A04868").pack(side="left", padx=(0, 6))
        for tag in task.get("tags", [])[:2 if not compact else 1]:
            self.badge(meta, f"#{tag}", "#F5EEF0", "#8B6B73").pack(side="left", padx=(0, 5))
        if task.get("goal_title"):
            self.badge(meta, f"◎ {task['goal_title']}", colors["soft"], "#A04868").pack(side="left", padx=(0, 5))
        if task.get("subtasks"):
            done = sum(1 for step in task["subtasks"] if step["completed"])
            self._label(meta, f"☷ {done}/{len(task['subtasks'])}", 8, self.colors["text_faint"], False, bg=self.colors["surface"]).pack(side="left")
        actions = tk.Frame(body, bg=self.colors["surface"])
        actions.pack(side="right", padx=(6, 0))
        self._button(actions, "详情", lambda tid=task["id"]: self.open_task_dialog(tid), "ghost").pack(side="left")
        self._button(actions, "⋮", lambda tid=task["id"], widget=frame: self.open_context_menu(tid, widget), "ghost").pack(side="left")
        self._bind_right_click(frame, task["id"])
        frame._task_id = task["id"]  # type: ignore[attr-defined]
        frame.set_size()
        for child in (frame, body, middle, title, meta):
            child.bind("<Double-Button-1>", lambda _event, tid=task["id"]: self.open_task_dialog(tid))
            child.bind("<ButtonPress-1>", lambda event, tid=task["id"], row=frame: self._drag_start(event, tid, row), add="+")
            child.bind("<B1-Motion>", self._drag_motion, add="+")
            child.bind("<ButtonRelease-1>", self._drag_release, add="+")
        return frame

    def _drag_start(self, event: tk.Event, task_id: str, row: tk.Widget) -> None:
        self._drag_task_id = task_id
        self._drag_widget = row
        self._drag_start_y = int(event.y_root)

    def _drag_motion(self, event: tk.Event) -> None:
        if not self._drag_widget or abs(int(event.y_root) - self._drag_start_y) < 5:
            return
        try:
            self._drag_widget.configure(highlightbackground=self.colors["strong"], highlightthickness=2)
        except tk.TclError:
            pass

    def _drag_release(self, event: tk.Event) -> None:
        task_id = self._drag_task_id
        row = self._drag_widget
        self._drag_task_id = None
        self._drag_widget = None
        if not task_id or not row or abs(int(event.y_root) - self._drag_start_y) < 5:
            return
        parent = row.master
        siblings = [child for child in parent.winfo_children() if getattr(child, "_task_id", None)]
        ordered = [getattr(child, "_task_id") for child in siblings]
        if task_id not in ordered:
            return
        ordered.remove(task_id)
        insert_at = len(ordered)
        target_task_id: str | None = None
        for child in siblings:
            child_id = getattr(child, "_task_id")
            if child_id == task_id:
                continue
            middle = child.winfo_rooty() + child.winfo_height() / 2
            if int(event.y_root) < middle:
                insert_at = ordered.index(child_id)
                target_task_id = child_id
                break
        ordered.insert(insert_at, task_id)
        dragged = self.db.get_task(task_id)
        target = self.db.get_task(target_task_id) if target_task_id else (self.db.get_task(ordered[-2]) if len(ordered) > 1 else None)
        if dragged and target and dragged["priority"] != target["priority"]:
            self.db.update_task(task_id, {"priority": target["priority"]})
        self.db.reorder_tasks(ordered)
        self.render()
        self.show_toast("任务顺序已更新")

    def _bind_right_click(self, widget: tk.Misc, task_id: str) -> None:
        widget.bind("<Button-3>", lambda event, tid=task_id: self.open_context_menu(tid, event))
        for child in widget.winfo_children():
            self._bind_right_click(child, task_id)

    def _toggle_selection(self, task_id: str, selected: bool) -> None:
        if selected:
            self.selected_task_ids.add(task_id)
        else:
            self.selected_task_ids.discard(task_id)
        self.render()

    def empty_state(self, parent: tk.Misc, title: str, description: str, command=None) -> None:
        box = Card(parent, app=self, tone="soft", stroke=True, padding=(24, 6))
        managers = {child.winfo_manager() for child in parent.winfo_children()}
        if "grid" in managers and "pack" not in managers:
            box.grid(sticky="ew", pady=4)
        else:
            box.pack(fill="x", pady=4)
        body_bg = box.body.cget("bg")
        PigMark(box.body, app=self, variant="mascot").pack(pady=(18, 6))
        box.set_size()
        self._label(box.body, title, 10, self.colors["text"], True, bg=body_bg).pack()
        self._label(box.body, description, 8, self.colors["text_soft"], False, bg=body_bg).pack(pady=(4, 0))
        if command:
            PillButton(box.body, app=self, text="+ 新建第一条", command=command, kind="ghost", size="sm").pack(pady=(10, 18))
        else:
            self._label(box.body, "", 6, self.colors["text_soft"], False, bg=body_bg).pack(pady=(0, 14))
