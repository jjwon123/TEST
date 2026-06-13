# Codex 전달용 파이프라인 구조안

## 프로젝트 정의
이 프로젝트는 이벤트 하나를 입력하면 멀티채널 콘텐츠 세트를 생성하는 **멀티 에이전트형 운영 시스템**이다.

각 stage는 단순 데이터 보관 폴더가 아니라:
- 이전 단계 산출물을 읽고
- 추론하고 판단하고
- 필요하면 멈추고 사람 승인받고
- 다음 단계로 핸드오프하는
**에이전트 실행 단위**다.

또한 다음 전제를 따른다.
- **ComfyUI**: 비주얼 후보 생성 엔진
- **Figma 유료 플랜**: 템플릿 기반 조립 / export / 관리 레이어
- `workflow.py`: 단순 실행 스크립트가 아니라 오케스트레이터
- JSON 산출물: 결과물이자 다음 stage 입력 컨텍스트

---

# 1. 상위 구조

```text
automation-platform/
├── core/
│   ├── schemas/
│   ├── models/
│   ├── states/
│   ├── channels/
│   ├── templates/
│   ├── policies/
│   └── utils/
│
├── events/
│   └── {event-id}/
│       ├── event-input.json
│       ├── brand-guide.json
│       ├── references/
│       └── notes.md
│
├── pipeline/
│   ├── 01_event_brief/
│   ├── 02_content_planning/
│   ├── 03_visual_candidates/
│   ├── 04_admin_selection/
│   ├── 05_figma_assembly/
│   ├── 06_qa_packaging/
│   └── 07_asset_archive/
│
├── runs/
│   └── {run-id}/
│       ├── run-status.json
│       ├── approvals.json
│       ├── logs/
│       ├── 01_event_brief/
│       ├── 02_content_planning/
│       ├── 03_visual_candidates/
│       ├── 04_admin_selection/
│       ├── 05_figma_assembly/
│       ├── 06_qa_packaging/
│       └── 07_asset_archive/
│
├── assets/
│   ├── approved/
│   ├── rejected/
│   ├── reusable/
│   ├── exports/
│   └── indexes/
│
├── services/
│   ├── llm/
│   ├── comfyui/
│   ├── figma/
│   ├── storage/
│   └── notifications/
│
├── ui/
│   ├── dashboard/
│   ├── event-brief/
│   ├── content-planning/
│   ├── candidate-selection/
│   ├── figma-assembly/
│   ├── qa-review/
│   └── asset-library/
│
├── scripts/
│   ├── workflow.py
│   ├── setup_run.py
│   ├── validate_run.py
│   ├── regenerate_outputs.py
│   ├── export_package.py
│   └── promote_assets.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PIPELINE.md
│   ├── AGENT_SPEC.md
│   ├── STATES.md
│   ├── SCHEMAS.md
│   ├── TEMPLATES.md
│   ├── QA.md
│   └── ROADMAP.md
│
└── CLAUDE.md
```

---

# 2. Core Layer

## core/schemas/
공통 JSON schema를 둔다.

추천 파일:
- event-input.schema.json
- brand-guide.schema.json
- brief.schema.json
- content-plan.schema.json
- visual-plan.schema.json
- image-prompts.schema.json
- candidate-manifest.schema.json
- selected-assets.schema.json
- figma-assembly-plan.schema.json
- channel-outputs.schema.json
- qa-report.schema.json
- final-package-manifest.schema.json
- asset-archive.schema.json
- run-status.schema.json
- approval.schema.json

## core/models/
도메인 정의서:
- EVENT.md
- BRAND.md
- RUN.md
- APPROVAL.md
- TEMPLATE.md
- ASSET.md
- CHANNEL_OUTPUT.md

## core/states/
상태 머신 정의:
- event-states.json
- run-states.json
- approval-states.json
- transitions.md

추천 run 상태:
- created
- briefing
- brief_review
- planning
- plan_review
- candidate_generating
- selection_pending
- assembling
- qa_pending
- archived
- failed

