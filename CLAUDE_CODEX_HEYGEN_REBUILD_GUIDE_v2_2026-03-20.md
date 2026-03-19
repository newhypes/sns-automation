# Claude → Codex 리빌드 지침서 v2
## SNS 자동화 프로젝트 재설계 가이드
### 기준 아키텍처: HeyGen + Chat UI + Remotion + n8n + DeerFlow

작성일: 2026-03-20
문서 목적: Claude가 새 채팅에서 지금까지의 의사결정과 작업 맥락을 한 번에 이해하고, Codex에게 기존 코드베이스를 **폐기하지 않고 리빌드**하도록 정확하게 지시하기 위한 상세 실행 문서.

---

## 0. 한 줄 요약

기존의 `정적 배경 + TTS + 자막` 중심 숏폼 공장은 메인 전략에서 내린다.

새 기본 포맷은 아래다.

**메인 포맷**
- WhatsApp/카톡 스타일 **채팅 UI**가 화면의 중심
- **우하단 고정 호스트 캐릭터**를 HeyGen으로 생성
- 호스트가 남녀 메시지를 읽고 마지막에 **심리 해석**을 제공
- 채팅 UI는 **Remotion 템플릿**으로 JSON 기반 자동 렌더
- 전체 파이프라인은 **n8n**이 오케스트레이션
- **DeerFlow는 리서치/전략 엔진**, 생산 러너가 아님

즉,

**기존:** 정적 텍스트 숏폼 공장  
**새 방향:** 채팅 상황 재연 + 브랜드 호스트 캐릭터 + 심리 해석 엔진

---

## 1. 이 문서가 해결하려는 문제

지금까지 Claude가 방향을 제시하고 Codex가 구현을 진행해 왔지만, 기존 지시의 가장 큰 문제는 아래와 같았다.

1. **콘셉트 설명은 있었지만 렌더 스펙이 부족했다.**  
   그래서 Codex가 정적인 자막 슬라이드쇼로 도망갔다.

2. **기술 스택의 역할 분리가 불분명했다.**  
   ffmpeg, n8n, OpenClaw, Codex, DeerFlow, HeyGen의 역할이 섞여 있었다.

3. **콘텐츠 전략과 수익화 전략이 생산 자동화에 밀려 있었다.**  
   “많이 만들기”는 있었지만 “무슨 포맷으로 이길지”가 약했다.

4. **캐릭터/브랜드 자산 개념이 없었다.**  
   매 영상마다 새 그림을 뽑는 방향은 자동화와 브랜딩 모두에 불리하다.

이 문서는 위 문제를 해결하기 위해,
- 무엇을 유지할지
- 무엇을 중단할지
- 무엇을 새로 만들지
- Claude가 Codex에게 어떤 순서로 무엇을 시킬지
를 상세히 정리한다.

---

## 2. 지금까지의 최종 합의 사항

### 2.1 유지할 것

기존 프로젝트에서 아래 자산은 유지한다.

- 로컬 맥미니 기반 실행 환경
- Docker / n8n / queue 중심 구조
- OpenClaw + Codex 협업 구조
- 파일 기반 recoverability
- 업로드 스크립트 및 플랫폼 연결 스캐폴드
- 로컬 TTS / 오디오 / ffmpeg / 렌더 유틸 자산
- 기존 폴더 구조와 작업 흐름의 큰 틀

### 2.2 메인 전략에서 내릴 것

아래는 메인 포맷에서 제외한다.

- 정적 그라디언트 배경 영상
- ASS 자막 중심 기본 영상
- 1 topic → female/male/psych 3개 복제 생산 기본값
- 하루 수십 개 대량 업로드를 최우선으로 두는 운영 방식
- 브라우저 로그인 클릭 자동화를 실운영 기본 방식으로 채택하는 것

### 2.3 새 최종 포맷

**1순위 메인 포맷**
- 채팅 UI가 메시지를 하나씩 보여준다.
- 우하단 고정 호스트 캐릭터가 메시지를 읽고 반응한다.
- 마지막 5~8초는 심리 해석이다.
- 저장/댓글/팔로우 또는 향후 리드 수집 CTA를 넣는다.

이 포맷은 다음 니치와 잘 맞는다.
- 연애 심리
- 관계 해석
- 문자 패턴 해석
- 애착/거리두기
- 썸/읽씹/늦답/애매한 관계

