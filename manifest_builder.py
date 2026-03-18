#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_VIDEO_SIZE = "1080x1920"
DEFAULT_FPS = 30

TEMPLATE_MAP = {
    "keyword_card": "psych_hook_v1",
    "concept_card": "psych_concept_v1",
    "chat_ui": "psych_chat_v1",
    "explanation_card": "psych_explanation_v1",
    "reframe_card": "psych_reframe_v1",
    "cta_card": "psych_cta_v1",
}


def base_name(payload: dict[str, Any]) -> str:
    return f"{payload['date']}_{payload['slug']}_{payload['variant']}"


def script_to_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    cursor = 0.0
    cards = []
    for card in payload["cards"]:
        duration = round(float(card["duration_sec"]), 3)
        cards.append(
            {
                "card_id": int(card["card_id"]),
                "asset_type": str(card["visual_type"]),
                "template": TEMPLATE_MAP.get(str(card["visual_type"]), "psych_generic_v1"),
                "start_sec": round(cursor, 3),
                "duration_sec": duration,
                "onscreen_text": str(card.get("onscreen_text", "")),
                "motion": str(card.get("motion", "fade_in")),
                "voiceover": str(card.get("voiceover", "")),
                "type": str(card.get("type", "")),
            }
        )
        cursor += duration

    stem = base_name(payload)
    return {
        "date": str(payload["date"]),
        "base_name": stem,
        "slug": str(payload["slug"]),
        "variant": str(payload["variant"]),
        "format": str(payload["format"]),
        "video_size": DEFAULT_VIDEO_SIZE,
        "fps": DEFAULT_FPS,
        "audio_path": f"/files/audio/{stem}.mp3",
        "subtitle_path": f"/files/subs/{stem}.ass",
        "background_mode": "gradient",
        "background_asset": None,
        "cards": cards,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a render manifest from psych_script_card JSON.")
    parser.add_argument("input", help="psych_script_card.json path")
    parser.add_argument("output", help="render_manifest.json path")
    args = parser.parse_args()

    payload = load_json(Path(args.input))
    manifest = script_to_manifest(payload)
    write_json(Path(args.output), manifest)


if __name__ == "__main__":
    main()
