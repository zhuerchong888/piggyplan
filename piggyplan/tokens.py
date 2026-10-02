"""设计 token：唯一的颜色、字号、间距、圆角来源。

页面与组件一律从这里取值；本文件之外的模块不得出现字面量色号。
色值来源与两级强调色规则见 docs/superpowers/specs/
2026-09-28-piggyplan-visual-refactor-design.md 第 3 节。
"""
from __future__ import annotations

import tkinter.font as tkfont

# --- 中性色：与主题无关 ---
NEUTRAL = {
    "bg": "#FFF9F8",
    "surface": "#FFFFFF",
    "surface_soft": "#FFF1F5",
    "line": "#F7E8ED",
    "line_strong": "#EEC6D4",
    "ink": "#2E2126",          # 15.4:1 on surface
    "ink_soft": "#7A666D",     # 5.32:1 on surface, 4.67:1 on pink.soft
    "ink_faint": "#A9969D",    # 仅装饰性大字号，禁止用于正文
}

# --- 四套浅色主题 ---
# accent/accentDeep 只做图形；ink 才允许做文字；shell 是"墨线只在壳上"的描边色。
THEMES = {
    "pink":     {"name": "小猪粉",   "accent": "#F8CEDB", "accentDeep": "#F2B4C7", "ink": "#B8405F", "soft": "#FDECF1", "wash": "#FFF8FA"},
    "peach":    {"name": "蜜桃橘",   "accent": "#F9D3C5", "accentDeep": "#F3BDA9", "ink": "#B4522F", "soft": "#FFF0EA", "wash": "#FFF9F6"},
    "mint":     {"name": "薄荷绿",   "accent": "#C7E5DB", "accentDeep": "#A8D6C7", "ink": "#2E7A68", "soft": "#EAF7F2", "wash": "#F7FCFA"},
    "lavender": {"name": "薰衣草",   "accent": "#DDD2EE", "accentDeep": "#C6B4E4", "ink": "#6A4E9E", "soft": "#F3EFFB", "wash": "#FAF8FD"},
}
THEME_KEYS = tuple(THEMES)
SHELL = NEUTRAL["ink"]  # 墨线只画在壳上：对话框、侧边栏卡、空状态、Toast

SEMANTIC = {
    "high":    {"shape": "#F86870", "ink": "#B8405F"},  # 心形色取自猪图 #F86870
    "success": {"shape": "#55A781", "ink": "#2E7A68"},
    "warning": {"shape": "#CB8750", "ink": "#A85A22"},
}

SPACE = {"0": 0, "1": 4, "2": 8, "3": 12, "4": 16, "5": 24, "6": 32, "7": 48}
# 自绘假抗锯齿的外圈两环各占 1px，故半径最小取 6（chip 原为 4，因此上调）。
RADIUS = {"chip": 6, "control": 10, "card": 14, "pill": 22}

# --- 字族解析：按角色映射，避免小字号加粗 ---
FONT_PREFERENCE = ("Noto Sans SC", "Microsoft YaHei UI")
FONT_TABLE = {
    "Noto Sans SC": {
        "display": ("Noto Sans SC Medium", 22), "title": ("Noto Sans SC Medium", 13),
        "body": ("Noto Sans SC", 11), "meta": ("Noto Sans SC", 9),
        "micro": ("Noto Sans SC Medium", 8),
    },
    "Microsoft YaHei UI": {
        "display": ("Microsoft YaHei UI", 22, "bold"), "title": ("Microsoft YaHei UI", 13, "bold"),
        "body": ("Microsoft YaHei UI", 11), "meta": ("Microsoft YaHei UI", 9),
        "micro": ("Microsoft YaHei UI", 8, "bold"),
    },
}
DEFAULT_FAMILY = "Microsoft YaHei UI"


def resolve_family(root) -> str:
    installed = set(tkfont.families(root))
    for family in FONT_PREFERENCE:
        if family in installed:
            return family
    return DEFAULT_FAMILY


def resolve_fonts(root) -> dict:
    return dict(FONT_TABLE[resolve_family(root)])


def font_rules(root=None) -> dict:
    """归一化成 (family, size, weight) 三元组，供断言检查。"""
    table = resolve_fonts(root) if root is not None else FONT_TABLE[DEFAULT_FAMILY]
    return {name: (spec[0], spec[1], spec[2] if len(spec) > 2 else "normal")
            for name, spec in table.items()}


def contrast(a: str, b: str) -> float:
    def luminance(hex_value: str) -> float:
        channels = [int(hex_value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def palette(theme_key: str) -> dict[str, str]:
    theme = THEMES.get(theme_key) or THEMES["pink"]
    colors = {**NEUTRAL, **theme}
    for role, values in SEMANTIC.items():
        colors[role] = values["shape"]
        colors[f"{role}_ink"] = values["ink"]
    # 向后兼容：Task 7 之前页面仍在读 strong/text/high 等旧键。
    colors["strong"] = theme["ink"]
    colors["text"] = colors["ink"]
    colors["text_soft"] = colors["ink_soft"]
    colors["text_faint"] = colors["ink_faint"]
    colors["soft_surface"] = colors["surface_soft"]  # 旧键：侧边栏底色
    colors["shell"] = SHELL
    return colors
