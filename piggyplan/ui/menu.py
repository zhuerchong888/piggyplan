"""任务卡右键上下文菜单。"""

from __future__ import annotations

import tkinter as tk
from typing import Any
from ..util import offset_date, today_key


class MenuMixin:
    def open_context_menu(self, task_id: str, event_or_widget: Any) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        menu = tk.Menu(self, tearoff=0, bg=self.colors["surface"], fg=self.colors["text"], activebackground=self.colors["soft"], activeforeground=self.colors["text"], bd=0, relief="flat", font=("Microsoft YaHei UI", 9))
        menu.add_command(label="完成" if task["status"] == "todo" else "撤销完成", command=lambda: self.toggle_task(task_id))
        menu.add_command(label="编辑", command=lambda: self.open_task_dialog(task_id))
        menu.add_separator()
        menu.add_command(label="设为高优" if task["priority"] != "high" else "设为普通", command=lambda: self.set_task_priority(task_id, "high" if task["priority"] != "high" else "normal"))
        menu.add_command(label="安排到今天", command=lambda: self.set_task_date(task_id, today_key()))
        menu.add_command(label="安排到明天", command=lambda: self.set_task_date(task_id, offset_date(1)))
        menu.add_command(label="选择日期…", command=lambda: self.open_task_dialog(task_id))
        menu.add_separator()
        menu.add_command(label="解除目标关联" if task.get("goal_id") else "挂载到目标…", command=lambda: self.toggle_task_goal(task_id))
        menu.add_command(label="保存为模板", command=lambda: self.save_template(task_id))
        menu.add_separator()
        menu.add_command(label="删除", command=lambda: self.delete_task(task_id))
        if isinstance(event_or_widget, tk.Event):
            menu.tk_popup(event_or_widget.x_root, event_or_widget.y_root)
        else:
            widget = event_or_widget
            x = widget.winfo_rootx() + widget.winfo_width() - 10
            y = widget.winfo_rooty() + widget.winfo_height() - 4
            menu.tk_popup(x, y)
        menu.grab_release()
