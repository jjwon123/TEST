# 워크플로우

이 프로젝트는 GPT보다 똑똑한 기획툴을 만드는 것이 아니다.

목표는 디자이너가 브랜드 이벤트 이미지를 만들 때 필요한 레퍼런스 수집, 콘텐츠 기획, 프롬프트, ComfyUI 후보 생성, 사람 선택, QA 패키징, 자산 아카이브를 한 흐름으로 관리하는 로컬 제작 콘솔이다.

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
