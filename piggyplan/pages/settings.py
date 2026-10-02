"""偏好设置页：主题、启动、热键与数据维护入口。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any
from ..constants import APP_VERSION, HOTKEY_DEFAULT, THEMES
from ..util import category_label, display_hotkey


class SettingsMixin:
    def render_settings(self, parent: tk.Misc) -> None:
        self.page_header(parent, "工作方式", "设置", "让软件更贴合你的工作方式；数据和备份始终留在本机。", (APP_VERSION, "本地桌面版"))
        row = 1
        self.settings_card(parent, row, "常规", "默认值和窗口行为")
        general = tk.Frame(parent, bg=self.SURFACE)
        general.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13), padx=0)
        self._settings_line(general, "默认分类", "快速新增时使用的分类", "combo", self.settings.get("default_category", "work"), self._save_default_category)
        self._settings_line(general, "默认启动页", "下次打开软件时进入的页面", "combo_page", self.settings.get("startup_page", "today"), self._save_startup_page)
        self._settings_line(general, "开机自启", "登录 Windows 后自动在后台启动 PiggyPlan", "check", self.settings.get("startup_enabled") == "1", self._save_startup_enabled)
        self._settings_line(general, "启动后最小化", "配合开机自启使用，不抢占前台窗口", "check", self.settings.get("startup_minimized") == "1", self._save_startup_minimized)
        self._settings_line(general, "关闭按钮行为", "关闭窗口时隐藏到托盘，或直接退出软件", "combo_close", self.settings.get("close_to_tray", "1"), self._save_close_mode)
        row += 2
        self.settings_card(parent, row, "外观", "浅色主题与动效偏好")
        appearance = tk.Frame(parent, bg=self.SURFACE)
        appearance.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        theme_line = tk.Frame(appearance, bg=self.SURFACE)
        theme_line.pack(fill="x", padx=14, pady=11)
        self._label(theme_line, "主题色", 9, self.TEXT, True, bg=self.SURFACE).pack(side="left")
        theme_choices = tk.Frame(theme_line, bg=self.SURFACE)
        theme_choices.pack(side="right")
        for key, theme in THEMES.items():
            color = theme["accent"]
            tk.Button(theme_choices, text="  ", bg=color, activebackground=theme["strong"], relief="flat", bd=0, width=4, height=2, command=lambda key=key: self.set_theme(key), cursor="hand2", highlightbackground=theme["strong"] if key == self.theme_key else self.SURFACE, highlightthickness=2).pack(side="left", padx=4)
            self._label(theme_choices, theme["name"], 7, self.TEXT_SOFT, False, bg=self.SURFACE).pack(side="left", padx=(0, 8))
        self._settings_line(appearance, "减少动效", "降低页面变化和弹窗动画", "check", self.settings.get("reduce_motion", "0") == "1", self._save_reduce_motion)
        row += 2
        self.settings_card(parent, row, "快捷键", "窗口内快捷操作；全局快速添加可在其他软件前台使用")
        shortcuts = tk.Frame(parent, bg=self.SURFACE)
        shortcuts.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        self._settings_line(shortcuts, "新建待办", "Ctrl + N", "info", "可用")
        self._settings_line(shortcuts, "快速搜索", "Ctrl + F", "info", "可用")
        hotkey_state = "已注册" if self.integration._hotkey_registered else (self.integration.hotkey_error or "不可用")
        self._settings_line(shortcuts, "全局快速添加", "可修改，例如 Ctrl + Alt + T；冲突时会明确提示", "hotkey", self.settings.get("global_hotkey", HOTKEY_DEFAULT), self._save_global_hotkey)
        self._settings_line(shortcuts, "当前状态", "系统会检测快捷键是否被其他软件占用", "info", hotkey_state)
        row += 2
        self.settings_card(parent, row, "数据与备份", "完整备份包含任务、目标、标签、模板和计划历史")
        data = tk.Frame(parent, bg=self.SURFACE)
        data.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        actions = tk.Frame(data, bg=self.SURFACE)
        actions.pack(fill="x", padx=14, pady=12)
        for text, command in (("导出完整备份", self.export_json), ("导出历史 CSV", self.export_csv), ("从备份恢复", self.import_json), ("清空所有数据", self.clear_all), ("打开数据目录", self.open_data_folder), ("打开日志目录", self.open_log_folder)):
            self._button(actions, text, command, "danger" if text == "清空所有数据" else "outline").pack(side="left", padx=(0, 6))
        self._label(data, f"数据库路径：{self.db.path}", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(anchor="w", padx=14, pady=(0, 12))
        row += 2
        self.settings_card(parent, row, "任务模板", "模板不保存旧的日期和目标")
        templates = tk.Frame(parent, bg=self.SURFACE)
        templates.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        values = self.db.list_templates()
        if values:
            for template in values:
                line = tk.Frame(templates, bg=self.SURFACE)
                line.pack(fill="x", padx=14, pady=7)
                self._label(line, template["title"], 9, self.TEXT, True, bg=self.SURFACE).pack(side="left")
                self._label(line, f"{category_label(template['category'])} · {len(template['subtasks'])} 个子步骤", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(side="left", padx=10)
                self._button(line, "使用", lambda item=template: self.open_new_task(template=item), "ghost").pack(side="right")
                self._button(line, "删除", lambda tid=template["id"]: self.delete_template(tid), "ghost").pack(side="right")
        else:
            self._label(templates, "还没有模板。在待办详情中可以保存为模板。", 8, self.TEXT_SOFT, False, bg=self.SURFACE).pack(anchor="w", padx=14, pady=13)
        row += 2
        self.settings_card(parent, row, "本地优先", "隐私与桌面能力")
        local = tk.Frame(parent, bg=self.SURFACE)
        local.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        tray_status = "已启用" if self.integration.tray_available else "当前环境不可用"
        self._label(local, f"所有核心数据都保存在本机 SQLite，不需要账号或网络。\n原生桌面能力：系统托盘 {tray_status} · 单实例已启用 · 每日自动备份保留最近 14 份。", 9, self.TEXT_SOFT, False, bg=self.SURFACE, justify="left").pack(anchor="w", padx=14, pady=13)

    def settings_card(self, parent: tk.Misc, row: int, title: str, description: str) -> None:
        card = tk.Frame(parent, bg=self.BG)
        card.grid(row=row, column=0, sticky="ew", pady=(7, 5))
        self._label(card, title, 10, self.TEXT, True, bg=self.BG).pack(anchor="w")
        self._label(card, description, 8, self.TEXT_SOFT, False, bg=self.BG).pack(anchor="w", pady=(2, 0))

    def _settings_line(self, parent: tk.Misc, title: str, description: str, kind: str, value: Any, command=None) -> None:
        line = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0)
        line.pack(fill="x", pady=(0, 1))
        copy = tk.Frame(line, bg=self.SURFACE)
        copy.pack(side="left", fill="x", expand=True, padx=15, pady=11)
        self._label(copy, title, 9, self.TEXT, True, bg=self.SURFACE, anchor="w").pack(fill="x")
        self._label(copy, description, 8, self.TEXT_SOFT, False, bg=self.SURFACE, anchor="w").pack(fill="x", pady=(3, 0))
        control = tk.Frame(line, bg=self.SURFACE)
        control.pack(side="right", padx=15, pady=9)
        if kind == "combo":
            var = tk.StringVar(value="工作" if value == "work" else "生活")
            combo = ttk.Combobox(control, textvariable=var, values=["工作", "生活"], state="readonly", width=9)
            combo.pack()
            combo.bind("<<ComboboxSelected>>", lambda _event: command("life" if var.get() == "生活" else "work"))
        elif kind == "combo_page":
            var = tk.StringVar(value={"today": "今天", "upcoming": "之后", "all": "全部"}.get(value, "今天"))
            combo = ttk.Combobox(control, textvariable=var, values=["今天", "之后", "全部"], state="readonly", width=9)
            combo.pack()
            combo.bind("<<ComboboxSelected>>", lambda _event: command({"今天": "today", "之后": "upcoming", "全部": "all"}[var.get()]))
        elif kind == "combo_close":
            var = tk.StringVar(value="隐藏到托盘" if str(value) == "1" else "直接退出")
            combo = ttk.Combobox(control, textvariable=var, values=["隐藏到托盘", "直接退出"], state="readonly", width=11)
            combo.pack()
            combo.bind("<<ComboboxSelected>>", lambda _event: command("1" if var.get() == "隐藏到托盘" else "0"))
        elif kind == "hotkey":
            row = tk.Frame(control, bg=self.SURFACE)
            row.pack()
            var = tk.StringVar(value=display_hotkey(str(value)))
            entry = ttk.Entry(row, textvariable=var, width=16)
            entry.pack(side="left")
            self._button(row, "保存", lambda: command(var.get()), "outline").pack(side="left", padx=(6, 0))
        elif kind == "check":
            var = tk.BooleanVar(value=bool(value))
            tk.Checkbutton(control, variable=var, command=lambda: command(var.get()), bg=self.SURFACE, activebackground=self.SURFACE, selectcolor=self.SURFACE, highlightthickness=0).pack()
        else:
            self._label(control, str(value), 8, self.colors["strong"], True, bg=self.SURFACE).pack()
