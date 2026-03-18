# WF02 → WF03 변경안 및 ffmpeg 카드 기반 렌더 설계

## 1. n8n WF03 워크플로우 변경안

### 기존 WF02 구조
```
Schedule → Generate Topic → Generate Hook → Assign Variants
→ Generate Script (MLX) → TTS → Subtitle → Render (단일 배경) → Queue → Upload
```

### 신규 WF03 구조
```
Schedule
  → Read topic_pack.json (DeerFlow 결과 intake)
  → Select Topic (priority + repeat_risk 기준)
  → Generate psych_card Script (Claude API or GPT)
  → Save psych_script_card.json
  → TTS (카드별 voiceover 분리 생성)
  → Build render_manifest.json
  → Card Renderer (ffmpeg card-based)
  → Merge Cards → Final MP4
  → Upload Queue
  → Platform Upload (YouTube/TikTok/Instagram)
  → Log Result
```

### 핵심 변경 노드

#### 노드 1: Topic Intake
- 기존: MLX로 topic 즉석 생성
- 변경: `/files/topics/topic_pack_YYYY-MM-DD.json` 읽기
- 없을 경우: MLX fallback으로 즉석 생성 (기존 방식 유지)

#### 노드 2: Script Generator
- 기존: MLX HTTP 호출 (단순 spoken script)
- 변경: Claude API 또는 GPT → psych_card 구조 JSON 출력
- 출력: `psych_script_card.json` (카드 배열 포함)

#### 노드 3: TTS Generator
- 기존: 전체 스크립트 1개 MP3
- 변경: 카드별 voiceover 분리 생성 후 순서대로 concat
- 출력: `audio/SLUG_card_01.mp3` ... `audio/SLUG_card_06.mp3` + `audio/SLUG_full.mp3`

#### 노드 4: Manifest Builder
- 신규: psych_script_card.json → render_manifest.json 변환
- start_sec 자동 계산 (각 카드 duration_sec 누적)

#### 노드 5: Card Renderer
- 기존: ffmpeg 단일 배경 + 자막
- 변경: 카드별 개별 렌더 후 concat (아래 ffmpeg 설계 참고)

---

## 2. ffmpeg 카드 기반 렌더 구조

### 기존 렌더 방식
```bash
ffmpeg -loop 1 -i background.png -i audio.mp3 \
  -vf "ass=subtitle.ass" \
  -t 27 output.mp4
```
→ 정지 이미지 1장 + 자막 오버레이. 단조롭고 retention 약함.

### 신규 카드 기반 렌더 방식

#### 개념
각 카드를 독립적인 클립으로 렌더한 뒤 concat으로 합치는 구조.

```
card_01.mp4  (hook,     2.5초, keyword_card,     zoom_in)
card_02.mp4  (claim,    4.0초, concept_card,     slide_up)
card_03.mp4  (example,  6.0초, chat_ui,          message_pop)
card_04.mp4  (explain,  7.0초, explanation_card, pan_slow)
card_05.mp4  (reframe,  4.0초, reframe_card,     fade_in)
card_06.mp4  (cta,      3.5초, cta_card,         pulse)
        ↓
ffmpeg concat → final.mp4 (27초)
```

#### 카드 타입별 렌더 방법

**T1. keyword_card (hook)**
```bash
ffmpeg -t {duration} \
  -f lavfi -i "color=c=0x1a1a2e:size=1080x1920:rate=30" \
  -vf "
    drawtext=text='{onscreen_text}':
      fontsize=90:fontcolor=white:
      x=(w-tw)/2:y=(h-th)/2:
      fontfile=/path/to/font.ttf:
      borderw=4:bordercolor=black,
    zoompan=z='min(zoom+0.002,1.05)':d={frames}:s=1080x1920
  " card_01.mp4
```

