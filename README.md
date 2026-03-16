# sns-automation

`topic -> script -> TTS -> background -> subtitles -> render -> upload` 파이프라인용 작업 저장소입니다.

현재 업로드 자동화는 아래 파일로 연결됩니다.

- YouTube Shorts: [pipeline/youtube_upload.py](/Users/bigmac/openclaw/workspace/sns_auto/pipeline/youtube_upload.py)
- TikTok: [pipeline/tiktok_upload.py](/Users/bigmac/openclaw/workspace/sns_auto/pipeline/tiktok_upload.py)
- Instagram Reels: [pipeline/instagram_upload.py](/Users/bigmac/openclaw/workspace/sns_auto/pipeline/instagram_upload.py)
- n8n workflow generator: [build_wf02_final.py](/Users/bigmac/openclaw/workspace/sns_auto/build_wf02_final.py)

## Credential Paths

업로더는 아래 경로를 기본값으로 사용합니다.

- YouTube client secret: `~/.openclaw/credentials/youtube_client_secret.json`
- YouTube token cache: `~/.openclaw/credentials/youtube_token.json`
- TikTok credentials: `~/.openclaw/credentials/tiktok_credentials.json`
- Instagram credentials: `~/.openclaw/credentials/instagram_credentials.json`

## 1. YouTube Shorts OAuth2

### Google Cloud 설정

1. Google Cloud Console에서 프로젝트를 만든 뒤 YouTube Data API v3를 활성화합니다.
2. OAuth consent screen을 설정합니다.
3. Credentials에서 `OAuth client ID`를 만들고 Application type은 `Desktop app`으로 선택합니다.
4. 다운로드한 JSON을 `~/.openclaw/credentials/youtube_client_secret.json`으로 저장합니다.

첫 업로드 시 [pipeline/youtube_upload.py](/Users/bigmac/openclaw/workspace/sns_auto/pipeline/youtube_upload.py)가 브라우저 인증을 열고, 승인 후 `youtube_token.json`을 저장합니다. 이후에는 refresh token으로 자동 갱신합니다.

### YouTube credential 예시

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": [
      "http://localhost"
    ]
  },
  "privacy_status": "private",
  "category_id": "22",
  "made_for_kids": false
}
```

`privacy_status` / `category_id` / `made_for_kids`는 `installed` 밖에 같이 넣어도 됩니다.

### 수동 테스트

```bash
python3 pipeline/youtube_upload.py /Users/bigmac/.openclaw/workspace/content_factory/publish_queue/<task>.json
```

## 2. TikTok Content Posting API

### TikTok 개발자 설정

1. TikTok Developer Portal에서 앱을 생성합니다.
2. `Content Posting API` 사용 권한을 신청합니다.
3. OAuth 승인 후 access token, refresh token을 발급받습니다.
4. 아래 JSON을 `~/.openclaw/credentials/tiktok_credentials.json`에 저장합니다.

### TikTok credential 예시

```json
{
  "client_key": "YOUR_CLIENT_KEY",
  "client_secret": "YOUR_CLIENT_SECRET",
  "access_token": "YOUR_ACCESS_TOKEN",
  "refresh_token": "YOUR_REFRESH_TOKEN",
  "privacy_level": "SELF_ONLY",
  "disable_comment": false,
  "disable_duet": false,
  "disable_stitch": false,
  "video_cover_timestamp_ms": 1000
}
```

[pipeline/tiktok_upload.py](/Users/bigmac/openclaw/workspace/sns_auto/pipeline/tiktok_upload.py)는 `refresh_token`이 있으면 먼저 토큰 갱신을 시도한 뒤, Direct Post 업로드를 수행합니다.

### 수동 테스트

```bash
python3 pipeline/tiktok_upload.py /Users/bigmac/.openclaw/workspace/content_factory/publish_queue/<task>.json
```

## 3. Instagram Reels Graph API

### Meta 앱 설정

1. Meta for Developers에서 앱을 만들고 Instagram Graph API를 연결합니다.
2. Instagram Professional account와 Facebook Page를 연결합니다.
3. long-lived access token과 `instagram_user_id`를 확보합니다.
4. 렌더된 mp4를 Meta 서버가 읽을 수 있는 공개 URL로 노출해야 합니다.

Instagram Reels는 로컬 파일 경로를 직접 업로드하지 못하므로, 아래 둘 중 하나가 필요합니다.

- `media_base_url`: 렌더된 mp4 파일명이 그대로 노출되는 공개 베이스 URL
- `media_url_template`: 파일명/베이스명을 조합하는 템플릿 URL

### Instagram credential 예시

```json
{
  "access_token": "YOUR_LONG_LIVED_TOKEN",
  "instagram_user_id": "YOUR_IG_USER_ID",
  "graph_api_version": "v22.0",
  "media_base_url": "https://cdn.example.com/content_factory/videos/",
  "share_to_feed": true,
  "thumb_offset_ms": 1000,
  "poll_interval_seconds": 5,
  "poll_timeout_seconds": 300
}
```

또는:

```json
{
  "access_token": "YOUR_LONG_LIVED_TOKEN",
  "instagram_user_id": "YOUR_IG_USER_ID",
  "media_url_template": "https://cdn.example.com/reels/{filename}"
}
```

### 수동 테스트

```bash
python3 pipeline/instagram_upload.py /Users/bigmac/.openclaw/workspace/content_factory/publish_queue/<task>.json
```

## 4. n8n 자동 업로드

[build_wf02_final.py](/Users/bigmac/openclaw/workspace/sns_auto/build_wf02_final.py)는 렌더 완료 후 아래 순서로 업로드 노드를 생성합니다.

1. `build_upload_queue`
2. `validate_upload_queue`
3. `split_upload_tasks`
4. `route_*_upload`
5. `upload_*`
6. `log_*_upload`

업로드 HTTP 노드는 로컬 파이프라인 서비스에 연결됩니다.

- `POST http://host.docker.internal:8010/upload/youtube`
- `POST http://host.docker.internal:8010/upload/tiktok`
- `POST http://host.docker.internal:8010/upload/instagram`

로그는 두 군데에 남습니다.

- 파이프라인 서비스 로그: `/Users/bigmac/.openclaw/workspace/content_factory/logs/upload/`
- n8n 추가 로그: `/Users/bigmac/.openclaw/workspace/content_factory/logs/upload/YYYY-MM-DD_n8n_upload.log`

## Notes

- YouTube Shorts는 별도 Shorts API가 아니라 일반 `videos.insert` 업로드입니다. 세로 비율과 짧은 길이 조건을 만족하면 Shorts로 분류됩니다.
- TikTok / Instagram API 권한은 앱 심사 상태에 따라 실제 배포 계정에서 제한될 수 있습니다.
- Instagram Reels는 공개 URL을 필수로 요구하므로, CDN 또는 외부 접근 가능한 static hosting 설정이 먼저 되어 있어야 합니다.
