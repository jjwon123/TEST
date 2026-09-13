# 워크플로우

## 2026-07-20 Console transition rules

- Evidence review: when decisions are complete but selected evidence is insufficient, return to the deferred card; when sufficient, open concept selection.
- Concept selection: confirmation opens copy review.
- Copy review: approval opens the linked image-candidate run; revision request remains in the same copy-review case.
- Image selection: completion exposes QA and archive as the single next action.

- When product proof is missing or rejected, the normal flow continues without product claims. The console locks ingredient, efficacy, number, and result claims until an official product page is captured and reviewed; the detailed direct-entry form is not part of the mission flow.
- Copy-review save always transitions to references. A directly matched production run is preferred; otherwise the production run selected in the console is used when it is ready for references.

## 2026-07-21 Production continuation

`카피 승인 → 레퍼런스 수집·검수 → 이미지 방향 → 이미지 후보 생성 → 이미지 선택 → QA 패키지`

- 레퍼런스 수집 job이 끝나면 이미지 방향 화면을 연다.
- 이미지 후보 생성 job이 끝나면 이미지 비교·선택 화면을 연다.
- 이미지 선택 확정 뒤에는 선택 반영과 QA packaging job을 순서대로 실행하고 최종 패키지 화면을 연다.

> 2026-07-18 console UX: `근거 검수 시작` opens the event-scoped evidence review in the current mission area. It must not jump to, or rely on, a collapsed diagnostics section below the mission.

> 2026-07-18 review scope: the evidence-review workspace shows only the decision-ready summary, planning use, one limitation, optional source detail, and `채택 / 보류 / 제외`. Collection paths, public-URL capture, CSV, raw score tags, and editing controls remain outside the human review flow.

## 이벤트 단위 빠른 근거 검수 (2026-07-01)

```text
이벤트 선택
-> 후보 3개 출처·요약 확인
-> 시스템 검수안 계산
-> 사람이 확인창 승인
-> 서버 전체 검증
-> 원자적 배치 저장
-> 근거 큐 재계산
```

- 추천은 판정을 대신하지 않으며 확인 전 저장되지 않는다.
- 같은 역할 후보가 여러 개면 최고 후보만 selected, 나머지는 shortlist다.
- 이벤트 밖 신호와 빈 사유 데이터는 저장할 수 없다.

## 공개 근거 후보 수집과 출처 감사 (2026-07-01)

```text
공신력 있는 공개 출처 조사
-> 원문 대신 관찰 요약·전략 함의 작성
-> 기관/URL/발행일/방법론 보존
-> unreviewed 신호 import
-> 출처 snapshot 감사
-> 이벤트별 사람 검수
```

- 외부 카테고리 연구는 특정 제품 효능 proof로 전이하지 않는다.
- 독립 출처 최소 2곳은 sourceType이 아니라 URL host 기준으로 계산한다.
- 이벤트 입력에 명시된 혜택은 `event_brief -> internal` 후보로 저장할 수 있지만
  원본 이벤트 조건 대조 후 사람이 선택해야 한다.
- 출처 감사 통과는 사람 검수를 대체하지 않는다.

## 이벤트 근거 준비 큐 (2026-07-01)

```text
20개 이벤트 근거 계획
-> 대표 5건 우선 선택
-> 이벤트별 조사 질문/검색어 확인
-> 공개 URL 캡처(sourceRef.eventId 저장)
-> 사람 정제 및 근거 역할 분류
-> selected 판정
-> selected 3개 + 필수 역할 + 출처 2종 검사
-> 이벤트 전용 InsightBrief
-> 콘셉트/카피 재생성
```

- 큐 상태:
  - `needs_collection`: 이벤트 범위 후보가 없어 외부 근거 수집 필요.
  - `needs_review`: unreviewed 또는 shortlist 후보를 사람이 판정해야 함.
  - `ready`: 개수, 필수 역할, 출처 다양성을 모두 충족.
- 신호 3개가 모두 같은 역할 또는 같은 출처면 ready가 아니다.
- 이벤트를 선택하기 전에는 전체 신호 카드가 검수 화면에 노출되지 않는다.
- 오래된 사람 검수는 보존하지만 이벤트 근거가 불일치하면 완료 집계에서
  제외한다.

## 이벤트별 근거 격리 (2026-06-30)

```text
공개 신호 수집
-> sourceRef.eventId 또는 topic 부여
-> 사람 selected 검수
-> 이벤트 전용 InsightBrief 생성
-> InsightBrief.eventId 정확 일치 확인
-> 콘셉트/카피 생성
-> marketingEvidenceEventId 기록
-> 이벤트 근거 감사
-> 카피 검수 허용
```

- 구체 이벤트는 `general` 또는 다른 이벤트의 ready InsightBrief를 사용하지 않는다.
- 이벤트별 파일:
  `design_brain_wiki/marketing_signals/insight-briefs/<event-id>.json`
- 전용 근거가 없으면 생성 결과는 `needs_signal_review`이며 승인할 수 없다.
- 과거 캐시에 신호 ID가 있어도 `marketingEvidenceEventId`가 현재 이벤트와
  다르면 재생성 대상이다.

## 검수 피드백 완결성 게이트 (2026-06-30)

```text
전략 또는 카피 확인
-> 루브릭 점수 입력
-> 사유 태그 1개 이상 선택
-> 구체 검수 메모 입력
-> 서버 검증
-> 저장
-> 다음 미검수 카드로 이동
```

- 전략, run 콘셉트, run 카피, 벤치마크 카피에 공통 적용한다.
- 전략 CSV는 import dry-run에서 같은 기준을 먼저 검사한다.
- 메인 진행률은 별도 브라우저 세션 값이 아니라 저장소의 실제 검수 수치로
  계산한다.
- 사유가 없는 선택·거절·수정은 다음 생성에 활용할 수 없으므로 저장하지 않는다.

## 교정 학습 실증 감사 (2026-06-28)

```text
채널별 카피 직접 수정
-> 검수 저장
-> 승인된 CopyCorrectionRecord 저장
-> 교정 학습 확인
-> 같은 이벤트·선택 콘셉트로 카피 새 생성
-> correctionSearch.appliedIds 대조
-> 통과 또는 적용 조건 점검
```

- 실행:
  `.venv\Scripts\python.exe scripts\audit_copy_correction_loop.py --verify-application`
- 결과:
  `.tmp/model-benchmarks/copy-correction-loop-audit.json`
- 실제 수정이 없는 승인본은 교정 학습 대상으로 세지 않는다.
- 직접 문구 재적용은 기존 정책대로 같은 브랜드·이벤트·채널 및 원문
  exact-match 조건에서만 허용한다.
- 감사 과정은 벤치마크 결과 파일을 덮어쓰지 않고 메모리에서 새 생성을
  수행한다.

