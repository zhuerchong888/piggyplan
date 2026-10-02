"""组件层：圆角卡片、胶囊按钮、徽章与品牌标记。

页面与原语只消费这些组件；tk.Frame 画不出圆角，因此 Card/PillButton/Chip
用 Canvas 自绘，再用 create_window 把真实子容器嵌回 Canvas，交互控件
（Entry/Combobox）因此保持原生行为。
"""
from __future__ import annotations

import tkinter as tk

from ..tokens import RADIUS, SPACE
from .shape import heart, mix, snout, soft_round_rect


class Card(tk.Canvas):
    """圆角卡片。对外仍是一个普通控件，可 grid/pack，子控件放进 .body。

    用 Canvas 而不是 Frame：Tk 的 Frame 无法画圆角。用 create_window 把
    真正的子容器嵌进来，Entry/Combobox 等交互控件因此保持原生行为。
    """

    def __init__(self, parent, *, app, tone: str = "surface", radius: int = 14,
                 padding: tuple[int, int] = (16, 14), stroke: bool = False,
                 hoverable: bool = False) -> None:
        self.app = app
        self.radius = radius
        self.padding_x, self.padding_y = padding
        self.tone = tone
        self.stroke = stroke
        self.backdrop = parent.cget("bg") or app.colors["bg"]
        super().__init__(parent, bg=self.backdrop, highlightthickness=0, bd=0)
        self.body = tk.Frame(self, bg=self._fill())
        self._window = self.create_window(self.padding_x, self.padding_y,
                                          window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._follow_body)
        self.bind("<Configure>", self._follow_canvas)
        if hoverable:
            # 指针移进 body 的子控件会触发 body 的 <Leave>，直接反色会闪烁；
            # Leave 后延迟确认指针确实离开了整块画布再取消 hover。
            self.body.bind("<Enter>", lambda _e: self.hover(True), add="+")
            self.body.bind("<Leave>", lambda _e: self.after(10, self._maybe_unhover), add="+")

    def _fill(self, hovered: bool = False) -> str:
        colors = self.app.colors
        table = {"surface": colors["surface"], "soft": colors["soft"],
                 "accent": colors["accent"], "wash": colors["wash"],
                 "bg": colors["bg"], "shell": colors["surface"]}
        base = table.get(self.tone, colors["surface"])
        return mix(base, colors["accent"], 0.35) if hovered and self.tone == "surface" else base

    def _maybe_unhover(self) -> None:
        x, y = self.winfo_pointerxy()
        inside = (self.winfo_rootx() <= x < self.winfo_rootx() + self.winfo_width()
                  and self.winfo_rooty() <= y < self.winfo_rooty() + self.winfo_height())
        if not inside:
            self.hover(False)

    def hover(self, on: bool) -> None:
        self.body.configure(bg=self._fill(on))
        self.redraw(self._fill(on))

    def redraw(self, fill: str | None = None) -> None:
        for item in self.find_all():
            if item != self._window:
                self.delete(item)
        width, height = int(self["width"]), int(self["height"])
        soft_round_rect(self, 2, 2, width - 2, height - 2, self.radius,
                        fill or self._fill(), backdrop=self.backdrop,
                        stroke=self.app.colors["shell"] if self.stroke else None)
        self.tag_lower(*[i for i in self.find_all() if i != self._window])
        self.tag_raise(self._window)

    def _follow_body(self, event) -> None:
        wanted_width = event.width + 2 * self.padding_x
        wanted_height = event.height + 2 * self.padding_y
        if (int(self["width"]), int(self["height"])) != (wanted_width, wanted_height):
            self.configure(width=wanted_width, height=wanted_height)
            self.redraw()

    def _follow_canvas(self, event) -> None:
        # 被 grid(sticky="ew") 拉伸时，让 body 跟随宽度，从而支持 wraplength 自适应。
        self.after_idle(lambda: self.itemconfigure(
            self._window, width=max(1, event.width - 2 * self.padding_x)))


