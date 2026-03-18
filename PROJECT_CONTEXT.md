# SNS 자동화 프로젝트 - Claude 프로젝트 지침

## 프로젝트 개요
맥미니에서 n8n + MLX + edge-tts + ffmpeg으로 완전 자동화된 숏폼 SNS 콘텐츠 파이프라인 구축 중.
관계심리학 콘텐츠를 자동 생성해서 TikTok/YouTube Shorts/Instagram Reels에 자동 업로드하는 시스템.

---

## 현재 완료된 것 ✅

### 인프라
- n8n Docker 실행 중: `content-factory-n8n` (port 5678)
- MLX 로컬 서버: `localhost:8000` (Qwen2.5-7B-Instruct-4bit)
- edge-tts 설치 완료
- ffmpeg-full 설치 완료 (libass 포함 - ASS 자막 지원)
- GitHub 자동 커밋/푸시: https://github.com/newhypes/sns-automation

### 파이프라인
- ✅ topic → hook → script 생성 (MLX)
- ✅ edge-tts 음성 생성 (female/male/psych 3종)
- ✅ ASS 자막 생성 (크고 굵은 흰색, 검은 외곽선, 하단 중앙)
- ✅ ffmpeg 영상 렌더링 (1080x1920, 배경 그라디언트)
- ✅ publish_queue 생성
- ✅ 업로드 스크립트 scaffold 완성 (크리덴셜 연결 대기 중)

### n8n 워크플로우
- 현재 워크플로우: `WF02_final.json`, `WF02_final_import.json`
- 위치: `/Users/bigmac/openclaw/workspace/sns_auto/`

---

## 남은 작업 ❌

### 1. YouTube Shorts 크리덴셜 연결 (다음 작업)
- Google Cloud Console에서 프로젝트 생성
- YouTube Data API v3 활성화
- OAuth2 client_secret.json 다운로드
- 저장: `~/.openclaw/credentials/youtube_client_secret.json`
- 첫 실행 시 브라우저 OAuth 승인 → `youtube_token.json` 자동 생성

### 2. TikTok 크리덴셜 연결
- TikTok Developer 계정 생성
- Content Posting API 신청
- 저장: `~/.openclaw/credentials/tiktok_credentials.json`

### 3. Instagram Reels 크리덴셜 연결
- Meta Developer 계정
- Instagram Graph API
- 공개 접근 가능한 video_url 필요 (media_base_url 설정)
- 저장: `~/.openclaw/credentials/instagram_credentials.json`

### 4. 품질 개선 (나중에)
- 자막 싱크 0.3초 오차 fine-tuning
- edge-tts → ElevenLabs 유료 전환 (음질 개선)
- 배경 그라디언트 → 실제 이미지/영상으로 업그레이드
- 캐릭터 이미지 90장 생성 (female/male/psych 각 30장)

---

## 핵심 경로

### 맥미니 경로
```
콘텐츠 폴더:     /Users/bigmac/.openclaw/workspace/content_factory/
n8n Docker:      /Users/bigmac/.openclaw/workspace/content_factory/n8n/
워크플로우 파일:  /Users/bigmac/openclaw/workspace/sns_auto/
크리덴셜:        /Users/bigmac/.openclaw/credentials/
```

### 콘텐츠 폴더 구조
```
content_factory/
├── scripts/       # JSON 스크립트
├── audio/         # MP3 음성
├── subs/          # SRT/ASS 자막
├── videos/        # MP4 최종 영상
├── images/
│   ├── female_host/   # 핑크/오렌지 그라디언트
│   ├── male_host/     # 블루/다크 그라디언트
│   └── psych_host/    # 퍼플/블랙 그라디언트
├── queue/
│   ├── pending/
│   ├── rendering/
│   ├── ready_to_upload/
│   ├── uploaded/
│   └── failed/
└── logs/
    ├── generation/
    └── upload/
```

### n8n 볼륨 마운트
- `/files` → `/Users/bigmac/.openclaw/workspace/content_factory/`

---

## 콘텐츠 전략