이 프로젝트는 GPT보다 똑똑한 기획툴을 만드는 것이 아니다.

목표는 디자이너가 브랜드 이벤트 이미지를 만들 때 필요한 레퍼런스 수집, 콘텐츠 기획, 프롬프트, ComfyUI 후보 생성, 사람 선택, QA 패키징, 자산 아카이브를 한 흐름으로 관리하는 로컬 제작 콘솔이다.

## 2026-06-20 기준: 콘셉트 비평과 카피 QA 분리

- 콘셉트 후보 생성 직후에는 카피 패키지가 아직 없으므로 채널별 필드, 채널 불일치, CTA 누락 같은 카피 QA를 적용하지 않는다.
- 콘셉트 단계 QA는 콘셉트 3안 개수, 전략 축 중복, 최소 2개 이상 차별화, 근거 신호 준비 상태만 판단한다.
- 선택 콘셉트로 카피 패키지를 생성한 뒤에야 채널별 필수 필드, 카피 반복, 근거 연결, 금지 표현, unsupported claim, scorecard 치명 오류를 판단한다.
- 파일럿 목표 감사는 화면 텍스트 깨짐뿐 아니라 최종 scorecard의 치명 오류까지 함께 확인한다.

## 2026-06-20 기준: 20건 평가 확장 흐름

- `scripts/run_ad_planning_pilot.py --limit 20`은 화장품 고정 평가셋 20건 전체에 콘셉트 3안을 준비한다.
- 콘셉트 선택 전에는 카피를 생성하지 않는다. 현재 20건 중 15건은 `concept_review_pending`, 5건은 `complete` 상태다.
- 콘솔의 이벤트 기획 검수 데스크는 선택 대기와 카피 승인 대기를 전체 노출한다. 더 이상 5건만 잘라 보여주지 않는다.
- 전략 30건 검수는 자동 추천으로 대체하지 않는다. 추천 초안은 입력 보조이며, 사람이 저장해야 `selected / shortlist`로 집계된다.

## 2026-06-21 기준: 연결 확인용 기본 콘셉트 선택

- `scripts/run_ad_planning_pilot.py --limit 20 --select-pending-concepts`는 선택 대기 케이스에 `concept_01`을 기본 선택해 카피 패키지 생성까지 연결한다.
- 결과에는 `selectionSource: connection_check_default`와 안내 메모를 남긴다.
- 이 선택은 사람 선호, 최종 승인, 사람 평가로 집계하지 않는다.
- 이 흐름의 목적은 20건 전체 카피 생성 파이프라인이 깨지지 않는지 확인하는 것이다.
- 품질 목표 통과에는 여전히 사람이 20건 카피를 평가하고 수정/승인 기록을 저장해야 한다.

## 2026-06-28 기준: 벤치마크 카피 수정·학습 저장 흐름

```text
미검수 이벤트 3건 집중 표시
-> 채널별 카피 필드 직접 수정
-> 8개 루브릭 + 사유 태그 + 메모 입력
-> 수정 요청 또는 최종 승인 저장
-> 생성 원문 generatedCopy 보존
-> 최종문 copy 반영
-> scorecard 재검사
-> CopyCorrectionRecord 채널별 저장
-> 다음 미검수 이벤트 자동 표시
```

- 최종 승인에는 사람 평균 4.0 이상과 QA issue 0건이 필요하다.
- 수정 요청도 교정 데이터로 저장하며 `approved: false`로 구분한다.
- 최종 승인본은 `approved: true`로 저장된다.
- 같은 내용으로 다시 저장하면 동일 correction ID를 갱신해 중복 데이터를 만들지 않는다.

## 2026-06-28 기준: 교정 데이터 재사용

```text
승인된 CopyCorrectionRecord 검색
-> 업종/브랜드 격리
-> 같은 이벤트 + 같은 채널 확인
-> 현재 생성 필드가 저장된 originalCopy와 정확히 같은지 확인
-> 일치하는 필드만 editedCopy로 교체
-> correctionExampleIds 기록
-> 최종 QA
```

- 다른 이벤트의 수정문은 직접 복사하지 않는다.
- 다른 브랜드의 교정은 검색하지 않는다.
- 브랜드가 없는 생성은 타 브랜드 교정을 가져오지 않는다.
- 외부 모델에는 승인 교정을 예시로 제공하고, 로컬 결정론적 생성기는 exact-match 교정만 안전하게 적용한다.

## 2026-06-28 기준: 전략 30건 집중 검수

```text
메인 화면 전략 검수 시작
-> 추천 상위 전략 3건 표시
-> 광고 원문과 추상 전략 비교
-> 필요하면 추천값 수정
-> 추천대로 판정 또는 선택/참고/거절 저장
-> 다음 미검수 3건 자동 표시
-> selected + shortlist 30건 달성
```

- 추천대로 판정 저장은 확인창을 통한 사람의 명시적 결정이다.
- 추천 점수만으로 자동 selected 승격하지 않는다.
- selected는 생성 예시로 사용하고 shortlist는 참고 근거로만 사용한다.

## MVP 기준 흐름

```text
01_event_brief
→ 02_content_planning
→ 03_reference_research
→ 04_visual_candidates
→ 05_admin_selection
→ 06_qa_packaging
→ 07_asset_archive
```

기존 `05_figma_assembly`는 제거된 상태다. Figma 조립을 전제로 하지 않고, 사람이 선택한 이미지 후보와 프롬프트를 기준으로 QA/패키징으로 넘어간다.

호환 메모:

- 기존 코드/런 산출물의 물리 폴더명 `03_visual_candidates`는 당분간 유지한다.
- 기존 코드/런 산출물의 물리 폴더명 `04_admin_selection`도 당분간 유지한다.
- 새 실행 단계명은 `04_visual_candidates`, `05_admin_selection`을 기준으로 사용한다.

## 01_event_brief: 이벤트 브리프

입력:

- `events/[event]/event-input.json`
- `events/[event]/brand-guide.json`

출력:

- `01_event_brief/brief.json`
- `01_event_brief/notes.md`

목표:

- 이벤트 목적, 대상, 혜택, 일정, 채널, 핵심 메시지를 정리한다.
- 브랜드와 이벤트 정보가 충돌하는 부분을 발견한다.
- 카테고리별 리스크를 초기에 표시한다.

마케팅 인텔리전스 확장 예정:

- 카피 생성 전 `marketing-signals.json`과 `insight-brief.json`을 만든다.
- 초기에는 01/02 내부 산출물로 붙이고, 안정화되면 별도 `00_marketing_intelligence` 단계로 분리한다.
- 시장/고객/트렌드/계절/날씨/채널 신호가 부족하면 강한 훅을 임의 생성하지 않고 근거 부족으로 표시한다.

