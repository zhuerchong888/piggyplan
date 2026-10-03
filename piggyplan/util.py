"""日期 / 文本 / uid / 热键规范化 / 开机自启等纯工具函数。"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from .constants import AUTOSTART_KEY, AUTOSTART_VALUE, HOTKEY_DEFAULT

try:
    import winreg
except ImportError:  # pragma: no cover - only used on non-Windows hosts
    winreg = None


def today_text() -> str:
    """Return the natural-day caption used by the native window header."""

    return date_text(today_key(), long=True)


def normalize_hotkey(value: str | None) -> str | None:
    """Normalize a user-entered hotkey to a small Windows-friendly grammar."""

    if not value:
        return None
    parts = [part.strip().lower() for part in value.replace(" ", "").split("+") if part.strip()]
    if len(parts) < 2:
        return None
    modifiers = {"ctrl", "control", "alt", "shift", "win", "windows"}
    if any(part not in modifiers for part in parts[:-1]):
        return None
    key = parts[-1]
    if key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        pass
    elif len(key) == 1 and key.isascii() and key.isalnum():
        pass
    elif key in {"space", "insert", "delete", "home", "end", "pageup", "pagedown", "left", "right", "up", "down"}:
        pass
    else:
        return None
    ordered: list[str] = []
    for name in ("ctrl", "alt", "shift", "win"):
        if name in parts[:-1] or (name == "win" and any(item in {"windows", "win"} for item in parts[:-1])):
            ordered.append(name)
    return "+".join([*ordered, key])


def display_hotkey(value: str | None) -> str:
    normalized = normalize_hotkey(value) or HOTKEY_DEFAULT
    return " + ".join(part.upper() if part in {"ctrl", "alt", "shift", "win"} else part.upper() if part.startswith("f") else part.title() for part in normalized.split("+"))


def autostart_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --minimized'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else Path(sys.executable)
    # __file__ 现在是 piggyplan/util.py；入口脚本在它的上一级目录。
    entry = Path(__file__).resolve().parent.parent / "piggyplan_desktop.py"
    return f'"{runner.resolve()}" "{entry}" --minimized'


def set_windows_autostart(enabled: bool) -> None:
    if winreg is None or sys.platform != "win32":
        raise OSError("当前系统不支持 Windows 开机自启")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, AUTOSTART_VALUE, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_VALUE)
            except FileNotFoundError:
                pass


def uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today_key() -> str:
    return date.today().isoformat()


def offset_date(days: int, base: date | None = None) -> str:
    return ((base or date.today()) + timedelta(days=days)).isoformat()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def date_text(value: str | None, long: bool = False) -> str:
    parsed = parse_date(value)
    if not parsed:
        return "未安排"
    if long:
        weekdays = "一二三四五六日"
        return f"{parsed.year}年{parsed.month}月{parsed.day}日 周{weekdays[parsed.weekday()]}"
    distance = (parsed - date.today()).days
    if distance == 0:
        return "今天"
    if distance == 1:
        return "明天"
    if distance == -1:
        return "昨天"
    return f"{parsed.month}月{parsed.day}日"


def category_label(value: str) -> str:
    """Display labels can change while stored work/life keys stay compatible."""
    return "学习" if value == "life" else "工作"


def start_of_week(value: date | None = None) -> date:
    current = value or date.today()
    return current - timedelta(days=current.weekday())


def end_of_week(value: date | None = None) -> date:
    return start_of_week(value) + timedelta(days=6)


def split_tags(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = value.replace("，", ",").replace("、", ",").split(",")
    else:
        values = list(value)
    result: list[str] = []
    for item in values:
        tag = str(item).strip()
        if tag and tag not in result:
            result.append(tag)
    return result


def goal_choice_labels(goals: Iterable[dict[str, Any]], include_standalone: bool = False) -> dict[str, str]:
    """Keep every goal selectable even when titles or display labels repeat."""

    entries = list(goals)
    titles = [goal["title"] + ("（已达成）" if goal["status"] == "achieved" else "") for goal in entries]
    choices = {"独立待办": ""} if include_standalone else {}
    for goal, title in zip(entries, titles):
        label = title
        if titles.count(title) > 1 or label in choices:
            label = f"{title} · {category_label(goal['category'])} · {goal['id'][-6:]}"
        suffix = 2
        unique = label
        while unique in choices:
            unique = f"{label} ({suffix})"
            suffix += 1
        choices[unique] = goal["id"]
    return choices