### 2.4 채널 운영 방식

초기에는 3채널을 동시에 키우지 않는다.

**기본 원칙**
- 1개의 flagship 브랜드 계정으로 시작
- 그 안에서 시리즈를 테스트
- 승자 포맷이 나오면 그때 세분화 검토

권장 시리즈
1. `Chat Autopsy` — 메인
2. `Psych Decoder` — 보조
3. `Avatar Commentary` — 실험

---

## 3. 기술 역할 분리

### 3.1 Claude의 역할

Claude는 다음을 담당한다.
- 전략 정리
- 요구사항 구체화
- 데이터 스키마 설계
- Codex에게 줄 실행 지시문 작성
- 결과 리뷰 기준 제시
- 포맷/브랜딩/수익화 관점 피드백

Claude는 직접 구현자가 아니라 **설계 총괄 + 품질 감독자**다.

### 3.2 Codex의 역할

Codex는 다음을 담당한다.
- 기존 리포지토리 분석
- 리빌드에 필요한 신규 파일/모듈 구현
- Remotion 템플릿 개발
- HeyGen 연동 모듈 구현
- n8n workflow 초안 생성 및 수정
- 기존 legacy 로직 격리
- 테스트 스크립트 작성

Codex는 **실제 구현 엔진**이다.

### 3.3 n8n의 역할

n8n은 메인 런너다.

담당 기능
- 스케줄링
- 워크플로우 제어
- 파일 이동
- API 호출 순서 관리
- 실패 재시도
- 로그 기록
- 업로드 트리거

n8n은 **control tower**다.

### 3.4 DeerFlow의 역할

DeerFlow는 생산 엔진이 아니라 **리서치 엔진**이다.

담당 기능
- 트렌드 조사
- 경쟁 계정 분석
- 댓글 pain point 추출
- 제목/훅 패턴 수집
- 주간 전략 리포트 작성

DeerFlow는 다음을 만들면 된다.
- `trend_packet.json`
- `comment_pain_points.json`
- `hook_families.json`
- `weekly_strategy_report.md`

### 3.5 HeyGen의 역할

HeyGen은 전체 영상을 통으로 만드는 도구가 아니다.

현재 프로젝트에서 HeyGen의 역할은 아래로 제한한다.
- 고정 호스트 캐릭터 생성
- 호스트의 짧은 립싱크 오버레이 클립 생성
- 필요시 avatar commentary 단독 영상 생성

HeyGen이 하지 않을 것
- 채팅 UI 렌더
- 전체 타임라인 편집의 중심
- 프로젝트 스케줄링
- 리서치

### 3.6 Remotion의 역할

Remotion은 **본편 화면 렌더러**다.

담당 기능
- 채팅 UI 레이아웃
- 버블 애니메이션
- typing indicator
- message timeline 동기화
- psych card/diagnosis 장면
- final composition

### 3.7 ffmpeg의 역할

ffmpeg는 보조 후처리 도구다.

담당 기능
- 오디오 정규화
- 최종 인코딩
- 썸네일 생성
- 보조 합성 및 포맷 변환

중요: ffmpeg를 메인 장면 엔진으로 쓰지 않는다.

---

## 4. HeyGen 운용 원칙

### 4.1 수동으로 한 번 해야 하는 초기 세팅

이 단계는 사람이 직접 한다.

1. HeyGen 계정 생성
2. 무료 플랜으로 2~3개 샘플 테스트
3. 호스트 방향 선택
   - Photo Avatar
   - Custom Digital Twin
4. 호스트의 룩, 표정, 구도 승인
5. 최종 avatar_id 또는 사용할 호스트 자산 확정

중요:
- 이 단계는 자동화 대상이 아니다.
- 사람 눈으로 품질을 보고 결정해야 한다.

### 4.2 이후 자동화 원칙

초기 세팅이 끝나면, 매번 사이트에 들어가서 손으로 만들지 않는다.

원칙
- 공식 API / MCP / Skills / OpenClaw 경로 우선
- 브라우저 로그인 자동화는 fallback만 허용
- UI 클릭 자동화는 프로덕션 기본값으로 금지

### 4.3 구독 vs API 운영 원칙

초기 검증 단계
- 무료 플랜 또는 Creator 플랜으로 포맷 검증
- 사람이 품질을 보고 수정

