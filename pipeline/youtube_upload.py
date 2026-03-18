#!/usr/bin/env python3
import argparse
import re
import secrets
import socket
import sys
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from upload_common import (
    CREDENTIAL_ROOT,
    UploadError,
    credential_missing_payload,
    load_credentials,
    normalize_hashtags,
    print_json,
    read_task_and_video,
    save_json,
    sanitize_text,
    success_payload,
    failure_payload,
    request_json,
)


PLATFORM = "youtube_shorts"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULT_CREDENTIAL_FILE = CREDENTIAL_ROOT / "youtube_client_secret.json"
DEFAULT_TOKEN_FILE = None
CHANNEL_ID_BY_VARIANT = {
    "female": "UCsjQI_dDu7Y-5oBcokJQWQw",
    "male": "UCsbm6ooh97MQl0h9ufUzRGA",
    "psych": "UCsbm6ooh97MQl0h9ufUzRGA",
}
TOKEN_ROUTE_BY_VARIANT = {
    "female": "female",
    "male": "male",
    "psych": "male",
}
VARIANT_RE = re.compile(r"(?:^|[_\W])(female|male|psych)(?:$|[_\W])", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
INLINE_LABEL_RE = re.compile(r"\b(hook|topic|script)\s*:\s*", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload a rendered video to YouTube Shorts")
    parser.add_argument("task_file")
    parser.add_argument("--credential-file", default=str(DEFAULT_CREDENTIAL_FILE))
    parser.add_argument("--token-file")
    return parser.parse_args()


def extract_client_config(payload: dict[str, Any]) -> dict[str, Any]:
    if "installed" in payload:
        return payload["installed"]
    if "web" in payload:
        return payload["web"]
    return payload


def iso_to_timestamp(value: str | None) -> float:
    if not value:
        return 0
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0


def token_is_valid(payload: dict[str, Any]) -> bool:
    expires_at = iso_to_timestamp(payload.get("expires_at"))
    return bool(payload.get("access_token")) and expires_at > time.time() + 60


def save_token(token_file: Path, payload: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    expires_in = int(payload.get("expires_in", 3600))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    saved = dict(previous or {})
    saved.update(payload)
    if previous and previous.get("refresh_token") and not saved.get("refresh_token"):
        saved["refresh_token"] = previous["refresh_token"]
    saved["expires_at"] = expires_at.isoformat()
    save_json(token_file, saved)
    return saved


def refresh_access_token(client: dict[str, Any], token_file: Path) -> dict[str, Any] | None:
    if not token_file.exists():
        return None
    current = load_credentials(token_file)
    refresh_token = current.get("refresh_token")
    if not refresh_token:
        return None
    response = requests.post(
        client["token_uri"],
        data={
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=60,
    )
    if not response.ok:
        raise UploadError(f"YouTube token refresh failed: {response.status_code} {response.text}")
    payload = response.json()
    payload["refresh_token"] = refresh_token
    return save_token(token_file, payload, current)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    server_version = "SNSAutoYouTubeOAuth/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path != "/oauth2callback":
            self.send_response(404)
            self.end_headers()
            return
        self.server.auth_payload = {key: values[0] for key, values in query.items()}  # type: ignore[attr-defined]
        if "error" in query:
            body = b"YouTube authorization failed. You can close this window."
        else:
            body = b"YouTube authorization completed. You can close this window."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def interactive_authorize(client: dict[str, Any], token_file: Path) -> dict[str, Any]:
    port = get_free_port()
    redirect_uri = f"http://127.0.0.1:{port}/oauth2callback"
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    auth_url = f"{client['auth_uri']}?{urlencode(params)}"
    server = ThreadingHTTPServer(("127.0.0.1", port), OAuthCallbackHandler)
    server.timeout = 1
    server.auth_payload = None  # type: ignore[attr-defined]
    print(f"YouTube OAuth URL: {auth_url}", file=sys.stderr, flush=True)
    opened = webbrowser.open(auth_url, new=1, autoraise=True)
    if not opened:
        print(f"Open this URL to authorize YouTube upload: {auth_url}", file=sys.stderr)
    deadline = time.time() + 300
    while time.time() < deadline:
        server.handle_request()
        payload = getattr(server, "auth_payload", None)
        if payload is None:
            continue
        if payload.get("state") != state:
            raise UploadError("YouTube OAuth state verification failed")
        if payload.get("error"):
            raise UploadError(f"YouTube OAuth authorization failed: {payload['error']}")
        code = payload.get("code")
        if not code:
            raise UploadError("YouTube OAuth callback did not include an authorization code")
        response = requests.post(
            client["token_uri"],
            data={
                "client_id": client["client_id"],
                "client_secret": client["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            timeout=60,
        )
        if not response.ok:
            raise UploadError(f"YouTube OAuth token exchange failed: {response.status_code} {response.text}")
        return save_token(token_file, response.json())
    raise UploadError("YouTube OAuth timed out. Retry after completing browser authorization.")


def ensure_access_token(client: dict[str, Any], token_file: Path) -> dict[str, Any]:
    if token_file.exists():
        current = load_credentials(token_file)
        if token_is_valid(current):
            return current
    refreshed = refresh_access_token(client, token_file)
    if refreshed and token_is_valid(refreshed):
        return refreshed
    return interactive_authorize(client, token_file)


def detect_variant(task: dict[str, Any], video_path: Path) -> str:
    candidates = [
        task.get("variant"),
        task.get("base_name"),
        task.get("title"),
        task.get("video_file"),
        " ".join(str(value) for value in task.get("hashtags", [])),
        video_path.stem,
    ]
    for candidate in candidates:
        text = str(candidate or "").strip()
        if not text:
            continue
        match = VARIANT_RE.search(text)
        if match:
            return match.group(1).lower()
        lower = text.lower()
        if lower in CHANNEL_ID_BY_VARIANT:
            return lower
    raise UploadError(f"Unable to determine variant for YouTube upload: {task_file_hint(task, video_path)}")


def task_file_hint(task: dict[str, Any], video_path: Path) -> str:
    return f"base_name={task.get('base_name')} video={video_path.name}"


def select_token_file(task: dict[str, Any], video_path: Path, cli_token_file: str | None) -> Path:
    if cli_token_file:
        return Path(cli_token_file).expanduser()
    variant = detect_variant(task, video_path)
    route_key = TOKEN_ROUTE_BY_VARIANT[variant]
    routed_path = CREDENTIAL_ROOT / f"youtube_token_{route_key}.json"
    legacy_path = CREDENTIAL_ROOT / "youtube_token.json"
    if routed_path.exists():
        return routed_path
    if route_key == "male" and legacy_path.exists():
        return legacy_path
    return routed_path


def extract_sentences(*values: Any) -> list[str]:
    sentences: list[str] = []
    for value in values:
        cleaned = sanitize_text(value, drop_topic_lines=True)
        cleaned = INLINE_LABEL_RE.sub("", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        if not cleaned:
            continue
        parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(cleaned) if part.strip()]
        if not parts:
            parts = [cleaned]
        sentences.extend(parts)
    return sentences


def build_upload_title(task: dict[str, Any], video_path: Path) -> str:
    candidates = extract_sentences(task.get("hook"), task.get("title"), task.get("caption"))
    if candidates:
        return candidates[0][:100].strip()
    return video_path.stem[:100]


def build_upload_description(task: dict[str, Any], title: str) -> str:
    title_key = re.sub(r"\s+", " ", title).strip().lower()
    detail_line = ""
    raw_sources = [task.get("script"), task.get("caption"), task.get("description")]
    for raw_source in raw_sources:
        for sentence in extract_sentences(raw_source):
            sentence_key = re.sub(r"\s+", " ", sentence).strip().lower()
            if sentence_key.startswith(title_key):
                trimmed = sentence[len(title) :].strip(" -:|")
                sentence = trimmed or sentence
                sentence_key = re.sub(r"\s+", " ", sentence).strip().lower()
            if sentence_key and sentence_key != title_key:
                detail_line = sentence
                break
        if detail_line:
            break
    lines = [title]
    if detail_line:
        lines.append(detail_line)
    hashtags = " ".join(normalize_hashtags(task.get("hashtags")))
    if hashtags:
        lines.append(hashtags)
    return "\n".join(lines[:3])[:4900].strip()


def fetch_authenticated_channel(access_token: str) -> dict[str, Any]:
    payload = request_json(
        "GET",
        "https://www.googleapis.com/youtube/v3/channels",
        expected_statuses=(200,),
        headers={"Authorization": f"Bearer {access_token}"},
        params={"part": "id,snippet", "mine": "true"},
    )
    items = payload.get("items") or []
    if not items:
        raise UploadError("No YouTube channel is linked to the authorized account")
    item = items[0]
    return {
        "id": item.get("id"),
        "title": (item.get("snippet") or {}).get("title"),
    }


def create_upload_session(
    access_token: str,
    task: dict[str, Any],
    video_path: Path,
    credential_payload: dict[str, Any],
    *,
    title: str,
    description: str,
) -> str:
    tags = [tag.lstrip("#") for tag in task.get("hashtags", []) if str(tag).strip()]
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags[:15],
            "categoryId": str(credential_payload.get("category_id", "22")),
        },
        "status": {
            "privacyStatus": credential_payload.get("privacy_status", "private"),
            "selfDeclaredMadeForKids": bool(credential_payload.get("made_for_kids", False)),
        },
    }
    response = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=resumable",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(video_path.stat().st_size),
            "X-Upload-Content-Type": "video/mp4",
        },
        json=metadata,
        timeout=60,
    )
    if response.status_code not in (200, 201):
        raise UploadError(f"YouTube upload session creation failed: {response.status_code} {response.text}")
    location = response.headers.get("Location")
    if not location:
        raise UploadError("YouTube did not return a resumable upload URL")
    return location


def upload_video(access_token: str, upload_url: str, video_path: Path) -> dict[str, Any]:
    with video_path.open("rb") as handle:
        response = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "video/mp4",
                "Content-Length": str(video_path.stat().st_size),
            },
            data=handle,
            timeout=900,
        )
    if response.status_code not in (200, 201):
        raise UploadError(f"YouTube upload failed: {response.status_code} {response.text}")
    return response.json()


