#!/usr/bin/env python3
import argparse
import json
import mimetypes
import random
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont


CONTENT_ROOT = Path("/Users/bigmac/.openclaw/workspace/content_factory")
CONTAINER_ROOT = Path("/files")
WORKSPACE_ROOT = Path(__file__).resolve().parent
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8010
VIDEO_SIZE = (1080, 1920)
VIDEO_FPS = 30
SUBTITLE_FONT_SIZE = 80
SENTENCE_END_RE = re.compile(r"""[.!?]["')\]]*$""")
SUBTITLE_LABEL_RE = re.compile(r"^\s*(hook|script)\s*:\s*", re.IGNORECASE)
SCRIPT_LABEL_RE = re.compile(r"^\s*(hook|topic|script)\s*:\s*(.*)$", re.IGNORECASE)

VOICE_MAP = {
    "female": {
        "voice": "en-US-JennyNeural",
        "image_dir": "female_host",
        "bg_color": "0xF2C6D2",
        "gradient_colors": ("0xF6D7B8", "0xEFA6C8", "0xFFF1DB"),
        "gradient_type": "linear",
        "gradient_speed": 0.012,
    },
    "male": {
        "voice": "en-US-GuyNeural",
        "image_dir": "male_host",
        "bg_color": "0xB7D0F5",
        "gradient_colors": ("0xA7C6F2", "0xD9E8F5", "0x7FA7D8"),
        "gradient_type": "radial",
        "gradient_speed": 0.008,
    },
    "psych": {
        "voice": "en-US-AriaNeural",
        "image_dir": "psych_host",
        "bg_color": "0xC9DDB5",
        "gradient_colors": ("0x101827", "0x273349", "0x05070C"),
        "gradient_type": "circular",
        "gradient_speed": 0.006,
    },
}

PLATFORMS = ("tiktok", "youtube_shorts", "instagram_reels")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
UPLOAD_SCRIPT_MAP = {
    "youtube_shorts": WORKSPACE_ROOT / "pipeline" / "upload_youtube.sh",
    "tiktok": WORKSPACE_ROOT / "pipeline" / "upload_tiktok.sh",
    "instagram_reels": WORKSPACE_ROOT / "pipeline" / "upload_instagram.sh",
}
PLATFORM_CREDENTIALS = {
    "youtube_shorts": Path("~/.openclaw/credentials/youtube_client_secret.json").expanduser(),
    "tiktok": Path("~/.openclaw/credentials/tiktok_credentials.json").expanduser(),
    "instagram_reels": Path("~/.openclaw/credentials/instagram_credentials.json").expanduser(),
}
FILTER_SUPPORT_CACHE: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_content_tree() -> None:
    for relative in (
        "audio",
        "subs",
        "videos",
        "publish_queue",
        "queue/pending",
        "queue/rendering",
        "queue/ready_to_upload",
        "queue/failed",
        "queue/uploaded",
        "logs/generation",
        "logs/render",
        "logs/upload",
    ):
        ensure_directory(CONTENT_ROOT / relative)


def to_host_path(path_like: str | None) -> Path | None:
    if not path_like:
        return None
    path = Path(path_like)
    if str(path).startswith(str(CONTAINER_ROOT)):
        return CONTENT_ROOT / path.relative_to(CONTAINER_ROOT)
    if str(path).startswith(str(CONTENT_ROOT)):
        return path
    return CONTENT_ROOT / str(path_like).lstrip("/")


