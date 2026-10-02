"""应用级常量：名称、版本、注册表、热键默认值与四套主题。

THEMES 原属 PiggyPlanApp；Task 5 引入 tokens.py 后将迁走，此处只是过渡归属。
"""

from __future__ import annotations

APP_NAME = "日常 · PiggyPlan"
APP_VERSION = "1.0.0-local"
DAY_FORMAT = "%Y-%m-%d"
APP_MUTEX_NAME = "Local\\PiggyPlan.Desktop.SingleInstance"
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE = "PiggyPlan"
HOTKEY_DEFAULT = "ctrl+alt+t"
THEMES = {
    "pink": {"name": "小猪粉", "accent": "#F8CEDB", "strong": "#D96288", "soft": "#FDECF1", "wash": "#FFF8FA"},
    "peach": {"name": "蜜桃橘", "accent": "#F9D3C5", "strong": "#D9775C", "soft": "#FFF0EA", "wash": "#FFF9F6"},
    "mint": {"name": "薄荷绿", "accent": "#C7E5DB", "strong": "#489A88", "soft": "#EAF7F2", "wash": "#F7FCFA"},
    "lavender": {"name": "薰衣草", "accent": "#DDD2EE", "strong": "#8064B4", "soft": "#F3EFFB", "wash": "#FAF8FD"},
}
