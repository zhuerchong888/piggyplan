"""组件层：圆角卡片、胶囊按钮、徽章与品牌标记。

页面与原语只消费这些组件；tk.Frame 画不出圆角，因此 Card/PillButton/Chip
用 Canvas 自绘，再用 create_window 把真实子容器嵌回 Canvas，交互控件
（Entry/Combobox）因此保持原生行为。
"""
from __future__ import annotations

import tkinter as tk

from ..tokens import RADIUS
from .shape import heart, mix, round_rect, snout, soft_round_rect


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
        self._hovered = False
        self._hover_after = None
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
            self.body.bind("<Leave>", self._schedule_unhover, add="+")

    def _fill(self, hovered: bool = False) -> str:
        colors = self.app.colors
        table = {"surface": colors["surface"], "soft": colors["soft"],
                 "accent": colors["accent"], "wash": colors["wash"],
                 "bg": colors["bg"], "shell": colors["surface"]}
        base = table.get(self.tone, colors["surface"])
        return mix(base, colors["accent"], 0.20) if hovered and self.tone == "surface" else base

    def _schedule_unhover(self, _event) -> None:
        if self._hover_after is not None:
            self.after_cancel(self._hover_after)
        self._hover_after = self.after(10, self._maybe_unhover)

    def _maybe_unhover(self) -> None:
        self._hover_after = None
        x, y = self.winfo_pointerxy()
        inside = (self.winfo_rootx() <= x < self.winfo_rootx() + self.winfo_width()
                  and self.winfo_rooty() <= y < self.winfo_rooty() + self.winfo_height())
        if not inside:
            self.hover(False)

    def hover(self, on: bool) -> None:
        previous = self.body.cget("bg")
        self._hovered = on
        fill = self._fill(on)
        if previous == fill:
            return

        def recolor(widget) -> None:
            try:
                matches = widget.cget("bg").lower() == previous.lower()
            except tk.TclError:
                matches = False
            if matches:
                widget.configure(bg=fill)
                if hasattr(widget, "backdrop"):
                    widget.backdrop = fill
                    widget._last_paint = None
                    redraw = getattr(widget, "redraw", None)
                    if redraw:
                        redraw()
            for child in widget.winfo_children():
                recolor(child)

        recolor(self.body)
        self.redraw(fill)

    def redraw(self, fill: str | None = None) -> None:
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 4 or height <= 4:
            return
        fill = fill or self._fill(self._hovered)
        paint = (width, height, fill, self.stroke)
        if paint == getattr(self, "_last_paint", None):
            return  # <Configure> 链会触发多次 redraw；尺寸与颜色没变就别重建多边形
        self._last_paint = paint
        for item in self.find_all():
            if item != self._window:
                self.delete(item)
        soft_round_rect(self, 2, 2, width - 2, height - 2, self.radius,
                        fill, backdrop=self.backdrop,
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
        if self.fixed:
            # 对话框等固定几何场景：body 铺满画布内部，页脚才能钉在底边。
            self.itemconfigure(
                self._window, width=max(1, event.width - 2 * self.padding_x),
                height=max(1, event.height - 2 * self.padding_y))
        else:
            self.itemconfigure(self._window, width=max(1, event.width - 2 * self.padding_x))
        self.redraw()

    def destroy(self) -> None:
        if self._hover_after is not None:
            self.after_cancel(self._hover_after)
            self._hover_after = None
        super().destroy()


class PillButton(tk.Canvas):
    """统一圆角按钮，保留原生 Tab、Enter 与空格操作。"""

    _KINDS = ("primary", "soft", "outline", "ghost", "link", "danger")

    def __init__(self, parent, *, app, text: str, command=None,
                 kind: str = "primary", size: str = "md") -> None:
        self.app = app
        self.kind = kind
        self.size = size
        self.command = command
        height = {"sm": 30, "md": 36, "lg": 40}[size]
        self.backdrop = parent.cget("bg") or app.colors["bg"]
        super().__init__(parent, bg=self.backdrop, height=height, width=1,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._text = self.create_text(0, 0, anchor="center", text=text)
        self._hover = False
        self._pressed = False
        self._focused = False
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Button-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.configure(takefocus=True)
        self.bind("<Return>", self._activate)
        self.bind("<space>", self._activate)
        self.bind("<FocusIn>", lambda _e: self._set_focus(True))
        self.bind("<FocusOut>", lambda _e: self._set_focus(False))
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
            fill = mix(colors["strong"], colors["ink"], 0.10 if hovered else 0.0)
            return fill, "#FFFFFF"
        if self.kind == "soft":
            return (colors["soft"] if not hovered else mix(colors["soft"], colors["accent"], 0.6),
                    colors["ink"])
        if self.kind == "danger":
            return (colors["soft"] if not hovered else colors["accent"]), colors["high_ink"]
        if self.kind in ("outline", "link"):
            return (self.backdrop if not hovered else colors["surface_soft"]), colors["strong"]
        return (self.backdrop if not hovered else colors["surface_soft"]), colors["ink_soft"]

    def redraw(self) -> None:
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 4 or height <= 4:
            return
        state = (width, height, self._hover, self._pressed, self._focused,
                 self.backdrop, self.itemcget(self._text, "text"))
        if state == getattr(self, "_last_paint", None):
            return
        self._last_paint = state
        for item in self.find_all():
            if item != self._text:
                self.delete(item)
        fill, foreground = self._palette(self._hover or self._pressed)
        radius = min(RADIUS["control"], height // 2)
        soft_round_rect(self, 3, 3, width - 3, height - 3, radius, fill, backdrop=self.backdrop,
                        stroke=self.app.colors["line_strong"] if self.kind == "outline" else None,
                        stroke_width=2)
        if self._focused:
            round_rect(self, 1, 1, width - 1, height - 1, radius + 1,
                       fill="", outline=self.app.colors["strong"], width=1, tags="focus")
        self.coords(self._text, width / 2, height / 2)
        self.itemconfigure(self._text, fill=foreground, font=self._font())
        self.tag_raise(self._text)

    def _set_hover(self, on: bool) -> None:
        self._hover = on
        if not on:
            self._pressed = False
        self.redraw()

    def _press(self, _event) -> str:
        self._pressed = True
        self.focus_set()
        self.redraw()
        return "break"

    def _release(self, event) -> str:
        if self._pressed:
            self._pressed = False
            self.redraw()
            if 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
                self.invoke()
        return "break"

    def _set_focus(self, focused: bool) -> None:
        self._focused = focused
        if not focused:
            self._pressed = False
        self.redraw()

    def _activate(self, _event) -> str:
        self.invoke()
        return "break"

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
    """可用键盘勾选的圆形控件，未完成时仍有明确轮廓。"""

    def __init__(self, parent, *, app, completed: bool = False, command=None, size: int = 22) -> None:
        self.app = app
        self.completed = completed
        self.command = command
        self.size = size
        self._focused = False
        self._pressed = False
        self.backdrop = parent.cget("bg") or app.colors["surface"]
        super().__init__(parent, bg=self.backdrop, width=size, height=size,
                         highlightthickness=0, bd=0, cursor="hand2", takefocus=True)
        self.bind("<Button-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", self._activate)
        self.bind("<space>", self._activate)
        self.bind("<FocusIn>", lambda _e: self._set_focus(True))
        self.bind("<FocusOut>", lambda _e: self._set_focus(False))
        self.bind("<Leave>", lambda _e: setattr(self, "_pressed", False))
        self._draw()

    def invoke(self) -> None:
        if self.command:
            self.command()

    def _activate(self, _event) -> str:
        self.invoke()
        return "break"

    def _press(self, _event) -> str:
        self._pressed = True
        self.focus_set()
        return "break"

    def _release(self, event) -> str:
        pressed = self._pressed
        self._pressed = False
        if pressed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.invoke()
        return "break"

    def _set_focus(self, focused: bool) -> None:
        self._focused = focused
        if not focused:
            self._pressed = False
        self._draw()

    def set_completed(self, completed: bool) -> None:
        self.completed = completed
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        size = self.size
        colors = self.app.colors
        if self._focused:
            self.create_oval(1, 1, size - 1, size - 1, outline=colors["strong"], width=1, tags="focus")
        self.create_oval(3, 3, size - 3, size - 3,
                         fill=colors["strong"] if self.completed else self.backdrop,
                         outline=colors["strong"] if self.completed else mix(colors["strong"], self.backdrop, 0.30),
                         width=1.5, tags="indicator")
        if self.completed:
            self.create_line(size * 0.30, size * 0.51, size * 0.45, size * 0.64, size * 0.70, size * 0.36,
                             fill="#FFFFFF", width=2, capstyle="round", joinstyle="round", smooth=True)

    def redraw(self) -> None:
        self._draw()