def to_container_path(host_path: Path) -> str:
    return str(CONTAINER_ROOT / host_path.relative_to(CONTENT_ROOT))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_directory(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def build_base_name(data: dict[str, Any]) -> str:
    if data.get("base_name"):
        return str(data["base_name"])
    return "_".join(
        [
            str(data["date"]),
            str(data["slug"]),
            str(data["hook_slug"]),
            str(data["variant"]),
        ]
    )


def load_queue_manifest(queue_file: str | None, fallback: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    queue_host = to_host_path(queue_file) if queue_file else None
    if queue_host and queue_host.exists():
        try:
            payload = json.loads(queue_host.read_text(encoding="utf-8"))
            return payload, queue_host
        except json.JSONDecodeError:
            pass

    base_name = build_base_name(fallback)
    default_path = CONTENT_ROOT / "queue" / "pending" / f"{base_name}.json"
    payload = {
        "job_id": base_name,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "date": fallback.get("date"),
        "topic": fallback.get("topic"),
        "hook": fallback.get("hook"),
        "slug": fallback.get("slug"),
        "hook_slug": fallback.get("hook_slug"),
        "variant": fallback.get("variant"),
        "voice": fallback.get("voice"),
        "status": "pending",
        "retry_count": int(fallback.get("retry_count", 0)),
        "last_error": None,
    }
    return payload, default_path


def update_queue_manifest(
    queue_file: str | None,
    fallback: dict[str, Any],
    status: str,
    destination: str,
    extra: dict[str, Any] | None = None,
) -> str:
    manifest, current_path = load_queue_manifest(queue_file, fallback)
    destination_path = CONTENT_ROOT / "queue" / destination / f"{manifest['job_id']}.json"
    manifest.update(extra or {})
    manifest["status"] = status
    manifest["updated_at"] = utc_now()
    write_json(destination_path, manifest)
    if current_path != destination_path and current_path.exists():
        current_path.unlink()
    return to_container_path(destination_path)


def log_failure(stage: str, data: dict[str, Any], error: str) -> None:
    log_file = CONTENT_ROOT / "logs" / stage / f"{data.get('date', datetime.now().date().isoformat())}_{stage}.log"
    append_jsonl(
        log_file,
        {
            "timestamp": utc_now(),
            "stage": stage,
            "success": False,
            "error": error,
            "base_name": build_base_name(data),
            "topic": data.get("topic"),
            "hook": data.get("hook"),
            "variant": data.get("variant"),
        },
    )


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def run_with_retries(stage: str, attempts: int, data: dict[str, Any], fn):
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - runtime path
            last_error = exc
            if attempt < attempts:
                time.sleep(min(3, attempt))
    assert last_error is not None
    raise last_error


def probe_duration(audio_path: Path) -> float:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(audio_path),
        ]
    )
    payload = json.loads(result.stdout)
    return round(float(payload["format"]["duration"]), 3)


def ffmpeg_supports_filter(filter_name: str) -> bool:
    global FILTER_SUPPORT_CACHE
    if FILTER_SUPPORT_CACHE is None:
        FILTER_SUPPORT_CACHE = run_command(["ffmpeg", "-hide_banner", "-filters"]).stdout
    return re.search(rf"(^|\s){re.escape(filter_name)}(\s|$)", FILTER_SUPPORT_CACHE, re.MULTILINE) is not None


def choose_background_asset(variant: str) -> tuple[Path | None, str]:
    style = VOICE_MAP.get(variant, {})
    image_dir = CONTENT_ROOT / "images" / style.get("image_dir", "")
    if not image_dir.exists():
        return None, "gradient"
    candidates = [path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS]
    if not candidates:
        return None, "gradient"
    selected = random.choice(sorted(candidates))
    if selected.suffix.lower() in VIDEO_EXTENSIONS:
        return selected, "video"
    return selected, "image"


def parse_timestamp(value: str) -> float:
    hh, mm, rest = value.split(":")
    ss, ms = rest.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000


def parse_srt(path: Path) -> list[dict[str, Any]]:
    blocks = path.read_text(encoding="utf-8").strip().split("\n\n")
    entries: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_raw, end_raw = [piece.strip() for piece in lines[1].split("-->")]
        entries.append(
            {
                "start": parse_timestamp(start_raw),
                "end": parse_timestamp(end_raw),
                "text": " ".join(lines[2:]),
            }
        )
    return entries


def find_font_path() -> Path:
    candidates = (
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Black.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No supported TTF font found for subtitle rendering")


def find_subtitle_font_path() -> Path:
    candidates = (
        Path("/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Black.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return find_font_path()


def subtitle_font_name() -> str:
    path = find_subtitle_font_path().name.lower()
    if "din condensed" in path:
        return "DIN Condensed"
    if "arial narrow" in path:
        return "Arial Narrow"
    if "arial black" in path:
        return "Arial Black"
    if "arial" in path:
        return "Arial"
    return "Arial"


def sanitize_subtitle_text(text: str) -> str:
    cleaned = " ".join(text.split())
    cleaned = SUBTITLE_LABEL_RE.sub("", cleaned)
    cleaned = cleaned.strip().strip('"').strip("'").strip()
    return cleaned


def split_subtitle_text(text: str, max_width: int = 860) -> list[str]:
    words = text.split()
    if not words:
        return []

    probe = ImageDraw.Draw(Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0)))
    font = subtitle_font()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word]).strip()
        trial_bbox = probe.textbbox((0, 0), trial, font=font, stroke_width=8)
        trial_width = trial_bbox[2] - trial_bbox[0]
        if current and trial_width > max_width:
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)

    if current:
        chunks.append(" ".join(current))

    return chunks