추천 stage 상태:
- not_started
- in_progress
- review_pending
- approved
- rejected
- needs_regeneration
- done
- blocked

## core/channels/
채널별 운영 규칙:
- instagram-cardnews.json
- instagram-feed.json
- threads-image.json
- twitter-image.json
- blog-thumbnail.json
- blog-inline-image.json
- community-banner.json
- brunch-cover.json

## core/templates/
Figma 템플릿 메타 정보:
- instagram/cardnews-5slide-v1.json
- instagram/cardnews-7slide-v1.json
- instagram/feed-single-v1.json
- blog/thumbnail-v1.json
- blog/inline-image-v1.json
- community/notice-banner-v1.json
- brunch/cover-v1.json

각 템플릿 메타 필수 필드 예:
- template_id
- channel_id
- figma_file_key
- figma_node_id
- ratio
- text_slots
- visual_slots
- max_text_length
- safe_area
- cta_slot
- export_rule

## core/policies/
공통 정책:
- qa-rules.json
- forbidden-phrases.json
- naming-rules.json
- export-rules.json
- brand-safety-rules.json

---

# 3. Pipeline Layer

모든 stage가 완전히 같은 파일 구조를 가질 필요는 없다.  
대신 **공통 최소 규약**과 **stage 타입별 확장 구조**를 나눠서 설계한다.

## 3-1. 공통 최소 규약
모든 stage 폴더는 최소한 아래 3개 파일을 가진다.

```text
{stage}/
├── README.md
├── input.schema.json
└── output.schema.json
```

- `README.md`: 사람용 개요 문서. 이 stage의 목적, 위치, 입출력, 다음 단계 관계를 설명한다.
- `input.schema.json`: 이 stage가 읽는 데이터 구조를 정의한다.
- `output.schema.json`: 이 stage가 반드시 내보내야 하는 데이터 구조를 정의한다.

---

## 3-2. Stage 타입 분류
이 프로젝트의 stage는 성격상 아래 3종류로 나눈다.

### A. Agent Reasoning Stage
에이전트가 직접 읽고, 추론하고, 판단해서 결과를 생성하는 단계.

대상:
- 01_event_brief
- 02_content_planning
- 03_visual_candidates
- 05_figma_assembly
- 06_qa_packaging

핵심 문서:
- `AGENT_SPEC.md`

권장 구조:
```text
{stage}/
├── README.md
├── AGENT_SPEC.md
├── input.schema.json
├── output.schema.json
├── decision-rules.md
├── handoff.md
├── fail-cases.md
├── examples/
├── prompts/
└── handlers/
```

각 파일 역할:
- `AGENT_SPEC.md`: 에이전트 역할 정의, 추론 단계, 판단 기준, human gate, handoff 규칙
- `decision-rules.md`: 좋은 판단 / 나쁜 판단 기준, 우선순위 규칙
- `handoff.md`: 다음 stage에 무엇을 어떤 의미로 넘기는지 설명
- `fail-cases.md`: 실패 조건, 재시도 조건, 재생성 시 유지할 값
- `examples/`: 예시 입출력 파일
- `prompts/`: 내부 프롬프트 조각 또는 prompt template
- `handlers/`: stage별 처리 코드 또는 adapter

---

### B. Human Decision Stage
에이전트가 실행 완료 후 사람에게 판단을 넘기고, 선택 결과를 기록하는 단계.

대상:
- 04_admin_selection

핵심 문서:
- `SELECTION_GUIDE.md`

권장 구조:
```text
04_admin_selection/
├── README.md
├── SELECTION_GUIDE.md
├── input.schema.json
├── output.schema.json
├── selection-criteria.md
├── handoff.md
├── examples/
└── ui-notes.md
```

각 파일 역할:
- `SELECTION_GUIDE.md`: 후보를 어떻게 제시하고, 사람이 어떤 형식으로 선택하며, 선택 결과를 어떻게 기록하는지 정의
- `selection-criteria.md`: 채택 / 제외 / 재생성 판단 기준
- `handoff.md`: 선택 결과를 다음 stage로 넘기는 규칙
- `ui-notes.md`: 나중에 운영 UI를 붙일 때 필요한 선택 화면 메모

