"""UI 原语：页头 / 分节标题 / 卡片 / 徽章 / 任务行 / 空状态，以及拖拽、右键、圈选绑定。

页面只消费这些原语，不直接拼 Frame；颜色与字号经 self.colors 与类常量获取
（Task 5 起改走 tokens）。"""

from __future__ import annotations

import tkinter as tk
from typing import Any
from ..tokens import RADIUS, SPACE
from ..util import category_label, date_text, offset_date, today_key
from .mascot import PigMark
from .widgets import Card, CheckCircle, Chip, HeartIcon, PillButton, SnoutIcon


class PrimitivesMixin:
    def page_header(self, parent: tk.Misc, eyebrow: str, title: str, description: str, stat: tuple[str, str] | None = None) -> tk.Frame:
        bg = parent.cget("bg")
        header = tk.Frame(parent, bg=bg)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 26))
        header.grid_columnconfigure(0, weight=1, minsize=0)
        heading = self._label(header, title, 26, self.colors["text"], True, bg=bg, anchor="w", width=1)
        heading.grid(row=0, column=0, sticky="ew")
        heading.bind("<Configure>", lambda e: heading.configure(wraplength=max(150, e.width)))
        copy = self._label(header, description, 10, self.colors["text_soft"], bg=bg, anchor="w", justify="left", width=1)
        copy.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        copy.bind("<Configure>", lambda e: copy.configure(wraplength=max(150, e.width)))
        if stat:
            summary = tk.Frame(header, bg=bg)
            summary.grid(row=0, column=1, rowspan=2, sticky="e", padx=(18, 0))
            self._label(summary, stat[0], 16, self.colors["strong"], True, bg=bg).pack(anchor="e")
            caption = self._label(summary, stat[1], 9, self.colors["text_soft"], bg=bg, justify="right", wraplength=155)
            caption.pack(anchor="e", pady=(4, 0))
        return header

    def section_title(self, parent: tk.Misc, title: str, count: int | None = None, action_text: str | None = None, command=None, color: str | None = None) -> tk.Frame:
        bg = parent.cget("bg")
        frame = tk.Frame(parent, bg=bg)
        left = tk.Frame(frame, bg=bg)
        left.pack(side="left", pady=(12, 9))
        self._label(left, title, 11, color or self.colors["text"], True, bg=bg).pack(side="left")
        if count is not None:
            self._label(left, str(count), 9, self.colors["text_soft"], bg=bg).pack(side="left", padx=8)
        if action_text and command:
            self._button(frame, action_text, command, "link").pack(side="right")
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
        bg = parent.cget("bg")
        frame = tk.Frame(parent, bg=bg, bd=0)
        frame.pack(fill="x")
        frame.grid_columnconfigure(1, weight=1, minsize=0)
        controls = tk.Frame(frame, bg=bg)
        controls.grid(row=0, column=0, sticky="n", pady=(15, 12), padx=(1, 14))
        if selectable:
            chosen = tk.BooleanVar(value=task["id"] in self.selected_task_ids)
            selector = tk.Checkbutton(controls, variable=chosen,
                command=lambda tid=task["id"], var=chosen: self._toggle_selection(tid, var.get()),
                bg=bg, activebackground=bg, selectcolor=colors["soft"], bd=0, highlightthickness=0)
            selector.pack(side="left", padx=(0, 5))
        check = CheckCircle(controls, app=self, completed=task["status"] == "completed",
                            command=lambda tid=task["id"]: self.toggle_task(tid))
        check.pack(side="left")
        middle = tk.Frame(frame, bg=bg, cursor="hand2")
        middle.grid(row=0, column=1, sticky="ew", pady=(12, 13))
        title_row = tk.Frame(middle, bg=bg)
        title_row.pack(fill="x")
        if task["priority"] == "high" and task["status"] != "completed":
            HeartIcon(title_row, app=self, size=11).pack(side="left", padx=(0, 7))
        title = self._label(title_row, task["title"], 11,
                            colors["text_soft"] if task["status"] == "completed" else colors["text"],
                            bg=bg, anchor="w", justify="left", width=1)
        title.pack(side="left", fill="x", expand=True)
        title.bind("<Configure>", lambda e: title.configure(wraplength=max(110, e.width)))
        if task.get("note") and not compact:
            note = self._label(middle, task["note"].splitlines()[0][:150], 9, colors["text_soft"],
                                bg=bg, anchor="w", width=1)
            note.pack(fill="x", pady=(5, 0))
        parts = []
        if show_date:
            parts.append(date_text(task.get("planned_date")))
        parts.append(category_label(task["category"]))
        parts.extend(f"#{tag}" for tag in task.get("tags", [])[:2])
        if task.get("goal_title"):
            parts.append("◎ " + task["goal_title"])
        if task.get("subtasks"):
            done = sum(1 for step in task["subtasks"] if step["completed"])
            parts.append(f"{done}/{len(task['subtasks'])} 步骤")
        meta = self._label(middle, "   ".join(parts), 9, colors["text_soft"], bg=bg, anchor="w", width=1)
        meta.pack(fill="x", pady=(6, 0))
        actions = tk.Frame(frame, bg=bg)
        actions.grid(row=0, column=2, sticky="ne", pady=10, padx=(10, 0))
        self._button(actions, "编辑", lambda tid=task["id"]: self.open_task_dialog(tid), "ghost").pack(side="left")
        self._button(actions, "⋯", lambda tid=task["id"], widget=frame: self.open_context_menu(tid, widget), "ghost").pack(side="left")
        tk.Frame(frame, bg=colors["line"], height=1).grid(row=1, column=0, columnspan=3, sticky="ew")
        self._bind_right_click(frame, task["id"])
        frame._task_id = task["id"]
        for child in (frame, middle, title, meta):
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
        bg = parent.cget("bg")
        box = tk.Frame(parent, bg=bg)
        managers = {child.winfo_manager() for child in parent.winfo_children()}
        if "grid" in managers and "pack" not in managers:
            box.grid(sticky="ew", pady=12)
        else:
            box.pack(fill="x", pady=12)
        PigMark(box, app=self, variant="mascot").pack(pady=(25, 14))
        self._label(box, title, 13, self.colors["text"], True, bg=bg).pack()
        self._label(box, description, 10, self.colors["text_soft"], bg=bg, wraplength=400, justify="center").pack(pady=(8, 0))
        if command:
            caption = "新建目标" if "目标" in title else "新建待办"
            PillButton(box, app=self, text=caption, command=command, kind="soft").pack(pady=(18, 26))