def subtitle_display_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []

    for entry in entries:
        text = sanitize_subtitle_text(str(entry["text"]))
        if not text:
            continue

        chunks = split_subtitle_text(text)
        if not chunks:
            continue

        start = float(entry["start"])
        end = float(entry["end"])
        total_duration = max(0.1, end - start)
        chunk_duration = total_duration / len(chunks)

        for index, chunk in enumerate(chunks):
            chunk_start = start + (chunk_duration * index)
            chunk_end = end if index == len(chunks) - 1 else start + (chunk_duration * (index + 1))
            segments.append({"start": chunk_start, "end": chunk_end, "text": chunk})

    return segments or entries


def normalize_script_for_tts(script: str) -> str:
    segments: list[str] = []

    for raw_line in script.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        match = SCRIPT_LABEL_RE.match(stripped)
        if match:
            label = match.group(1).lower()
            remainder = match.group(2).strip()
            if label == "topic":
                continue
            stripped = remainder

        stripped = stripped.strip().strip('"').strip("'").strip()
        if stripped:
            segments.append(stripped)

    return "\n\n".join(segments)


def format_ass_timestamp(seconds: float) -> str:
    total_cs = max(0, int(round(seconds * 100)))
    hours, rem = divmod(total_cs, 360000)
    minutes, rem = divmod(rem, 6000)
    secs, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def ass_color(color: str, alpha: str = "00") -> str:
    normalized = color.replace("#", "").replace("0x", "")
    if len(normalized) != 6:
        raise ValueError(f"Unsupported color: {color}")
    rr, gg, bb = normalized[:2], normalized[2:4], normalized[4:]
    return f"&H{alpha}{bb}{gg}{rr}"


def escape_ass_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def subtitle_font(size: int = SUBTITLE_FONT_SIZE) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(find_subtitle_font_path()), size)


def build_ass_subtitles(segments: list[dict[str, Any]], destination: Path) -> None:
    style_block = "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            ",".join(
                [
                    "Default",
                    subtitle_font_name(),
                    str(SUBTITLE_FONT_SIZE),
                    ass_color("#FFFFFF"),
                    ass_color("#FFFFFF"),
                    ass_color("#000000"),
                    ass_color("#000000", "FF"),
                    "-1",
                    "0",
                    "0",
                    "0",
                    "100",
                    "100",
                    "0",
                    "0",
                    "1",
                    "7",
                    "0",
                    "2",
                    "110",
                    "110",
                    "170",
                    "1",
                ]
            ),
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
    )
    events = [
        f"Dialogue: 0,{format_ass_timestamp(segment['start'])},{format_ass_timestamp(segment['end'])},Default,,0,0,0,,{escape_ass_text(str(segment['text']))}"
        for segment in segments
    ]
    destination.write_text(style_block + "\n" + "\n".join(events) + "\n", encoding="utf-8")


def render_subtitle_frame(
    text: str,
    destination: Path,
    style: dict[str, Any],
) -> None:
    overlay = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = subtitle_font()
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=8)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = int((VIDEO_SIZE[0] - text_width) / 2)
    y = VIDEO_SIZE[1] - text_height - 170
    draw.text(
        (x, y),
        text,
        font=font,
        fill=(255, 255, 255, 255),
        stroke_width=8,
        stroke_fill=(0, 0, 0, 255),
    )

    overlay.save(destination, format="PNG")


