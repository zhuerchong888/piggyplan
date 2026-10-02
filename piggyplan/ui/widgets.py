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
                 hoverable: bool = False, fixed: bool = False) -> None:
        self.app = app
        self.radius = radius
        self.padding_x, self.padding_y = padding
        self.tone = tone
        self.stroke = stroke
        self.fixed = fixed  # True：几何管理器决定画布尺寸（对话框），body 不反调尺寸
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
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 4 or height <= 4:
            return
        paint = (width, height, fill or self._fill(), self.stroke)
        if paint == getattr(self, "_last_paint", None):
            return  # <Configure> 链会触发多次 redraw；尺寸与颜色没变就别重建多边形
        self._last_paint = paint
        for item in self.find_all():
            if item != self._window:
                self.delete(item)
        soft_round_rect(self, 2, 2, width - 2, height - 2, self.radius,
                        fill or self._fill(), backdrop=self.backdrop,
                        stroke=self.app.colors["shell"] if self.stroke else None)
        # Tcl 的 lower 一次只接受一个 item；逐个下移并倒序迭代，保持创建时的层级。
        for item_id in reversed([i for i in self.find_all() if i != self._window]):
            self.tag_lower(item_id)
        self.tag_raise(self._window)

    def set_size(self) -> None:
        """构建完成后同步按 body 需求高度定画布，消灭布局级联。

        宽度交给几何管理器（fill="x"）；高度用 winfo_reqheight 立即可得，
        不需要等 <Configure> 往返——200 张卡逐张"试探-回调-再试探"就是
        性能预算爆炸的根源。
        """
        wanted = self.body.winfo_reqheight() + 2 * self.padding_y
        if int(self["height"]) != wanted:
            self.configure(height=wanted)
        self._last_paint = None
        self.redraw()

    def _follow_body(self, event) -> None:
        if self.fixed:
            self.redraw()
            return
        wanted_height = event.height + 2 * self.padding_y
        if int(self["height"]) != wanted_height:
            self.configure(height=wanted_height)
            self._last_paint = None
            self.redraw()

    def _follow_canvas(self, event) -> None:
        # 被 grid(sticky="ew") 拉伸时，让 body 跟随宽度，从而支持 wraplength 自适应。
        self.after_idle(self.redraw)
        if self.fixed:
            # 对话框等固定几何场景：body 铺满画布内部，页脚才能钉在底边。
            self.after_idle(lambda: self.itemconfigure(
                self._window, width=max(1, event.width - 2 * self.padding_x),
                height=max(1, event.height - 2 * self.padding_y)))
        else:
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
        self._fit_to_text()

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
            # 按钮文字也是文字：底色用 ink 级（>=4.5:1），accentDeep 只配图形。
            fill = mix(colors["ink"], "#000000", 0.10 if hovered else 0.0)
            return fill, "#FFFFFF"
        if self.kind == "soft":
            return (colors["soft"] if not hovered else mix(colors["soft"], colors["accent"], 0.6),
                    colors["ink"])
        if self.kind == "danger":
            return ("#FFF0F0" if not hovered else "#FBE0E0"), "#C9575B"
        return (colors["bg"] if not hovered else colors["surface_soft"]), colors["ink_soft"]

    def redraw(self) -> None:
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 4 or height <= 4:
            return
        state = (width, height, self._hover, self._pressed, self.itemcget(self._text, "text"))
        if state == getattr(self, "_last_paint", None):
            return
        self._last_paint = state
        for item in self.find_all():
            if item != self._text:
                self.delete(item)
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
        text_w = int(self.tk.call("font", "measure", app.font("micro"), text))
        self.configure(width=text_w + 14)
        self.bind("<Configure>", lambda _e: self.redraw())

    def redraw(self) -> None:
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 4 or height <= 4:
            return
        state = (width, height, self._fill)
        if state == getattr(self, "_last_paint", None):
            return
        self._last_paint = state
        for item in self.find_all():
            if item != self._id_text:
                self.delete(item)
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


class CheckCircle(tk.Canvas):
    """自绘圆形勾选：完成 = ink 圆 + 白勾；未完成 = soft 圆点。"""

    def __init__(self, parent, *, app, completed: bool = False, command=None, size: int = 22) -> None:
        self.app = app
        self.completed = completed
        self.command = command
        self.size = size
        self.backdrop = parent.cget("bg") or app.colors["surface"]
        super().__init__(parent, bg=self.backdrop, width=size, height=size,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", self._click)
        self._draw()

    def _click(self, _event) -> None:
        if self.command:
            self.command()

    def set_completed(self, completed: bool) -> None:
        self.completed = completed
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        size = self.size
        colors = self.app.colors
        radius = size // 2 - 1
        if self.completed:
            soft_round_rect(self, 1, 1, size - 1, size - 1, radius, colors["ink"], backdrop=self.backdrop)
            self.create_line(size * 0.28, size * 0.53, size * 0.44, size * 0.69, size * 0.73, size * 0.32,
                             fill="#FFFFFF", width=2, capstyle="round", joinstyle="round", smooth=True)
        else:
            soft_round_rect(self, 1, 1, size - 1, size - 1, radius, colors["soft"], backdrop=self.backdrop)


class CheckCircle(tk.Canvas):
    """自绘圆形勾选：完成 = ink 圆 + 白勾；未完成 = soft 圆点。"""

    def __init__(self, parent, *, app, completed: bool = False, command=None, size: int = 22) -> None:
        self.app = app
        self.completed = completed
        self.command = command
        self.size = size
        self.backdrop = parent.cget("bg") or app.colors["surface"]
        super().__init__(parent, bg=self.backdrop, width=size, height=size,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", self._click)
        self._draw()

    def _click(self, _event) -> None:
        if self.command:
            self.command()

    def set_completed(self, completed: bool) -> None:
        self.completed = completed
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        size = self.size
        colors = self.app.colors
        radius = size // 2 - 1
        if self.completed:
            soft_round_rect(self, 1, 1, size - 1, size - 1, radius, colors["ink"], backdrop=self.backdrop)
            self.create_line(size * 0.28, size * 0.53, size * 0.44, size * 0.69, size * 0.73, size * 0.32,
                             fill="#FFFFFF", width=2, capstyle="round", joinstyle="round", smooth=True)
        else:
            soft_round_rect(self, 1, 1, size - 1, size - 1, radius, colors["soft"], backdrop=self.backdrop)


class CheckCircle(tk.Canvas):
    """自绘圆形勾选：完成 = ink 圆 + 白勾；未完成 = soft 圆点。"""

    def __init__(self, parent, *, app, completed: bool = False, command=None, size: int = 22) -> None:
        self.app = app
        self.completed = completed
        self.command = command
        self.size = size
        self.backdrop = parent.cget("bg") or app.colors["surface"]
        super().__init__(parent, bg=self.backdrop, width=size, height=size,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", self._click)
        self._draw()

    def _click(self, _event) -> None:
        if self.command:
            self.command()

    def set_completed(self, completed: bool) -> None:
        self.completed = completed
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        size = self.size
        colors = self.app.colors
        radius = size // 2 - 1
        if self.completed:
            soft_round_rect(self, 1, 1, size - 1, size - 1, radius, colors["ink"], backdrop=self.backdrop)
            self.create_line(size * 0.28, size * 0.53, size * 0.44, size * 0.69, size * 0.73, size * 0.32,
                             fill="#FFFFFF", width=2, capstyle="round", joinstyle="round", smooth=True)
        else:
            soft_round_rect(self, 1, 1, size - 1, size - 1, radius, colors["soft"], backdrop=self.backdrop)
