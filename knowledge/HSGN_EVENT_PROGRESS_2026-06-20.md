# HSGN 이벤트 제작 진행 기록 (2026-06-20)

## 목표

HSGN 화장품 이벤트를 기존 OpenAI API 없이 local deterministic planning flow로 생성하고, 콘솔/Playwright 연결까지 확인한다.

## 진행

- 새 이벤트 입력 생성: `events/hsgn-summer-tone-care-2026/event-input.json`
- 새 브랜드 가이드 생성: `events/hsgn-summer-tone-care-2026/brand-guide.json`
- 생성 run: `runs/2026-06-20_01-26-50_hsgn-여름-톤-케어-집중-이벤트`
- 01 브리프 실행 및 승인 완료.
- 02 콘텐츠 기획 실행 완료.
- 콘셉트 3안 중 `concept_02`를 연결 확인용으로 임시 선택.
- 선택 콘셉트 기반 카피 패키지 생성 완료.
- Playwright 콘솔 UI 감사 통과: `.tmp/console-ui-audit/latest-console-ui-playwright.json`

## 코드 보정

- `services/ad_strategy/generation.py`
  - OpenAI API 키가 없을 때 `provider_unavailable`로 막지 않고 `local_deterministic` provider 실행으로 기록하도록 보정.
  - local copy critic이 단일 선택 콘셉트를 보고 "3안 부족"으로 오판하지 않도록 완화.
- HSGN 이벤트 채널을 실제 channel registry ID로 보정:
  - `instagram_feed`
  - `blog_thumbnail`
  - `blog_inline_image`
  - `community_banner`

## 현재 상태

- 02 단계 상태: `review_pending`
- provider: `local_deterministic`
- provider status: `ok`
- scorecard: `warning`
- criticalErrorCount: `0`

## 남은 문제

- 카피에 반복 문장과 어색한 한글 경고가 남아 있다.
- 현재 마케팅 신호 데이터 일부가 깨진 한글/랜덤 seed 기반이라 HSGN 실사용 카피 품질에는 아직 부족하다.
- `tests.test_ad_planning_engine.test_scorecard_warns_when_marketing_signals_are_not_selected`는 전역 `InsightBrief ready` 상태에 영향을 받아 테스트 격리가 추가로 필요하다.

## 다음 작업

1. HSGN copy package를 사람이 읽는 한국어로 재작성한다.
2. 깨진 마케팅 신호를 실사용 데이터로 교체하거나 HSGN 전용 수동 신호를 추가한다.
3. `02_content_planning` 최종 승인 후 `03_reference_research`로 이동한다.