def build_background_input(duration: float, style: dict[str, Any], asset_path: Path | None, asset_type: str) -> tuple[list[str], str]:
    scale_crop = "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if asset_path and asset_type == "image":
        return ["-loop", "1", "-t", f"{duration:.3f}", "-i", str(asset_path)], scale_crop
    if asset_path and asset_type == "video":
        return ["-stream_loop", "-1", "-t", f"{duration:.3f}", "-i", str(asset_path)], scale_crop

    colors = style.get("gradient_colors", ("0x2F3A56", "0x101827"))
    gradient_filter = (
        "gradients="
        f"size=1080x1920:rate={VIDEO_FPS}:duration={duration:.3f}:"
        f"c0={colors[0]}:c1={colors[1]}:c2={colors[2]}:"
        f"n=3:type={style.get('gradient_type', 'linear')}:"
        f"speed={style.get('gradient_speed', 0.01)}:x0=0:y0=0:x1=1080:y1=1920"
    )
    return ["-f", "lavfi", "-i", gradient_filter], "fps=30,format=rgba"


def build_overlay_timeline(segments: list[dict[str, Any]], duration: float, temp_dir: Path, style: dict[str, Any]) -> Path:
    blank_path = temp_dir / "blank.png"
    Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0)).save(blank_path, format="PNG")

    concat_file = temp_dir / "overlay_concat.txt"
    lines: list[str] = []
    cursor = 0.0

    def append_frame(frame_path: Path, frame_duration: float) -> None:
        if frame_duration <= 0.02:
            return
        lines.append(f"file '{frame_path}'")
        lines.append(f"duration {frame_duration:.3f}")

    for index, segment in enumerate(segments):
        start = max(0.0, float(segment["start"]))
        end = min(duration, float(segment["end"]))
        if start > cursor:
            append_frame(blank_path, start - cursor)
            cursor = start

        frame_path = temp_dir / f"segment_{index:03d}.png"
        render_subtitle_frame(str(segment["text"]), frame_path, style)
        append_frame(frame_path, max(0.1, end - start))
        cursor = max(cursor, end)

    if cursor < duration:
        append_frame(blank_path, duration - cursor)

    final_frame = blank_path if not segments else temp_dir / f"segment_{len(segments) - 1:03d}.png"
    lines.append(f"file '{final_frame}'")
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return concat_file


def render_video_with_ass(
    audio_host: Path,
    ass_host: Path,
    video_host: Path,
    duration: float,
    style: dict[str, Any],
    asset_path: Path | None,
    asset_type: str,
) -> None:
    bg_input_args, bg_filter = build_background_input(duration, style, asset_path, asset_type)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            *bg_input_args,
            "-i",
            str(audio_host),
            "-filter_complex",
            f"[0:v]{bg_filter},subtitles='{str(ass_host)}'[v]",
            "-map",
            "[v]",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-r",
            str(VIDEO_FPS),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-t",
            f"{duration:.3f}",
            str(video_host),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def render_video_from_srt(
    audio_host: Path,
    srt_host: Path,
    video_host: Path,
    ass_host: Path,
    duration: float,
    style: dict[str, Any],
    asset_path: Path | None,
    asset_type: str,
) -> str:
    entries = subtitle_display_entries(parse_srt(srt_host))
    if not entries:
        raise RuntimeError("No subtitle entries were parsed from SRT")

    build_ass_subtitles(entries, ass_host)
    if ffmpeg_supports_filter("subtitles"):
        render_video_with_ass(audio_host, ass_host, video_host, duration, style, asset_path, asset_type)
        return "ass"

    with tempfile.TemporaryDirectory(prefix="sns_auto_render_") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        concat_file = build_overlay_timeline(entries, duration, temp_dir, style)
        bg_input_args, bg_filter = build_background_input(duration, style, asset_path, asset_type)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                *bg_input_args,
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-i",
                str(audio_host),
                "-filter_complex",
                f"[0:v]{bg_filter},format=rgba[bg];[1:v]fps={VIDEO_FPS},format=rgba[subs];[bg][subs]overlay=0:0:shortest=1,format=yuv420p[v]",
                "-map",
                "[v]",
                "-map",
                "2:a:0",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-r",
                str(VIDEO_FPS),
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                "-t",
                f"{duration:.3f}",
                str(video_host),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    return "overlay_png"


def first_script_line(script: str) -> str:
    for line in script.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.replace('"', "")
    return script.strip().replace('"', "")


def build_caption(data: dict[str, Any]) -> str:
    return f"{data['hook']} {first_script_line(data['script'])}".strip()


