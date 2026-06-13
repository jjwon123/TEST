# ARCHIVE_SPEC.md

## Mission

QA를 통과한 최종 자산을 구조화된 인덱스에 등록하고, 다음 이벤트에서 재사용 가능한 자산 풀을 누적 관리한다.
단순 파일 복사가 아니라 **검색 가능한 재사용 인덱스 시스템**이다.

---

## Inputs

| 파일 | 경로 (run 내부) | 필수 |
|------|----------------|------|
| `final-package-manifest.json` | `06_qa_packaging/final-package-manifest.json` | 필수 |
| `qa-report.json` | `06_qa_packaging/qa-report.json` | 필수 |
| `selected-assets.json` | `04_admin_selection/selected-assets.json` | 선택 (visual_keywords 보강용) |
| `brand-guide.json` | `brand-guide.json` (run 루트) | 선택 (visual_keywords 보강용) |

---

## QA 필터링 규칙

**`qa-report.json.summary.status == "pass"`인 경우에만 전체 프레임을 archive 대상으로 간주한다.**

- `issues` 배열에서 특정 `frameId`에 `severity: blocker | error`가 있으면 해당 프레임은 개별 제외한다.
- QA 통과 안 된 자산(fail 상태)은 `asset-archive.json`에 포함하지 않는다.
- QA 제외된 자산 수는 `summary.qa_filtered_out`에 기록한다.

---

## Archive 규칙

1. QA pass 자산 → `assets/approved/{event_id}/` 에 파일 복사
2. `reuse_score >= 0.7` 자산 → `assets/reusable/{channel_id}/{template_family}/` 에 추가 복사
3. 파일이 이미 존재하면 덮어쓰지 않고 `_v2`, `_v3` suffix 사용
4. 메타데이터 없이 파일만 복사하는 것은 금지 — `asset-archive.json` 없이 폴더에만 넣지 않는다

---

## Indexing 규칙

### 글로벌 인덱스: `assets/indexes/global-index.json`

- 이벤트가 쌓일수록 자산이 누적되는 전체 검색 풀
- **upsert 방식**: `asset_id`를 기본 키로 사용. 동일 `asset_id` 재등록 시 append가 아닌 update
- 구조: `{ "updated_at": "...", "assets": [ { asset record }, ... ] }`

### 이벤트 인덱스: `assets/indexes/by-event/{event_id}.json`

- 이벤트별 단독 인덱스 — 이벤트 단위 재실행 시 덮어쓰기
- 글로벌 인덱스와 별개로 관리

### `asset_id` 형식

```
{event_id}__{frame_id}
예: spring-gold-2026__instagram_card_news_01_slide_01
```

---

## reuse_score 계산 기준

`core/policies/archive-reuse-policy.json`의 `reuse_score` 섹션을 읽어 계산한다.
하드코딩 금지.

`template_family`는 가능한 경우 `core/templates/`에 존재하는 `template_id`를 기록한다. 추론 우선순위는
`final-package-manifest.json` 직접 필드 → `05_figma_assembly/channel-outputs.json` → `04_admin_selection/selected-assets.json` → `02_content_planning/content-plan.json` → 파일명/output id 패턴이다. 추론 근거는 `template_inference_source`와 `reuse_score_breakdown.template_inference_source`에 남긴다.

| 요소 | 기여 | 조건 |
|------|------|------|
| `qa_pass` | +0.3 | qa_status == pass |
| `channel_suitability` | +0.1 | instagram, naver_blog 등 reuse-friendly 채널 |
| `template_stability` | +0.1 | card_news, single_feed 등 안정 템플릿 |
| `event_specificity_penalty` | -0.1/키워드 | 이벤트, 기간, 한정, 마감 등 (최대 -0.3) |

판정 기준:
- `score >= 0.7` → `reusable`
- `score >= 0.4` → `limited_reuse`
- `score < 0.4` → `not_reusable`

계산 근거는 `reuse_score_breakdown`에 항상 기록한다 (나중에 모델 기반 점수로 교체 가능하도록).

---

## Output 구조

### `asset-archive.json` — 시스템이 읽는 인덱스

```json
{
  "stage": "07_asset_archive",
  "schema_version": "0.1.0",
  "event_id": "spring-gold-2026",
  "source_run_id": "2026-04-18_...",
  "archived_at": "2026-04-18T...",
  "summary": {
    "total_assets": 9,
    "approved": 9,
    "reusable": 5,
    "qa_filtered_out": 0
  },
  "assets": [
    {
      "asset_id": "spring-gold-2026__instagram_card_news_01_slide_01",
      "event_id": "spring-gold-2026",
      "event_type": "investment_consulting",
      "channel_id": "instagram",
      "template_family": "instagram_cardnews_5slide_v1",
      "template_id": "instagram_cardnews_5slide_v1",
      "template_inference_source": "final-package-manifest.template_id",
      "intended_use": "hook",
      "visual_keywords": ["금융", "신뢰", "골드"],
      "tags": ["channel:instagram", "format:1080x1080", "reuse:reusable"],
      "qa_status": "pass",
      "reuse_score": 0.5,
      "reuse_score_breakdown": {
        "qa_pass": 0.3,
        "channel_suitability": 0.1,
        "template_stability": 0.1,
        "event_specificity_penalty": 0.0
      },
      "reuse_recommended_for": ["instagram", "threads"],
      "reuse_status": "reusable",
      "source_candidate_id": "",
      "source_run_id": "2026-04-18_...",
      "archive_path_approved": "assets/approved/spring-gold-2026/instagram_card_news_01_slide_01.png",
      "archive_path_reusable": "assets/reusable/instagram/card_news/instagram_card_news_01_slide_01.png",
      "dimensions": { "width": 1080, "height": 1080 },
      "archived_at": "2026-04-18T..."
    }
  ]
}
```

### `reuse-notes.md` — 사람이 읽는 요약

다음 이벤트에서 재사용 가능한 자산 목록, 채널별 분류, 사용 시 주의사항을 사람이 읽기 쉽게 정리한다.
`asset-archive.json`의 데이터를 반복하지 않고, **운영자 판단에 필요한 요약**만 작성한다.

---

## Do Not

- QA 미통과 자산을 reusable 인덱스에 포함하지 않는다
- 파일만 복사하고 메타데이터(asset-archive.json)를 생략하지 않는다
- `reuse_score` 기준을 handler 내부에 하드코딩하지 않는다 — policy 파일을 읽는다
- `global-index.json`에 동일 `asset_id`를 중복 append하지 않는다 — upsert만 허용
- `asset-archive.json`과 `reuse-notes.md`의 역할을 섞지 않는다
  - `asset-archive.json`: 시스템 인덱스, 검색·자동화 입력
  - `reuse-notes.md`: 운영자 요약, 다음 이벤트 준비용 메모
