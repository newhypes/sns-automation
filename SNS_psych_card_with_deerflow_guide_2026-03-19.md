# SNS 자동화 가이드 v2
## 메인 포맷: 심리 해설 카드형 + DeerFlow 리서치 레이어

이 문서는 다른 AI(Codex, Claude, ChatGPT, OpenClaw 등)에게 그대로 넘겨서 작업을 시킬 수 있도록 작성된 실행 지침서다.

---

## 1. 프로젝트 목적

기존 SNS 자동화 프로젝트의 핵심 목표는 유지한다.

- 관계심리 숏폼 콘텐츠를 자동 생성한다.
- TikTok / YouTube Shorts / Instagram Reels에 업로드한다.
- n8n을 메인 실행 엔진으로 사용한다.
- MLX를 저비용 초안 생성 엔진으로 사용한다.
- ffmpeg를 결정론적 렌더 엔진으로 사용한다.
- 업로드는 queue 기반으로 안정적으로 처리한다.

다만 메인 영상 포맷은 바꾼다.

기존 메인 포맷:
- 배경 그라디언트 + 음성 + 자막 중심 텍스트형 숏폼

새 메인 포맷:
- 심리 해설 카드형 (Psych Explainer Card Format)
- DeerFlow를 앞단 트렌드/리서치/포맷 분석 레이어로 추가

---

## 2. 핵심 전략 결정

### 바뀌는 것

1. 메인 영상 포맷을 `psych` 중심으로 재편한다.
2. 고정 이미지 팟캐스트형을 메인 포맷에서 내린다.
3. DeerFlow를 "메인 러너"가 아니라 "리서치/기획 엔진"으로 붙인다.
4. n8n은 계속 메인 프로덕션 컨트롤 타워로 유지한다.

### 유지하는 것

1. 기존 content_factory 폴더 구조
2. 기존 n8n + MLX + ffmpeg 파이프라인
3. 기존 queue 기반 업로드 구조
4. 기존 파일 네이밍 규칙
5. 기존 female / male / psych 계정 구조

### 중요한 원칙

- Deterministic workflow first.
- Agentic autonomy second.
- DeerFlow는 매일 실행되는 메인 생산 러너가 아니다.
- DeerFlow는 리서치, 트렌드 분석, 토픽 팩 생성, 경쟁채널 분석에 사용한다.
- 실제 반복 실행은 n8n이 담당한다.

---

## 3. 목표 포맷 정의: 심리 해설 카드형

### 포맷 목적

짧은 시간 안에 관계심리 주제를 명확하게 설명하고, 시청자가 즉시 이해할 수 있도록 하는 정보형 쇼츠 포맷.

### 영상 길이

- 권장: 22~32초
- 기본 목표: 27초 전후

### 화면 구조

영상은 한 명의 심리 해설자(`psych`)가 설명하는 구조로 간다.

권장 씬 구성:

1. Hook Card (0~2초)
2. Claim Card (3~7초)
3. Example Card (8~14초)
4. Explanation Card (15~22초)
5. Conclusion / Reframe Card (23~27초)
6. CTA Card (선택, 2~4초)

### 화면 요소

반드시 아래 요소를 조합해 사용한다.

- 키워드 카드
- 체크리스트 카드
- 상황 예시 카드
- 메시지/채팅 UI 카드
- 통계/심리 개념 카드
- 루프 배경 영상 또는 추상적 모션 배경
- 강한 자막 하이라이트

### 금지사항

- 단순 정지 이미지 1장만 20초 이상 유지 금지
- 팟캐스트 마이크 이미지 + 자막만 반복 금지
- 게임 브레인롯 배경을 메인 포맷으로 고정 금지
- 배경과 무관한 장식적 요소만 과도하게 사용 금지

---

## 4. 왜 psych 중심으로 가는가

심리 해설 카드형은 자동화가 쉽고, 관계심리 니치와 잘 맞으며, 브랜드 신뢰 형성에도 유리하다.

장점:

- 화자 1명 중심이라 자동화가 쉽다.
- 씬 구조가 규칙적이라 템플릿화가 쉽다.
- female/male 논쟁형보다 렌더 복잡도가 낮다.
- 채널의 전문성, 신뢰감, 설명력을 만들기 좋다.
- 향후 female/male 포맷을 서브 포맷으로 붙이기 쉽다.