## 02_content_planning: 콘텐츠 기획

입력:

- `01_event_brief/brief.json`
- 채널/템플릿 레지스트리

출력:

- `02_content_planning/content-plan.json`
- `02_content_planning/notes.md`

목표:

- 채널별 산출물 종류를 정한다.
- 각 산출물의 메시지, CTA, 비주얼 방향, 카피 구조를 잡는다.
- 이미지 후보 생성에 필요한 `image_needs`를 만든다.

광고 기획 검수 데스크 확장 기준:

- 이벤트 확인 후 콘셉트 3안을 비교하고, 사람이 콘셉트 1개를 선택한다.
- 선택된 콘셉트로 채널별 카피 패키지를 만든다.
- 각 카피에는 문장 자체만 두지 않고 `문구 근거`, `타깃`, `제품 역할`, `혜택 역할`, `채널 역할`을 함께 기록한다.
- 내부 ID나 JSON 구조가 사용자 화면에 보이면 실패로 보고, 사람 검수자는 `선택 / 수정 요청 / 최종 승인`만 판단한다.

## 03_reference_research: 레퍼런스 리서치

입력:

- `event-input.json`
- `brand-guide.json`
- 필요 시 기존 `references/` 폴더

출력:

- `references/reference-collection-plan.json`
- `03_reference_research/reference-research.json`
- `03_reference_research/notes.md`
- 자동 수집 실행 시 `references/reference-manifest.json`, `selected-references.json`

`reference-research.json` 핵심 필드:

- `moodKeywords`
- `compositionKeywords`
- `lightingKeywords`
- `colorPalette`
- `materialTexture`
- `avoidKeywords`
- `promptHints`
- `negativePromptHints`
- `selectedReferences`

목표:

- 이벤트와 채널에 맞는 레퍼런스 검색 쿼리를 만든다.
- 이미 수집된 레퍼런스가 있으면 선택 상태를 요약한다.
- 레퍼런스 방향성을 04 이미지 후보 프롬프트에 전달한다.
- 필요하면 Pinterest/로컬 레퍼런스 수집과 Qwen-VL 리뷰를 실행한다.

운영 기준:

- 기본 stage 실행은 무거운 브라우저 수집 없이 계획/요약만 만든다.
- `REFERENCE_RESEARCH_MODE=auto_search`를 설정하면 기존 자동 검색/선정 파이프라인을 stage 안에서 실행할 수 있다.

## 04_visual_candidates: 이미지 후보 생성

입력:

- `02_content_planning/content-plan.json`
- `references/reference-manifest.json`이 있으면 선택 레퍼런스
- 제품 라이브러리 정보
- ComfyUI workflow registry

출력:

- 물리 폴더: `03_visual_candidates/`
- `visual-plan.json`
- `image-prompts.json`
- `candidate-manifest.json`
- `previews/`

목표:

- 채널별 이미지 후보 생성을 위한 프롬프트를 만든다.
- 제품, 브랜드, 이벤트, 채널 규격, 선택 레퍼런스를 함께 반영한다.
- `03_reference_research/reference-research.json`의 mood/composition/lighting/color/texture/avoid/prompt hint를 프롬프트에 반영한다.
- ComfyUI placeholder 또는 live 모드로 후보 미리보기를 만든다.

명령:

```powershell
python scripts\workflow.py --run runs\<run-id> --stage 04_visual_candidates
```

ComfyUI live 재생성:

```powershell
$env:COMFYUI_GENERATION_MODE='live'
python scripts\workflow.py --run runs\<run-id> --stage 04_visual_candidates --mode regenerate --group <group-id>
```

## 05_admin_selection: 이미지 선택

입력:

- 물리 폴더: `03_visual_candidates/image-prompts.json`
- 물리 폴더: `03_visual_candidates/candidate-manifest.json`
- 콘솔 또는 CLI에서 사람이 저장한 선택값

출력:

- 물리 폴더: `04_admin_selection/`
- `selected-assets.json`
- `selection-notes.md`

목표:

- 어떤 이미지를 어느 채널에 쓸지 결정한다.
- 선택, 탈락, 보류, 재생성 요청을 남긴다.
- 선택 완료 시 06 QA 패키징 단계가 열린다.

## 06_qa_packaging: QA 패키징

입력:

- `04_admin_selection/selected-assets.json`
- 콘텐츠 플랜과 브랜드 가이드
- Figma 산출물이 있는 구형 런의 경우 `05_figma_assembly/channel-outputs.json`, `copy-map.json`

출력:

- `06_qa_packaging/qa-report.json`
- `06_qa_packaging/final-package-manifest.json`
- `06_qa_packaging/qa-packaging.json`
- `06_qa_packaging/notes.md`

목표:

- 선택 자산 누락, 금지어, 필수 문구, CTA, 채널 규격, 파일 존재 여부를 확인한다.
- 수정이 필요하면 어느 단계로 돌아갈지 `suggested_fix_stage`에 남긴다.
- 최종 패키징에 필요한 매니페스트를 만든다.

## 07_asset_archive: 자산 아카이브

입력:

- QA 통과 자산
- 선택 이유와 재사용 메모

출력:

- `07_asset_archive/asset-archive.json`
- `07_asset_archive/reuse-notes.md`
- `assets/indexes/global-index.json`

목표:

- 재사용 가능한 이미지, 카피, 레퍼런스를 태깅한다.
- 다음 이벤트에서 다시 찾을 수 있게 만든다.

## 승인 게이트

```text
brief_approved
content_plan_approved
references_ready
visual_candidates_ready
assets_selected
qa_approved
reuse_ready
```

## 현재 구현상 주의

- 새 stage ID는 `03_reference_research`, `04_visual_candidates`, `05_admin_selection`이다.
- 기존 산출물 호환 때문에 실제 파일 경로는 일부 구명칭을 유지한다.
- `03_visual_candidates`와 `04_admin_selection`을 명령으로 입력해도 workflow alias가 새 단계로 매핑한다.
## 2026-05-28 - 03_reference_research 룰 기반 판단 강화

`03_reference_research`는 이제 다음 입력을 함께 사용한다.

```text
event-input.json
+ brand-guide.json
+ assets/rules/brand-persona.json
+ assets/rules/event-rules.json
+ assets/rules/reference-rules.json
+ assets/rules/visual-avoid-rules.json
-> search query
-> reference score
-> selected / shortlist / rejected
```

`reference-research.json`에는 `ruleSources`, `qualityFilter`, `referenceDecisions`, `promptHints`, `negativePromptHints`를 남긴다. `bullion_investment`는 캐릭터/캠핑/장난감/가짜 텍스트 계열을 hard reject로 본다.

## 2026-05-30 - good/bad reference_training 기반 03 품질 리포트 추가

