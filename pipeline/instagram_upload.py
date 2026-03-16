#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

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
    success_payload,
)


PLATFORM = "instagram_reels"
DEFAULT_CREDENTIAL_FILE = CREDENTIAL_ROOT / "instagram_credentials.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload a rendered video to Instagram Reels")
    parser.add_argument("task_file")
    parser.add_argument("--credential-file", default=str(DEFAULT_CREDENTIAL_FILE))
    return parser.parse_args()


def graph_url(version: str, suffix: str) -> str:
    return f"https://graph.facebook.com/{version}/{suffix.lstrip('/')}"


def resolve_public_video_url(task: dict[str, Any], video_path: Path, credentials: dict[str, Any]) -> str:
    if task.get("public_video_url"):
        return str(task["public_video_url"])
    if credentials.get("media_url_template"):
        return str(credentials["media_url_template"]).format(
            filename=video_path.name,
            stem=video_path.stem,
            base_name=task.get("base_name", video_path.stem),
        )
    media_base_url = credentials.get("media_base_url")
    if media_base_url:
        return urljoin(str(media_base_url).rstrip("/") + "/", video_path.name)
    raise UploadError("Instagram upload requires media_base_url or media_url_template in instagram_credentials.json")


def create_media_container(task: dict[str, Any], public_video_url: str, credentials: dict[str, Any]) -> dict[str, Any]:
    version = credentials.get("graph_api_version", "v22.0")
    user_id = str(credentials["instagram_user_id"])
    response = request_json(
        "POST",
        graph_url(version, f"{user_id}/media"),
        expected_statuses=(200,),
        data={
            "media_type": "REELS",
            "video_url": public_video_url,
            "caption": build_caption_text(task, max_length=2200),
            "share_to_feed": "true" if credentials.get("share_to_feed", True) else "false",
            "thumb_offset": str(int(credentials.get("thumb_offset_ms", 1000))),
            "access_token": credentials["access_token"],
        },
    )
    if response.get("error"):
        raise UploadError(f"Instagram media container creation failed: {response}")
    return response


def wait_for_container(container_id: str, credentials: dict[str, Any]) -> dict[str, Any]:
    version = credentials.get("graph_api_version", "v22.0")
    timeout_seconds = int(credentials.get("poll_timeout_seconds", 300))
    interval_seconds = int(credentials.get("poll_interval_seconds", 5))
    deadline = __import__("time").time() + timeout_seconds
    last_payload: dict[str, Any] | None = None
    while __import__("time").time() < deadline:
        last_payload = request_json(
            "GET",
            graph_url(version, container_id),
            expected_statuses=(200,),
            params={
                "fields": "status_code,status",
                "access_token": credentials["access_token"],
            },
        )
        if last_payload.get("error"):
            raise UploadError(f"Instagram media status check failed: {last_payload}")
        state = str(last_payload.get("status_code") or last_payload.get("status") or "").upper()
        if state in {"FINISHED", "PUBLISHED"}:
            return last_payload
        if state in {"ERROR", "EXPIRED"}:
            raise UploadError(f"Instagram media processing failed: {last_payload}")
        __import__("time").sleep(interval_seconds)
    raise UploadError(f"Instagram media processing timed out: {last_payload}")


def publish_container(container_id: str, credentials: dict[str, Any]) -> dict[str, Any]:
    version = credentials.get("graph_api_version", "v22.0")
    user_id = str(credentials["instagram_user_id"])
    response = request_json(
        "POST",
        graph_url(version, f"{user_id}/media_publish"),
        expected_statuses=(200,),
        data={
            "creation_id": container_id,
            "access_token": credentials["access_token"],
        },
    )
    if response.get("error"):
        raise UploadError(f"Instagram publish failed: {response}")
    return response


def fetch_media_details(media_id: str, credentials: dict[str, Any]) -> dict[str, Any]:
    version = credentials.get("graph_api_version", "v22.0")
    response = request_json(
        "GET",
        graph_url(version, media_id),
        expected_statuses=(200,),
        params={
            "fields": "id,permalink,media_product_type,status_code",
            "access_token": credentials["access_token"],
        },
    )
    if response.get("error"):
        raise UploadError(f"Instagram media detail lookup failed: {response}")
    return response


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
                f"Missing Instagram credentials. Place Graph API tokens at {credential_file}.",
            )
        )
        return 0

    try:
        task, video_path = read_task_and_video(task_file)
        credentials = load_credentials(credential_file, ["access_token", "instagram_user_id"])
        public_video_url = resolve_public_video_url(task, video_path, credentials)
        container = create_media_container(task, public_video_url, credentials)
        container_id = container.get("id")
        if not container_id:
            raise UploadError(f"Instagram container response did not include id: {container}")
        wait_for_container(str(container_id), credentials)
        publish_response = publish_container(str(container_id), credentials)
        media_id = publish_response.get("id")
        media_details = fetch_media_details(str(media_id), credentials) if media_id else {}
        print_json(
            success_payload(
                PLATFORM,
                task_file,
                credential_file,
                container_id=container_id,
                media_id=media_id,
                video_url=public_video_url,
                permalink=media_details.get("permalink"),
                upload_status="published",
                message="Instagram Reels upload completed",
                api_response={
                    "container": container,
                    "publish": publish_response,
                    "media": media_details,
                },
            )
        )
        return 0
    except Exception as exc:
        print_json(failure_payload(PLATFORM, task_file, credential_file, str(exc)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
