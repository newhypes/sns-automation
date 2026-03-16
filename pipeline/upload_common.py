#!/usr/bin/env python3
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests


CONTENT_ROOT = Path("/Users/bigmac/.openclaw/workspace/content_factory")
CONTAINER_ROOT = Path("/files")
CREDENTIAL_ROOT = Path("~/.openclaw/credentials").expanduser()
LABEL_RE = re.compile(r"^\s*(hook|topic|script)\s*:\s*(.*)$", re.IGNORECASE)


class UploadError(RuntimeError):
    pass


def print_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_content_path(path_like: str | None) -> Path | None:
    if not path_like:
        return None
    path = Path(path_like)
    if str(path).startswith(str(CONTAINER_ROOT)):
        return CONTENT_ROOT / path.relative_to(CONTAINER_ROOT)
    if str(path).startswith(str(CONTENT_ROOT)):
        return path
    return CONTENT_ROOT / str(path_like).lstrip("/")


def sanitize_text(value: Any, *, drop_topic_lines: bool = False) -> str:
    lines: list[str] = []
    for raw_line in str(value or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        match = LABEL_RE.match(stripped)
        if not match:
            lines.append(stripped)
            continue
        label = match.group(1).lower()
        body = match.group(2).strip()
        if label == "topic" and drop_topic_lines:
            continue
        if body:
            lines.append(body)
    return " ".join(lines).strip()


def normalize_hashtags(values: Any) -> list[str]:
    hashtags: list[str] = []
    if isinstance(values, list):
        iterable = values
    elif values:
        iterable = str(values).split()
    else:
        iterable = []
    for value in iterable:
        token = str(value).strip()
        if not token:
            continue
        if not token.startswith("#"):
            token = f"#{token.lstrip('#')}"
        hashtags.append(token)
    return hashtags


def build_caption_text(task: dict[str, Any], max_length: int | None = None) -> str:
    parts: list[str] = []
    title = sanitize_text(task.get("title"))
    caption = sanitize_text(task.get("caption"), drop_topic_lines=True)
    if title:
        parts.append(title)
    if caption and caption.lower() != title.lower():
        parts.append(caption)
    hashtags = normalize_hashtags(task.get("hashtags"))
    if hashtags:
        parts.append(" ".join(hashtags))
    merged = "\n\n".join(part for part in parts if part).strip()
    if max_length is not None and len(merged) > max_length:
        return merged[: max_length - 1].rstrip() + "…"
    return merged


def success_payload(platform: str, task_file: Path, credential_file: Path, **extra: Any) -> dict[str, Any]:
    payload = {
        "success": True,
        "status": "uploaded",
        "platform": platform,
        "task_file": str(task_file),
        "credential_file": str(credential_file),
    }
    payload.update(extra)
    return payload


def failure_payload(
    platform: str,
    task_file: Path,
    credential_file: Path,
    message: str,
    *,
    status: str = "failed",
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "success": False,
        "status": status,
        "platform": platform,
        "task_file": str(task_file),
        "credential_file": str(credential_file),
        "message": message,
    }
    payload.update(extra)
    return payload


def credential_missing_payload(platform: str, task_file: Path, credential_file: Path, message: str) -> dict[str, Any]:
    return failure_payload(
        platform,
        task_file,
        credential_file,
        message,
        status="manual_credentials_required",
    )


def read_task_and_video(task_file: Path) -> tuple[dict[str, Any], Path]:
    task = load_json(task_file)
    video_path = resolve_content_path(task.get("video_file"))
    if video_path is None or not video_path.exists():
        raise UploadError(f"Video file is missing: {task.get('video_file')}")
    return task, video_path


def load_credentials(credential_file: Path, required_fields: list[str] | None = None) -> dict[str, Any]:
    if not credential_file.exists():
        missing = f"Missing credential file: {credential_file}"
        raise FileNotFoundError(missing)
    payload = load_json(credential_file)
    missing_fields = [field for field in (required_fields or []) if not payload.get(field)]
    if missing_fields:
        raise UploadError(f"Credential file is missing required fields: {', '.join(missing_fields)}")
    return payload


def truncate_for_error(text: str, limit: int = 400) -> str:
    compact = " ".join(text.strip().split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def request_json(
    method: str,
    url: str,
    *,
    expected_statuses: tuple[int, ...] = (200,),
    timeout: int = 60,
    **kwargs: Any,
) -> dict[str, Any]:
    response = requests.request(method, url, timeout=timeout, **kwargs)
    if response.status_code not in expected_statuses:
        raise UploadError(
            f"API request failed ({response.status_code}) {url}: {truncate_for_error(response.text)}"
        )
    if not response.text.strip():
        return {}
    try:
        return response.json()
    except ValueError as exc:
        raise UploadError(f"API returned non-JSON response from {url}: {truncate_for_error(response.text)}") from exc


def request_text(
    method: str,
    url: str,
    *,
    expected_statuses: tuple[int, ...] = (200,),
    timeout: int = 300,
    **kwargs: Any,
) -> str:
    response = requests.request(method, url, timeout=timeout, **kwargs)
    if response.status_code not in expected_statuses:
        raise UploadError(
            f"API request failed ({response.status_code}) {url}: {truncate_for_error(response.text)}"
        )
    return response.text


def poll_until(
    fn,
    *,
    timeout_seconds: int,
    interval_seconds: int,
    success_states: set[str],
    failure_states: set[str],
    state_getter,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_payload: dict[str, Any] | None = None
    while time.time() < deadline:
        last_payload = fn()
        state = str(state_getter(last_payload)).upper()
        if state in success_states:
            return last_payload
        if state in failure_states:
            raise UploadError(f"Upload failed with status {state}: {json.dumps(last_payload, ensure_ascii=False)}")
        time.sleep(interval_seconds)
    if last_payload is None:
        raise UploadError("Timed out before upload status could be checked")
    raise UploadError(f"Timed out while waiting for upload completion: {json.dumps(last_payload, ensure_ascii=False)}")