`03_reference_research` 판단 입력에 `assets/reference_training/<profile>/good|bad` seed dataset을 추가했다.

```text
brand rules
+ event rules
+ visual avoid rules
+ good/bad reference_training
-> search query
-> reference score
-> selected / shortlist / rejected
-> reference-quality-report
```

추가 출력:

```text
runs/<run-id>/03_reference_research/reference-quality-report.json
runs/<run-id>/03_reference_research/reference-quality-report.md
```

리포트는 selected 안의 bad signal, good seed similarity, reject reason 명확성, fallback 오염 여부를 확인한다.

## 2026-05-30 - good seed 2차 카테고리 분리

`bullion_investment` good seed를 3개 카테고리로 분리했다.

```text
assets/reference_training/bullion_investment/good/product_reference/
assets/reference_training/bullion_investment/good/finance_mood_reference/
assets/reference_training/bullion_investment/good/poster_layout_reference/
```

`reference-quality-report`에 다음 커버리지를 추가했다.

```json
{
  "goodSeedCoverage": {
    "product_reference": 10,
    "finance_mood_reference": 10,
    "poster_layout_reference": 10
  },
  "selectedCategoryCoverage": {
    "product_reference": 4,
    "finance_mood_reference": 4,
    "poster_layout_reference": 4
  },
  "selectedCoverage": {
    "product_identity": 8,
    "mood": 8,
    "composition": 12,
    "lighting": 8,
    "headline_space": 8
  }
}
```

선택 로직은 good seed category를 round-robin으로 섞어 제품컷에만 몰리지 않도록 한다.
## 2026-05-30 - Senior Designer Brain Wiki를 03_reference_research 상위 판단 기준으로 추가

이미지 생성 전 판단 흐름을 아래처럼 확장한다.

```text
design_brain_wiki
+ assets/rules
+ assets/reference_training
+ event-input.json
+ brand-guide.json
-> Senior Designer Reference Judge
-> search query
-> reference score
-> selected / shortlist / rejected
-> reference-quality-report
-> 04_visual_candidates
```

`design_brain_wiki`는 다음 역할을 가진다.

- 디자인 원칙: hierarchy, grid, typography, color, whitespace 기준 제공.
- 브랜드 전략: brand personality, system fit, distinctiveness, premium/trust 판단 제공.
- 레퍼런스 판단: selected/shortlist/rejected 기준과 report rule 제공.
- 채널 사용성: instagram/cardnews/banner/blog/landing page별 실무 적용성 판단.
- 업종 playbook: bullion, cosmetics, jewelry, fashion, tech, editorial 업종별 신뢰/리스크 기준 제공.
- feedback language: AI가 시니어 디자이너처럼 이유를 설명하는 문장 템플릿 제공.

04_visual_candidates와 ComfyUI는 이 판단이 통과된 뒤에만 실행한다.
## 2026-05-31 - Reference Judge 연결 전 Wiki Test Gate 추가

`design_brain_wiki`는 다음 테스트를 통과한 뒤 `03_reference_research`에 연결한다.

```text
design_brain_wiki
-> reference_judge_sample_set
-> run_reference_judge_wiki_tests.py
-> reference-judge-test-report
-> pass일 때만 03_reference_research 연결
```

테스트 위치:

```text
design_brain_wiki/tests/reference_judge_sample_set.json
scripts/run_reference_judge_wiki_tests.py
design_brain_wiki/tests/output/reference-judge-test-report.json
design_brain_wiki/tests/output/reference-judge-test-report.md
```

현재 샘플 테스트 범위:

- `bullion_investment`: 금 투자 상담 이벤트 기준 selected/shortlist/rejected 판단.
- `cosmetics_skincare`: 스킨케어 제품/상담 캠페인 기준 판단.
- `jewelry_luxury`: 주얼리 럭셔리 캠페인 기준 판단.

운영 연결 전 확인:

- good 후보는 selected로 분류되는가.
- bad 후보는 rejected로 분류되는가.
- ambiguous 후보는 selected로 과승인되지 않고 shortlist로 남는가.
- 피드백이 "고급스럽습니다/잘 맞습니다" 수준이 아니라 역할, 사용 위치, 부족한 기준, 리스크 신호를 설명하는가.
## 2026-05-31 - 기원님 교정 루프를 로컬 콘솔에 추가

판단 훈련 흐름은 이제 파일 직접 편집보다 로컬 콘솔을 우선 사용한다.

```text
training_sessions/<profile>/<session>
-> AI first judgement
-> local console 판단 훈련 탭
-> Kiwon review 저장
-> kiwon_review_state.json
-> kiwon_review_summary.md
-> correction_log / wiki_update_suggestions 반영
```

사용자는 각 reference에 대해 아래만 입력하면 된다.

```text
agree / disagree / unsure
correctDecision
kiwonReason
ruleToUpdate
```

이 교정 데이터가 v0.3에서 실제 Reference Judge 보정 기준이 된다.
## 2026-06-03 - ComfyUI 이전 품질 게이트 보강

ComfyUI 생성 단계와 독립적으로 아래 점검/학습 루프를 추가했다.

1. 01/02 산출물 QA
   - `scripts/audit_planning_quality.py --run runs\<run-id>`
   - 브리프 핵심 입력, 금지 표현, 산출물/image_needs 정합성, 메시지 다양성 점검.

2. Reference Judge 훈련 세션
   - `scripts/create_reference_training_session.py --profile cosmetics_skincare --session-id <id> --exclude-profile-history`
   - 필요 시 `--qwen-vision`으로 Qwen/Ollama 비전 평가를 붙인다.

3. 검수 저장
   - 콘솔 판단 훈련 UI가 `status`, `correctDecision`, `kiwonReason`, `ruleToUpdate`, `reasonTags`를 저장한다.

4. 학습 요약
   - 저장 시 `kiwon_review_summary.md`, `correction_summary.md`, `learned_rules.json` 자동 갱신.
   - 기존 세션은 `scripts/summarize_reference_training_session.py`로 backfill.

5. holdout 비교
   - `scripts/compare_reference_sessions.py --profile cosmetics_skincare`
   - session 001 / holdout 001 / holdout 002 / holdout 003 정확도와 전이 패턴 비교.

6. 04 prompt audit
   - `scripts/audit_visual_prompts.py --run runs\<run-id>`
   - `cosmetics_skincare`에서는 H&B 세일감, 혜택 위계, 제품 신뢰, 웹페이지 캡처/URL바, fake text risk를 별도 점검.

7. Hook 점검
   - `scripts/project_hook_check.py --run runs\<run-id>`
   - Python compile, console JS check, planning audit, prompt audit을 묶어서 실행.
## 2026-06-03 - 06_qa_packaging 품질 근거 추적

06_qa_packaging은 이제 최종 패키지 파일뿐 아니라 upstream 품질 근거도 함께 점검한다.