운영 원칙:

- 메인 포맷은 psych
- female/male은 서브 포맷 또는 실험 포맷
- topic 1개당 반드시 psych 1개는 생성
- 초기 Phase 1에서는 psych 단일 포맷만 안정화해도 된다

---

## 5. DeerFlow의 역할

DeerFlow는 다음 역할만 맡긴다.

### DeerFlow가 해야 하는 일

1. 트렌드 리서치
   - YouTube Shorts, TikTok, Instagram에서 관계심리/연애/문자습관/애착 관련 인기 주제 수집

2. 경쟁채널 분석
   - 제목 패턴
   - 첫 2초 훅 구조
   - 영상 길이 분포
   - 설명형/논쟁형/문자형 포맷 비율

3. 토픽 팩 생성
   - 하루 20~50개 수준의 후보 토픽 생성
   - 중복 제거
   - 클러스터링
   - 우선순위 점수화

4. 포맷 분석 리포트 생성
   - 어떤 유형이 retention에 유리한지 정리
   - 어떤 제목 패턴이 많이 쓰이는지 정리
   - 어떤 시청자 감정을 건드리는지 정리

5. 리서치 결과를 구조화된 JSON으로 저장

### DeerFlow가 하면 안 되는 일

1. 매일 전체 생산 파이프라인 스케줄 실행
2. 업로드 큐 제어
3. TTS / 자막 / ffmpeg / 업로드를 직접 메인 오케스트레이션
4. 크리덴셜이 얽힌 민감한 업로드 자동화의 중앙 제어

### 결론

DeerFlow = research and planning brain
n8n = production runner
MLX = cheap routine writer
ffmpeg = deterministic renderer

---

## 6. 새로운 전체 아키텍처

### Layer A: Research / Planning Layer

도구:
- DeerFlow
- GPT / Claude / OpenClaw / Codex

기능:
- 최신 트렌드 수집
- 경쟁 채널 분석
- topic pack 생성
- hook 패턴 분석
- script template 개선
- visual template 개선

출력:
- trend_report.json
- competitor_report.json
- topic_pack.json
- format_playbook.json
- prompt_patch.md

### Layer B: Production Layer

도구:
- n8n
- MLX
- edge-tts 또는 ElevenLabs
- subtitle generator
- ffmpeg
- uploader scripts

기능:
- 일정 실행
- topic intake
- script generation
- audio generation
- subtitle generation
- video rendering
- upload queue 생성
- 플랫폼 업로드
- 리포트/재시도

