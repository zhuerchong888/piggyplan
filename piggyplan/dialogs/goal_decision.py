"""目标达成/删除时的剩余待办处置对话框。"""

from __future__ import annotations

import tkinter as tk

from ..ui.dialog import Dialog
from ..ui.widgets import PillButton


class GoalDecisionMixin:
    def goal_decision_dialog(self, goal_id: str, action: str) -> None:
        goal = self.db.get_goal(goal_id)
        if not goal:
            return
        is_achieve = action == "achieve"
        dialog = Dialog(self, "达成长期目标" if is_achieve else "删除长期目标", "480x330" if is_achieve else "480x270")
        container = dialog.content
        title = "标记目标已达成" if is_achieve else "删除长期目标"
        self._label(container, title, 15, self.colors["text"], True).pack(anchor="w", padx=2, pady=(0, 4))
        if is_achieve:
            self._label(container, f"「{goal['title']}」还有 {goal['remaining']} 个未完成待办，请选择如何处理。", 9, self.colors["text_soft"], False, wraplength=416, justify="left").pack(anchor="w", padx=2, pady=(0, 13))
            choice = tk.StringVar(value="detach")
            options = [("detach", "转为独立待办", "待办保留，解除与该目标的关联"), ("complete", "全部标记为完成", "写入当前完成时间，并计入实际完成数量"), ("delete", "删除这些待办", "未完成待办移入删除状态，不计入完成数量")]
        else:
            self._label(container, f"「{goal['title']}」仍有关联待办，请选择处理方式。", 9, self.colors["text_soft"], False, wraplength=416, justify="left").pack(anchor="w", padx=2, pady=(0, 13))
            choice = tk.StringVar(value="detach")
            options = [("detach", "保留并转为独立待办", "关联待办本身不变，只解除目标关系"), ("delete", "删除未完成关联待办", "已完成待办保留，未完成待办移入删除状态")]
        body = tk.Frame(container, bg=self.colors["surface"])
        body.pack(fill="x", padx=2)
        for value, label, description in options:
            line = tk.Frame(body, bg=self.colors["surface"])
            line.pack(fill="x", pady=4)
            tk.Radiobutton(line, variable=choice, value=value, bg=self.colors["surface"], activebackground=self.colors["bg"], selectcolor=self.colors["surface"], highlightthickness=0).pack(side="left")
            copy = tk.Frame(line, bg=self.colors["surface"])
            copy.pack(side="left", padx=4)
            self._label(copy, label, 9, self.colors["text"], True, bg=self.colors["surface"]).pack(anchor="w")
            self._label(copy, description, 8, self.colors["text_soft"], False, bg=self.colors["surface"]).pack(anchor="w")
        footer = dialog.footer_actions

        def confirm() -> None:
            if is_achieve:
                self.db.achieve_goal(goal_id, choice.get())
                message = f"目标「{goal['title']}」已达成"
            else:
                self.db.delete_goal(goal_id, choice.get())
                self.selected_goal_id = None
                message = "长期目标已删除"
            dialog.destroy()
            self.render()
            self.show_toast(message)

        PillButton(footer, app=self, text="取消", command=dialog.destroy, kind="ghost").pack(side="right", padx=(0, 7))
        PillButton(footer, app=self, text="确认", command=confirm, kind="primary").pack(side="right", padx=(0, 2))