중기 운영 단계
- 포맷이 맞으면 API/공식 자동화 경로 검토
- 비용, 안정성, 실패 복구 기준으로 비교

원칙
- “완전 자동화”를 위해 API를 목표로 한다.
- 하지만 시작은 구독 기반 검증이 더 현실적일 수 있다.

### 4.4 캐릭터 자산 전략

캐릭터는 매 영상마다 새로 생성하지 않는다.

**호스트는 브랜드 자산**이다.

선택지 A: Avatar ID 재사용
- 한 번 만든 호스트를 계속 재사용
- 가장 단순하고 안정적

선택지 B: 캐릭터 팩 재사용
- 동일 얼굴의 이미지 12~20장 세트 확보
- 표정, 의상, 구도만 다르게 구성
- 이미지 기반 립싱크 입력으로 활용

현재 기준 추천
- 가능하면 **Avatar ID 재사용형**을 우선
- 캐릭터 팩은 보조 전략

---

## 5. 새 영상 포맷의 상세 스펙

### 5.1 화면 구조

권장 레이아웃
- 중앙/상단 70~80%: 채팅 UI
- 우하단 15~20%: 호스트 캐릭터
- 하단: 필요시 강조 캡션 또는 CTA

핵심 원칙
- 화면의 주인공은 채팅 상황이다.
- 호스트는 브랜드 앵커이자 해설자다.

### 5.2 장면 구조

#### Scene A — Hook (0~2초)
- 강한 문제 제기
- 예: “읽씹 후 8시간 뒤 답장, 이건 무슨 뜻일까?”
- 채팅 일부 미리 노출 가능
- 호스트는 짧게 리액션만

#### Scene B — Chat Replay (2~16초)
- 채팅 버블이 하나씩 등장
- 등장 직전 typing indicator 허용
- female/male 메시지별 오디오 재생
- 호스트가 메시지를 읽거나 가볍게 반응

#### Scene C — Psych Diagnosis (16~26초)
- 채팅 화면을 dim/blur
- 호스트가 정면 발화
- 핵심 진단 문장 크게 표시
- 보조 포인트 2~3개 카드 표시

#### Scene D — CTA (26~30초)
- 저장, 팔로우, 댓글 유도
- 추후 제품/리드 수집으로 연결 가능

### 5.3 채팅 UI 애니메이션 규칙

각 메시지 버블 규칙
- 등장 전: `opacity 0`, `translateY 20px`, `scale 0.96`
- 등장 시: 8~12프레임 pop-in
- 짧은 bubble 등장 사운드 허용
- 다음 메시지 등장 시 이전 대화는 위로 밀림
- 일부 메시지 전 typing indicator 0.3~0.6초

### 5.4 자막 원칙

- 채팅 파트에서는 버블 텍스트 자체가 자막 역할
- 해설 파트에서만 강한 강조 자막 사용
- 한 장면에 텍스트를 과도하게 겹치지 않는다

### 5.5 오디오 원칙

오디오를 하나의 긴 파일로 만들지 않는다.

필수 구성
- female message 1
- male message 1
- female message 2
- male message 2
- psych commentary

즉, **메시지 단위 오디오 분리 생성**이 기본이다.

---

## 6. 스크립트는 문장이 아니라 데이터다

기존 실패 원인 중 하나는 “긴 대본 한 덩어리”를 먼저 만들고 나중에 영상에 억지로 맞춘 점이다.

새 원칙은 아래다.

- Claude는 스토리를 `scene_manifest`로 구조화한다.
- Codex는 그 manifest를 읽는 렌더러를 만든다.
- n8n은 manifest를 다음 단계로 전달한다.

### 6.1 필수 manifest 종류

1. `trend_packet.json`
2. `idea_card.json`
3. `scene_manifest.json`
4. `render_manifest.json`
5. `publish_manifest.json`
6. `performance_row.json`

### 6.2 대표 `scene_manifest.json` 예시