---

### C. Archive / Index Stage
추론보다 분류, 인덱싱, 재사용 태깅이 핵심인 단계.

대상:
- 07_asset_archive

핵심 문서:
- `ARCHIVE_SPEC.md`

권장 구조:
```text
07_asset_archive/
├── README.md
├── ARCHIVE_SPEC.md
├── input.schema.json
├── output.schema.json
├── indexing-rules.md
├── reuse-rules.md
├── tagging-policy.md
└── examples/
```

각 파일 역할:
- `ARCHIVE_SPEC.md`: 어떤 자산을 어떻게 분류하고 어떤 메타데이터를 남길지 정의
- `indexing-rules.md`: 인덱스 생성 기준
- `reuse-rules.md`: 재사용 가능 여부 판단 기준
- `tagging-policy.md`: 태그 정책, naming, 검색 기준

---

## 3-3. Stage 타입별 매핑표

| Stage | Type | Core Spec File |
|---|---|---|
| 01_event_brief | Agent Reasoning Stage | AGENT_SPEC.md |
| 02_content_planning | Agent Reasoning Stage | AGENT_SPEC.md |
| 03_visual_candidates | Agent Reasoning Stage | AGENT_SPEC.md |
| 04_admin_selection | Human Decision Stage | SELECTION_GUIDE.md |
| 05_figma_assembly | Agent Reasoning Stage | AGENT_SPEC.md |
| 06_qa_packaging | Agent Reasoning Stage | AGENT_SPEC.md |
| 07_asset_archive | Archive / Index Stage | ARCHIVE_SPEC.md |

---

## 3-4. 설계 원칙
- 모든 stage를 동일한 템플릿으로 강제하지 않는다.
- 하지만 공통 최소 규약(`README.md`, `input.schema.json`, `output.schema.json`)은 유지한다.
- 추론 중심 단계는 `AGENT_SPEC.md`를 기준으로 설계한다.
- 사람 선택 중심 단계는 `SELECTION_GUIDE.md`를 기준으로 설계한다.
- 아카이브 단계는 `ARCHIVE_SPEC.md`를 기준으로 설계한다.
- `workflow.py`는 stage 타입을 읽고 적절한 실행/대기/핸드오프 로직을 수행해야 한다.

---

# 4. Stage 정의

## 01_event_brief
목적:
- 이벤트 입력과 브랜드 가이드를 읽고 공통 브리프 생성

입력:
- event-input.json
- brand-guide.json

출력:
- brief.json

human gate:
- brief 승인

---

## 02_content_planning
목적:
- 어떤 채널 콘텐츠가 필요한지 구조화

입력:
- brief.json

출력:
- content-plan.json

human gate:
- content plan 승인

---

## 03_visual_candidates
목적:
- ComfyUI 기반 비주얼 후보 생성 전략 / 프롬프트 / 후보 매니페스트 생성

입력:
- brief.json
- content-plan.json

출력:
- visual-plan.json
- image-prompts.json
- candidate-manifest.json

비고:
- Midjourney 중심이 아니라 **ComfyUI adapter 중심 설계**
- 커버 / 서포트 / 정보형 이미지 용도 태깅 필요
- 텍스트 삽입 안전성 필드 필요

---

## 04_admin_selection
목적:
- 사람이 후보 선택 / 제외 / 재생성 요청

입력:
- candidate-manifest.json
- 후보 썸네일 / 이미지

출력:
- selected-assets.json
- selection-notes.md

human gate:
- 관리자 선택 승인

---

## 05_figma_assembly
목적:
- 선택된 자산과 카피를 Figma 템플릿에 매핑

입력:
- selected-assets.json
- content-plan.json
- brief.json
- template metadata

출력:
- figma-assembly-plan.json
- copy-map.json
- channel-outputs.json