- `qa-report.json`: `qualityArtifacts`에 품질 근거 파일 존재 여부, status, 요약을 기록한다.
- `final-package-manifest.json`: 각 파일 레코드에 `qualityEvidence.artifacts`와 `qualityEvidence.selection`을 붙인다.
- `qa-packaging.json`: `package_manifest.quality_artifacts`와 top-level `quality_artifacts`를 포함한다.
- 점검 대상: `planning-quality-audit.json`, `reference-quality-report.json`, `prompt-audit.json`, `generation-quality.json`, `selected-assets.json`.
- 누락/실패한 품질 근거는 QA issue로 승격되고 `suggested_fix_stage`를 통해 되돌아갈 단계를 명시한다.

## 2026-06-04 - 선택 후보 기준 QA Evidence 판정

06_qa_packaging은 `selected-assets.json`에 기록된 최종 선택 후보를 먼저 기준으로 삼는다.

- `generation-quality.json`: 선택 후보가 generated이면 pass, placeholder/prompt_only이면 warning, failed/error이면 fail로 본다.
- `prompt-audit.json`: 선택 후보에 해당하는 audit item이 있으면 해당 item의 pass/warning/fail을 우선한다.
- 선택 후보별 `qualityEvidence.artifacts[]`에는 각 근거 파일의 상태와 요약이 들어간다.
- 콘솔 `/api/runs/<run-id>`는 `qa_report`, `final_package_manifest`, `qa_packaging`을 내려주고, 최종 패키지 화면에서 QA Evidence를 표시한다.
## Meta Ad Library reference provider (2026-06-07)

```text
Ad Reference 검색
→ Meta 광고 카드 내부 원본 이미지 다운로드
→ references/meta_ads/searches/<검색-id>/images/
→ 현재 run/references/selected/ 복사
→ run/references/reference-manifest.json 등록
→ 03_reference_research가 selected reference로 읽음
→ 04_visual_candidates 프롬프트 방향에 반영
```

- 카드 캡처는 `captures/`에 보조 증거로 남긴다.
- 광고 이미지가 많은 캐러셀은 광고당 최대 10장으로 제한한다.
- 자동 연결을 원하지 않으면 콘솔의 `현재 작업 레퍼런스로 연결`을 끈다.

## Meta 검증 브랜드 레지스트리 수집 (2026-06-10)

```text
assets/rules/meta-brand-registry.json
→ 업종별 브랜드 1~3개 소량 수집
→ 광고주명 별칭 엄격 일치
→ 기본 해상도·비율 검사
→ references/meta_ads/brand_registry_runs/
→ 브리프 역할 필터와 Reference Judge
→ 필요할 때만 run reference로 연결
```

- 현재 초기 레지스트리는 화장품 20개, 주얼리 20개다.
- 브랜드 레지스트리 수집은 범용 키워드 검색보다 우선하는 안정 수집 경로다.
- 브랜드 공식 광고도 현재 브리프와 다른 제품군일 수 있으므로 자동 selected 연결은 금지한다.

## 운영 게이트 및 전체 상태 감사

- `generation_status=failed|error`인 후보는 selected로 저장할 수 없다.
- QA issue에 `severity=error|blocker`가 남아 있거나 QA status가 fail이면 06 승인할 수 없다.
- QA 오류 수정 라우팅은 issue의 status뿐 아니라 severity도 본다.
- upstream 단계를 재실행하면 downstream 상태를 `locked`로 되돌리고 `run-status.json`의 `stale_stages`에 무효화 원인을 기록한다.
- 전체 상태 점검:

```powershell
.venv\Scripts\python.exe scripts\audit_full_pipeline_health.py
```
# 2026-06-14 01·02 기획 승인 흐름 확장

```text
01_event_brief
  -> brief.json + strategic-brief.json
  -> 사람 승인
02_content_planning
  -> concept-candidates.json (서로 다른 3안)
  -> concept-review.json (사람 선택)
  -> selected-concept.json
  -> copy-package.json (요청 채널별 완성 카피)
  -> copy-review.json (수정·최종 승인)
  -> planning-scorecard.json
  -> 02 단계 승인
03_reference_research
```

- 콘셉트 선택 전에는 카피 패키지가 `blocked_pending_concept_selection` 상태다.
- 콘셉트와 최종 카피 승인 전에는 03단계를 열 수 없다.
- 치명 QA 오류가 남아 있으면 02단계 승인이 차단된다.
# 02 콘텐츠 기획 외부 품질 생성 흐름 (2026-06-14)

```text
승인된 brief
  -> selected 전략 검색 + shortlist 참고
  -> OpenAI strategist 콘셉트 3안
  -> critic 평가
  -> 실패 항목만 strategist 재작성
  -> 사람 콘셉트 선택
  -> OpenAI copywriter 채널별 카피
  -> critic 평가
  -> 실패 항목만 copywriter 재작성
  -> 사람 직접 수정 + 8항목 채점 + 최종 승인
  -> 경고 0건일 때만 03_reference_research 잠금 해제
```

- 외부 역할 호출은 이벤트당 최대 8회다.
- `provider_unavailable`, 치명 오류, 일반 품질 경고, 평균 4점 미만은 02 승인을 차단한다.
- 결정론적 baseline은 비교 자료이며 승인 가능한 fallback이 아니다.
# 광고 기획 고정 평가 워크플로 보강 (2026-06-15)

1. `scripts/benchmark_ad_planning.py --run-external --limit 5`로 누락된 외부 콘셉트 3안 파일럿을 생성한다.
2. 콘솔에서 사람이 콘셉트 하나를 선택한 뒤에만 채널 카피를 생성한다.
3. 케이스마다 결정론적 기준선과 외부 결과를 고정 해시 기반 A/B 순서로 섞는다.
4. 콘솔에서 출처를 보지 않고 A/B 선호와 8개 루브릭을 저장한다.
5. 평가 저장 직후 종합 리포트를 다시 계산한다.
6. 5건 파일럿의 치명 오류가 0일 때만 20건으로 확장한다.
7. 20건 외부 생성과 사람 검수가 모두 끝나야 품질 목표를 `pass` 처리한다.
# 광고 기획 QA 및 학습 승격 규칙 (2026-06-15)