```json
{
  "video_id": "2026-03-20_case_001",
  "series": "chat_autopsy",
  "hook": "읽씹 후 8시간 뒤 답장, 이건 무슨 뜻일까?",
  "host": {
    "provider": "heygen",
    "avatar_id": "host_female_main",
    "placement": "bottom_right",
    "style": "stylized_human",
    "pose": "serious_soft"
  },
  "messages": [
    {
      "speaker": "female",
      "side": "left",
      "text": "오늘 진짜 재밌었어 :)",
      "appear_at_sec": 1.0,
      "voice": "female_main",
      "bubble_style": "sender",
      "show_typing_before": false
    },
    {
      "speaker": "male",
      "side": "right",
      "text": "나도 ㅋㅋ 잘 들어갔어?",
      "appear_at_sec": 3.0,
      "voice": "male_main",
      "bubble_style": "receiver",
      "show_typing_before": true
    },
    {
      "speaker": "female",
      "side": "left",
      "text": "응. 다음에 또 보자",
      "appear_at_sec": 5.8,
      "voice": "female_main",
      "bubble_style": "sender",
      "show_typing_before": false
    },
    {
      "speaker": "male",
      "side": "right",
      "text": "그래 :)",
      "appear_at_sec": 12.6,
      "voice": "male_main",
      "bubble_style": "receiver",
      "show_typing_before": true
    }
  ],
  "psych_commentary": {
    "start_at_sec": 16.0,
    "voice": "psych_main",
    "text": "문제는 답장 속도 자체보다 초반의 온도와 후반의 온도 차이가 너무 크다는 점이야.",
    "bullet_points": [
      "간헐적 반응은 집착을 강화할 수 있음",
      "우선순위 저하 신호일 수 있음",
      "행동보다 온도 변화를 봐야 함"
    ]
  },
  "cta": {
    "text": "이런 관계 패턴 더 보려면 저장해둬",
    "style": "soft_follow"
  },
  "meta": {
    "target_duration_sec": 30,
    "aspect_ratio": "9:16",
    "language": "ko"
  }
}
```

---

## 7. 기존 코드베이스를 어떻게 수정할 것인가

### 7.1 절대 하면 안 되는 것

Codex에게 아래 작업을 시키지 말 것.

- 기존 리포 전체 삭제
- 기존 업로드/queue 구조 전면 폐기
- ffmpeg 전부 제거
- 기존 scripts/audio/subs 폴더 전면 무효화
- 기존 n8n workflow를 즉시 삭제

원칙은 **버리기보다 격리**다.

### 7.2 유지 대상

아래는 유지한다.

- n8n 컨테이너/볼륨 구조
- queue/pending/ready/failed/posted 구조
- 로컬 실행 환경
- 업로드 스크립트 scaffold
- 오디오 생성 유틸
- ffmpeg 후처리 유틸
- OpenClaw workspace 구조
- 로깅, 재시도, recoverability 개념

### 7.3 legacy 처리 대상

삭제하지 말고 `legacy` 또는 `deprecated`로 분리한다.

- gradient-only renderer
- ASS subtitle only pipeline
- female/male/psych 3-clone auto generation 기본 로직
- variant background generator 기본 경로

### 7.4 신규 추가 모듈

#### A. `/remotion/` 프로젝트
예시 구조
- `src/compositions/ChatAutopsy.tsx`
- `src/components/ChatBubble.tsx`
- `src/components/TypingIndicator.tsx`
- `src/components/HostOverlay.tsx`
- `src/components/PsychDiagnosisCard.tsx`
- `src/components/CtaCard.tsx`
- `src/lib/loadManifest.ts`
- `src/lib/timeline.ts`
- `src/index.ts`

#### B. `/manifests/`
- `trend/`
- `idea/`
- `scene/`
- `render/`
- `publish/`
- `performance/`

#### C. `heygen/` 모듈
- `heygen_client.py`
- `create_host_clip.py`
- `poll_job_status.py`
- `cache_avatar_assets.py`
- `merge_host_overlay.py`

#### D. 새로운 n8n workflow
예시 파일명
- `WF03_chat_autopsy_pipeline.json`

#### E. 성과 로깅
- `performance_log.jsonl`
- 플랫폼별 지표 저장 로직

---

## 8. n8n 새 파이프라인

### WF00 Research Intake
입력
- DeerFlow 결과
- 수동 아이디어
- 댓글 데이터

출력
- `trend_packet.json`

### WF01 Idea Scoring
평가 항목
- stop-scroll strength
- clarity
- emotional tension
- visualizability
- originality
- monetization fit

출력
- `idea_card.json`

### WF02 Scene Manifest Build
입력
- 상위 idea

출력
- `scene_manifest.json`
- `publish_manifest.json`

