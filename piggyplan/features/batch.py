"""批量操作与撤销：完成、改字段、改期、挂接目标、删除。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any
from ..ui.dialog import Dialog
from ..util import category_label, goal_choice_labels, offset_date, parse_date, today_key


class BatchMixin:
    def _selected_tasks(self) -> list[dict[str, Any]]:
        values = []
        for task_id in list(self.selected_task_ids):
            task = self.db.get_task(task_id)
            if task and task.get("status") != "deleted":
                values.append(task)
        return values

    def batch_complete(self) -> None:
        tasks = [task for task in self._selected_tasks() if task["status"] == "todo"]
        if not tasks:
            return
        for task in tasks:
            self.db.toggle_task(task["id"])
        ids = [task["id"] for task in tasks]
        self.selected_task_ids.clear()
        self.render()
        self.show_toast(f"已完成 {len(ids)} 项", undo_callback=lambda ids=ids: self._undo_batch_complete(ids))

    def _undo_batch_complete(self, task_ids: list[str]) -> None:
        for task_id in task_ids:
            task = self.db.get_task(task_id)
            if task and task["status"] == "completed":
                self.db.toggle_task(task_id)
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量完成")

    def batch_set(self, field: str, value: str) -> None:
        if field not in {"category", "priority"}:
            return
        tasks = self._selected_tasks()
        if not tasks:
            return
        snapshots = [(task["id"], task[field]) for task in tasks]
        for task in tasks:
            self.db.update_task(task["id"], {field: value})
        self.selected_task_ids.clear()
        self.render()
        label = {"category": category_label(value), "priority": "高优先级" if value == "high" else "普通优先级"}[field]
        self.show_toast(f"已将 {len(tasks)} 项设为{label}", undo_callback=lambda snapshots=snapshots, field=field: self._undo_batch_values(snapshots, field))

    def _undo_batch_values(self, snapshots: list[tuple[str, Any]], field: str) -> None:
        for task_id, value in snapshots:
            if self.db.get_task(task_id):
                self.db.update_task(task_id, {field: value})
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量修改")

    def batch_set_date(self) -> None:
        tasks = self._selected_tasks()
        if not tasks:
            return
        dialog = Dialog(self, "批量设置计划日期", "480x250")
        content = dialog.content
        self._label(content, "批量设置计划日期", 15, self.colors["text"], True, bg=self.colors["surface"]).pack(anchor="w", pady=(0, 5))
        self._label(content, f"修改已选择的 {len(tasks)} 项；未安排不计入计划完成率。", 9, self.colors["text_soft"], False, bg=self.colors["surface"], wraplength=430, justify="left").pack(anchor="w")
        row = tk.Frame(content, bg=self.colors["surface"])
        row.pack(fill="x", pady=16)
        date_var = tk.StringVar()
        ttk.Entry(row, textvariable=date_var, width=15).pack(side="left")
        for label, value in (("今天", today_key()), ("明天", offset_date(1)), ("未安排", "")):
            self._button(row, label, lambda value=value: date_var.set(value), "ghost").pack(side="left", padx=(6, 0))
        error = self._label(content, "", 9, self.colors["high_ink"], False, bg=self.colors["surface"])
        error.pack(anchor="w")
        footer = dialog.footer_actions

        def apply() -> None:
            value = date_var.get().strip() or None
            if value and not parse_date(value):
                error.configure(text="日期格式应为 YYYY-MM-DD")
                return
            snapshots = [(task["id"], task.get("planned_date")) for task in tasks]
            for task in tasks:
                self.db.update_task(task["id"], {"planned_date": value})
            dialog.destroy()
            self.selected_task_ids.clear()
            self.render()
            self.show_toast("批量计划日期已更新", undo_callback=lambda snapshots=snapshots: self._undo_batch_dates(snapshots))

        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=(0, 7))
        self._button(footer, "确认修改", apply, "primary").pack(side="right", padx=(0, 2))
        dialog.bind("<Return>", lambda _event: apply())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def _undo_batch_dates(self, snapshots: list[tuple[str, str | None]]) -> None:
        for task_id, value in snapshots:
            if self.db.get_task(task_id):
                self.db.update_task(task_id, {"planned_date": value})
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量日期修改")

    def batch_attach_goal(self) -> None:
        goals = self.db.list_goals(status="active")
        if not goals:
            messagebox.showinfo("没有进行中的目标", "请先创建一个进行中的长期目标。", parent=self)
            return
        if len(goals) == 1:
            self._batch_set_goal(goals[0]["id"])
            return
        dialog = Dialog(self, "挂载到目标", "460x230")
        self._label(dialog.content, "挂载到长期目标", 15, self.colors["text"], True, bg=self.colors["surface"]).pack(anchor="w", pady=(0, 16))
        values = goal_choice_labels(goals)
        selected = tk.StringVar(value=next(iter(values)))
        ttk.Combobox(dialog.content, textvariable=selected, values=list(values), state="readonly", width=1).pack(fill="x")
        footer = dialog.footer_actions

        def apply() -> None:
            dialog.destroy()
            self._batch_set_goal(values[selected.get()])

        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=(0, 7))
        self._button(footer, "确认挂载", apply, "primary").pack(side="right", padx=(0, 2))

    def _batch_set_goal(self, goal_id: str | None) -> None:
        tasks = self._selected_tasks()
        if not tasks:
            return
        snapshots = [(task["id"], task.get("goal_id")) for task in tasks]
        for task in tasks:
            self.db.update_task(task["id"], {"goal_id": goal_id})
        self.selected_task_ids.clear()
        self.render()
        self.show_toast("目标关联已批量更新", undo_callback=lambda snapshots=snapshots: self._undo_batch_goal(snapshots))

    def _undo_batch_goal(self, snapshots: list[tuple[str, str | None]]) -> None:
        for task_id, value in snapshots:
            if self.db.get_task(task_id):
                self.db.update_task(task_id, {"goal_id": value})
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量目标关联")

    def batch_delete(self) -> None:
        tasks = self._selected_tasks()
        if not tasks:
            return
        if not messagebox.askyesno("批量删除", f"确定删除已选择的 {len(tasks)} 项吗？删除前会保留计划历史。", parent=self):
            return
        for task in tasks:
            self.db.delete_task(task["id"])
        ids = [task["id"] for task in tasks]
        self.selected_task_ids.clear()
        self.render()
        self.show_toast(f"已删除 {len(ids)} 项", undo_callback=lambda ids=ids: self._undo_batch_delete(ids))

    def _undo_batch_delete(self, task_ids: list[str]) -> None:
        for task_id in task_ids:
            self.db.restore_task(task_id)
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量删除")