class PillButton(tk.Canvas):
    """胶囊按钮。Tk 的 Button 画不出圆角，因此自绘并自己接管键盘/鼠标语义。"""

    _KINDS = ("primary", "soft", "ghost", "danger")

    def __init__(self, parent, *, app, text: str, command=None,
                 kind: str = "primary", size: str = "md") -> None:
        self.app = app
        self.kind = kind
        self.size = size
        self.command = command
        height = {"sm": 28, "md": 36, "lg": 44}[size]
        self.backdrop = parent.cget("bg") or app.colors["bg"]
        super().__init__(parent, bg=self.backdrop, height=height, width=1,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._text = self.create_text(0, 0, anchor="center", text=text)
        self._hover = False
        self._pressed = False
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Button-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.configure(takefocus=True)
        self.bind("<Return>", lambda _e: self.invoke())
        self.bind("<space>", lambda _e: self.invoke())
        self.after_idle(self._fit_to_text)

    def _font(self):
        return self.app.font("micro" if self.size == "sm" else "body")

    def _fit_to_text(self) -> None:
        """请求宽度 = 文字宽 + 水平内边距；父布局仍可 fill="x" 拉伸画布。"""
        text_w = int(self.tk.call("font", "measure", self._font(),
                                  self.itemcget(self._text, "text")))
        pad = {"sm": 24, "md": 28, "lg": 32}[self.size]
        self.configure(width=text_w + pad)
        self.redraw()

    def _palette(self, hovered: bool) -> tuple[str, str]:
        colors = self.app.colors
        if self.kind == "primary":
            fill = mix(colors["accentDeep"], "#000000", 0.06 if hovered else 0.0)
            return fill, "#FFFFFF"
        if self.kind == "soft":
            return (colors["soft"] if not hovered else mix(colors["soft"], colors["accent"], 0.6),
                    colors["ink"])
        if self.kind == "danger":
            return ("#FFF0F0" if not hovered else "#FBE0E0"), "#C9575B"
        return (colors["bg"] if not hovered else colors["surface_soft"]), colors["ink_soft"]

    def redraw(self) -> None:
        for item in self.find_all():
            if item != self._text:
                self.delete(item)
        width, height = int(self["width"]), int(self["height"])
        fill, foreground = self._palette(self._hover or self._pressed)
        soft_round_rect(self, 2, 2, width - 2, height - 2, min(RADIUS["pill"], height // 2),
                        fill, backdrop=self.backdrop)
        self.coords(self._text, width / 2, height / 2)
        self.itemconfigure(self._text, fill=foreground, font=self._font())
        self.tag_raise(self._text)

    def _set_hover(self, on: bool) -> None:
        self._hover = on
        if not on:
            self._pressed = False
        self.redraw()

    def _press(self, _event) -> None:
        self._pressed = True
        self.focus_set()
        self.redraw()

    def _release(self, event) -> None:
        if self._pressed:
            self._pressed = False
            self.redraw()
            self.invoke()

    def invoke(self) -> None:
        if self.command:
            self.command()

    def set_text(self, text: str) -> None:
        self.itemconfigure(self._text, text=text)
        self._fit_to_text()


class Chip(tk.Canvas):
    """圆角小徽章：分类 / 优先级 / 标签的统一形态。"""

    def __init__(self, parent, *, app, text: str, fill: str | None = None,
                 foreground: str | None = None) -> None:
        self.app = app
        colors = app.colors
        self._fill = fill or colors["soft"]
        self._fg = foreground or colors["strong"]
        self.backdrop = parent.cget("bg") or app.colors["bg"]
        super().__init__(parent, bg=self.backdrop, highlightthickness=0, bd=0,
                         height=22, width=1)
        self._id_text = self.create_text(0, 0, text=text, fill=self._fg,
                                         font=app.font("micro"))
        self.bind("<Configure>", lambda _e: self.redraw())
        self.after_idle(self._fit)

    def _fit(self) -> None:
        text_w = int(self.tk.call("font", "measure", self.app.font("micro"),
                                  self.itemcget(self._id_text, "text")))
        self.configure(width=text_w + 14)
        self.redraw()

    def redraw(self) -> None:
        for item in self.find_all():
            if item != self._id_text:
                self.delete(item)
        width, height = int(self["width"]), int(self["height"])
        soft_round_rect(self, 1, 1, width - 1, height - 1, RADIUS["chip"],
                        self._fill, backdrop=self.backdrop)
        self.coords(self._id_text, width / 2, height / 2)
        self.tag_raise(self._id_text)


class HeartIcon(tk.Canvas):
    """高优先级标记：实心心形，取自猪图头顶那颗心。"""

    def __init__(self, parent, *, app, size: int = 12) -> None:
        self.backdrop = parent.cget("bg") or app.colors["bg"]
        super().__init__(parent, bg=self.backdrop, width=size + 4, height=size + 4,
                         highlightthickness=0, bd=0)
        heart(self, (size + 4) // 2, (size + 4) // 2 + 1, size, app.colors["high"])


class SnoutIcon(tk.Canvas):
    """分节标记：微缩猪鼻，全应用统一标点。"""

    def __init__(self, parent, *, app, size: int = 14) -> None:
        self.backdrop = parent.cget("bg") or app.colors["bg"]
        height = round(size * 0.72) + 4
        super().__init__(parent, bg=self.backdrop, width=size + 4, height=height,
                         highlightthickness=0, bd=0)
        snout(self, (size + 4) // 2, height // 2, size,
              fill=app.colors["accentDeep"], hole=app.colors["surface"])
