"""统一小猪粉视觉：暖白底、深色正文和克制的玫瑰色操作。"""
from __future__ import annotations

import tkinter.font as tkfont

# 正文中性色与品牌色分开，主题不能覆盖 ink。
NEUTRAL = {
    "bg": "#FFFCFD",
    "surface": "#FFFFFF",
    "surface_soft": "#FFF4F7",
    "sidebar": "#FBF1F4",
    "line": "#F0E4E8",
    "line_strong": "#E8DADF",
    "ink": "#322B31",
    "ink_soft": "#746770",
    "ink_faint": "#796873",
}

# 仅保留粉色。旧备份中的其他主题名在 palette 中统一回退。
THEMES = {
    "pink": {"name": "小猪粉", "accent": "#F2BCD0", "accentDeep": "#DD88A7",
             "ink": "#AC3C60", "soft": "#FCEEF3", "wash": "#FFFCFD"},
}
THEME_KEYS = tuple(THEMES)
SHELL = NEUTRAL["line_strong"]

SEMANTIC = {
    "high":    {"shape": "#DF6A84", "ink": "#AC3C60"},
    "success": {"shape": "#55A781", "ink": "#2C755E"},
    "warning": {"shape": "#CB8750", "ink": "#9A5528"},
}

SPACE = {"0": 0, "1": 4, "2": 8, "3": 12, "4": 16, "5": 24, "6": 32, "7": 48}
# 自绘假抗锯齿的外圈两环各占 1px，故半径最小取 6（chip 原为 4，因此上调）。
RADIUS = {"chip": 6, "control": 10, "card": 14, "pill": 22}

# --- 字族解析：按角色映射，避免小字号加粗 ---
FONT_PREFERENCE = ("Microsoft YaHei UI", "Noto Sans SC")
FONT_TABLE = {
    "Noto Sans SC": {
        "display": ("Noto Sans SC Medium", 26), "title": ("Noto Sans SC Medium", 13),
        "body": ("Noto Sans SC", 11), "meta": ("Noto Sans SC", 9),
        "micro": ("Noto Sans SC", 9),
    },
    "Microsoft YaHei UI": {
        "display": ("Microsoft YaHei UI", 26, "bold"), "title": ("Microsoft YaHei UI", 13, "bold"),
        "body": ("Microsoft YaHei UI", 11), "meta": ("Microsoft YaHei UI", 9),
        "micro": ("Microsoft YaHei UI", 9),
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
    colors = {**NEUTRAL, **{key: value for key, value in theme.items() if key != "ink"}}
    for role, values in SEMANTIC.items():
        colors[role] = values["shape"]
        colors[f"{role}_ink"] = values["ink"]
    # 品牌动作文字与普通正文各有独立角色；兼容旧页面的别名。
    colors["strong"] = theme["ink"]
    colors["accent_ink"] = theme["ink"]
    colors["action_ink"] = theme["ink"]
    colors["text"] = colors["ink"]
    colors["text_soft"] = colors["ink_soft"]
    colors["text_faint"] = colors["ink_faint"]
    colors["soft_surface"] = colors["sidebar"]
    colors["shell"] = SHELL
    return colors
