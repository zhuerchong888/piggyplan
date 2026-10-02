"""单任务操作与撤销：完成/删除/优先级/改期/挂接目标/模板。"""

from __future__ import annotations

from tkinter import messagebox


class TaskActionsMixin:
    def toggle_task(self, task_id: str) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        previous = task["status"]
        self.db.toggle_task(task_id)
        self.render()
        self.show_toast("已完成" if previous == "todo" else "已撤销完成", undo_id=task_id, undo_status=previous)

    def _undo_task(self, task_id: str, previous_status: str | None) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        if task["status"] == "deleted":
            self.db.restore_task(task_id)
        elif previous_status == "todo" and task["status"] == "completed":
            self.db.toggle_task(task_id)
        elif previous_status == "completed" and task["status"] == "todo":
            self.db.toggle_task(task_id)
        if self.toast and self.toast.winfo_exists(): self.toast.destroy()
        self.render()
        self.show_toast("已撤回上一步操作")

    def delete_task(self, task_id: str) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        self.db.delete_task(task_id)
        self.render()
        self.show_toast(f"已移除「{task['title']}」", undo_id=task_id, undo_status=task["status"])

    def save_template(self, task_id: str) -> None:
        self.db.create_template(task_id)
        self.show_toast("已保存为任务模板")

    def delete_template(self, template_id: str) -> None:
        if messagebox.askyesno("删除模板", "确定删除这个任务模板吗？", parent=self):
            self.db.delete_template(template_id)
            self.render()
            self.show_toast("模板已删除")

    def set_task_priority(self, task_id: str, priority: str) -> None:
        task = self.db.get_task(task_id)
        if task:
            self.db.update_task(task_id, {"priority": priority})
            self.render()
            self.show_toast("优先级已更新")

    def set_task_date(self, task_id: str, planned_date: str | None) -> None:
        task = self.db.get_task(task_id)
        if task:
            self.db.update_task(task_id, {"planned_date": planned_date})
            self.render()
            self.show_toast("计划日期已更新")

    def toggle_task_goal(self, task_id: str) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        if task.get("goal_id"):
            self.db.update_task(task_id, {"goal_id": None})
            self.render()
            self.show_toast("已解除目标关联")
        else:
            active = self.db.list_goals(status="active")
            if len(active) == 1:
                self.db.update_task(task_id, {"goal_id": active[0]["id"]})
                self.render()
                self.show_toast(f"已挂载到「{active[0]['title']}」")
            else:
                self.open_task_dialog(task_id)

    def confirm_goal_achieve(self, goal_id: str) -> None:
        goal = self.db.get_goal(goal_id)
        if not goal:
            return
        if not goal["remaining"]:
            self.db.achieve_goal(goal_id, "detach")
            self.render()
            self.show_toast(f"目标「{goal['title']}」已达成")
            return
        self.goal_decision_dialog(goal_id, "achieve")

    def confirm_goal_delete(self, goal_id: str) -> None:
        goal = self.db.get_goal(goal_id)
        if goal:
            self.goal_decision_dialog(goal_id, "delete")
