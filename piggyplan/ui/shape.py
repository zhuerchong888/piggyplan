"""Canvas 自绘原语。Tk 的 Canvas 没有圆角、没有抗锯齿，这里补上。

假抗锯齿的做法：在 backdrop 与 fill 之间画两圈 1px 中间色环，越靠外越接近
backdrop。实测半径 >=6 时肉眼已看不出锯齿，因此 RADIUS 最小值定为 6。
"""
from __future__ import annotations

import tkinter as tk

# (向外扩张像素, 与 backdrop 的混合比)：外环更淡、内环更浓，形成渐变边。
HALO = ((2, 0.35), (1, 0.70))


def _rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))


def mix(color_a: str, color_b: str, ratio: float) -> str:
    """ratio=0 得 color_a，ratio=1 得 color_b。"""
    a, b = _rgb(color_a), _rgb(color_b)
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * ratio) for i in range(3))


def round_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **style) -> int:
    """用 smooth 多边形逼近圆角矩形。四角各给三个控制点，避免贝塞尔外凸。"""
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **style)


def soft_round_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int,
                    fill: str, *, backdrop: str, stroke: str | None = None,
                    stroke_width: int = 2) -> list[int]:
    """画一块带圆角、边缘平滑的色块；stroke 非空时在其内缘描墨线。"""
    ids = [
        round_rect(canvas, x1 - grow, y1 - grow, x2 + grow, y2 + grow, radius + grow,
                   fill=mix(backdrop, fill, ratio), outline="")
        for grow, ratio in HALO
    ]
    ids.append(round_rect(canvas, x1, y1, x2, y2, radius, fill=fill, outline=""))
    if stroke:
        # Tk 的描边多边形是锯齿的 1px 线；改用"外圈实心描边色 + 内实心填充色"
        # 两层叠出平滑墨线，这也是"墨线只在壳上"的唯一实现方式。
        ids.append(round_rect(canvas, x1 + 1, y1 + 1, x2 - 1, y2 - 1, max(1, radius - 1),
                              fill=stroke, outline=""))
        ids.append(round_rect(canvas, x1 + stroke_width, y1 + stroke_width,
                              x2 - stroke_width, y2 - stroke_width, max(1, radius - stroke_width),
                              fill=fill, outline=""))
    return ids


def heart(canvas: tk.Canvas, center_x: int, center_y: int, size: int, fill: str) -> int:
    """高优先级标记：取自猪图头顶那颗心，替代红字"高"。"""
    points = [
        center_x, center_y + size * 0.35,
        center_x - size * 0.5, center_y - size * 0.05,
        center_x - size * 0.25, center_y - size * 0.35,
        center_x, center_y - size * 0.1,
        center_x + size * 0.25, center_y - size * 0.35,
        center_x + size * 0.5, center_y - size * 0.05,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, fill=fill, outline="")


def snout(canvas: tk.Canvas, center_x: int, center_y: int, width: int,
          fill: str, hole: str) -> list[int]:
    """分节标记：猪鼻轮廓 + 两个鼻孔。全应用统一标点。"""
    height = round(width * 0.72)
    ids = [canvas.create_oval(center_x - width / 2, center_y - height / 2,
                              center_x + width / 2, center_y + height / 2,
                              fill=fill, outline="")]
    nose = max(1, round(width * 0.16))
    for offset in (-width * 0.2, width * 0.2):
        ids.append(canvas.create_oval(center_x + offset - nose / 2, center_y - nose,
                                      center_x + offset + nose / 2, center_y + nose,
                                      fill=hole, outline=""))
    return ids