### 3개 계정
- **female**: 여성 팟캐스트 관점 (en-US-JennyNeural)
- **male**: 남성 팟캐스트 관점 (en-US-GuyNeural)  
- **psych**: 심리학 나레이터 (en-US-AriaNeural)

### 생산 목표
- 1 topic → 3 variant 영상
- 목표: 5 topics/day = 15 videos/day = 45 uploads/day
- 현재 단계: Phase 1 안정화 (1-2 topics/day)

### 파일 네이밍
- `YYYY-MM-DD_topic-slug_variant.ext`
- 예: `2026-03-15_why-ignoring-texts_female.mp4`

---

## 주요 파일 목록 (sns_auto 폴더)

| 파일 | 설명 |
|------|------|
| `WF02_final.json` | 최신 n8n 워크플로우 |
| `WF02_final_import.json` | n8n import용 |
| `pipeline_service.py` | 렌더링 핵심 서비스 (port 8010) |
| `build_wf02_final.py` | 워크플로우 빌더 |
| `smoke_test_pipeline.py` | 전체 파이프라인 테스트 |
| `youtube_upload.py` | YouTube 업로드 |
| `tiktok_upload.py` | TikTok 업로드 |
| `instagram_upload.py` | Instagram 업로드 |
| `upload_common.py` | 업로드 공통 유틸 |
| `generate_variant_backgrounds.sh` | 배경 이미지 생성 |
| `CODEX.md` | Codex AI 작업 지침 |
| `README.md` | 크리덴셜 설정 가이드 |

---

## 작업 도구

### Claude (현재)
- 전략 수립, 파일 생성, 워크플로우 JSON 작성
- 오류 분석 및 해결 방향 제시

### Codex CLI (터미널 자동화)
- 실제 파일 수정, 터미널 명령 실행, 에러 자동 수정
- 실행: `cd /Users/bigmac/openclaw/workspace/sns_auto && codex`
- 작업 지시: CODEX.md 읽고 실행

### n8n (워크플로우 실행)
- 접속: http://localhost:5678
- 스케줄 실행, 파이프라인 오케스트레이션

### MLX 서버 (로컬 LLM)
- 실행: `mlx_lm.server --model mlx-community/Qwen2.5-7B-Instruct-4bit --port 8000`

---

## 다음 대화 시작 방법

이 파일을 Claude 프로젝트에 첨부하고 아래처럼 시작하세요:

```
PROJECT_CONTEXT.md를 읽었어. 
지금 YouTube 크리덴셜 연결부터 시작하자.
```

또는 Codex에:
```
CODEX.md와 PROJECT_CONTEXT.md 읽고 YouTube 크리덴셜 연결부터 해줘.
```

---

## 영상 스타일 & 컨셉

### 현재 영상 구성
- **포맷**: 배경 그라디언트 + 음성 + ASS 자막 (텍스트 기반 숏폼)
- **크기**: 1080x1920 (9:16 세로)
- **길이**: 약 27초
- **스타일**: 심리학 인용 + 나레이션 스타일

### 배경 스타일 (variant별)
- **female**: 따뜻한 핑크/오렌지 그라디언트 (`warm_sunrise_01.png` 등 3장)
- **male**: 차갑고 모던한 블루/다크 그라디언트
- **psych**: 어둡고 미스터리한 퍼플/블랙 그라디언트
- 이미지 위치: `/files/images/female_host/`, `/files/images/male_host/`, `/files/images/psych_host/`

### 자막 스타일
- ASS 자막, libass 렌더
- 큰 흰색 볼드 텍스트 + 검은 외곽선
- 하단 중앙 배치
- 한 줄씩 표시
- 폰트 사이즈 80 고정
- 싱크 오차 약 0.3초 (추후 개선 예정)

### 음성
- 현재: edge-tts (테스트용)
- 추후: ElevenLabs 유료 전환 예정
- female: `en-US-JennyNeural`
- male: `en-US-GuyNeural`
- psych: `en-US-AriaNeural`

### 향후 개선 예정
- 배경: 그라디언트 → AI 생성 이미지 또는 루프 영상
- 캐릭터 이미지 90장 생성 (female/male/psych 각 30장)
- 음성: ElevenLabs로 교체
- 자막 싱크 fine-tuning