1. 외부 모델 응답은 API Structured Output과 로컬 JSON Schema 검증을 모두 통과해야 한다.
2. 콘셉트 비평과 카피 비평 결과는 각각 최종 QA에 남긴다.
3. 비평 수정은 실패 대상으로 지정된 `targetIds`만 교체한다.
4. 확인되지 않은 가격·혜택·기간·효능, 경쟁사 원문 복제, 업종 혼용, 요청 채널 불일치는 자동 차단한다.
5. 채널 계약, 글자 수, 내부 문구, 제품·오퍼·CTA 연결 경고가 남으면 승인할 수 없다.
6. 사람 수정·승인 시 교정 레코드에 이벤트·브랜드·업종·채널·모델·전후 카피·QA를 저장한다.
7. 이후 생성에는 동일 브랜드 승인 교정을 우선하고 다른 브랜드 교정은 사용하지 않는다.
8. 전략 `selected`는 추상 전략 완성과 8개 루브릭 평균 4점 이상을 요구한다.
9. `scripts/audit_ad_planning_goal.py`가 핵심 조건 7개를 모두 통과해야 목표 달성으로 판정한다.
# 광고 기획 파일럿 리뷰 패킷 (2026-06-16)

ComfyUI/이미지 제작을 제외하고 광고 기획 품질 목표를 진행할 때는 다음 리뷰 패킷을 먼저 생성한다.

```powershell
.venv\Scripts\python.exe scripts\export_ad_planning_review_packet.py
```

- JSON: `.tmp/model-benchmarks/ad-planning-review-packet.json`
- Markdown: `.tmp/model-benchmarks/ad-planning-review-packet.md`
- 패킷은 파일럿 5건의 외부 결과, 콘셉트 선택, 사람 평가 상태를 표시한다.
- 패킷은 Meta 전략 46건 중 우선 검수할 30건 큐와 selected 승격에 필요한 누락 필드를 표시한다.
- `OPENAI_API_KEY`가 없으면 외부 생성은 실행하지 않고 `blocked_waiting_for_api_key` 상태로 남긴다.
- 결정론적 baseline은 비교 기준일 뿐 승인 가능한 fallback으로 쓰지 않는다.
# 광고 기획 리뷰 패킷 콘솔 노출 (2026-06-16)

- 콘솔 bootstrap은 `planningReviewPacket`을 포함한다.
- 별도 API는 `GET /api/planning-review-packet`이다.
- 대시보드 상단의 `광고 기획 파일럿 리뷰 패킷` 패널에서 다음을 확인한다.
  - API 키 설정 여부
  - 파일럿 5건 외부 생성 완료 수
  - 파일럿 5건 사람 평가 완료 수
  - selected/shortlist 전략 수
  - 현재 blocker 목록
- 전략 검수 또는 벤치마크 평가를 저장하면 응답에 최신 `reviewPacket`이 포함되고 UI 상태가 갱신된다.
# 전략 검수 CSV 워크플로 (2026-06-16)

콘솔에서 한 건씩 검수하기 어렵다면 CSV 시트를 사용한다.

```powershell
.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --limit 30
```

- 생성 위치: `.tmp/model-benchmarks/ad-strategy-review-sheet.csv`
- 사람이 채울 필드:
  - `decision`: `selected`, `shortlist`, `rejected`, `unreviewed`
  - 추상 전략 필드: `targetInsight`, `hookMechanism`, `persuasionSequence`, `offerMechanism`, `proofMechanism`, `ctaType`, `toneTraits`, `channelFit`
  - 8개 점수: `score_strategyClarity`, `score_targetEmpathy`, `score_productConnection`, `score_distinctiveness`, `score_channelFit`, `score_koreanCopyQuality`, `score_brandFit`, `score_actionability`
  - `reasonTags`, `reviewNote`
- 저장 전 검증:

```powershell
.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --import-sheet
```

- 실제 반영:

```powershell
.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --import-sheet --apply
```

- `selected`는 target insight, hook, persuasion sequence, CTA가 비어 있으면 실패한다.
- `selected`는 8개 점수 평균 4.0 이상이어야 한다.
- `shortlist`와 `rejected`도 8개 점수가 모두 필요하다.
# 광고 기획 파일럿 실행 오케스트레이터 (2026-06-16)

ComfyUI/이미지 제작을 제외하고 광고 기획 품질 목표를 점검할 때는 파일럿 실행기를 먼저 돌린다.

```powershell
.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5
```

- `OPENAI_API_KEY`가 있으면 화장품 고정 평가셋 파일럿 5건의 외부 모델 생성 흐름을 실행한다.
- `OPENAI_API_KEY`가 없으면 외부 모델 생성은 건너뛰고 다음 운영 산출물을 갱신한다.
  - `.tmp/model-benchmarks/ad-planning-pilot-run.json`
  - `.tmp/model-benchmarks/ad-planning-review-packet.json`
  - `.tmp/model-benchmarks/ad-planning-review-packet.md`
  - `.tmp/model-benchmarks/ad-strategy-review-sheet.csv`
  - `.tmp/model-benchmarks/ad-planning-goal-audit.json`
- 콘솔에서는 광고 기획 리뷰 패킷 패널의 `파일럿 5건 실행/갱신` 버튼이 같은 흐름을 background job으로 실행한다.
- API 장애나 API 키 미설정 상태에서는 결정론적 baseline을 승인 가능한 결과로 승격하지 않고 `blocked_waiting_for_api_key` 또는 `provider_unavailable` 상태로 남긴다.

## 광고 전략 CSV 콘솔 검수 반영 (2026-06-16)

전략 30건 검수는 CLI와 콘솔 양쪽에서 같은 job을 사용한다.

```powershell
.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --limit 30
.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --import-sheet
.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --import-sheet --apply
```

콘솔에서는 광고 기획 리뷰 패킷 패널에서 다음 버튼을 사용한다.

- `Strategy CSV export 30`: 검수 대상 30건을 CSV로 내보낸다.
- `Strategy CSV validate`: 반영 없이 CSV 오류만 검사한다.
- `Strategy CSV apply`: CSV 내용을 전략 저장소에 반영한다.

운영 규칙:

- `apply` 전에는 반드시 dry-run 검증 결과 `errors: []`를 확인한다.
- `selected`는 target insight, hook, persuasion sequence, CTA와 8개 루브릭 평균 4.0 이상이 필요하다.
- `shortlist`와 `rejected`도 8개 루브릭 점수가 모두 필요하다.
- `selected`/`shortlist` 합계가 30건 이상이 되기 전까지 외부 모델 생성 예시 풀은 목표 기준을 만족하지 못한다.

## 벤치마크 사람 평가 CSV 워크플로 (2026-06-16)

외부 모델 결과가 생성된 뒤 사람 평가는 CSV로도 처리할 수 있다.

```powershell
.venv\Scripts\python.exe scripts\manage_ad_planning_benchmark_review_sheet.py --limit 5
.venv\Scripts\python.exe scripts\manage_ad_planning_benchmark_review_sheet.py --import-sheet
.venv\Scripts\python.exe scripts\manage_ad_planning_benchmark_review_sheet.py --import-sheet --apply
```

콘솔에서는 광고 기획 리뷰 패킷 패널에서 다음 버튼을 사용한다.