def main() -> int:
    args = parse_args()
    task_file = Path(args.task_file).expanduser().resolve()
    credential_file = Path(args.credential_file).expanduser()

    if not task_file.exists():
        print_json(failure_payload(PLATFORM, task_file, credential_file, f"Task file does not exist: {task_file}"))
        return 2

    if not credential_file.exists():
        print_json(
            credential_missing_payload(
                PLATFORM,
                task_file,
                credential_file,
                f"Missing YouTube OAuth client secret. Place the desktop app JSON at {credential_file}.",
            )
        )
        return 0

    try:
        task, video_path = read_task_and_video(task_file)
        variant = detect_variant(task, video_path)
        expected_channel_id = CHANNEL_ID_BY_VARIANT[variant]
        token_file = select_token_file(task, video_path, args.token_file)
        credential_payload = load_credentials(credential_file)
        client = extract_client_config(credential_payload)
        required = ["client_id", "client_secret", "auth_uri", "token_uri"]
        missing = [field for field in required if not client.get(field)]
        if missing:
            raise UploadError(f"YouTube client secret JSON is missing fields: {', '.join(missing)}")
        token_payload = ensure_access_token(client, token_file)
        authenticated_channel = fetch_authenticated_channel(token_payload["access_token"])
        actual_channel_id = str(authenticated_channel.get("id") or "")
        if actual_channel_id != expected_channel_id:
            raise UploadError(
                f"Authorized YouTube channel mismatch for {variant}: expected {expected_channel_id}, "
                f"got {actual_channel_id or 'unknown'} ({authenticated_channel.get('title') or 'unknown'}). "
                f"Re-authorize using {token_file}."
            )
        title = build_upload_title(task, video_path)
        description = build_upload_description(task, title)
        upload_url = create_upload_session(
            token_payload["access_token"],
            task,
            video_path,
            credential_payload,
            title=title,
            description=description,
        )
        video_metadata = upload_video(token_payload["access_token"], upload_url, video_path)
        video_id = video_metadata.get("id")
        print_json(
            success_payload(
                PLATFORM,
                task_file,
                credential_file,
                variant=variant,
                target_channel_id=expected_channel_id,
                target_channel_title=authenticated_channel.get("title"),
                upload_title=title,
                upload_description=description,
                video_id=video_id,
                video_url=f"https://www.youtube.com/shorts/{video_id}" if video_id else None,
                message="YouTube Shorts upload completed",
                token_file=str(token_file),
                api_response=video_metadata,
            )
        )
        return 0
    except Exception as exc:
        print_json(failure_payload(PLATFORM, task_file, credential_file, str(exc)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
