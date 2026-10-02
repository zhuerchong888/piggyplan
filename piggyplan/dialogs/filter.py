"""全部待办的筛选对话框。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..ui.dialog import Dialog
from ..ui.widgets import PillButton


class FilterDialogMixin:
    def open_filter_dialog(self) -> None:
        dialog = Dialog(self, "筛选待办", "420x410")
        form = dialog.content
        self._label(form, "筛选待办", 16, self.colors["text"], True).pack(anchor="w", padx=2)
        self._label(form, "临时筛选不会改变任务本身。", 9, self.colors["text_soft"], False).pack(anchor="w", padx=2, pady=(3, 17))
        variables: dict[str, tk.StringVar] = {}
        choices = [("category", "分类", [("all", "全部分类"), ("work", "工作"), ("life", "生活")]), ("priority", "优先级", [("all", "全部优先级"), ("high", "高优先级"), ("normal", "普通优先级")]), ("goal", "目标关系", [("all", "全部待办"), ("linked", "已关联目标"), ("standalone", "独立待办")]), ("status", "状态", [("todo", "待办"), ("completed", "已完成"), ("all", "全部状态")]), ("tag", "标签", [("all", "全部标签")] + [(tag, f"#{tag}") for tag in self.db.all_tags()])]
        for key, title, values in choices:
            line = tk.Frame(form, bg=self.colors["surface"])
            line.pack(fill="x", pady=5)
            self._label(line, title, 9, self.colors["text"], True, bg=self.colors["surface"]).pack(side="left")
            var = tk.StringVar(value=self.filter_values[key])
            variables[key] = var
            display = [label for _value, label in values]
            value_map = {label: value for value, label in values}
            combo = ttk.Combobox(line, values=display, state="readonly", width=20)
            combo.set(next((label for value, label in values if value == self.filter_values[key]), display[0]))
            combo.pack(side="right")
            combo._value_map = value_map  # type: ignore[attr-defined]
            combo._key = key  # type: ignore[attr-defined]
            combo.bind("<<ComboboxSelected>>", lambda _event, combo=combo, key=key: variables[key].set(combo._value_map[combo.get()]))  # type: ignore[attr-defined]
        footer = dialog.footer_actions
        PillButton(footer, app=self, text="取消", command=dialog.destroy, kind="ghost").pack(side="right", padx=8)

        def apply() -> None:
            for key, variable in variables.items():
                self.filter_values[key] = variable.get() or "all"
            dialog.destroy()
            self.render()

        PillButton(footer, app=self, text="应用筛选", command=apply, kind="primary").pack(side="right", padx=(0, 2))