def make_success(data: dict[str, Any], **extra: Any) -> dict[str, Any]:
    response = dict(data)
    response.update(extra)
    response["success"] = True
    return response


def make_failure(stage: str, data: dict[str, Any], error: Exception | str) -> dict[str, Any]:
    message = str(error)
    queue_file = update_queue_manifest(
        data.get("queue_file"),
        data,
        status="failed",
        destination="failed",
        extra={"last_error": message, "retry_count": int(data.get("retry_count", 0)) + 1},
    )
    log_failure(stage, data, message)
    failure = dict(data)
    failure.update({"success": False, "error": message, "queue_file": queue_file})
    return failure


def handle_tts(data: dict[str, Any]) -> dict[str, Any]:
    ensure_content_tree()
    base_name = build_base_name(data)
    audio_host = CONTENT_ROOT / "audio" / f"{base_name}.mp3"
    srt_host = CONTENT_ROOT / "subs" / f"{base_name}.srt"

    def execute() -> dict[str, Any]:
        ensure_directory(audio_host.parent)
        ensure_directory(srt_host.parent)
        spoken_script = normalize_script_for_tts(str(data["script"]))
        run_command(
            [
                "edge-tts",
                "-t",
                spoken_script,
                "-v",
                str(data["voice"]),
                "--write-media",
                str(audio_host),
                "--write-subtitles",
                str(srt_host),
            ]
        )
        duration = probe_duration(audio_host)
        queue_file = update_queue_manifest(
            data.get("queue_file"),
            data,
            status="tts_completed",
            destination="pending",
            extra={
                "voice": data.get("voice"),
                "audio_file": to_container_path(audio_host),
                "srt_file": to_container_path(srt_host),
                "duration_seconds": duration,
            },
        )
        append_jsonl(
            CONTENT_ROOT / "logs" / "generation" / f"{data['date']}_tts.log",
            {
                "timestamp": utc_now(),
                "stage": "tts",
                "success": True,
                "base_name": base_name,
                "audio_file": to_container_path(audio_host),
                "srt_file": to_container_path(srt_host),
                "duration_seconds": duration,
            },
        )
        return make_success(
            data,
            base_name=base_name,
            audio_file=to_container_path(audio_host),
            audio_host_file=str(audio_host),
            srt_file=to_container_path(srt_host),
            srt_host_file=str(srt_host),
            duration_seconds=duration,
            queue_file=queue_file,
        )

    try:
        return run_with_retries("generation", 3, data, execute)
    except Exception as exc:  # pragma: no cover - runtime path
        return make_failure("generation", data, exc)


def handle_render(data: dict[str, Any]) -> dict[str, Any]:
    ensure_content_tree()
    base_name = build_base_name(data)
    audio_host = to_host_path(data.get("audio_file"))
    srt_host = to_host_path(data.get("srt_file"))
    if not audio_host or not audio_host.exists():
        return make_failure("render", data, "Audio file is missing before render stage")
    if not srt_host or not srt_host.exists():
        return make_failure("render", data, "Subtitle file is missing before render stage")

    video_host = CONTENT_ROOT / "videos" / f"{base_name}.mp4"
    duration = float(data.get("duration_seconds") or probe_duration(audio_host))
    ass_host = CONTENT_ROOT / "subs" / f"{base_name}.ass"
    style = VOICE_MAP.get(str(data.get("variant")), VOICE_MAP["psych"])
    background_asset, background_type = choose_background_asset(str(data.get("variant")))

    def execute() -> dict[str, Any]:
        update_queue_manifest(data.get("queue_file"), data, status="rendering", destination="rendering")
        subtitle_mode = render_video_from_srt(
            audio_host,
            srt_host,
            video_host,
            ass_host,
            duration,
            style,
            background_asset,
            background_type,
        )
        queue_file = update_queue_manifest(
            data.get("queue_file"),
            data,
            status="rendered",
            destination="ready_to_upload",
            extra={
                "audio_file": data.get("audio_file"),
                "srt_file": data.get("srt_file"),
                "ass_file": to_container_path(ass_host),
                "video_file": to_container_path(video_host),
                "duration_seconds": duration,
                "video_width": VIDEO_SIZE[0],
                "video_height": VIDEO_SIZE[1],
                "background_type": background_type,
                "background_asset": to_container_path(background_asset) if background_asset else None,
                "subtitle_mode": subtitle_mode,
            },
        )
        append_jsonl(
            CONTENT_ROOT / "logs" / "render" / f"{data['date']}_render.log",
            {
                "timestamp": utc_now(),
                "stage": "render",
                "success": True,
                "base_name": base_name,
                "video_file": to_container_path(video_host),
                "background_type": background_type,
                "background_asset": str(background_asset) if background_asset else None,
                "subtitle_mode": subtitle_mode,
                "ass_file": to_container_path(ass_host),
                "video_width": VIDEO_SIZE[0],
                "video_height": VIDEO_SIZE[1],
            },
        )
        return make_success(
            data,
            base_name=base_name,
            video_file=to_container_path(video_host),
            video_host_file=str(video_host),
            ass_file=to_container_path(ass_host),
            ass_host_file=str(ass_host),
            queue_file=queue_file,
            duration_seconds=duration,
            video_width=VIDEO_SIZE[0],
            video_height=VIDEO_SIZE[1],
            background_type=background_type,
            background_asset=to_container_path(background_asset) if background_asset else None,
            subtitle_mode=subtitle_mode,
        )

    try:
        return run_with_retries("render", 2, data, execute)
    except Exception as exc:  # pragma: no cover - runtime path
        return make_failure("render", data, exc)