### WF03 Voice Generation
- female/male/psych 음성 분리 생성
- 메시지 단위 오디오 생성

### WF04 Host Clip Generation
- `scene_manifest` 기반으로 HeyGen 호출
- 호스트 클립 생성
- avatar_id 재사용

### WF05 Chat UI Render
- Remotion이 `scene_manifest`를 읽어 채팅 UI 렌더

### WF06 Composite
- chat UI + host clip + commentary + captions + CTA 합성
- ffmpeg 후처리

### WF07 Publish
- YouTube Shorts 업로드
- TikTok 업로드
- Instagram Reels 업로드

### WF08 Metrics Pull
- 기본 성과 지표 저장
- 성과 로그 누적

---

## 9. Claude가 Codex에게 내려야 하는 작업 우선순위

### Phase 1 — 코드베이스 감사
Codex에게 먼저 시킬 일
1. 현재 리포 구조 스캔
2. 기존 파이프라인 요약
3. 유지/legacy/신규 구현 항목 분리
4. 위험 요소 목록 작성

산출물
- `REPO_AUDIT.md`
- `MIGRATION_PLAN.md`

### Phase 2 — 새 렌더 엔진 골격 구축
1. Remotion 프로젝트 추가
2. `scene_manifest` 로더 추가
3. ChatAutopsy composition 골격 작성
4. ChatBubble / TypingIndicator / HostOverlay 컴포넌트 추가

산출물
- 기본 렌더가 가능한 최소 동작 버전

### Phase 3 — HeyGen 연동
1. avatar_id 기반 호스트 클립 요청 모듈 작성
2. job polling 작성
3. 실패 재시도 로직 추가
4. 캐시/임시파일 관리 추가

### Phase 4 — n8n 통합
1. scene manifest 생성 → voice → host clip → render → composite 순으로 workflow 구성
2. 파일 기반 전달 구조 정리
3. 실패 시 rollback/retry 전략 추가

### Phase 5 — 성과학습 루프
1. 업로드 결과 저장
2. 성과 로그 누적
3. idea score와 결과 비교 루프 추가

---

## 10. Claude가 Codex에게 줄 핵심 지시 문장

아래 문장은 그대로 전달해도 된다.

### 10.1 전체 방향 지시

> 기존 프로젝트를 폐기하지 말고 리빌드하라.  
> 현재 인프라(n8n, queue, uploader, 로컬 실행 환경, ffmpeg 후처리)는 유지한다.  
> 정적 그라디언트 + ASS + 긴 TTS 대본 중심 기본 포맷은 legacy로 격리한다.  
> 새 메인 포맷은 Chat UI + HeyGen host overlay + psychology commentary다.  
> Chat UI는 Remotion이 `scene_manifest.json`을 읽어 자동 렌더해야 한다.  
> HeyGen은 우하단 호스트 캐릭터 클립 생성에만 사용한다.  
> n8n은 전체 오케스트레이션과 실패 복구를 담당한다.  
> 브라우저 로그인 클릭 자동화는 기본 전략으로 채택하지 마라.

### 10.2 구현 지시

> 먼저 현재 리포를 분석해 무엇을 유지하고 무엇을 legacy로 둘지 문서화하라.  
> 그 다음 `/remotion/`, `/manifests/`, `heygen/` 모듈을 추가하라.  
> `scene_manifest` 기반으로 채팅 버블이 순차 등장하는 9:16 숏폼 렌더 템플릿을 구현하라.  
> host overlay는 우하단 15~20% 영역에 합성하라.  
> 메시지 오디오는 반드시 line-by-line 구조로 분리하라.  
> psych commentary는 후반부 장면 전환으로 구현하라.  
> 기존 3-variant 자동 복제 로직은 기본값에서 제거하라.

---

## 11. Claude가 새 채팅에서 바로 붙여넣을 시작 프롬프트

아래를 새 채팅에서 Claude에게 그대로 넣어도 된다.

