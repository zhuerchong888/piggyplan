"""最小 PNG 实现：仅覆盖本项目的资产管线所需。

只支持 8bit RGB/RGBA、无隔行；只写 RGBA。存在的意义是让 tools/build_assets.py
保持零第三方依赖——不引入 Pillow 也能抠底与缩放。
"""
from __future__ import annotations

import struct
import zlib

_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def decode(data: bytes) -> tuple[int, int, bytearray]:
    """返回 (width, height, RGBA 字节)。调色板与灰度输入一律展开为 RGBA。"""
    assert data[:8] == _SIGNATURE, "不是 PNG"
    offset = 8
    palette: bytes | None = None
    idat = bytearray()
    width = height = 0
    depth = color_type = 0
    while offset < len(data):
        length, kind = struct.unpack(">I4s", data[offset : offset + 8])
        body = data[offset + 8 : offset + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color_type = struct.unpack(">IIBB", body[:10])
            assert len(body) < 13 or body[12] == 0, "不支持隔行 PNG"
        elif kind == b"PLTE":
            palette = body
        elif kind == b"IDAT":
            idat += body
        offset += 12 + length
    assert depth == 8, f"仅支持 8bit，实际 {depth}"
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    stride = width * channels
    raw = zlib.decompress(bytes(idat))
    rows = bytearray(height * stride)
    previous = bytearray(stride)
    cursor = 0
    for y in range(height):
        filter_type = raw[cursor]
        cursor += 1
        line = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        for x in range(stride):
            left = line[x - channels] if x >= channels else 0
            up = previous[x]
            up_left = previous[x - channels] if x >= channels else 0
            value = line[x]
            if filter_type == 1:
                value += left
            elif filter_type == 2:
                value += up
            elif filter_type == 3:
                value += (left + up) >> 1
            elif filter_type == 4:
                predictor = left + up - up_left
                distances = (abs(predictor - left), abs(predictor - up), abs(predictor - up_left))
                value += left if distances[0] <= min(distances[1:]) else (up if distances[1] <= distances[2] else up_left)
            line[x] = value & 255
        rows[y * stride : (y + 1) * stride] = line
        previous = line
    rgba = bytearray(width * height * 4)
    for index in range(width * height):
        if color_type == 6:
            rgba[index * 4 : index * 4 + 4] = rows[index * 4 : index * 4 + 4]
        elif color_type == 2:
            rgb = rows[index * 3 : index * 3 + 3]
            rgba[index * 4 : index * 4 + 3] = rgb
            rgba[index * 4 + 3] = 255
        elif color_type == 3:
            entry = palette[rows[index] * 3 : rows[index] * 3 + 3]
            rgba[index * 4 : index * 4 + 3] = entry
            rgba[index * 4 + 3] = 255
        else:  # 灰度 / 灰度+alpha
            grey = rows[index * channels]
            alpha = rows[index * channels + 1] if channels == 2 else 255
            rgba[index * 4 : index * 4 + 3] = bytes((grey, grey, grey))
            rgba[index * 4 + 3] = alpha
    return width, height, rgba


def encode(width: int, height: int, rgba: bytes) -> bytes:
    stride = width * 4

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))

    scanlines = b"".join(b"\x00" + bytes(rgba[y * stride : (y + 1) * stride]) for y in range(height))
    return (_SIGNATURE
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanlines, 9))
            + chunk(b"IEND", b""))


def white_to_alpha(width: int, height: int, rgba: bytearray, low: int = 232, high: int = 250) -> bytearray:
    """近白 -> 透明，中间线性渐变，避免硬边锯齿。"""
    for index in range(width * height):
        at = index * 4
        lightest = min(rgba[at], rgba[at + 1], rgba[at + 2])
        if lightest >= high:
            alpha = 0
        elif lightest <= low:
            alpha = 255
        else:
            alpha = int(255 * (high - lightest) / (high - low))
        rgba[at + 3] = alpha
    return rgba


def resize(width: int, height: int, rgba: bytes, new_width: int, new_height: int) -> bytearray:
    """预乘 alpha 的双线性缩放。不预乘会让透明像素的黑色边缘渗进可见像素。"""
    out = bytearray(new_width * new_height * 4)
    for y in range(new_height):
        gy = (y + 0.5) * height / new_height - 0.5
        y0 = min(max(int(gy), 0), height - 1)
        y1 = min(y0 + 1, height - 1)
        fy = min(max(gy - y0, 0.0), 1.0)
        for x in range(new_width):
            gx = (x + 0.5) * width / new_width - 0.5
            x0 = min(max(int(gx), 0), width - 1)
            x1 = min(x0 + 1, width - 1)
            fx = min(max(gx - x0, 0.0), 1.0)
            total = [0.0, 0.0, 0.0, 0.0]
            for row, weight_y in ((y0, 1 - fy), (y1, fy)):
                for column, weight_x in ((x0, 1 - fx), (x1, fx)):
                    at = (row * width + column) * 4
                    alpha = rgba[at + 3]
                    weight = weight_y * weight_x
                    for channel in range(3):
                        total[channel] += rgba[at + channel] * alpha * weight
                    total[3] += alpha * weight
            at = (y * new_width + x) * 4
            coverage = total[3]
            for channel in range(3):
                out[at + channel] = int(round(total[channel] / coverage)) if coverage else 0
            out[at + 3] = int(round(coverage))
    return out


def crop(width: int, height: int, rgba: bytes, box: tuple[int, int, int, int]) -> tuple[int, int, bytearray]:
    left, top, right, bottom = box
    cropped_width, cropped_height = right - left, bottom - top
    out = bytearray(cropped_width * cropped_height * 4)
    for y in range(cropped_height):
        src = ((top + y) * width + left) * 4
        dst = y * cropped_width * 4
        out[dst : dst + cropped_width * 4] = rgba[src : src + cropped_width * 4]
    return cropped_width, cropped_height, out
