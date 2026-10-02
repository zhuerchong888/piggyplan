"""应用级常量：名称、版本、注册表与热键默认值。"""

from __future__ import annotations

APP_NAME = "日常 · PiggyPlan"
APP_VERSION = "1.0.0-local"
DAY_FORMAT = "%Y-%m-%d"
APP_MUTEX_NAME = "Local\\PiggyPlan.Desktop.SingleInstance"
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE = "PiggyPlan"
HOTKEY_DEFAULT = "ctrl+alt+t"