def handle_enqueue_upload(data: dict[str, Any]) -> dict[str, Any]:
    ensure_content_tree()
    base_name = build_base_name(data)
    ready_manifest_host = to_host_path(data.get("queue_file"))
    if not ready_manifest_host or not ready_manifest_host.exists():
        return make_failure("upload", data, "Ready-to-upload manifest is missing")

    tasks: list[dict[str, Any]] = []
    for platform in PLATFORMS:
        task = {
            "job_id": f"{base_name}_{platform}",
            "base_name": base_name,
            "platform": platform,
            "status": "queued_no_credentials",
            "retry_count": 0,
            "last_error": "Uploader credentials are not configured yet",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "video_file": data.get("video_file"),
            "title": data.get("hook"),
            "caption": build_caption(data),
            "credential_file": str(PLATFORM_CREDENTIALS[platform]),
            "script_path": str(UPLOAD_SCRIPT_MAP[platform]),
            "hashtags": [
                "#relationshippsychology",
                "#datingadvice",
                f"#{str(data.get('variant'))}",
            ],
        }
        task_path = CONTENT_ROOT / "publish_queue" / f"{task['job_id']}.json"
        write_json(task_path, task)
        task["task_file"] = to_container_path(task_path)
        tasks.append(task)

    manifest = json.loads(ready_manifest_host.read_text(encoding="utf-8"))
    manifest.update(
        {
            "status": "ready_to_upload",
            "upload_tasks": [task["task_file"] for task in tasks],
            "upload_platforms": [task["platform"] for task in tasks],
            "updated_at": utc_now(),
        }
    )
    write_json(ready_manifest_host, manifest)
    append_jsonl(
        CONTENT_ROOT / "logs" / "upload" / f"{data['date']}_upload_queue.log",
        {
            "timestamp": utc_now(),
            "stage": "upload_queue",
            "success": True,
            "base_name": base_name,
            "task_count": len(tasks),
        },
    )
    return make_success(data, base_name=base_name, queue_file=to_container_path(ready_manifest_host), upload_tasks=tasks)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_upload_script(platform: str, task_host: Path) -> dict[str, Any]:
    script_path = UPLOAD_SCRIPT_MAP[platform]
    if not script_path.exists():
        raise FileNotFoundError(f"Upload script is missing: {script_path}")

    completed = subprocess.run(
        [str(script_path), str(task_host)],
        check=False,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Upload script returned invalid JSON: {stdout}") from exc
    else:
        payload = {}

    payload.setdefault("success", completed.returncode == 0)
    payload.setdefault("status", "uploaded" if payload["success"] else "failed")
    if completed.stderr.strip():
        payload.setdefault("stderr", completed.stderr.strip())
    return payload


def handle_platform_upload(data: dict[str, Any], platform: str) -> dict[str, Any]:
    ensure_content_tree()
    task_host = to_host_path(data.get("task_file"))
    if not task_host or not task_host.exists():
        return make_failure("upload", data, f"Upload task file is missing for {platform}")

    task = load_json(task_host)
    if task.get("platform") != platform:
        return make_failure("upload", data, f"Upload task platform mismatch: expected {platform}, got {task.get('platform')}")

    try:
        result = run_upload_script(platform, task_host)
        now = utc_now()
        task.update(
            {
                "updated_at": now,
                "script_response": result,
            }
        )
        status = str(result.get("status", "failed"))
        message = str(result.get("message", "")).strip() or str(result.get("stderr", "")).strip()
        manual_statuses = {"manual_credentials_required", "scaffold_only"}

        if result.get("success"):
            task.update({"status": "uploaded", "uploaded_at": now, "last_error": None})
            destination = CONTENT_ROOT / "queue" / "uploaded" / f"{task['job_id']}.json"
            write_json(destination, task)
            if destination != task_host and task_host.exists():
                task_host.unlink()
            response_task_file = to_container_path(destination)
        elif status in manual_statuses:
            task.update({"status": status, "last_error": message or "Credential setup required"})
            write_json(task_host, task)
            response_task_file = to_container_path(task_host)
        else:
            task.update({"status": "failed", "last_error": message or "Upload failed"})
            destination = CONTENT_ROOT / "queue" / "failed" / f"{task['job_id']}.json"
            write_json(destination, task)
            if destination != task_host and task_host.exists():
                task_host.unlink()
            response_task_file = to_container_path(destination)

        append_jsonl(
            CONTENT_ROOT / "logs" / "upload" / f"{datetime.now().date().isoformat()}_{platform}.log",
            {
                "timestamp": now,
                "stage": f"upload_{platform}",
                "success": bool(result.get("success")),
                "status": task["status"],
                "task_file": response_task_file,
                "video_file": task.get("video_file"),
                "message": message or None,
            },
        )

        if task["status"] in manual_statuses:
            return make_success(data, platform=platform, task_file=response_task_file, upload_status=task["status"], message=task["last_error"])
        if result.get("success"):
            return make_success(data, platform=platform, task_file=response_task_file, upload_status="uploaded", message=result.get("message"))
        return make_failure("upload", data, message or f"{platform} upload failed")
    except Exception as exc:
        return make_failure("upload", data, exc)


class PipelineHandler(BaseHTTPRequestHandler):
    server_version = "SNSAutoPipeline/2.0"

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stdout.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:  # pragma: no cover - runtime only
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._write_json(
                200,
                {
                    "ok": True,
                    "service": "sns_auto_pipeline_service",
                    "content_root": str(CONTENT_ROOT),
                    "voices": VOICE_MAP,
                },
            )
            return
        if parsed.path.startswith("/files/"):
            target = to_host_path(parsed.path)
            if not target or not target.exists() or not target.is_file():
                self._write_json(404, {"ok": False, "error": "Not found"})
                return
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._write_json(404, {"ok": False, "error": "Unknown endpoint"})

    def do_POST(self) -> None:  # pragma: no cover - runtime only
        parsed = urlparse(self.path)
        try:
            data = self._read_body()
            if parsed.path == "/tts":
                payload = handle_tts(data)
            elif parsed.path == "/render":
                payload = handle_render(data)
            elif parsed.path == "/enqueue_upload":
                payload = handle_enqueue_upload(data)
            elif parsed.path == "/upload/youtube":
                payload = handle_platform_upload(data, "youtube_shorts")
            elif parsed.path == "/upload/tiktok":
                payload = handle_platform_upload(data, "tiktok")
            elif parsed.path == "/upload/instagram":
                payload = handle_platform_upload(data, "instagram_reels")
            else:
                self._write_json(404, {"ok": False, "error": "Unknown endpoint"})
                return
            self._write_json(200, payload)
        except Exception as exc:
            self._write_json(500, {"ok": False, "error": str(exc)})


def serve(host: str, port: int) -> None:
    ensure_content_tree()
    server = ThreadingHTTPServer((host, port), PipelineHandler)
    print(f"Pipeline service listening on http://{host}:{port}", flush=True)
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Local host service for SNS pipeline TTS/render steps")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