비고:
- Figma 유료 플랜 전제
- 초기에는 메타데이터 기반 조립 계획 중심
- 이후 MCP/API로 자동 배치 확장 가능

---

## 06_qa_packaging
목적:
- 최종 산출물 검수 및 패키징

입력:
- channel-outputs.json
- export 파일

출력:
- qa-report.json
- final-package-manifest.json

human gate:
- QA 승인

---

## 07_asset_archive
목적:
- 최종 자산 저장 + 재사용 가능한 지식으로 전환

입력:
- final-package-manifest.json
- selected-assets.json
- qa-report.json

출력:
- asset-archive.json
- reuse-notes.md

---

# 5. 서비스 레이어

## services/comfyui/
```text
services/comfyui/
├── client.py
├── queue.py
├── workflow_registry.py
├── prompt_builder.py
├── presets/
│   ├── product_clean.json
│   ├── campaign_keyvisual.json
│   ├── lifestyle_scene.json
│   └── editorial_poster.json
├── postprocess/
│   ├── upscale.py
│   ├── crop_preview.py
│   └── metadata_embed.py
└── README.md
```

## services/figma/
```text
services/figma/
├── client.py
├── template_mapper.py
├── text_fitter.py
├── export_manager.py
├── file_registry.json
└── README.md
```

---

# 6. Runs 구조

```text
runs/{run-id}/
├── run-status.json
├── approvals.json
├── logs/
│   ├── workflow.log
│   └── stage-errors.log
├── 01_event_brief/
│   ├── brief.json
│   └── notes.md
├── 02_content_planning/
│   ├── content-plan.json
│   └── notes.md
├── 03_visual_candidates/
│   ├── visual-plan.json
│   ├── image-prompts.json
│   ├── candidate-manifest.json
│   ├── raw-generations/
│   └── previews/
├── 04_admin_selection/
│   ├── selected-assets.json
│   └── selection-notes.md
├── 05_figma_assembly/
│   ├── figma-assembly-plan.json
│   ├── copy-map.json
│   ├── channel-outputs.json
│   └── exports/
├── 06_qa_packaging/
│   ├── qa-report.json
│   └── final-package-manifest.json
└── 07_asset_archive/
    ├── asset-archive.json
    └── reuse-notes.md
```

추천 run-status.json 예시:
```json
{
  "run_id": "2026-05-06_sample-001",
  "event_id": "sample-event",
  "current_stage": "04_admin_selection",
  "stage_status": {
    "01_event_brief": "approved",
    "02_content_planning": "approved",
    "03_visual_candidates": "done",
    "04_admin_selection": "review_pending",
    "05_figma_assembly": "locked",
    "06_qa_packaging": "locked",
    "07_asset_archive": "locked"
  }
}
```

---

# 7. Stage 타입별 핵심 명세 포맷

## 7-1. AGENT_SPEC 공통 포맷
`01_event_brief`, `02_content_planning`, `03_visual_candidates`, `05_figma_assembly`, `06_qa_packaging`에 적용한다.

```md
# AGENT_SPEC.md

## Mission
이 stage 에이전트가 해결해야 하는 문제

## Responsibility
책임지는 범위 / 책임지지 않는 범위

## Inputs
읽어야 하는 파일과 필수 필드

## Outputs
반드시 생성해야 하는 파일과 필수 필드

## Reasoning Steps
추론 순서

## Decision Criteria
판단 기준

## Human Gate
멈추고 사람에게 넘기는 조건

## Fail / Retry
실패 조건 / 재시도 조건

## Handoff
다음 stage로 넘기는 파일과 의미

## Do Not
금지 사항
```

---

## 7-2. SELECTION_GUIDE 포맷
`04_admin_selection`에 적용한다.

