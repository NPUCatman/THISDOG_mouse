"""Create the self-contained macOS theme overview using Pillow only.

Run with ``python -B tools/create_preview.py`` from the mac directory.
All input and output paths are confined to this script's mac directory.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "预览.png"
WIDTH = 1280
BG = "#F3F3F0"
INK = "#222923"
MUTED = "#626D63"
PAPER = "#FFFFFF"
GREEN = "#496950"
PALE = "#E8EEE7"
DARK = "#26302D"

MAIN = [
    ("normal", "正常选择"), ("working", "后台运行"),
    ("busy", "忙 / 等待"), ("text", "文本选择"),
    ("precision", "精确选择"), ("unavailable", "不可用"),
    ("move", "移动"), ("link", "链接选择"),
    ("horizontal", "水平调整"), ("vertical", "垂直调整"),
    ("diagonal1", "对角线调整 1"), ("diagonal2", "对角线调整 2"),
    ("alternate", "帮助 / 候选"), ("pen", "手写 · 编辑素材"),
]
EXTRAS = [(f"extra{i}", f"备选 {i}") for i in range(1, 6)] + [
    ("normal_redrawn", "矢量重绘")
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    raise FileNotFoundError("A Chinese font is required; configure font() for your machine.")


def load_asset(key: str) -> Image.Image:
    # No absolute or user-provided paths are accepted here.
    path = ASSETS / (key + ".png")
    if not path.is_file():
        raise FileNotFoundError(f"Missing preview asset: {path}")
    with Image.open(path) as src:
        return src.convert("RGBA")


def contain(src: Image.Image, size: int) -> Image.Image:
    out = Image.new("RGBA", (size, size))
    ratio = min(size / src.width, size / src.height)
    resized = src.resize(
        (max(1, round(src.width * ratio)), max(1, round(src.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    out.alpha_composite(resized, ((size - resized.width) // 2, (size - resized.height) // 2))
    return out


def main() -> None:
    # Fail before rendering if any required input is absent.
    assets = {key: load_asset(key) for key, _ in MAIN + EXTRAS}
    im = Image.new("RGB", (WIDTH, 1640), BG)
    d = ImageDraw.Draw(im)
    ftitle, fsection = font(60, True), font(28, True)
    fbody, flabel, fsmall = font(22), font(21, True), font(18)

    def text(x, y, value, f=fbody, color=INK):
        d.text((x, y), value, font=f, fill=color)

    def centered(x, y, w, value, f=flabel, color=INK):
        box = d.textbbox((0, 0), value, font=f)
        text(x + (w - (box[2] - box[0])) / 2, y, value, f, color)

    def paste(src, x, y, size):
        tile = contain(src, size)
        im.paste(tile, (int(x), int(y)), tile)

    text(52, 38, "这狗", ftitle)
    text(57, 118, "macOS / Mousecape", font(28), GREEN)
    d.rounded_rectangle((1030, 55, 1228, 100), 22, fill=PALE)
    centered(1030, 62, 198, "静态还原版", fbody, GREEN)
    text(55, 175, "32 pt / 48 pt  两种大小    ·    Retina 1× / 2×    ·    透明背景", fbody, MUTED)

    # Pixel-accurate 1× samples, each with both light and dark backing.
    d.rounded_rectangle((52, 230, 1228, 435), 22, fill=PAPER)
    text(78, 253, "实际画布大小", fsection)
    text(78, 300, "32 pt：32 / 64 px", fsmall, MUTED)
    text(78, 334, "48 pt：48 / 96 px", fsmall, MUTED)
    text(78, 381, "右侧按 1× 像素展示", fsmall, MUTED)
    for n, (size, caption) in enumerate([(32, "标准 32 pt"), (48, "大号 48 pt")]):
        left = 488 + n * 356
        for j, bg in enumerate(["#F2F4EF", DARK]):
            bx, by, bw, bh = left + j * 142, 254, 128, 124
            d.rounded_rectangle((bx, by, bx + bw, by + bh), 15, fill=bg)
            paste(assets["normal"], bx + (bw - size) // 2, by + (bh - size) // 2, size)
        centered(left, 392, 270, caption, fbody)

    text(55, 477, "主题造型", fsection)
    text(831, 482, "以下放大展示，便于查看细节", fsmall, MUTED)
    # Four columns; the final row contains two wider cards.
    x0, y0, gap, cw, ch = 52, 534, 20, 279, 160
    for i, (key, name) in enumerate(MAIN):
        col, row = i % 4, i // 4
        x, y = x0 + col * (cw + gap), y0 + row * (ch + 16)
        d.rounded_rectangle((x, y, x + cw, y + ch), 18, fill=PAPER)
        paste(assets[key], x + (cw - 86) // 2, y + 10, 86)
        centered(x, y + 113, cw, name)

    # Context swatches occupy the two free spaces in the last row.
    for col, (bg, label, fg) in enumerate([(PALE, "浅色背景", GREEN), (DARK, "深色背景", "#EAF1E8")], 2):
        x, y = x0 + col * (cw + gap), y0 + 3 * (ch + 16)
        d.rounded_rectangle((x, y, x + cw, y + ch), 18, fill=bg)
        paste(assets["normal"], x + (cw - 86) // 2, y + 10, 86)
        centered(x, y + 113, cw, label, flabel, fg)

    text(55, 1284, "六款正常箭头备选", fsection)
    text(699, 1290, "每款都是完整主题，可直接导入应用", fsmall, MUTED)
    extra_gap, extra_cw = 16, 182
    for i, (key, name) in enumerate(EXTRAS):
        x, y = 52 + i * (extra_cw + extra_gap), 1340
        d.rounded_rectangle((x, y, x + extra_cw, y + 170), 18, fill=PAPER)
        paste(assets[key], x + (extra_cw - 92) // 2, y + 12, 92)
        centered(x, y + 126, extra_cw, name, fbody)

    text(55, 1547, "原展示：小红书「你自己做吧」  ·  根据展示图静态还原", fsmall, MUTED)
    text(55, 1582, "在 Windows 完成文件结构校验；真实 Mac 应用效果尚未实测。", fsmall, MUTED)
    im.save(OUTPUT, format="PNG", optimize=True)
    print(f"Saved {OUTPUT} ({im.width} × {im.height})")


if __name__ == "__main__":
    main()
