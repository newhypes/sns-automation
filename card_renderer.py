#!/usr/bin/env python3
import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from render_chat_ui import draw_chat_card


VIDEO_SIZE = (1080, 1920)
VIDEO_FPS = 30
CONTENT_ROOT = Path("/Users/bigmac/.openclaw/workspace/content_factory")

CARD_THEME = {
    "keyword_card": {"bg": "#130F1F", "accent": "#FCA5A5", "text": "#F8FAFC", "sub": "#D8B4FE"},
    "concept_card": {"bg": "#151A2E", "accent": "#60A5FA", "text": "#F8FAFC", "sub": "#BFDBFE"},
    "explanation_card": {"bg": "#101827", "accent": "#34D399", "text": "#F8FAFC", "sub": "#A7F3D0"},
    "reframe_card": {"bg": "#1A1325", "accent": "#F472B6", "text": "#FFF1F7", "sub": "#FBCFE8"},
    "cta_card": {"bg": "#0F172A", "accent": "#F59E0B", "text": "#FFFBEB", "sub": "#FCD34D"},
}


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


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


def wrapped_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
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


def render_gradient_card(card: dict[str, Any], destination: Path) -> Path:
    asset_type = str(card["asset_type"])
    theme = CARD_THEME.get(asset_type, CARD_THEME["concept_card"])
    background = Image.new("RGBA", VIDEO_SIZE, hex_to_rgb(theme["bg"]) + (255,))
    glow = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((740, 180, 1060, 500), fill=hex_to_rgb(theme["accent"]) + (36,))
    glow_draw.ellipse((0, 1320, 360, 1680), fill=hex_to_rgb(theme["accent"]) + (24,))
    background = Image.alpha_composite(background, glow.filter(ImageFilter.GaussianBlur(radius=44)))

    draw = ImageDraw.Draw(background)
    chip_font = find_font(34, bold=True)
    title_font = find_font(82, bold=True)
    body_font = find_font(48)

    draw.rounded_rectangle((88, 160, 992, 1760), radius=46, fill=(255, 255, 255, 18), outline=(255, 255, 255, 42), width=2)
    draw.rounded_rectangle((140, 236, 404, 306), radius=28, fill=hex_to_rgb(theme["accent"]) + (255,))
    draw.text((172, 252), asset_type.replace("_", " ").upper(), font=chip_font, fill=(20, 20, 28, 255))

    text = str(card.get("onscreen_text", "")).strip()
    lines = wrapped_lines(draw, text, title_font, 720)
    title_y = 520
    for index, line in enumerate(lines[:3]):
        draw.text((144, title_y + (index * 114)), line, font=title_font, fill=hex_to_rgb(theme["text"]) + (255,))

    voiceover = str(card.get("voiceover", "")).strip()
    body_lines = wrapped_lines(draw, voiceover, body_font, 720)
    body_y = max(940, title_y + (len(lines[:3]) * 114) + 120)
    for index, line in enumerate(body_lines[:4]):
        draw.text((144, body_y + (index * 70)), line, font=body_font, fill=hex_to_rgb(theme["sub"]) + (255,))

    destination.parent.mkdir(parents=True, exist_ok=True)
    background.save(destination, format="PNG")
    return destination


def motion_filter(motion: str, fps: int) -> str:
    frames = max(1, fps * 30)
    if motion == "zoom_in":
        return f"zoompan=z='min(zoom+0.0015,1.05)':d=1:s={VIDEO_SIZE[0]}x{VIDEO_SIZE[1]}:fps={fps}"
    if motion == "pan_slow":
        return f"zoompan=z='1.03':x='iw*0.01*sin(on/18)':y='ih*0.01*cos(on/24)':d=1:s={VIDEO_SIZE[0]}x{VIDEO_SIZE[1]}:fps={fps}"
    if motion == "pulse":
        return f"zoompan=z='1+0.015*sin(on/5)':d=1:s={VIDEO_SIZE[0]}x{VIDEO_SIZE[1]}:fps={fps}"
    return f"fps={fps}"


def render_card_clip(card: dict[str, Any], output_path: Path, fps: int, work_dir: Path) -> Path:
    asset_type = str(card["asset_type"])
    image_path = work_dir / f"card_{int(card['card_id']):02d}.png"
    if asset_type == "chat_ui":
        draw_chat_card(str(card.get("voiceover") or card.get("onscreen_text") or ""), image_path)
    else:
        render_gradient_card(card, image_path)

    duration = max(0.3, float(card["duration_sec"]))
    vf_parts = [f"scale={VIDEO_SIZE[0]}:{VIDEO_SIZE[1]}:force_original_aspect_ratio=increase", f"crop={VIDEO_SIZE[0]}:{VIDEO_SIZE[1]}", motion_filter(str(card.get('motion', 'fade_in')), fps)]
    if str(card.get("motion")) in {"fade_in", "message_pop", "slide_up", "pulse"}:
        vf_parts.append("fade=t=in:st=0:d=0.24")
    vf_parts.append("format=yuv420p")

    run_command(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(image_path),
            "-vf",
            ",".join(vf_parts),
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]
    )
    return output_path


def concat_card_clips(card_paths: list[Path], output_path: Path) -> Path:
    concat_path = output_path.parent / "concat_list.txt"
    concat_path.write_text("".join(f"file '{path}'\n" for path in card_paths), encoding="utf-8")
    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            str(output_path),
        ]
    )
    return output_path


def mux_audio(video_only_path: Path, audio_path: Path, output_path: Path) -> Path:
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_only_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return output_path


def render_from_manifest(manifest: dict[str, Any], *, content_root: Path = CONTENT_ROOT) -> dict[str, Any]:
    fps = int(manifest.get("fps", VIDEO_FPS))
    base_name = str(manifest.get("base_name") or f"{manifest['slug']}_{manifest['variant']}")
    cards_dir = content_root / "cards" / base_name
    cards_dir.mkdir(parents=True, exist_ok=True)
    audio_path = Path(str(manifest["audio_path"]).replace("/files/", str(content_root) + "/"))
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found for card render: {audio_path}")

    with tempfile.TemporaryDirectory(prefix="sns_auto_cards_") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        rendered_cards: list[Path] = []
        for card in manifest["cards"]:
            clip_path = cards_dir / f"card_{int(card['card_id']):02d}.mp4"
            render_card_clip(card, clip_path, fps, temp_dir)
            rendered_cards.append(clip_path)

        video_only_path = cards_dir / "video_only.mp4"
        concat_card_clips(rendered_cards, video_only_path)

    final_output = content_root / "videos" / f"{base_name}.mp4"
    mux_audio(video_only_path, audio_path, final_output)
    return {
        "cards_dir": str(cards_dir),
        "card_files": [str(path) for path in rendered_cards],
        "video_only": str(video_only_path),
        "final_video": str(final_output),
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Render card-based psych video from render_manifest.json.")
    parser.add_argument("manifest", help="render_manifest.json path")
    parser.add_argument("--content-root", default=str(CONTENT_ROOT))
    args = parser.parse_args()

    manifest = load_json(Path(args.manifest))
    result = render_from_manifest(manifest, content_root=Path(args.content_root))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
