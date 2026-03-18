#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


VIDEO_SIZE = (1080, 1920)
BACKGROUND_TOP = "#120E1F"
BACKGROUND_BOTTOM = "#241A3A"
CARD_FILL = (255, 255, 255, 28)
CARD_BORDER = (255, 255, 255, 56)
TEXT_PRIMARY = (244, 240, 255, 255)
TEXT_SECONDARY = (181, 170, 215, 255)
BUBBLE_FILL = (101, 75, 166, 235)
BUBBLE_OUTLINE = (255, 255, 255, 40)


def find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
                Path("/System/Library/Fonts/Supplemental/Arial Black.ttf"),
            ]
        )
    candidates.extend(
        [
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Helvetica.ttc"),
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    normalized = color.lstrip("#")
    return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))


def gradient_background(size: tuple[int, int]) -> Image.Image:
    width, height = size
    top = hex_to_rgb(BACKGROUND_TOP)
    bottom = hex_to_rgb(BACKGROUND_BOTTOM)
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(int(top[index] + (bottom[index] - top[index]) * ratio) for index in range(3))
        for x in range(width):
            pixels[x, y] = color
    return image.convert("RGBA")


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word]).strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if current and (bbox[2] - bbox[0]) > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def add_soft_glow(base: Image.Image) -> Image.Image:
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((740, 180, 1060, 500), fill=(169, 126, 255, 46))
    glow_draw.ellipse((20, 1220, 340, 1540), fill=(95, 167, 255, 34))
    return Image.alpha_composite(base, glow.filter(ImageFilter.GaussianBlur(radius=42)))


def draw_chat_card(message: str, destination: Path, *, title: str = "PSYCH TEXT PATTERN") -> Path:
    image = add_soft_glow(gradient_background(VIDEO_SIZE))
    draw = ImageDraw.Draw(image)
    title_font = find_font(44, bold=True)
    meta_font = find_font(28)
    message_font = find_font(58, bold=True)

    card_box = (86, 182, 994, 1634)
    draw.rounded_rectangle(card_box, radius=42, fill=CARD_FILL, outline=CARD_BORDER, width=2)

    draw.text((140, 246), title, fill=TEXT_SECONDARY, font=title_font)
    draw.text((140, 310), "Seen 2:14 PM", fill=TEXT_SECONDARY, font=meta_font)

    bubble_left = 134
    bubble_top = 420
    bubble_width = 760
    max_text_width = bubble_width - 88
    lines = wrap_text(draw, message, message_font, max_text_width)
    line_height = 76
    bubble_height = max(180, 74 + (line_height * max(1, len(lines))))
    bubble_box = (bubble_left, bubble_top, bubble_left + bubble_width, bubble_top + bubble_height)
    draw.rounded_rectangle(bubble_box, radius=38, fill=BUBBLE_FILL, outline=BUBBLE_OUTLINE, width=2)

    text_y = bubble_top + 40
    for line in lines:
        draw.text((bubble_left + 42, text_y), line, fill=TEXT_PRIMARY, font=message_font)
        text_y += line_height

    footer_y = bubble_box[3] + 120
    draw.text((140, footer_y), "This pattern keeps your brain waiting for the next reward.", fill=TEXT_PRIMARY, font=find_font(38, bold=True))
    draw.text((140, footer_y + 72), "Intermittent contact feels more intense than stable care.", fill=TEXT_SECONDARY, font=find_font(32))

    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG")
    return destination


def parse_messages(values: Iterable[str]) -> str:
    items = [value.strip() for value in values if value.strip()]
    return "\n".join(items) if items else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a psych chat UI card to PNG.")
    parser.add_argument("--message", action="append", default=[], help="Message line to render. Can be repeated.")
    parser.add_argument("--output", required=True, help="Destination PNG path.")
    parser.add_argument("--title", default="PSYCH TEXT PATTERN")
    args = parser.parse_args()

    message = parse_messages(args.message)
    if not message:
        raise SystemExit("At least one --message is required")

    draw_chat_card(message, Path(args.output), title=args.title)


if __name__ == "__main__":
    main()