```text
너는 지금 SNS 자동화 프로젝트의 설계 총괄이다.
기존 프로젝트는 n8n, 로컬 맥미니, queue 기반 업로드 구조, ffmpeg/TTS 기반 숏폼 생산라인을 일부 갖고 있다.
하지만 기존 기본 포맷(정적 배경 + 자막 + 긴 TTS)은 메인 전략에서 내린다.

새 최종 방향은 다음과 같다.
1. 메인 포맷은 Chat UI + HeyGen host overlay + psych commentary다.
2. 중앙/상단은 WhatsApp/카톡 스타일 채팅 UI다.
3. 우하단에는 고정 호스트 캐릭터가 들어간다.
4. 호스트는 HeyGen으로 생성하며, 같은 avatar_id를 반복 재사용한다.
5. 채팅 UI는 Remotion이 scene_manifest.json을 읽고 자동 렌더한다.
6. n8n은 전체 파이프라인을 오케스트레이션한다.
7. DeerFlow는 리서치/전략 엔진일 뿐 생산 엔진이 아니다.
8. 브라우저 로그인 클릭 자동화는 메인 전략으로 쓰지 않는다.
9. 기존 코드베이스는 삭제하지 말고 유지/legacy/신규 모듈로 분리한다.

이 방향으로 Codex에게 줄 실행 계획을 작성하고, 먼저 리포 감사(Audit)와 마이그레이션 계획을 만들게 하라.
그 후 Remotion, HeyGen 연동, n8n workflow 수정 순으로 구현시키라.
각 단계의 완료 조건도 함께 정의하라.
```

---

## 12. Claude가 Codex에게 바로 붙여넣을 실행 프롬프트

```text
Read the existing repository and do not delete the current pipeline.
Your job is to migrate it toward a new main format instead of rebuilding from scratch.

Target format:
- 9:16 short video
- Main scene is a WhatsApp/Kakao-style chat UI
- Bottom-right host overlay generated via HeyGen
- Host reads male/female messages and then gives psychology commentary
- Chat UI must be rendered from scene_manifest.json using Remotion
- n8n remains the orchestration layer
- ffmpeg remains only for post-processing, encoding, and utilities
- DeerFlow is research only, not production runner

Tasks:
1. Audit the current repo and classify items into keep / legacy / new.
2. Create REPO_AUDIT.md and MIGRATION_PLAN.md.
3. Add a new /remotion project with:
   - ChatAutopsy composition
   - ChatBubble component
   - TypingIndicator component
   - HostOverlay component
   - PsychDiagnosisCard component
4. Add /manifests folders and a loader for scene_manifest.json.
5. Add heygen integration module for avatar clip generation and polling.
6. Create a new n8n workflow skeleton for the new pipeline.
7. Do not ship a generic subtitle slideshow.
8. Do not keep the old 3-variant clone logic as the default production path.
9. Keep existing uploader/queue/recoverability structures intact.

Deliver incremental commits or diffs and explain what was changed.
```

---

## 13. 완료 기준

아래를 만족해야 “리빌드 1차 성공”으로 본다.

1. Codex가 현재 리포를 keep / legacy / new로 분류했다.
2. Remotion으로 `scene_manifest` 기반 샘플 1개를 렌더할 수 있다.
3. 채팅 버블이 순차 등장하고 typing indicator가 보인다.
4. 우하단 호스트 자리 표시 또는 실제 호스트 클립이 합성된다.
5. psych commentary 장면 전환이 구현된다.
6. n8n workflow 골격이 새 포맷 기준으로 정리된다.
7. 기존 파이프라인은 삭제되지 않고 격리된다.

---

## 14. 절대 잊지 말아야 할 핵심 원칙

- 기존 인프라는 버리지 않는다.
- 출력 포맷만 크게 바꾼다.
- 캐릭터는 매번 새로 생성하지 않는다.
- 호스트는 브랜드 자산이다.
- 채팅 UI는 손작업이 아니라 JSON 자동 렌더다.
- HeyGen은 호스트 모듈이다.
- Remotion이 본편 장면 엔진이다.
- n8n이 러너다.
- DeerFlow는 조사 두뇌다.
- 브라우저 클릭 자동화는 fallback일 뿐이다.

---

## 15. 가장 짧은 실무 요약

Claude는 Codex에게 이렇게 이해시키면 된다.

**“우리는 기존 숏폼 자동화 인프라를 버리지 않는다. 다만 메인 포맷을 정적 텍스트 숏폼에서 Chat UI + HeyGen host overlay + psych commentary 구조로 전환한다. Remotion이 본편을 렌더하고, HeyGen은 호스트만 담당하며, n8n이 전체를 orchestration한다. 먼저 리포 감사와 마이그레이션 계획부터 작성하라.”**

