"""品牌形象图：构建期生成的 PNG 资产在界面上的挂载点。"""
from __future__ import annotations

import tkinter as tk

from ..assets import RAW


class PigMark(tk.Label):
    """品牌图。用 Label 承载 PhotoImage：Tk 的 Label 原生支持 RGBA PNG。"""

    def __init__(self, parent, *, app, variant: str = "logo") -> None:
        self._image = tk.PhotoImage(data=RAW[variant])   # 必须持有引用，否则被 GC 后图消失
        super().__init__(parent, image=self._image, bd=0,
                         highlightthickness=0,
                         bg=parent.cget("bg") or app.colors["bg"])