- `Benchmark CSV export 5`: 파일럿 5건의 블라인드 A/B 평가 시트를 생성한다.
- `Benchmark CSV validate`: 반영 없이 평가 입력 오류만 검사한다.
- `Benchmark CSV apply`: 평가를 `cosmetics-human-reviews.json`에 저장한다.

필수 입력:

- `blindPreferred`: `A` 또는 `B`
- `approved`: 무수정 승인 여부
- `edited`: 사람이 카피를 수정했는지 여부
- 8개 루브릭 점수: `score_strategyClarity`, `score_targetEmpathy`, `score_productConnection`, `score_distinctiveness`, `score_channelFit`, `score_koreanCopyQuality`, `score_brandFit`, `score_actionability`
- `reviewNote`: 선호 이유나 수정 필요 사항

주의:

- CSV의 `variantA`, `variantB`는 블라인드 비교용이며 source label을 노출하지 않는다.
- `apply` 전에는 반드시 dry-run의 `errors: []`를 확인한다.
- 사람 평가 20건이 모두 저장되기 전까지 목표 감사는 `human_reviews_complete`를 통과할 수 없다.
## 2026-06-17 변경 - OpenAI API 없는 광고 기획 파일럿

- 광고 기획 파일럿의 기본 provider는 `local`이다.
- 기본 실행:

```powershell
.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5
```

- 이 명령은 API 키 없이 다음을 갱신한다.
  - local 후보 콘셉트 3안
  - benchmark report
  - review packet
  - strategy review CSV
  - benchmark review CSV
  - goal audit
- OpenAI는 명시적으로 필요할 때만 선택한다.

```powershell
.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5 --provider openai
```

- Codex/Claude 스킬 기반 작성은 `ad-planning-copy-engine` 스킬의 JSON schema를 따른다.
- 콘셉트 선택 전에는 최종 카피를 승인하지 않는다.
## 2026-06-17 보강 - local 후보 품질 기준

- local provider는 API 없이 콘셉트 3안을 만든다.
- local 후보는 승인본이 아니라 사람 선택/수정/학습 루프의 초안이다.
- 콘셉트 선택 전에는 copy package를 생성하지 않는다.
- 깨진 문자열, 반복 문장, 과도한 질문형은 `awkward_korean` 또는 `repetitive_copy` 경고로 남긴다.
- 경고가 남은 copy package는 02단계 승인 대상으로 보지 않는다.

## 2026-06-17 변경 - 콘솔 광고 기획 검수 흐름

- 메인 콘솔의 광고 기획 영역은 `광고 기획 검수 데스크`로 운영한다.
- 사용자는 이벤트별로 제품, 목적, 다음 작업을 확인한 뒤 콘셉트 3안 중 하나를 선택한다.
- 콘셉트 선택 후 채널별 카피 패키지를 검수하고 8개 루브릭, 승인 여부, 수정 여부, 메모를 저장한다.
- A/B 블라인드 비교는 사용자 화면에서 제거한다.
- 전략 CSV와 내부 벤치마크 CSV는 고급 데이터 검수용으로만 유지한다.
## 2026-06-20 변경 - 파일럿 목표 감사 단계

광고 기획 품질 목표는 이제 파일럿 실행과 목표 감사를 분리해서 본다.

1. `파일럿 5건 새로고침` 또는 `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5`
   - 후보 3안과 카피 패키지, 리뷰 패킷을 갱신한다.
   - 실행 후 `cosmetics-pilot-goal-audit.json`도 함께 갱신된다.
2. `파일럿 목표 감사` 또는 `.venv\Scripts\python.exe scripts\audit_cosmetics_pilot_goal.py --limit 5`
   - 5건이 실제 품질 목표를 통과했는지 판정한다.
   - 후보 준비, 카피 준비, 사람 평가, 치명 오류, 평균 점수, 무수정 승인율, 콘셉트 분리, 근거 연결을 확인한다.
3. 감사가 `fail`이면 다음 단계로 가지 않는다.
   - 깨진 한글/raw JSON/HTML/프로그래밍 구조 노출은 치명 오류다.
   - 근거 신호가 비어 있으면 ready `InsightBrief`로 재생성한다.
4. 감사가 `pass`일 때만 20건 전체 평가셋 확장으로 넘어간다.
## 2026-07-01 - 제품 근거 입력 및 검수 흐름

`이벤트 근거 준비 → 이벤트 선택 → 공식 제품 근거 입력 → 제품 근거 후보 검수 → InsightBrief 생성`

- 공식 제품 근거 입력은 제품 proof가 부족한 이벤트에서만 보인다.
- 브랜드 페이지는 HTTPS URL, 내부 자료는 문서 번호를 요구한다.
- 입력 즉시 생성 근거로 승격하지 않고 `unreviewed` 후보로 저장한다.
- 사람이 원문과 확인 사실, 기획 해석, 주장 제한을 대조해 `selected`로 승인해야 사용할 수 있다.
- 제품별 시험 자료가 없으면 카테고리 연구나 유사 제품 정보를 제품 효능으로 전이하지 않는다.
## 2026-07-02 - 근거 검수 완료 후 자동 기획 연결

`근거 선택 완료 → 이벤트별 InsightBrief 자동 생성 → 콘셉트 3안 자동 최신화 → 사람 선택 → 채널 카피 생성`

- 근거 큐가 `ready`가 되는 순간 별도 버튼 없이 InsightBrief와 콘셉트 3안을 갱신한다.
- 새 근거가 연결되면 과거 콘셉트 선택과 카피는 재사용하지 않는다.
- 근거가 다시 부족해지면 결과를 `evidence_review_required`로 바꾸고 선택·카피를 삭제한다.
- 추천안은 판단 보조이며 자동 선택이나 승인으로 집계하지 않는다.
- 최종 카피는 `selectionSource=human`인 콘셉트에서만 검수할 수 있다.
- 연결 확인용 선택과 평가는 품질 목표 지표에서 제외한다.

## 2026-07-05 - 대표 파일럿 선택과 근거 준비 게이트

```text
근거 계획 priority 순서로 대표 5건 선택
→ 이벤트 전용 근거 ready 확인
→ 콘셉트 3안 선택 가능
→ 사람 콘셉트 선택
→ 채널 카피 생성
→ 사람 수정·승인
```

- `limit 5`는 데이터셋의 첫 5행을 뜻하지 않는다.
- 계획에 있는 이벤트는 `priority`와 계획 파일 순서로 선택한다.
- 계획에 없는 테스트 fixture만 원래 데이터셋 순서를 사용한다.
- 콘셉트 수가 3개여도 근거가 미검수면 `evidence_review_required`다.
- 감사와 검수 패킷의 `candidate ready`는 근거 준비까지 완료된 경우만 센다.

## 2026-07-05 - 콘셉트별 근거 구성

