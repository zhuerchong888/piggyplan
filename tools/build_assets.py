"""构建期：assets_src/piggy.png -> piggyplan/assets.py + icon.ico

不参与运行时。生成物提交进版本库，因此打包不需要 Python 之外的工具。
"""
from __future__ import annotations

import base64
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from piggyplan import png  # noqa: E402

SOURCE = ROOT / "assets_src" / "piggy.png"
TARGET = ROOT / "piggyplan" / "assets.py"
ICON = ROOT / "icon.ico"

# 头部裁切框：小尺寸下全身会糊，只保留头与心形（165x138 原图上目测标定）。
HEAD_BOX = (28, 8, 140, 108)
SIZES = {"logo": 40, "mascot": 120, "mascot_head": 28, "tray": 16}


def build() -> dict[str, bytes]:
    width, height, rgba = png.decode(SOURCE.read_bytes())
    png.white_to_alpha(width, height, rgba)
    images: dict[str, bytes] = {}
    for name, size in SIZES.items():
        if name.endswith("_head") or name == "tray":
            crop_width, crop_height, source = png.crop(width, height, rgba, HEAD_BOX)
        else:
            crop_width, crop_height, source = width, height, rgba
        target_height = max(1, round(size * crop_height / crop_width))
        images[name] = png.encode(size, target_height, png.resize(crop_width, crop_height, source, size, target_height))
    return images


def ico(images: dict[str, bytes]) -> bytes:
    """把已生成的 PNG 原样封进 ICO（Vista+ 允许 PNG 负载，无需 BMP+AND 掩码）。"""
    entries = [("tray", 16), ("mascot_head", 28), ("logo", 40), ("mascot", 120)]
    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory = bytearray()
    payloads = bytearray()
    for key, size in entries:
        payload = images[key]
        dimension = 0 if size >= 256 else size
        directory += struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(payload), offset)
        offset += len(payload)
        payloads += payload
    return header + bytes(directory) + bytes(payloads)


def main() -> None:
    images = build()
    lines = [
        '"""构建期生成，请勿手改：tools/build_assets.py。"""',
        "from __future__ import annotations",
        "",
        "RAW: dict[str, bytes] = {",
    ]
    for name, payload in images.items():
        encoded = base64.b64encode(payload).decode()
        lines.append(f'    "{name}": __import__("base64").b64decode(')
        for index in range(0, len(encoded), 96):
            lines.append(f'        "{encoded[index : index + 96]}"')
        lines.append("    ),")
    lines += ["}", ""]
    TARGET.write_text("\n".join(lines), encoding="utf-8")
    ICON.write_bytes(ico(images))
    for name, payload in images.items():
        print(f"{name:12} {len(payload):>7} bytes")


if __name__ == "__main__":
    main()
