#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import Any

import requests

from upload_common import (
    CREDENTIAL_ROOT,
    UploadError,
    build_caption_text,
    credential_missing_payload,
    failure_payload,
    load_credentials,
    print_json,
    read_task_and_video,
    request_json,
    save_json,
    success_payload,
)


PLATFORM = "tiktok"
DEFAULT_CREDENTIAL_FILE = CREDENTIAL_ROOT / "tiktok_credentials.json"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload a rendered video to TikTok")
    parser.add_argument("task_file")
    parser.add_argument("--credential-file", default=str(DEFAULT_CREDENTIAL_FILE))
    return parser.parse_args()


def refresh_access_token(credentials: dict[str, Any], credential_file: Path) -> dict[str, Any]:
    if not credentials.get("refresh_token"):
        return credentials
    if not credentials.get("client_key") or not credentials.get("client_secret"):
        return credentials
    response = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": credentials["client_key"],
            "client_secret": credentials["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": credentials["refresh_token"],
        },
        timeout=60,
    )
    if not response.ok:
        raise UploadError(f"TikTok token refresh failed: {response.status_code} {response.text}")
    raw_payload = response.json()
    refreshed = raw_payload.get("data", raw_payload)
    if "error" in refreshed:
        raise UploadError(f"TikTok token refresh failed: {refreshed}")
    merged = dict(credentials)
    merged.update({key: value for key, value in refreshed.items() if value})
    save_json(credential_file, merged)
    return merged


def init_upload(access_token: str, task: dict[str, Any], video_path: Path, credentials: dict[str, Any]) -> dict[str, Any]:
    size = video_path.stat().st_size
    payload = {
        "post_info": {
            "title": build_caption_text(task, max_length=2200),
            "privacy_level": credentials.get("privacy_level", "SELF_ONLY"),
            "disable_comment": bool(credentials.get("disable_comment", False)),
            "disable_duet": bool(credentials.get("disable_duet", False)),
            "disable_stitch": bool(credentials.get("disable_stitch", False)),
            "video_cover_timestamp_ms": int(credentials.get("video_cover_timestamp_ms", 1000)),
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": size,
            "total_chunk_count": 1,
        },
    }
    response = request_json(
        "POST",
        INIT_URL,
        expected_statuses=(200,),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json=payload,
    )
    error = response.get("error", {})
    if error and error.get("code") not in (None, "ok", "0"):
        raise UploadError(f"TikTok init failed: {response}")
    return response.get("data", response)


def transfer_video(upload_url: str, video_path: Path) -> None:
    size = video_path.stat().st_size
    with video_path.open("rb") as handle:
        response = requests.put(
            upload_url,
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(size),
                "Content-Range": f"bytes 0-{size - 1}/{size}",
            },
            data=handle,
            timeout=900,
        )
    if response.status_code not in (200, 201, 202, 204):
        raise UploadError(f"TikTok media transfer failed: {response.status_code} {response.text}")


def fetch_publish_status(access_token: str, publish_id: str) -> dict[str, Any]:
    response = request_json(
        "POST",
        STATUS_URL,
        expected_statuses=(200,),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={"publish_id": publish_id},
    )
    error = response.get("error", {})
    if error and error.get("code") not in (None, "ok", "0"):
        raise UploadError(f"TikTok status check failed: {response}")
    return response.get("data", response)


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
                f"Missing TikTok credentials. Place API tokens at {credential_file}.",
            )
        )
        return 0

    try:
        task, video_path = read_task_and_video(task_file)
        credentials = load_credentials(credential_file, ["access_token"])
        credentials = refresh_access_token(credentials, credential_file)
        access_token = credentials["access_token"]
        init_data = init_upload(access_token, task, video_path, credentials)
        upload_url = init_data.get("upload_url")
        publish_id = init_data.get("publish_id")
        if not upload_url or not publish_id:
            raise UploadError(f"TikTok init response did not include upload_url/publish_id: {init_data}")
        transfer_video(upload_url, video_path)
        status_payload = fetch_publish_status(access_token, publish_id)
        status_value = str(
            status_payload.get("status")
            or status_payload.get("publish_status")
            or status_payload.get("post_status")
            or "SUBMITTED"
        ).upper()
        success = not any(token in status_value for token in ("FAIL", "ERROR"))
        payload = (
            success_payload(
                PLATFORM,
                task_file,
                credential_file,
                publish_id=publish_id,
                upload_status=status_value.lower(),
                message=f"TikTok upload accepted with status {status_value}",
                api_response=status_payload,
            )
            if success
            else failure_payload(
                PLATFORM,
                task_file,
                credential_file,
                f"TikTok upload returned failure state {status_value}",
                upload_status=status_value.lower(),
                publish_id=publish_id,
                api_response=status_payload,
            )
        )
        print_json(payload)
        return 0 if success else 1
    except Exception as exc:
        print_json(failure_payload(PLATFORM, task_file, credential_file, str(exc)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