```text
명시 이벤트 유형 확인
→ 전략 축별 핵심 근거 선택
→ 남은 검수 신호를 보조 근거로 연결
→ 핵심 1개 이상·전체 3개 확인
→ 이벤트 유형/근거 추적 비평
→ 통과한 경우만 사람 선택
```

- 문제 재정의 축은 고객 문제·구매 저항을 핵심 근거로 삼는다.
- 선택 기준 축은 제품 proof·구매 저항·욕구·시장 흐름을 핵심 근거로 삼는다.
- 계절·정체성 축은 시기 명분·욕구·시장 흐름을 핵심 근거로 삼는다.
- 다른 역할의 검수 신호는 보조 근거로만 표시한다.
- 콘솔은 내부 신호 ID를 노출하지 않고 역할·인사이트·출처를 보여준다.

## 2026-07-05 - 콘셉트 자동 비평 게이트

```text
콘셉트 3안 생성
→ 이벤트 유형·근거 이벤트 일치 검사
→ 8개 루브릭 근거 계산
→ 치명 오류: fail
→ 4점 미만 또는 경고: revise
→ fail/revise: quality_repair_required
→ 전 항목 4점·이슈 0: 사람 선택 가능
```

- 자동 점수 5점은 허용하지 않는다.
- 사람 검수 전에 약한 타깃, 제품·혜택 연결 누락, 핵심 근거 중복, 범용 CTA를
  차단한다.
- 콘셉트 단계 근거 준비는 카피 존재 여부가 아니라
  `candidateReady.evidenceReady`로 판단한다.
- 연결 확인용 검수 기록은 메인 큐의 완료 판정에도 사용하지 않는다.

## 2026-07-05 - 선택 후 카피 생성·비평 게이트

```text
사람이 콘셉트 선택
→ 요청 채널별 카피 생성
→ 화면 표시 문자열 기준 글자 수 계산
→ 사실·근거·채널 계약·반복·한국어 검사
→ 치명 오류: fail
→ 평균 4점 미만 또는 경고: revise
→ 이슈 수정 후 사람 승인
→ 수정 전후와 사유 태그 저장
```

- 각 채널 산출물은 선택 콘셉트 ID와 이벤트 전용 근거 ID를 유지한다.
- 카드뉴스 전환 문장은 다음 슬라이드 역할에 맞춰 서로 다르게 만든다.
- 로컬 모델 경로와 벤치마크 경로에서 비평 규칙을 따로 복제하지 않는다.
- 자동 비평 통과는 사람의 최종 승인을 대체하지 않는다.

## 2026-07-12 - 02단계 최종 통합 검증

```text
콘셉트 사람 승인
→ 선택 콘셉트 기반 카피 생성
→ 카피 사람 승인
→ 분리 산출물을 통합 검수 문서로 조립
→ JSON Schema + 상태 전이 + 교차 참조 검증
→ 통과 시에만 03_visual_candidates 해제
```

- 실행 전 확인 명령:
  `python scripts/validate_ad_planning_output.py --run-dir runs/<run-id>`
- 이 검증은 기존 QA 점수만 믿지 않고 선택 ID, 요청 채널, 글자 수, 텍스트
  구조, 사람 승인 기록을 다시 대조한다.
## 2026-07-18 추가: 승인된 QA 경고의 아카이브 처리

- `06_qa_packaging`의 비차단 경고는 사람이 구체 승인 메모와 함께 승인할 수 있다.
- `07_asset_archive`는 해당 승인 기록이 있을 때만 `warn` 프레임을 아카이브한다.
- 아카이브 레코드에는 `qa_status=warn`을 보존해 완전 통과 자산과 구분한다.
- `error`, `blocker`, `fail` 또는 승인 메모 없는 경고는 계속 아카이브하지 않는다.
- 전체 기계 경로 검증은 운영 런과 자산을 격리한 아래 명령으로 실행한다.

```powershell
python scripts\smoke_test_full_pipeline.py
```

- 결과: `.tmp/full-pipeline-smoke/latest-report.json`
- 이 스모크의 `smoke_test` 승인은 운영 사람 검수로 집계하지 않는다.

## 2026-07-18 추가: 브리프 입력 필요 상태

- `brief.json.open_questions`가 남으면 01단계 상태는 `needs_input`이다.
- 런 상태는 `brief_input_required`로 기록하고 이후 단계는 잠금 상태를 유지한다.
- `approve_stage`는 미해결 질문이 있는 01단계 승인을 거절한다.
- 입력 파일을 수정한 뒤 01단계를 다시 실행해 질문이 사라진 경우에만
  `review_pending / brief_review`로 돌아간다.
> 2026-07-18 UX correction: the evidence-review mission is sequential: decide one candidate → receive the next candidate → automatically enter concept selection when the required evidence set becomes ready.
## 2026-07-25 Console continuation contract

The console treats every human-facing CTA as a handoff to exactly one next decision:

```text
copy approval → reference collection → prompt confirmation → image candidates
→ candidate selection → QA review → QA approval + production package
```

- Once reference collection has at least one selected asset, the internal `03_reference_research` gate is automatically approved to unlock visual candidates.
- Refresh/resume uses stage status rather than the old URL view: approved reference work opens prompts; completed visual work opens image selection; completed selection or QA review opens the QA package.
- `06_qa_packaging=review_pending` must be acknowledged by a human. The console CTA `QA 확인 후 패키지 만들기` stores that approval and immediately generates `production-package`; warnings remain visible instead of silently blocking the operator.

## 2026-07-26 Canonical ComfyUI visual generation

Brand workflows resolve from `services/comfyui/brand_workflows.py` to the API graph in `D:\CD\jewelry_ad_project\02_workflows\api\`; do not copy the graph into individual runs. The required live path is:

```text
workflow preset -> canonical API graph -> input upload -> ComfyUI /prompt
-> /history completion -> /view download -> candidate preview + manifest write-back
```

Run long live jobs detached from the interactive console. A candidate is live only when its preview file exists and its manifest records `generation_status=generated`, `generation_mode=live`, and a ComfyUI prompt id.

### Brand personality routing

- **Jewelry:** uses the approved API graph `jewelry_product_hero_v2.api.json`. Its base instruction protects the exact metal, setting, gem count, cut, silhouette, and luxury studio treatment; no person or worn-jewelry scene is permitted in product-hero mode.
- **Cosmetics:** uses the authored `cosmetic_product_hero_v2.json` canvas as the source of a queueable runtime API graph. This keeps its skincare-specific product/label protection, clean premium studio treatment, and no-extra-bottle/no-hand restrictions instead of falling back to the generic Qwen candidate graph.
- The event's product library category chooses the route. Campaign direction is appended after the brand base prompt, so a campaign can change the mood and composition without erasing category safeguards.