```md
# SELECTION_GUIDE.md

## Mission
이 단계에서 사람이 무엇을 결정해야 하는지

## Inputs
사람에게 보여줄 후보 데이터와 파일

## Selection Options
채택 / 제외 / 재생성 / 보류 등 선택 유형

## Selection Criteria
어떤 기준으로 선택해야 하는지

## Required Output Format
선택 결과를 어떤 JSON 구조로 기록해야 하는지

## Handoff
선택 결과를 다음 stage에 어떻게 넘기는지

## Notes for UI
운영 UI에서 어떤 식으로 보여줘야 하는지
```

---

## 7-3. ARCHIVE_SPEC 포맷
`07_asset_archive`에 적용한다.

```md
# ARCHIVE_SPEC.md

## Mission
최종 자산을 어떻게 저장하고 재사용 가능한 지식으로 전환할지

## Inputs
받아야 하는 최종 산출물과 메타데이터

## Archive Rules
저장 규칙 / 버전 규칙 / 분류 규칙

## Indexing Rules
검색 가능한 인덱스를 어떻게 만들지

## Reuse Rules
어떤 자산을 reusable로 볼지

## Output Structure
어떤 JSON / MD를 남길지

## Do Not
보관하면 안 되는 것 / 삭제해야 하는 것
```

---

# 8. workflow.py 역할

scripts/workflow.py는 단순 헬퍼가 아니라 오케스트레이터다.

역할:
- run 생성
- stage 실행
- 상태 기록
- 승인 대기
- 특정 stage 재실행
- 특정 산출물 재생성
- 실패 기록

추천 CLI:
```bash
python3 scripts/workflow.py --setup --event events/sample-event
python3 scripts/workflow.py --list-stages
python3 scripts/workflow.py --run runs/2026-05-06_sample-001 --stage 01_event_brief
python3 scripts/workflow.py --run runs/2026-05-06_sample-001 --stage 03_visual_candidates
python3 scripts/workflow.py --run runs/2026-05-06_sample-001 --stage 03_visual_candidates --mode regenerate --outputs image-prompts.json
python3 scripts/workflow.py --run runs/2026-05-06_sample-001 --approve 01_event_brief
```

---

# 9. Codex 구현 우선순위

## Phase 1
- docs/AGENT_SPEC.md 작성
- docs/ARCHITECTURE.md 작성
- core/schemas 초기 작성
- core/states 작성
- core/channels 작성
- core/templates 작성

## Phase 2
- pipeline/01~07 폴더 생성
- stage 타입별 공통 규약 반영
  - 01,02,03,05,06 → AGENT_SPEC.md
  - 04 → SELECTION_GUIDE.md
  - 07 → ARCHIVE_SPEC.md
- 각 stage별 README.md / input/output schema 작성
- workflow.py 오케스트레이터 구조 작성
- runs 자동 생성 기능 구현

## Phase 3
- 01_event_brief 구현
- 02_content_planning 구현
- 03_visual_candidates + ComfyUI adapter 연결
- 04_admin_selection 선택 결과 구조 구현
- 05_figma_assembly 템플릿 매핑 구현

## Phase 4
- 06_qa_packaging rule set 구현
- 07_asset_archive 재사용 메타 구현
- dashboard / review UI 설계
- asset index / search 구조 추가

---

# 10. Codex 전달용 핵심 한 줄

이 프로젝트는 이벤트 하나를 입력하면 멀티채널 콘텐츠 세트를 생성하는 **멀티 에이전트형 운영 시스템**이다.  
각 stage는 단순 폴더가 아니라 Claude Code/Codex가 추론하는 에이전트 실행 단위이며, JSON 산출물은 결과물이자 다음 stage 입력 컨텍스트다.  
단, 모든 stage가 같은 내부 파일 구조를 갖는 것은 아니고, stage 타입에 따라 `AGENT_SPEC.md`, `SELECTION_GUIDE.md`, `ARCHIVE_SPEC.md`를 다르게 사용한다.  
ComfyUI는 비주얼 후보 생성 엔진, Figma는 템플릿 기반 조립 엔진으로 사용한다.  
먼저 core / pipeline / runs / services 구조를 고정하고, 각 stage의 타입에 맞는 명세 파일과 schema를 공통 규약 아래 설계해야 한다.
