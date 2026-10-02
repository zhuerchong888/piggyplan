"""偏好设置：连续的表单布局、快捷键与本地数据维护。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ..constants import APP_VERSION, HOTKEY_DEFAULT
from ..util import category_label, display_hotkey


class SettingsMixin:
    def render_settings(self, parent: tk.Misc) -> None:
        parent.grid_columnconfigure(0, weight=1)
        self.page_header(parent, "工作方式", "设置", "按照你的习惯安排日常，数据与备份保存在本机。")

        general = self._settings_section(parent, 1, "常规", "默认选项与窗口行为")
        self._settings_line(general, "默认分类", "新建待办时使用的分类", "combo", self.settings.get("default_category", "work"), self._save_default_category)
        self._settings_line(general, "默认启动页", "打开软件后首先显示的页面", "combo_page", self.settings.get("startup_page", "today"), self._save_startup_page)
        self._settings_line(general, "开机自启", "登录 Windows 后自动启动", "check", self.settings.get("startup_enabled") == "1", self._save_startup_enabled)
        self._settings_line(general, "启动后最小化", "启动到系统托盘，保留当前工作窗口", "check", self.settings.get("startup_minimized") == "1", self._save_startup_minimized)
        self._settings_line(general, "关闭窗口", "选择关闭按钮的行为", "combo_close", self.settings.get("close_to_tray", "1"), self._save_close_mode)

        appearance = self._settings_section(parent, 3, "外观", "暖白背景、清晰正文与柔和的粉色点缀")
        self._settings_line(appearance, "主题", "全应用使用统一的小猪粉", "info", "小猪粉")

        shortcuts = self._settings_section(parent, 5, "快捷键", "窗口内操作与全局快速添加")
        self._settings_line(shortcuts, "新建待办", "窗口内快捷键", "info", "Ctrl + N")
        self._settings_line(shortcuts, "快速搜索", "窗口内快捷键", "info", "Ctrl + F")
        self._settings_line(shortcuts, "全局快速添加", "在其他软件中也可以随时记录想法", "hotkey", self.settings.get("global_hotkey", HOTKEY_DEFAULT), self._save_global_hotkey)
        hotkey_state = "已注册" if self.integration._hotkey_registered else (self.integration.hotkey_error or "不可用")
        self._settings_line(shortcuts, "快捷键状态", "若与其他软件冲突，可以修改上方组合键", "info", hotkey_state)

        data = self._settings_section(parent, 7, "数据与备份", "完整备份包含待办、目标、标签、模板和计划历史")
        self._settings_actions(data)

        templates = self._settings_section(parent, 9, "任务模板", "重复使用常见待办，日期与目标由你重新安排")
        bg = templates.cget("bg")
        values = self.db.list_templates()
        if values:
            for template in values:
                line = tk.Frame(templates, bg=bg)
                line.pack(fill="x")
                line.grid_columnconfigure(0, weight=1)
                copy = tk.Frame(line, bg=bg)
                copy.grid(row=0, column=0, sticky="ew", padx=(0, 20), pady=13)
                title = self._label(copy, template["title"], 11, self.colors["text"], False, bg=bg, anchor="w", justify="left")
                title.pack(fill="x")
                copy.bind("<Configure>", lambda event, label=title: label.configure(wraplength=max(80, event.width - 4)))
                self._label(copy, f"{category_label(template['category'])} · {len(template['subtasks'])} 个子步骤", 9, self.colors["text_soft"], False, bg=bg).pack(anchor="w", pady=(4, 0))
                actions = tk.Frame(line, bg=bg)
                actions.grid(row=0, column=1, sticky="e")
                self._button(actions, "使用", lambda item=template: self.open_new_task(template=item), "outline").pack(side="left", padx=(0, 8))
                self._button(actions, "删除", lambda tid=template["id"]: self.delete_template(tid), "ghost").pack(side="left")
                tk.Frame(line, bg=self.colors["line"], height=1).grid(row=1, column=0, columnspan=2, sticky="ew")
        else:
            self._label(templates, "还没有模板。在待办详情中可以保存为模板。", 10, self.colors["text_soft"], False, bg=bg).pack(anchor="w", pady=14)

        local = self._settings_section(parent, 11, "本地优先", "你的日常留在自己的电脑上")
        tray_status = "已启用" if self.integration.tray_available else "当前环境不可用"
        self._settings_line(local, "系统托盘", "关闭窗口后仍可从托盘打开", "info", tray_status)
        self._settings_line(local, "自动备份", "每天保存一次，保留最近 14 份", "info", "已启用")
        self._settings_line(local, "软件版本", "无需账号或网络连接", "info", APP_VERSION)

    def _settings_section(self, parent: tk.Misc, row: int, title: str, description: str) -> tk.Frame:
        bg = parent.cget("bg")
        header = tk.Frame(parent, bg=bg)
        header.grid(row=row, column=0, sticky="ew", pady=(26 if row > 1 else 2, 3))
        self._label(header, title, 13, self.colors["text"], True, bg=bg).pack(anchor="w")
        caption = self._label(header, description, 9, self.colors["text_soft"], False, bg=bg, justify="left")
        caption.pack(anchor="w", pady=(4, 0))
        header.bind("<Configure>", lambda event: caption.configure(wraplength=max(160, event.width - 4)))
        body = tk.Frame(parent, bg=bg)
        body.grid(row=row + 1, column=0, sticky="ew")
        return body

    def _settings_actions(self, parent: tk.Misc) -> None:
        bg = parent.cget("bg")
        actions = tk.Frame(parent, bg=bg)
        actions.pack(fill="x", pady=(14, 10))
        for column in range(2):
            actions.grid_columnconfigure(column, weight=1, uniform="data-actions")
        callbacks = (("导出完整备份", self.export_json), ("从备份恢复", self.import_json),
                     ("导出历史 CSV", self.export_csv), ("打开数据目录", self.open_data_folder),
                     ("打开日志目录", self.open_log_folder))
        for index, (text, command) in enumerate(callbacks):
            self._button(actions, text, command, "outline").grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 12), pady=(0, 9))
        location = self._label(parent, f"数据库：{self.db.path}", 9, self.colors["text_soft"], False, bg=bg, justify="left", anchor="w")
        location.pack(fill="x", pady=(0, 15))
        parent.bind("<Configure>", lambda event: location.configure(wraplength=max(160, event.width - 4)), add="+")
        tk.Frame(parent, bg=self.colors["line"], height=1).pack(fill="x")
        danger = tk.Frame(parent, bg=bg)
        danger.pack(fill="x", pady=(13, 0))
        danger.grid_columnconfigure(0, weight=1)
        warning = self._label(danger, "清空前请先导出备份。此操作会删除全部日常数据。", 9, self.colors["text_soft"], False, bg=bg, justify="left")
        warning.grid(row=0, column=0, sticky="w", padx=(0, 16))
        danger.bind("<Configure>", lambda event: warning.configure(wraplength=max(160, event.width - 165)))
        self._button(danger, "清空所有数据", self.clear_all, "danger").grid(row=0, column=1, sticky="e")

    def _settings_line(self, parent: tk.Misc, title: str, description: str, kind: str, value: Any, command=None) -> None:
        bg = parent.cget("bg")
        line = tk.Frame(parent, bg=bg)
        line.pack(fill="x")
        line.grid_columnconfigure(0, weight=1)
        copy = tk.Frame(line, bg=bg)
        copy.grid(row=0, column=0, sticky="ew", padx=(0, 24), pady=13)
        self._label(copy, title, 11, self.colors["text"], False, bg=bg, anchor="w").pack(fill="x")
        caption = self._label(copy, description, 9, self.colors["text_soft"], False, bg=bg, anchor="w", justify="left")
        caption.pack(fill="x", pady=(4, 0))
        copy.bind("<Configure>", lambda event: caption.configure(wraplength=max(120, event.width - 4)))
        control = tk.Frame(line, bg=bg)
        control.grid(row=0, column=1, sticky="e", pady=11)
        if kind in {"combo", "combo_page", "combo_close"}:
            if kind == "combo":
                options = {category_label(key): key for key in ("work", "life")}
                selected = category_label(value)
            elif kind == "combo_page":
                options = {"今天": "today", "之后": "upcoming", "全部": "all"}
                selected = {"today": "今天", "upcoming": "之后", "all": "全部"}.get(value, "今天")
            else:
                options = {"隐藏到托盘": "1", "直接退出": "0"}
                selected = "隐藏到托盘" if str(value) == "1" else "直接退出"
            var = tk.StringVar(value=selected)
            combo = ttk.Combobox(control, textvariable=var, values=list(options), state="readonly", width=14, font=self.font("body"))
            combo.pack()
            combo.bind("<<ComboboxSelected>>", lambda _event: command(options[var.get()]))
        elif kind == "hotkey":
            var = tk.StringVar(value=display_hotkey(str(value)))
            ttk.Entry(control, textvariable=var, width=16, font=self.font("body")).pack(side="left")
            self._button(control, "保存", lambda: command(var.get()), "outline").pack(side="left", padx=(8, 0))
        elif kind == "check":
            var = tk.BooleanVar(value=bool(value))
            tk.Checkbutton(control, variable=var, command=lambda: command(var.get()), bg=bg, activebackground=bg,
                           selectcolor=self.colors["surface"], fg=self.colors["strong"], activeforeground=self.colors["strong"],
                           highlightthickness=0, bd=0, cursor="hand2", takefocus=True).pack()
        else:
            self._label(control, str(value), 10, self.colors["text_soft"], False, bg=bg).pack()
        tk.Frame(line, bg=self.colors["line"], height=1).grid(row=1, column=0, columnspan=2, sticky="ew")
