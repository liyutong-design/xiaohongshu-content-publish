#!/usr/bin/env python3
"""步骤5：抠图与四页排版（对应 Coze 画板节点 153832 / 129186 / 109747 / 116382）。

- 封面：两行主标题 + 两行副标题 + 作者名 + 主视觉 + 两个辅助元素；
- 内容页 1~3：页面标题 + 三组小标题和正文；
- 四图统一 3:4（1242x1656）、统一色彩和字体层级；
- 生成素材为纯白背景卡通图，这里做近白色抠图（对应 Coze 抠图节点）；
- 素材缺失时仍生成完整文字排版，并在 manifest 中标记素材真实状态；
- 输出 01-cover.png / 02-content-1.png / 03-content-2.png / 04-content-3.png。

依赖：Pillow（pip install Pillow）。字体优先使用系统中文字体。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: 缺少 Pillow，请先执行 pip install Pillow", file=sys.stderr)
    sys.exit(2)

WIDTH, HEIGHT = 1242, 1656  # 3:4
BG_COLOR = (255, 248, 240)        # 米白
PRIMARY = (255, 105, 97)          # 小红书红
TEXT_DARK = (51, 51, 51)
TEXT_GRAY = (120, 120, 120)
CARD_BG = (255, 255, 255)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def load_font(size: int, bold: bool = False):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def cutout_white(img: "Image.Image", threshold: int = 240) -> "Image.Image":
    """近白色背景抠图：把接近纯白的像素置为透明（对应 Coze cutout 节点）。"""
    img = img.convert("RGBA")
    pixels = img.getdata()
    new_pixels = []
    for r, g, b, a in pixels:
        if r >= threshold and g >= threshold and b >= threshold:
            new_pixels.append((r, g, b, 0))
        else:
            new_pixels.append((r, g, b, a))
    img.putdata(new_pixels)
    return img


def load_element(visuals: dict, key: str, target_w: int) -> "Image.Image | None":
    entry = visuals.get("elements", {}).get(key, {})
    local = entry.get("local_file")
    if not local or not Path(local).exists():
        return None
    try:
        img = Image.open(local)
    except OSError:
        return None
    img = cutout_white(img)
    ratio = target_w / img.width
    return img.resize((target_w, int(img.height * ratio)), Image.LANCZOS)


def wrap_text(draw, text: str, font, max_width: int) -> list:
    """按像素宽度逐字换行，适配中文无空格文本。"""
    lines, current = [], ""
    for ch in text:
        trial = current + ch
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def draw_centered(draw, y: int, text: str, font, fill, max_width: int = WIDTH - 160) -> int:
    lines = wrap_text(draw, text, font, max_width)
    line_h = font.size + 16
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((WIDTH - w) / 2, y), line, font=font, fill=fill)
        y += line_h
    return y


def make_cover(structure: dict, split: dict, visuals: dict, out_path: Path):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = load_font(96, bold=True)
    font_sub = load_font(44)
    font_author = load_font(36)

    # 顶部装饰条
    draw.rectangle([0, 0, WIDTH, 18], fill=PRIMARY)

    y = 120
    y = draw_centered(draw, y, split.get("title1", ""), font_title, PRIMARY)
    y = draw_centered(draw, y, split.get("title2", ""), font_title, PRIMARY)
    y += 30
    sub1 = split.get("subtitle1", "")
    sub2 = split.get("subtitle2", "")
    if sub1:
        y = draw_centered(draw, y, sub1, font_sub, TEXT_GRAY)
    if sub2:
        y = draw_centered(draw, y, sub2, font_sub, TEXT_GRAY)

    # 主视觉与辅助元素
    main_img = load_element(visuals, "main_image", 560)
    el1 = load_element(visuals, "element_img1", 220)
    el2 = load_element(visuals, "element_img2", 220)
    base_y = y + 60
    if main_img is not None:
        img.paste(main_img, ((WIDTH - main_img.width) // 2, base_y), main_img)
    if el1 is not None:
        img.paste(el1, (80, base_y + 60), el1)
    if el2 is not None:
        img.paste(el2, (WIDTH - el2.width - 80, base_y + 60), el2)

    # 作者名
    author = structure.get("author", "")
    if author:
        font_a = font_author
        w = draw.textlength(author, font=font_a)
        draw.text(((WIDTH - w) / 2, HEIGHT - 140), author, font=font_a, fill=TEXT_DARK)

    img.save(out_path)


def make_content_page(page_index: int, structure: dict, out_path: Path):
    """page_index: 1-3，对应 content1-3 / 4-6 / 7-9。"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_page_title = load_font(64, bold=True)
    font_sub = load_font(44, bold=True)
    font_body = load_font(34)
    font_title_small = load_font(34)

    draw.rectangle([0, 0, WIDTH, 18], fill=PRIMARY)

    # 总标题 + 页面标题
    y = 60
    title = structure.get("title", "")
    y = draw_centered(draw, y, title, font_title_small, TEXT_GRAY)
    page_title = structure.get(f"page_title{page_index}", "")
    y = draw_centered(draw, y + 10, page_title, font_page_title, PRIMARY)
    y += 40

    margin = 90
    card_w = WIDTH - margin * 2
    for i in range(3):
        n = page_index * 3 - 2 + i  # 1-9
        sub = structure.get(f"sub_title{n}", "")
        body = structure.get(f"content{n}", "")

        # 卡片
        body_lines = wrap_text(draw, body, font_body, card_w - 80)
        card_h = 90 + len(body_lines) * (font_body.size + 14) + 50
        draw.rounded_rectangle([margin, y, margin + card_w, y + card_h],
                               radius=28, fill=CARD_BG, outline=(255, 214, 210), width=3)
        # 小标题
        draw.text((margin + 40, y + 32), sub, font=font_sub, fill=PRIMARY)
        # 正文
        ty = y + 100
        for line in body_lines:
            draw.text((margin + 40, ty), line, font=font_body, fill=TEXT_DARK)
            ty += font_body.size + 14
        y += card_h + 40

    img.save(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="制作一张封面和三张内容页（3:4）")
    parser.add_argument("--output-dir", default=str(config.DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    structure_path = out_dir / "structure.json"
    split_path = out_dir / "split.json"
    visuals_path = out_dir / "visuals.json"

    for p in (structure_path, split_path):
        if not p.exists():
            print(f"ERROR: 找不到 {p}，请先完成前序步骤", file=sys.stderr)
            return 2

    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    split = json.loads(split_path.read_text(encoding="utf-8"))
    visuals = json.loads(visuals_path.read_text(encoding="utf-8")) if visuals_path.exists() \
        else {"elements": {}}

    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "cover": out_dir / "01-cover.png",
        "content-1": out_dir / "02-content-1.png",
        "content-2": out_dir / "03-content-2.png",
        "content-3": out_dir / "04-content-3.png",
    }

    make_cover(structure, split, visuals, files["cover"])
    for i in range(1, 4):
        make_content_page(i, structure, files[f"content-{i}"])

    print(json.dumps({"status": "ok",
                      "files": {k: str(v) for k, v in files.items()}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