출력:
- scripts/*.json
- audio/*.mp3
- subs/*.srt 또는 *.ass
- videos/*.mp4
- queue/*.json
- reports/*.json

---

## 7. 새 파일/데이터 스키마

다른 AI는 아래 스키마를 기준으로 설계하거나 수정해야 한다.

### 7.1 trend_report.json

```json
{
  "report_date": "2026-03-19",
  "niche": "relationship psychology",
  "platforms": ["youtube_shorts", "tiktok", "instagram_reels"],
  "top_patterns": [
    {
      "pattern_name": "why-do-you-still-miss-them",
      "description": "unfinished closure / intermittent reinforcement angle",
      "strength_score": 8.7,
      "evidence": ["title pattern", "hook style", "visual structure"]
    }
  ],
  "emerging_topics": [
    {
      "topic": "why mixed signals feel addictive",
      "cluster": "attachment / ambiguity",
      "score": 9.1,
      "novelty": 7.8,
      "repeat_risk": 3.1
    }
  ],
  "recommended_formats": [
    "psych_card",
    "chat_ui_explainer"
  ],
  "notes": []
}
```

### 7.2 topic_pack.json

```json
{
  "pack_date": "2026-03-19",
  "niche": "relationship psychology",
  "topics": [
    {
      "slug": "mixed-signals-feel-addictive",
      "title": "Why mixed signals feel addictive",
      "cluster": "ambiguity",
      "emotion_target": "anxiety + curiosity",
      "format": "psych_card",
      "priority": "high",
      "score": 9.0,
      "angle": "intermittent reinforcement"
    }
  ]
}
```

### 7.3 psych_script_card.json

```json
{
  "date": "2026-03-19",
  "slug": "mixed-signals-feel-addictive",
  "variant": "psych",
  "format": "psych_card",
  "target_duration_sec": 27,
  "title": "Why mixed signals feel addictive",
  "hook_text": "Why do mixed signals make you obsess more?",
  "cards": [
    {
      "card_id": 1,
      "type": "hook",
      "duration_sec": 2.5,
      "voiceover": "Why do mixed signals make you obsess more?",
      "onscreen_text": "Mixed signals = more obsession?",
      "visual_type": "keyword_card",
      "motion": "zoom_in"
    },
    {
      "card_id": 2,
      "type": "claim",
      "duration_sec": 4.0,
      "voiceover": "Because uncertainty keeps your brain chasing closure.",
      "onscreen_text": "Uncertainty keeps you chasing closure",
      "visual_type": "concept_card",
      "motion": "slide_up"
    },
    {
      "card_id": 3,
      "type": "example",
      "duration_sec": 6.0,
      "voiceover": "They reply late, watch your stories, then disappear again.",
      "onscreen_text": "Late replies. Story views. Then silence.",
      "visual_type": "chat_ui",
      "motion": "message_pop"
    },
    {
      "card_id": 4,
      "type": "explanation",
      "duration_sec": 7.0,
      "voiceover": "That random pattern acts like intermittent reward. The brain holds on harder when the reward is unpredictable.",
      "onscreen_text": "Unpredictable reward = stronger attachment",
      "visual_type": "explanation_card",
      "motion": "pan_slow"
    },
    {
      "card_id": 5,
      "type": "reframe",
      "duration_sec": 4.0,
      "voiceover": "So it may not be deep love. It may be unresolved anxiety.",
      "onscreen_text": "Not always love. Sometimes unresolved anxiety.",
      "visual_type": "reframe_card",
      "motion": "fade_in"
    },
    {
      "card_id": 6,
      "type": "cta",
      "duration_sec": 3.0,
      "voiceover": "Have you ever mistaken inconsistency for chemistry?",
      "onscreen_text": "Have you confused inconsistency with chemistry?",
      "visual_type": "cta_card",
      "motion": "pulse"
    }
  ],
  "hashtags": [
    "#psychology",
    "#dating",
    "#attachment",
    "#relationshipadvice"
  ]
}
```

### 7.4 render_manifest.json

```json
{
  "slug": "mixed-signals-feel-addictive",
  "variant": "psych",
  "format": "psych_card",
  "video_size": "1080x1920",
  "fps": 30,
  "audio_path": "audio/2026-03-19_mixed-signals-feel-addictive_psych.mp3",
  "subtitle_path": "subs/2026-03-19_mixed-signals-feel-addictive_psych.ass",
  "background_mode": "loop_video",
  "cards": [
    {
      "card_id": 1,
      "asset_type": "keyword_card",
      "template": "psych_hook_v1"
    }
  ]
}
```

---

## 8. 심리 해설 카드형 제작 규칙

### 제목 규칙

제목은 아래 유형 중심으로 만든다.

- Why you still miss them
- Why mixed signals feel addictive
- Why late replies create obsession
- Psychology of people who keep you confused
- Why closure matters more than chemistry

### Hook 규칙

처음 2초 안에 아래 중 하나를 해야 한다.

- 질문 던지기
- 오해 뒤집기
- 감정 이름 붙이기
- 흔한 경험을 즉시 호출하기

예시:
- Why do you want them more after they pull away?
- That may not be love. It may be uncertainty.
- The worst relationships are often the hardest to forget.

### 내용 규칙

각 영상은 아래 구조를 반드시 따라야 한다.

1. 문제 제기
2. 관찰 가능한 예시
3. 심리 개념 설명
4. 재해석 또는 정리
5. 댓글/저장 유도

### 톤 규칙

- 차분하고 단정한 설명형 톤
- 과장된 공포 조성 금지
- 단정적 진단 금지
- 의학적/임상적 확정 표현 남용 금지
- 자기계발식 공허한 문장 남발 금지

---

## 9. 시각 템플릿 규칙

다른 AI는 아래 4종 템플릿을 우선 설계해야 한다.

### T1. Hook Keyword Card
- 큰 핵심 문장 1개
- 배경은 어두운 추상 루프 또는 미세 모션
- 1.5~2.5초

### T2. Example / Chat UI Card
- 문자/카톡/DM 형태로 사례 제시
- 3~6초
- 타이핑 애니메이션 또는 말풍선 팝업

### T3. Concept / Explanation Card
- 심리 개념 1개
- 보조 키워드 2~3개
- 4~7초

### T4. Reframe / CTA Card
- 결론 한 줄
- 댓글 질문 또는 저장 유도 문장
- 2~4초

템플릿은 공통 컴포넌트로 설계하고, 카드 타입만 바꿔서 재사용 가능해야 한다.

---

## 10. DeerFlow가 생성해야 하는 산출물

DeerFlow에게 아래 작업을 맡긴다.

### 작업 A: Trend Scan
매일 1회 또는 주 3회 실행

출력:
- `reports/trend_report_YYYY-MM-DD.json`

포함 내용:
- 최근 상위 주제 클러스터
- 자주 보이는 제목 패턴
- 첫 2초 훅 패턴
- 설명형 포맷 강도
- 중복/포화된 주제 경고

### 작업 B: Competitor Report
주 1~2회 실행

출력:
- `reports/competitor_report_YYYY-MM-DD.json`

포함 내용:
- 상위 채널 10~30개 분석
- 영상 길이 범위
- 제목 템플릿 패턴
- 화면 구성 패턴
- 썸네일/첫 프레임 특징

### 작업 C: Topic Pack Builder
매일 실행 가능

출력:
- `topics/topic_pack_YYYY-MM-DD.json`

포함 내용:
- topic 20~50개
- 우선순위 점수
- emotional trigger
- recommended format
- repeat risk

### 작업 D: Format Playbook Update
주 1회 실행

출력:
- `reports/format_playbook_YYYY-MM-DD.json`

포함 내용:
- 이번 주 잘 먹히는 hook 유형
- chat UI 사용 비율 권장치
- CTA 위치 권장안
- 포맷 과포화 경고

---

## 11. n8n이 해야 하는 일

n8n은 DeerFlow 결과물을 받아 아래 순서로 실행한다.

1. topic pack intake
2. psych_card용 topic 선택
3. MLX로 1차 스크립트 초안 생성
4. 필요 시 GPT 또는 고급 모델로 refinement
5. script JSON 저장
6. TTS 생성
7. 자막 생성
8. card assets / manifest 생성
9. ffmpeg 렌더
10. upload queue 생성
11. 플랫폼 업로드
12. 보고서 기록 및 실패 재시도

### 매우 중요

- n8n은 창의 전략을 즉석에서 invent 하지 않는다.
- n8n은 playbook과 template을 읽고 실행만 한다.
- 모든 단계는 파일과 상태 마커를 남겨야 한다.
- 중간 실패 시 재개 가능해야 한다.

---

## 12. 다른 AI에게 맡길 구체 작업 목록

다른 AI는 아래 작업을 우선순위대로 수행해야 한다.

### Priority 1
1. psych_card용 script JSON 스키마 확정
2. render_manifest 스키마 확정
3. card template 4종 설계
4. n8n workflow 변경안 설계

### Priority 2
5. DeerFlow trend_report / topic_pack JSON 산출 포맷 설계
6. DeerFlow용 프롬프트 작성
7. MLX용 psych_card script generation prompt 작성
8. title / hook scoring 규칙 설계

### Priority 3
9. ffmpeg 렌더링 파이프라인을 card-based 구조로 수정
10. chat UI 카드 자동 생성 로직 추가
11. reusable motion backgrounds 구조 설계
12. quality gate 및 fallback 규칙 추가

### Priority 4
13. female / male 서브 포맷을 psych_card 파생형으로 재설계
14. analytics 피드백 루프 설계
15. performance report와 topic selection loop 연결

---

## 13. 구현 순서

### Phase 1: format shift
목표:
- psych 단일 포맷이 안정적으로 자동 생성/렌더되게 만들기

해야 할 일:
- script schema 변경
- card template 4종 제작
- ffmpeg 템플릿 수정
- psych 전용 10개 샘플 생성

### Phase 2: deerflow integration
목표:
- DeerFlow가 매일 topic pack과 trend report를 공급하게 만들기

해야 할 일:
- DeerFlow prompt 설계
- JSON output 표준화
- n8n intake 노드 추가
- 중복 topic 제거 규칙 추가

### Phase 3: quality loop
목표:
- 조회수/저장률/완시율을 바탕으로 topic selection 개선

해야 할 일:
- 업로드 결과를 리포트로 저장
- topic별 performance tagging
- 다음 날 topic scoring에 반영

### Phase 4: multi-format expansion
목표:
- psych 안정화 후 female/male 또는 chat_ui 파생 포맷 확대

---

## 14. 성공 기준

### 최소 성공 기준
- DeerFlow가 topic pack JSON을 생성한다.
- n8n이 topic pack을 읽어 psych_card 1개를 끝까지 렌더한다.
- 하나의 psych_card 영상이 자동으로 queue에 들어간다.
- 실패 시 어느 단계에서 멈췄는지 로그가 남는다.

### 운영 성공 기준
- 하루 3개 psych_card를 안정적으로 생성한다.
- 30개 이상 렌더 실패 없이 누적된다.
- topic과 render 결과가 추적 가능하다.
- 이후 female/male 서브 포맷 확장이 쉬운 구조가 된다.

---

## 15. 다른 AI에게 절대 하지 말아야 할 지시

- 처음부터 모든 포맷을 동시에 완성하려 하지 말 것
- DeerFlow를 메인 스케줄러로 만들지 말 것
- 현재 working asset을 버리고 전면 재구축하지 말 것
- 크리덴셜을 프롬프트나 코드에 하드코딩하지 말 것
- 업로드 안정화 전에 45 uploads/day 풀스케일을 목표로 하지 말 것

---

## 16. 다른 AI에 바로 붙여넣는 시작 프롬프트

아래 문장을 그대로 복사해서 다른 AI에 넣어도 된다.

```text
첨부한 가이드 파일을 읽고, 현재 SNS 자동화 프로젝트를 "심리 해설 카드형 + DeerFlow 리서치 레이어" 구조로 재설계해줘.

중요 원칙:
1) n8n은 메인 production runner로 유지
2) DeerFlow는 trend research / topic pack / competitor analysis 전용
3) 기존 working assets는 최대한 재사용
4) psych 포맷을 메인 포맷으로 먼저 안정화
5) 결과물은 추상적인 설명이 아니라 실제 구현 가능한 산출물 중심으로 제시

먼저 아래 4가지를 만들어줘:
- psych_card JSON schema
- DeerFlow output schema (trend_report.json, topic_pack.json)
- n8n workflow 수정안
- ffmpeg/card-template 기반 렌더 구조 설계안

그 다음, 실제 파일 구조 변경안과 구현 순서를 단계별로 제안해줘.
```

---

## 17. Codex 또는 개발형 AI에게 주는 작업 명령

```text
이 가이드 파일을 읽고 다음 작업을 수행해.

1) 기존 프로젝트 구조를 유지하면서 psych_card 메인 포맷에 맞는 새 JSON 스키마 파일 초안을 만든다.
2) DeerFlow가 출력할 trend_report.json, competitor_report.json, topic_pack.json 샘플 파일을 만든다.
3) n8n 워크플로우 변경안을 문서화한다.
4) ffmpeg 렌더 구조를 "card-based scene manifest" 방식으로 바꾸는 설계 문서를 만든다.
5) 기존 배경 그라디언트 기반 렌더러에서 loop background + card overlay 구조로 전환하기 위한 변경 포인트를 정리한다.

주의:
- 설명만 하지 말고 실제 파일 초안, 예시 JSON, 예시 디렉터리 구조를 출력해.
- 기존 working assets를 지우지 말고 확장 방식으로 설계해.
- 메인 생산 러너는 n8n이며 DeerFlow는 앞단 리서치 레이어라는 원칙을 지켜.
```

---

## 18. 최종 한 줄 원칙

이 프로젝트는 이제

`DeerFlow가 무엇을 만들지 더 잘 찾고, n8n이 그것을 매일 안전하게 만든다.`

라는 구조로 움직여야 한다.