**T2. chat_ui (example)**
```bash
# Python 스크립트로 PIL/Pillow로 채팅 UI 이미지 프레임 생성
# → ffmpeg로 이미지 시퀀스를 영상으로 변환
python3 render_chat_ui.py \
  --messages "They reply late, watch your stories, then disappear again." \
  --duration 6.0 \
  --output card_03.mp4
```

**T3. concept_card / explanation_card**
```bash
ffmpeg -t {duration} \
  -f lavfi -i "color=c=0x16213e:size=1080x1920:rate=30" \
  -vf "
    drawtext=text='{line1}':fontsize=72:fontcolor=white:x=(w-tw)/2:y=700,
    drawtext=text='{line2}':fontsize=52:fontcolor=0xaaaaaa:x=(w-tw)/2:y=820,
    fade=t=in:st=0:d=0.3
  " card_04.mp4
```

**T4. cta_card**
```bash
ffmpeg -t {duration} \
  -f lavfi -i "color=c=0x0f3460:size=1080x1920:rate=30" \
  -vf "
    drawtext=text='{cta_text}':fontsize=68:fontcolor=white:x=(w-tw)/2:y=(h-th)/2,
    fade=t=in:st=0:d=0.2
  " card_06.mp4
```

#### 카드 concat + 오디오 합치기
```bash
# concat list 생성
echo "file 'card_01.mp4'" > concat_list.txt
echo "file 'card_02.mp4'" >> concat_list.txt
echo "file 'card_03.mp4'" >> concat_list.txt
echo "file 'card_04.mp4'" >> concat_list.txt
echo "file 'card_05.mp4'" >> concat_list.txt
echo "file 'card_06.mp4'" >> concat_list.txt

# 비디오 concat
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy video_only.mp4

# 오디오 합치기
ffmpeg -i video_only.mp4 -i audio_full.mp3 \
  -c:v copy -c:a aac -shortest \
  final_output.mp4
```

---

## 3. 디렉터리 구조 변경안

### 추가되는 폴더
```
content_factory/
├── topics/                    # DeerFlow topic pack 저장
│   └── topic_pack_YYYY-MM-DD.json
├── reports/                   # DeerFlow 리서치 결과
│   ├── trend_report_YYYY-MM-DD.json
│   ├── competitor_report_YYYY-MM-DD.json
│   └── format_playbook_YYYY-MM-DD.json
├── manifests/                 # render_manifest.json 저장
│   └── SLUG_manifest.json
├── cards/                     # 카드별 중간 렌더 클립
│   └── SLUG/
│       ├── card_01.mp4
│       ├── card_02.mp4
│       └── ...
├── templates/                 # 카드 시각 템플릿
│   ├── psych_hook_v1.json
│   ├── psych_chat_v1.json
│   ├── psych_concept_v1.json
│   └── psych_cta_v1.json
└── (기존 폴더 유지)
    ├── scripts/
    ├── audio/
    ├── subs/
    ├── videos/
    ├── queue/
    └── logs/
```

---

## 4. 기존 assets 재사용 원칙

- 기존 배경 그라디언트 이미지 → `background_mode: gradient` fallback으로 유지
- 기존 ASS 자막 생성 로직 → 전체 영상 자막용으로 유지 (카드 온스크린 텍스트와 별개)
- 기존 edge-tts TTS → 카드별 분리 생성으로 확장 (기존 full-script TTS도 병행)
- 기존 queue 구조 → 변경 없음
- 기존 upload 스크립트 → 변경 없음

---

## 5. Phase 1 구현 우선순위

1. `render_chat_ui.py` 작성 (채팅 UI 카드 렌더러)
2. `card_renderer.py` 작성 (카드 타입별 ffmpeg 호출)
3. `manifest_builder.py` 작성 (psych_script_card → render_manifest 변환)
4. `pipeline_service.py` 수정 (카드 기반 렌더 파이프라인 통합)
5. n8n WF03 빌드 (WF02 기반 확장)
6. psych 샘플 10개 생성 및 검증
