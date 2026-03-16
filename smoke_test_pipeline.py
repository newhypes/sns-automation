#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import pipeline_service


def resolve_script_path(explicit_path: str | None) -> Path:
    if explicit_path:
        candidate = Path(explicit_path)
        if candidate.exists():
            return candidate

    scripts_dir = pipeline_service.CONTENT_ROOT / "scripts"
    candidates = sorted(scripts_dir.glob("*.json"))
    if not candidates:
        raise FileNotFoundError(f"No script JSON files found in {scripts_dir}")
    return candidates[-1]


def run_variant(payload: dict, script_path: Path, variant: str) -> dict:
    voice = pipeline_service.VOICE_MAP[variant]["voice"]
    base_name = f"{payload['date']}_{payload['slug']}_{payload['hook_slug']}_{variant}"
    queue_file = f"/files/queue/pending/{base_name}.json"

    pipeline_service.write_json(
        pipeline_service.to_host_path(queue_file),
        {
            "job_id": base_name,
            "created_at": pipeline_service.utc_now(),
            "updated_at": pipeline_service.utc_now(),
            "status": "pending",
            "retry_count": 0,
            "last_error": None,
            "date": payload["date"],
            "topic": payload["topic"],
            "hook": payload["hook"],
            "slug": payload["slug"],
            "hook_slug": payload["hook_slug"],
            "variant": variant,
            "voice": voice,
            "script_file": f"/files/scripts/{script_path.name}",
        },
    )

    request = {
        **payload,
        "variant": variant,
        "voice": voice,
        "base_name": base_name,
        "queue_file": queue_file,
        "script_file": f"/files/scripts/{script_path.name}",
    }

    tts_result = pipeline_service.handle_tts(request)
    if not tts_result.get("success"):
        raise RuntimeError(f"TTS failed for {variant}: {tts_result['error']}")

    render_result = pipeline_service.handle_render(tts_result)
    if not render_result.get("success"):
        raise RuntimeError(f"Render failed for {variant}: {render_result['error']}")

    upload_result = pipeline_service.handle_enqueue_upload(render_result)
    if not upload_result.get("success"):
        raise RuntimeError(f"Upload queue failed for {variant}: {upload_result['error']}")

    return upload_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a host-side smoke test for the SNS content pipeline")
    parser.add_argument("--script-json")
    parser.add_argument("--variant", default="female", choices=["female", "male", "psych", "all"])
    args = parser.parse_args()

    script_path = resolve_script_path(args.script_json)
    payload = json.loads(script_path.read_text(encoding="utf-8"))
    variants = ["female", "male", "psych"] if args.variant == "all" else [args.variant]
    results = [run_variant(payload, script_path, variant) for variant in variants]
    print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
