# 프로젝트 대시보드

## 현재 상태 업데이트 (2026-06-13, 전체 남은 작업 분석)

- 결론: 운영 콘솔·레퍼런스 판단·placeholder 제어 흐름은 정상이고, 실제 제작 자산 완료 경로는 아직 부분 준비다.
- 서비스 상태: 콘솔/ComfyUI/Ollama 정상, OpenCLIP/CUDA 사용 가능.
- 검증: pipeline health `pass`, hook check `pass`, 자동 테스트 총 24개 통과.
- 판단 데이터:
  - `meta_brand_review_001` 100/100 완료.
  - 현재 H&B 브리프 적합 레퍼런스 큐 117/117 완료.
- 신규 Qwen 경쟁사 수집:
  - 화장품 10개 브랜드 accepted image 1장.
  - 주얼리 10개 브랜드 accepted image 5장.
  - 총 6장이라 신규 100장 검수 세션은 아직 만들 수 없다.
- 최우선 남은 작업:
  1. ComfyUI live 단일 후보 생성/회수 안정화.
  2. generated 후보로 05→06→07 실제 E2E 완료 및 approved asset 1개 이상 생성.
  3. Meta 재수집 회수율 개선.
- 상세: [[PROJECT_REMAINING_STATUS_2026-06-13]]

## 현재 상태 업데이트 (2026-06-13, Meta 검수 저장 기능 점검 완료)

- `meta_brand_review/meta_brand_review_001` 사람 검수 저장을 콘솔/API에서 점검했다.
- selected / shortlist / rejected 저장, API 재조회, 브라우저 새로고침 후 판단 유지가 모두 정상이다.
- 새로고침 시 마지막 선택 세션은 유지되지 않고 기본 `reference_learning/all`로 돌아가지만, 저장된 판단은 유지된다.
- 최종 검수 완료: 100/100, selected 19 / shortlist 52 / rejected 29, accuracy 0.52.
- 최신 완료 상태로 summary/compare 생성을 다시 실행했고 모두 정상 종료했다.
- 생성 결과:
  - `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/kiwon_review_summary.md`
  - `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/correction_summary.md`
  - `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/learned_rules.json`
  - `design_brain_wiki/training_sessions/meta_brand_review/_comparisons/session-comparison.json`

### 다음 작업

1. Meta 재수집 결과로 새 검수 세션을 만들 때 동일 저장 경로를 사용한다.
2. 필요하면 새로고침 후 마지막 선택 세션을 복원하는 UX를 추가한다.

## 현재 상태 업데이트 (2026-06-13, 전체 파이프라인 감사)

- 전체 감사 기준 결론은 `placeholder E2E는 동작, live 제작은 부분 준비`다.
- 대표 run에 Meta 레퍼런스 8장을 연결했고 01~07 제어 흐름을 검증했다.
- 실패 후보 선택과 실패 QA 승인 문제를 차단했다.
- 04 재생성 시 05~07의 오래된 완료/승인 상태를 자동으로 `locked` 처리하도록 수정했다.
- 최종 `scripts/audit_full_pipeline_health.py` 결과는 `pass`다.
- Qwen/Ollama는 실제 이미지 판정까지 정상이며 시작 스크립트의 오래된 고정 경로를 제거했다.
- 최우선 보완은 ComfyUI live 성능/회수와 Qwen 기반 Meta 100장 재수집이다.
- 상세: [[FULL_PIPELINE_AUDIT_2026-06-13]]

## 현재 상태 업데이트 (2026-06-13, 경쟁사 레지스트리 Meta 재수집)

- Meta 재수집은 `assets/rules/meta-brand-registry.json`의 화장품·주얼리 경쟁사 목록을 기준으로 시작한다.
- 신규 수집 이미지는 품질 통과 후 광고 성격을 자동 분류한다.
- `promotion_text_heavy`, `card_news`, `reject_noise`는 수집 단계에서 제외한다.
- Qwen 실패 또는 미실행 이미지는 자동 선택하지 않고 `unclassified/review`로 보류한다.
- 표본 재수집:
  - 화장품 3개 브랜드: 원본 광고 6개, 광고주 일치 4개, 품질 통과 이미지 9개.
  - 주얼리 3개 브랜드: 원본 광고 4개, 광고주 일치 3개, 품질 통과 이미지 1개.
- Ollama 0.30.6과 `qwen2.5vl:7b`를 2026-06-13 복구 설치했다.
- 실제 Medicube 표본 판정에서 `promotion_text_heavy`로 분류되고 자동 제외되는 것까지 확인했다.
- 기존 표본 10장은 `--no-creative-review`로 수집한 파일이라 재분류 전까지 `needsCreativeReview` 상태다.
- 표본 폴더:
  - `references/meta_ads/brand_registry_runs/2026-06-13_competitor_cosmetics_sample`
  - `references/meta_ads/brand_registry_runs/2026-06-13_competitor_jewelry_sample`

### 다음 작업

1. 경쟁사 표본을 자동 성격 분류와 함께 재수집 또는 재분류.
2. 통과 성격만으로 신규 100장 검수 세션을 만든 뒤 실제 브리프에 연결.

## 현재 상태 업데이트 (2026-06-11, Meta 병렬 개선 완료)

- Meta 100장 출처 대조 결과 Pinterest 실제 혼입은 0장이다. Pinterest처럼 보인 이미지는 Meta의 카드뉴스·프로모션 문구형 소재였다.
- `03_reference_research` Meta provider가 성격 검수 파일을 읽도록 연결해 `promotion_text_heavy` 34장, `card_news` 10장, `reject_noise`를 기본 제외한다.
- 화장품 Meta 후보는 성격 필터 적용 전 62장에서 적용 후 18장으로 줄어든다.
- 콘솔 API 기준 `meta_brand_review_001` 사람 검수 저장 기록은 0건이므로, 선택·제외 클릭 저장 여부를 다음 검수에서 확인해야 한다.
- 코드 리뷰 후 Meta reference 중복 import, 빈 브랜드명 일치 점수, 콘솔 완료 필터·상태 탭 충돌을 수정했다.
- 브랜드 수집기는 동시 batch 충돌 방지, 브랜드별 즉시 manifest 저장, `resume`/`retry-failed`, `failed-brands.json`을 지원한다.
- `meta_brand_review_001` 100장 성격 검수 결과: 프로모션 문구형 34, 카드뉴스 10, 모델·라이프스타일 19, 주얼리 제품 16장이다.
- 화장품 62장 중 프로모션 문구형과 카드뉴스가 44장이라 clean product·brand campaign 학습 풀에서는 기본 제외하는 기준을 잡았다.
- 콘솔 판단 훈련에 브랜드, 업종, 광고주 유형, 품질, 위험 신호, 완료 여부 필터를 추가했다.
- `03_reference_research`는 Meta 브랜드 검수 후보를 브리프 기준으로 검색하며 `direct` 우선, `partner`·`review` 감점 후 기존 Pinterest 결과와 병합한다.
- 테스트 런에서 Meta 후보 62개 중 direct/standard 8개를 선택·import했고 기존 Pinterest 및 Meta reference를 유지했다.
- 레지스트리 확장 조사: 화장품 20개, 주얼리 20개 후보를 `knowledge/META_BRAND_EXPANSION_CANDIDATES.md`에 정리했다.
- 통합 검증: 수집기 테스트 5개, provider 테스트 5개, UI 계약 테스트 3개, 브라우저 상태 동기화, `project_hook_check.py` 통과.

## 현재 상태 업데이트 (2026-06-11, Meta 브랜드 검수 100장)

- Meta 브랜드 광고 원본 풀 132장 중 검수 세션 100장을 구성했다.
- 공식 광고주 `direct` 88장, 협업 광고주 `partner` 12장을 분리 표기했다.
- 화장품·스킨케어 62장, 주얼리·럭셔리 38장, 총 23개 브랜드다.
- 브랜드당 최대 20장, 한 광고당 최대 5장으로 편중을 제한했다.
- 100장 모두 이미지 파일 정상, SHA 중복 0장이다.
- 세션: `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001`
- 다음 검수 핵심: 화장품 할인 문구형 프로모션 카드를 레퍼런스로 유지할지 제외할지 판단한다.

## 현재 상태 업데이트 (2026-06-10, 레퍼런스 학습 브리프 재정리)

- 범용 1,000장 수량 목표 대신 현재 H&B 나이아신아마이드 뷰티 브리프 적합성을 우선하도록 변경했다.
- 원본 2,072개 중 브리프 기본 게이트 통과 후보는 117개다.
- 최종 후보는 Pinterest/search 59개, Meta Ad Library 58개다.
- 다른 업종, 로컬/샘플/훈련 시드, 해외 Meta 광고, 저해상도, 웹 캡처, 명백한 다른 카테고리를 기본 제외한다.
- 기준 문서: `knowledge/REFERENCE_LEARNING_BRIEF.md`

## 현재 상태 업데이트 (2026-06-10, Meta 검증 브랜드 레지스트리)

- 화장품·스킨케어 20개, 주얼리·럭셔리 20개 브랜드 레지스트리를 추가했다.
- 브랜드 검색 결과 중 광고주명이 등록 별칭과 일치한 광고만 별도 저장한다.
- 콘솔 Meta 광고 수집 화면에서 업종별 브랜드 묶음을 1~30개 소량 수집할 수 있다.
- Medicube 테스트: 원본 광고 3개 → 광고주 일치 1개 → 이미지 7개.
- Cartier 테스트: 원본 광고 3개 → 광고주 일치 2개 → 허용 이미지 1개.
- 상세: `knowledge/META_BRAND_REGISTRY.md`

이 문서는 Obsidian에서 가장 먼저 보는 현재 상태판이다. 자세한 기준은 각 문서에 두고, 여기에는 자주 열어야 하는 링크와 최근 업데이트 포인트만 남긴다.

## 핵심 기준

- [[01_PROJECT_GOAL]]: 프로젝트 목표와 범위
- [[02_WORKFLOW]]: 1~7단계 실행 흐름
- [[03_BRAND_GUIDE]]: 브랜드 기준 작성/적용 원칙
- [[04_PROMPT_RULE]]: 텍스트/이미지 프롬프트 작성 기준
- [[10_PROJECT_SUMMARY]]: 전체 프로젝트 구조와 AI 구성 요약
- [[CONSOLE_UI_HANDOFF]]: 콘솔 UI 현재 상태와 다음 작업
- [[REFERENCE_LEARNING_1000]]: 1,000장 레퍼런스 학습 데이터셋과 검수 운영 기준

## 현재 상태 업데이트 (2026-06-08, Reference Learning 1000)

- Pinterest/search 18개 검색군에서 신규 이미지 484장을 수집했다.
- 레퍼런스 원본 2,072개를 인덱싱하고 정확 중복 804개, 근접 중복 49개를 검수 큐에서 제외했다.
- 최종 검수 가능한 고유 이미지 1,219장으로 1,000장 목표를 달성했다.
- 기존 검수 완료 198장, 새 검수 큐 1,021장을 50장 단위 21개 배치로 생성했다.
- 각 배치는 Pinterest, Meta, 업종 profile이 가능한 한 섞이도록 라운드로빈 구성했다.
- 콘솔 판단 훈련 상단에서 목표 달성, 중복 제거, 검수 진행률, 다음 미검수 배치를 확인할 수 있다.

## 운영 기록

- [[07_DECISIONS]]: 중요한 결정과 이유
- [[06_TROUBLESHOOTING]]: 실패 사례와 해결법
- [[05_MODEL_TEST]]: LM Studio, 이미지 모델, 워크플로 테스트
- [[08_COMFYUI_NOTES]]: ComfyUI 운영 메모

## 자동 업데이트 원칙

Codex/OpenCode 작업 후 프로젝트 기준에 영향을 주는 내용만 `knowledge/`에 반영한다.

업데이트 대상:

- 새 결정
- 새 기준
- 반복될 가능성이 있는 실패와 해결법
- 모델/ComfyUI 테스트 결과
- 워크플로 구조 변경
- 사람이 다음 작업에서 반드시 알아야 하는 맥락

업데이트하지 않는 대상:

- 단순 실행 로그
- 일회성 중간 산출물
- 임시 파일
- 후보 이미지 전체 목록
- run 폴더에 이미 보관되는 세부 결과

## 기록 위치 빠른 판단

```text
결정의 이유              -> 07_DECISIONS.md
브랜드/디자인 기준       -> 03_BRAND_GUIDE.md
프롬프트 규칙            -> 04_PROMPT_RULE.md
단계 흐름 변경           -> 02_WORKFLOW.md
에러/실패/해결법         -> 06_TROUBLESHOOTING.md
모델 테스트              -> 05_MODEL_TEST.md
ComfyUI 노드/워크플로    -> 08_COMFYUI_NOTES.md
실행 결과 원본           -> runs/
이벤트 입력 원본         -> events/
승인 자산                -> assets/
```

## 현재 상태 업데이트 (2026-05-25)

- 04_admin_selection 최소 구현 완료: 콘솔/CLI 선택값을 `04_admin_selection/selected-assets.json`과 `selection-notes.md`로 확정한다.
- `selected-assets.json` 구조 확정: `eventId`, `selectedAssets[]`, `regenerationRequests[]`, `summary`, `approvalStatus`.
- 04 완료 시 run 상태는 `qa_pending`, 현재 단계는 `06_qa_packaging`으로 넘어간다.
- 06_qa_packaging은 Figma 산출물이 없어도 `selected-assets.json` 기반의 최소 QA/패키지 매니페스트를 받을 수 있도록 연결 준비 완료.
- 최신 테스트 런에서 04 → 06 → `production-package` 생성까지 확인 완료.
- 아직 제외: ComfyUI 실생성 연결, 제품 합성, 영상 생성.

## 현재 상태 업데이트 (2026-05-25, 외부 워크플로 연결 후)

- `D:\CD\jewelry_ad_project\02_workflows`의 cosmetics/jewelry/bullion 워크플로를 ComfyUI 레지스트리에 연결.
- 03 후보 생성 시 제품 카테고리별 workflow 자동 매핑 준비 완료.
- hsgn cosmetic 최신 런에서 03→04→06→07 스모크 테스트 완료.
- 최종 패키지 화면은 파일 목록 대신 선택 후보 카드/이미지 미리보기/프롬프트 펼쳐보기를 보여주도록 개선.
- 남은 핵심: live ComfyUI 생성 안정화, 제품 합성/텍스트 오버레이 후처리, 이벤트/레퍼런스/프롬프트 품질 장기 검수.

## 현재 상태 업데이트 (2026-05-27, MVP 단계 기준 정리)

- 프로젝트 포지션을 "GPT보다 똑똑한 기획툴"이 아니라 "브랜드 이벤트 이미지 제작용 로컬 콘솔"로 재정의.
- 기준 단계명을 `01_event_brief → 02_content_planning → 03_reference_research → 04_visual_candidates → 05_admin_selection → 06_qa_packaging → 07_asset_archive`로 정리.
- `03_reference_research` stage 추가: 기본은 레퍼런스 검색 계획/요약, `REFERENCE_RESEARCH_MODE=auto_search`일 때 자동 검색/선정 실행.
- 기존 산출물 호환을 위해 물리 폴더 `03_visual_candidates`, `04_admin_selection`은 유지.
- workflow alias 추가: 기존 `03_visual_candidates`, `04_admin_selection` 명령은 각각 새 `04_visual_candidates`, `05_admin_selection`으로 매핑.

## 현재 상태 업데이트 (2026-05-27, ComfyUI live 생성 검증)

- 테스트 런 `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`에서 `instagram_cardnews_01__key_visual` 그룹 live 생성 성공.
- `qwen_candidate_2511` 후보 3장 생성/회수 완료: 1024x1024 PNG, `generation_status=generated`.
- `generation-quality.json` 추가: 후보별 live/placeholder 여부, 생성 에러, 파일 정보, ComfyUI prompt id, `reference_direction` 반영 체크를 기록한다.
- `product_input.png` fallback 오류와 과한 qwen 샘플링 기본값을 수정.
- 품질상 다음 과제는 baked-in 깨진 텍스트 억제와 bullion/gold 카테고리 고정.

## 현재 상태 업데이트 (2026-05-28, reference 품질 필터 강화)

- 금/은/투자/상담 이벤트를 `bullion_investment` profile로 감지해 레퍼런스 검색어와 선정 기준을 강화.
- 검색어가 프리미엄 금 투자/금융 상담/골드바/자산관리 캠페인 중심으로 생성되도록 수정.
- `reference-quality-filter.json` 기준 추가: `brandFit`, `eventFit`, `seriousnessFit`, `productRelevance`, `riskLevel`.
- kids/toy/kawaii/camping/theme park/picnic/wine/random package/fake text 방향은 금 투자 이벤트에서 reject 또는 shortlist 처리.
- 이미지 프롬프트에는 `blank space for Korean headline`, `no readable text`, `no fake typography`를 기본 포함.
- live 생성 전 `scripts/audit_visual_prompts.py`로 prompt audit을 생성한다.
- 테스트 런 prompt audit 결과: total 15, passed 15, warning 0, failed 0.

## 다음 할 일

1. audit 통과 프롬프트 기준으로 1~3장 live 테스트
2. 강화된 reference 기준으로 auto_search 재실행
3. 콘솔 선택 화면에 `generation-quality.json`/`reference-quality-filter.json`/`prompt-audit.json` 품질 상태 노출
4. 제품 합성/텍스트 오버레이 후처리 품질 검수
5. 이미지 평가 기준 체크리스트 정리

→ 상세: [[09_HANDOFF]]
## 현재 상태 업데이트 (2026-05-28, 브랜드/이벤트별 레퍼런스 룰 구조화)

- 이미지 생성 추가 테스트를 중단하고 기준 데이터 오염 제거를 우선순위로 전환.
- `assets/rules/brand-persona.json`, `event-rules.json`, `reference-rules.json`, `visual-avoid-rules.json`, `tone-rules.md` 생성.
- `bullion_investment` 허용 방향: premium gold investment, financial consultation, wealth management, luxury product photography, gold bar/coin/bullion, calm trust, minimal poster layout, dark navy/gold/white, blank Korean headline area.
- `bullion_investment` 금지 방향: mascot/cute/toy/kawaii/character/camping/picnic/theme park/wine bottle/package box/fake text/unreadable typography/childish 3d/game-like UI.
- 실패 live 후보 3장을 `assets/reference_training/bullion_investment/bad/`에 저장하고 bad tags를 기록.
- `03_reference_research`가 룰 파일을 읽어 `search_queries`, `qualityFilter`, `referenceDecisions`, `promptHints`, `negativePromptHints`에 반영하도록 수정.
- `03_visual_candidates`에서 bullion fallback이 `qwen_image_edit_1024.png`로 흐르지 않도록 neutral bullion 샘플 입력 이미지로 분기.

## 다음 할 일

1. `REFERENCE_RESEARCH_MODE=auto_search`로 룰 기반 selected/shortlist/rejected 분포 확인
2. good reference를 `assets/reference_training/bullion_investment/good/`에 직접 추가
3. selected reference가 안정된 뒤 04_visual_candidates placeholder audit -> 소량 live 테스트 순서로 재개

## 현재 상태 업데이트 (2026-05-30, bullion_investment good seed 및 03 품질 리포트)

- `assets/reference_training/bullion_investment/good/`에 good reference seed 10장 저장.
- `assets/reference_training/bullion_investment/good/metadata.json` 작성: filename, tags, whyGood, usefulFor 구조.
- `core/utils/reference_training.py` 추가: good/bad seed metadata를 읽고 candidate의 goodScore/badScore/scoreDelta를 계산.
- `scripts/reference_pipeline.py`가 `bullion_investment` selection gate에서 `training_alignment`를 반영.
- `03_reference_research`가 `reference-quality-report.json/md`를 생성하도록 확장.
- 검증 run: `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`.
- 결과: selected 8, rejected 5, selected bad signal 0, fallback clean true, status pass.
- bad seed 3장은 모두 rejected.

## 다음 할 일

1. good seed에 실제 캠페인/포스터형 reference를 추가해 product-only 편향 보완
2. 03 report pass 상태 유지 확인
3. 그 다음 04_visual_candidates는 placeholder/prompt audit부터 재개
4. live ComfyUI는 마지막에 1~3장만 소량 테스트

## 현재 상태 업데이트 (2026-05-30, good seed 2차 보강 완료)

- good seed를 30장으로 확장:
  - `product_reference`: 10장
  - `finance_mood_reference`: 10장
  - `poster_layout_reference`: 10장
- `metadata.json`에 `category`, `tags`, `whyGood`, `usefulFor` 구조 반영.
- `reference-quality-report`에 `goodSeedCoverage`, `selectedCategoryCoverage`, `selectedCoverage` 추가.
- selector가 good seed category를 round-robin으로 섞어 product-only 편향을 줄이도록 수정.
- 검증 결과:
  - status: pass
  - selected: 12
  - selected bad signal: 0
  - fallback clean: true
  - selected category coverage: product 4 / finance mood 4 / poster layout 4
  - selected role coverage: product_identity 8 / mood 8 / composition 12 / lighting 8 / headline_space 8
- ComfyUI live 생성은 여전히 중단 상태.

## 다음 할 일

1. `reference-quality-report` pass 상태에서 04_visual_candidates를 placeholder로만 생성
2. `prompt-audit`로 fake text/character/cute/camping 계열 차단 확인
3. 사람이 selected reference 방향을 확인한 뒤 live ComfyUI 소량 테스트
## 현재 상태 업데이트 (2026-05-30, Senior Designer Brain Wiki 1차 구축)

- 프로젝트 1차 목표를 "이미지 생성기"가 아니라 "브랜드/이벤트/레퍼런스를 판단하는 시니어 디자이너 에이전트"로 재정의.
- `design_brain_wiki/` 생성 완료.
- 생성된 축:
  - `01_design_principles`
  - `02_brand_strategy`
  - `03_reference_judgement`
  - `04_channel_usability`
  - `05_industry_playbooks`
  - `06_case_studies`
  - `07_my_taste_dataset`
  - `08_feedback_language`
  - `99_sources`
- 공식/신뢰 출처 기반으로 Design Council, IDEO, NN/g, Apple HIG, Material Design, IBM Carbon, Pentagram, COLLINS, Wolff Olins, Landor, Interbrand 기준을 AI 판단 질문/평가 항목/피드백 문장으로 변환.
- 공통 judge schema와 rubric 추가:
  - `design_brain_wiki/00_JUDGE_SCHEMA.md`
  - `design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json`
- ComfyUI는 계속 downstream 실행 단계로 유지. 지금 우선순위는 위키 기준을 Reference Judge/03_reference_research에 연결하는 것.

## 다음 작업

1. `03_reference_research`가 `design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json`과 관련 MD 기준을 읽도록 연결.
2. `reference-quality-report`에 senior designer feedback 문장과 wiki rule source를 기록.
3. 기원님이 직접 고른 good/bad/shortlist 판단을 `design_brain_wiki/07_my_taste_dataset`과 `assets/reference_training`에 누적.
4. 위키 기준 통과 후에만 04_visual_candidates placeholder/prompt audit로 이동.
## 현재 상태 업데이트 (2026-05-31, Wiki Judge 샘플 테스트 구축)

- `design_brain_wiki` 품질 검증용 샘플 테스트 세트 생성.
- 테스트 대상 3개 업종:
  - `bullion_investment`
  - `cosmetics_skincare`
  - `jewelry_luxury`
- 각 업종마다 good / bad / ambiguous 후보를 섞어 selected / shortlist / rejected 판단을 검증.
- 생성 파일:
  - `design_brain_wiki/tests/README.md`
  - `design_brain_wiki/tests/reference_judge_sample_set.json`
  - `scripts/run_reference_judge_wiki_tests.py`
  - `design_brain_wiki/tests/output/reference-judge-test-report.json`
  - `design_brain_wiki/tests/output/reference-judge-test-report.md`
- 최신 실행 결과:
  - total: 18
  - accuracy: 1.0
  - feedback depth rate: 1.0
  - status: pass

## 다음 작업

1. 이 evaluator를 `03_reference_research/reference-quality-report`에 연결.
2. 실제 collected reference 20장에 대해 wiki source, decision reason, senior designer feedback을 남기기.
3. 테스트 실패 시 전체 위키를 늘리지 말고 부족한 문서만 보강.
## 현재 상태 업데이트 (2026-05-31, Senior Designer Brain Wiki v0.2 확장)

- 정정: 현재 위키는 완성본이 아니라 `v0.1 골격 + 1차 테스트 세트`다.
- v0.2 확장 작업 추가:
  - studio case bank 50개 생성.
  - Pentagram 10 / COLLINS 10 / Wolff Olins 10 / Landor 10 / Interbrand 10.
  - 핵심 3개 업종 deep playbook 생성:
    - `bullion_investment`
    - `cosmetics_skincare`
    - `jewelry_luxury`
  - `industry_boundary_matrix` 추가.
  - 기원님 피드백 100개 누적 bank 추가.
  - good/bad/shortlist 레퍼런스 300장 성장 계획 추가.
- 현재 파일 수: `design_brain_wiki` 73개.
- 현재 case bank 수: 50개.

## 다음 작업

1. 기원님 실제 피드백 문장을 `kiwon_feedback_bank_100.md`에 채우기.
2. 실제 레퍼런스 이미지를 업종별 100장씩 good/shortlist/bad로 분류.
3. `03_reference_research`가 case bank/deep playbook을 근거로 피드백을 남기게 연결.
4. 실제 collected reference 100-300장 검증으로 v0.3 이동.
## 현재 상태 업데이트 (2026-05-31, bullion_investment 판단 훈련 세션 001)

- `bullion_investment` 실제 reference training seed 기반 30장 판단 훈련 세션 생성.
- 위치: `design_brain_wiki/training_sessions/bullion_investment/session_001/`
- 생성 파일:
  - `references/` 30장
  - `ai_judgement.json`
  - `ai_judgement.md`
  - `kiwon_review_template.md`
  - `correction_log.md`
  - `wiki_update_suggestions.md`
  - `README.md`
- 판단 방식: 로컬 Qwen/Ollama 비전 모델 호출 없음. 기존 seed metadata + design_brain_wiki 기준 기반 1차 판단.
- 결과:
  - total: 30
  - selected: 7
  - shortlist: 20
  - rejected: 3
- 주의: 초기 생성에서 `no fake text`, `no character` 태그를 위험 신호로 오독하는 문제가 있어 `scripts/create_bullion_training_session.py`에서 `no ...` 태그를 risk detection에서 제외하도록 수정 후 재생성.

## 다음 작업

1. 기원님이 `kiwon_review_template.md`에 agree/disagree/unsure와 교정 이유 입력.
2. `correction_log.md`에 과승인/과거절/추상 피드백 패턴 기록.
3. `wiki_update_suggestions.md` 기반으로 bullion playbook, feedback phrase, reference judge rubric 수정.
4. 이후 같은 방식으로 session_002를 실제 외부 수집 reference 30장으로 진행.
## 현재 상태 업데이트 (2026-05-31, 판단 훈련 UI 추가)

- 로컬 콘솔 `http://127.0.0.1:5177`에 `판단 훈련` 탭 추가.
- 목적: 기원님이 `kiwon_review_template.md`를 직접 편집하지 않고, 웹 화면에서 이미지와 AI 판단을 보며 교정 입력.
- 추가 API:
  - `GET /api/training-sessions`
  - `GET /api/training-sessions/<profile>/<session_id>`
  - `POST /api/training-sessions/<profile>/<session_id>/review`
  - `GET /training-assets/<profile>/<session_id>/<filename>`
- 저장 파일:
  - `kiwon_review_state.json`
  - `kiwon_review_summary.md`
- 화면 기능:
  - 30장 리스트 보기.
  - 이미지 미리보기.
  - AI decision/confidence/reason/usableElements/riskSignals/wikiSources 확인.
  - `맞음 / 틀림 / 애매` 선택.
  - `correctDecision`, `kiwonReason`, `ruleToUpdate` 저장.
- 검증:
  - `python -m py_compile scripts/console_server.py scripts/create_bullion_training_session.py` 통과.
  - `node --check ui/console/app.js` 통과.
  - `/api/bootstrap`에서 training session 1개 확인.
  - `session_001` 상세 30개 항목 확인.
## 현재 상태 업데이트 (2026-05-31, Reference Review Progress 정리)

- 현재 1차 목표는 이미지 생성이 아니라 `Senior Designer Brain Wiki -> Reference Judge -> Direction Director` 구축이다.
- ComfyUI live 생성은 보류 상태다. 레퍼런스 판단 기준과 기원님 교정 데이터가 쌓인 뒤 다시 연결한다.
- `design_brain_wiki/` v0.2 초안은 구축됨:
  - studio case bank 50개
  - bullion/cosmetics/jewelry deep playbook
  - reference judge rubric/schema
  - 샘플 judge test 18개 pass
- 단, 위키는 완성본이 아니라 `골격 + 1차 테스트 + v0.2 자료 확장` 상태다.
- 판단 훈련 UI가 로컬 콘솔 `http://127.0.0.1:5177`에 추가됨.
- 중요 정정:
  - `design_brain_wiki/training_sessions/bullion_investment/session_001/`은 실제 Pinterest 레퍼런스 세션이 아니다.
  - 기존 `assets/reference_training/bullion_investment/good|bad` seed 이미지를 가져온 seed test 세션이다.
  - 다음에는 seed test와 실제 Pinterest/search reference review 세션을 분리해야 한다.

## 다음 작업

1. `session_001`을 seed test로 명확히 라벨링.
2. 기존 run의 `references/candidates` 또는 새 수집 결과에서 실제 레퍼런스 30장을 가져와 `pinterest_session_001` 생성.
3. 콘솔 판단 훈련 UI에서 seed session / real reference session을 구분 표시.
4. 실제 레퍼런스 세션에서 selected / shortlist / rejected, confidence, 이유, 위험 요소, wiki 기준, seniorDesignerFeedback 생성.
5. 기원님 교정 입력을 받아 correction log와 wiki update suggestions로 누적.
## 현재 상태 업데이트 (2026-05-31, Pinterest 실제 레퍼런스 세션 분리 완료)

- 문제 정정: `session_001`은 Pinterest 세션이 아니라 seed test였으므로 `sessionType: seed_test`로 라벨링.
- `03_reference_research` auto_search를 `.venv` Python으로 재실행해 실제 Pinterest 검색 결과를 수집.
- 수집 확인:
  - 검색 URL: `https://kr.pinterest.com/search/pins/?q=...`
  - 이미지 URL: `i.pinimg.com`
  - pin URL: `https://kr.pinterest.com/pin/...`
- `scripts/reference_pipeline.py` 수정: Pinterest collector의 `metadata.jsonl`에서 `pin_url`, `image_url`, `downloaded_url`, `sha256`를 선정 후보까지 보존.
- `scripts/create_bullion_training_session.py` 수정: seed 폴더뿐 아니라 run의 실제 `reference-quality-filter.json`에서 30장 세션을 만들 수 있음.
- 생성 세션:
  - `design_brain_wiki/training_sessions/bullion_investment/pinterest_session_001/`
  - total 30
  - selected 4 / shortlist 5 / rejected 21
  - 30장 모두 `sourceIsPinterest: true`
- 콘솔 판단 훈련 UI에서 session type과 Pinterest pin 링크를 표시하도록 수정.

## 다음 작업

1. 기원님이 `bullion_investment/pinterest_session_001`을 콘솔에서 리뷰.
2. selected 4장이 너무 적은지, rejected 21장이 너무 엄격한지 교정 로그로 확인.
3. 다음 세션은 query_limit/per_query_limit을 늘리거나 직접 curated board URL을 넣어 selected 후보 품질을 높인다.
## 현재 상태 업데이트 (2026-05-31, 한국어 Pinterest 검색 + 빠른 비교 판정 UI)

- `bullion_investment` Pinterest 검색어를 한국어 우선으로 교체.
  - 예: `한국 금 투자 상담 카드뉴스 디자인`, `한국 금거래소 이벤트 배너 디자인`, `실물 금 투자 상담 인스타 카드뉴스`, `금 시세 상담 카드뉴스 디자인`.
  - 영문 쿼리는 한국 레퍼런스가 부족할 때 쓰는 보조 쿼리로 뒤쪽에만 유지.
- 새 실제 수집 세션 생성:
  - `design_brain_wiki/training_sessions/bullion_investment/pinterest_kr_session_001/`
  - total 30
  - selected 10 / shortlist 10 / rejected 10
  - 30장 모두 Pinterest/search 출처.
- 판단 훈련 UI 개선:
  - 두 장을 동시에 보여주는 `빠른 비교 판정` 패널 추가.
  - `왼쪽 좋음`, `오른쪽 좋음`, `둘 다 후보`, `둘 다 제외`, `건너뛰기`로 바로 저장 후 다음 쌍으로 이동.
  - 세션 순서는 selected/shortlist/rejected가 섞여 나오도록 조정.

## 다음 작업

1. 콘솔 `판단 훈련`에서 `bullion_investment/pinterest_kr_session_001`을 빠른 비교 방식으로 리뷰.
2. 한국어 검색이어도 외국 자료가 섞이는 항목을 `rejected`로 빠르게 교정.
3. 교정 결과에서 반복되는 부족 기준을 bullion playbook과 reference judge rubric에 반영.
## 현재 상태 업데이트 (2026-06-03, pinterest_kr_session_001 교정 요약 생성)

- `pinterest_kr_session_001` 리뷰 결과를 분석해 `correction_summary.md` 생성.
- 위치: `design_brain_wiki/training_sessions/bullion_investment/pinterest_kr_session_001/correction_summary.md`
- 핵심 결과:
  - 전체 일치율: 11/30, 36.7%.
  - AI selected 일치율: 2/10, 20.0%.
  - AI shortlist 일치율: 0/10, 0.0%.
  - AI rejected 일치율: 9/10, 90.0%.
  - 기원님 최종 판단: selected 5 / shortlist 0 / rejected 25.
- 주요 결론: AI가 한국어 검색어 적합성과 `부분 참고` 신호를 selected/shortlist 근거로 과대평가했다.

## 다음 작업

1. `bullion_investment_v0_2.md`에 한국형 금거래소/금투자 카드뉴스 selected/rejected 기준 추가.
2. `REFERENCE_JUDGE_RUBRIC.json`에 role coverage, searchQueryFit 분리, partial reference selected 금지 기준 반영.
3. feedback phrase 문장을 `부분 참고` 같은 추상 표현 대신 구체 근거형 문장으로 보강.
## 현재 상태 업데이트 (2026-06-03, 화장품 여름 H&B 세일 이벤트 브리프/기획 생성)

- 새 이벤트 생성: `events/summer-hb-beauty-sale-hsgn/`
- 이벤트명: `여름 H&B 뷰티 세일 나이아신아마이드 집중 케어`
- 방향: 올영세일 직접 모방이 아니라 한국 H&B 스토어 대형 세일 감성, 여름 스킨케어, 혜택/증정/할인 중심.
- 금지어에 `올리브영`, `올영`을 넣어 직접 브랜드 모방을 차단.
- 생성 run: `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어/`
- 01_event_brief:
  - 최초 생성 후 skincare 카테고리 리스크에서 타깃 정의가 인구통계 중심이라는 blocking 감지.
  - 타깃을 피부 고민/구매 상황/정보 탐색 채널 기준으로 보강.
  - 재생성 후 Category risk `clear`, blocking false.
  - 01 승인 완료.
- 02_content_planning:
  - deliverables 5개 생성.
  - image needs 5개.
  - quality status `approval_ready`.
  - 현재 02는 `review_pending`.

## 다음 작업

1. 02_content_planning 승인.
2. `cosmetics_skincare`용 한국어 Pinterest 검색 기준 확인/보강.
3. 03_reference_research 실행 후 화장품 판단 훈련 세션 생성.

## 현재 상태 업데이트 (2026-06-03, 화장품 Pinterest 레퍼런스 100장 수집)

- `cosmetics_skincare` 프로필을 rulebook에 추가하고 한국어/H&B/스킨케어 세일 중심 검색어를 우선 사용하도록 보강.
- `bullion_investment` 오탐을 줄이기 위해 단일 글자 `금`, `은` 및 일반 `상담` 키워드 감지를 제거하고 더 구체적인 금 투자 키워드로 교체.
- 화장품 여름 H&B 세일 run에서 02_content_planning 승인 완료.
- 03_reference_research를 `auto_search`로 재실행해 Pinterest/search 레퍼런스 100장을 선택.
- 현재 run 상태:
  - run: `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어/`
  - status: `reference_ready`
  - current_stage: `04_visual_candidates`
  - selected references: 100
- 콘솔 서버 확인: `http://127.0.0.1:5177`

## 다음 작업

1. 100장 중 실제 한국 H&B 세일 감성에 맞는지 빠른 리뷰.
2. 화장품용 판단 훈련 세션을 만들고 selected/shortlist/rejected 교정 기록 수집.
3. 통과한 레퍼런스를 기준으로 04_visual_candidates를 진행.

## 현재 상태 업데이트 (2026-06-03, 화장품 판단 훈련 세션 생성)

- 사용자가 `수집 + Qwen 검수`를 작은 값으로 한 번 실행해 최신 reference manifest가 1장으로 덮인 상태를 확인.
- 03_reference_research를 다시 100장 설정으로 복구 실행.
  - `REFERENCE_QUERY_LIMIT=8`
  - `REFERENCE_PER_QUERY_LIMIT=20`
  - `REFERENCE_SELECT_COUNT=100`
- 선택 레퍼런스 폴더 100장 복구 확인.
- 새 범용 세션 생성 스크립트 추가:
  - `scripts/create_reference_training_session.py`
- 생성 세션:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_session_001/`
  - total 30
  - selected 10 / shortlist 17 / rejected 3
  - source run: `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- 콘솔 `/api/training-sessions`에서 세션 노출 확인.
- 이후 운영 기준을 수정: 레퍼런스 검수는 계속 판단 훈련 데이터가 되어야 하므로, 화장품 세션을 30장 샘플이 아니라 전체 100장으로 재생성.
  - total 100
  - selected 41 / shortlist 56 / rejected 3

## 다음 작업

1. 콘솔 `판단 훈련`에서 `cosmetics_skincare/pinterest_session_001` 선택.
2. 빠른 비교 판정으로 100장 교정.
3. 교정 완료 후 correction_summary 생성 및 cosmetics playbook/rubric 업데이트.

## 현재 상태 업데이트 (2026-06-03, 화장품 100장 교육 테스트)

- `cosmetics_skincare/pinterest_session_001` 100장 리뷰 완료 확인.
- baseline AI 판단 일치율:
  - overall 15/100, 15.0%
  - AI selected match 9/41, 22.0%
  - AI shortlist match 5/56, 8.9%
  - AI rejected match 1/3, 33.3%
- 기원님 최종 분포:
  - selected 29
  - shortlist 12
  - rejected 59
- 생성 파일:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_session_001/correction_summary.md`
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_session_001/learned_replay_test.md`
- 반영 파일:
  - `design_brain_wiki/05_industry_playbooks/deep/cosmetics_skincare_v0_2.md`
  - `design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json`
- 결론:
  - 같은 100장에 대해서는 기원님 리뷰를 적용해 replay 100% 가능.
  - 새 이미지 generalization은 아직 미검증.
  - 메타데이터/검색어/기본 점수만으로는 기원님 판단을 잘 분리하지 못함.

## 다음 작업

1. 새 화장품 holdout reference 30-50장을 수집해 업데이트된 기준으로 재판정.
2. 빠른 비교 UI에 제외/선택 사유 태그를 추가해 더 구체적인 학습 신호 수집.
3. 가능하면 Qwen/비전 모델에서 `localHBSaleFit`, `benefitHierarchy`, `productTrust`, `foreignSaleRisk`를 이미지 기반으로 평가하게 연결.

## 현재 상태 업데이트 (2026-06-03, 검색어/메타데이터 evidence 분리)

- 화장품 Pinterest 검색어를 단순 쿼리로 교체.
  - 예: `스킨케어 이벤트 배너`, `화장품 이벤트 배너`, `뷰티 이벤트 배너`, `스킨케어 배너 디자인`, `화장품 카드뉴스 디자인`.
- `scripts/reference_pipeline.py` 수정:
  - `text_relevance_score`가 검색어, 파일명, path를 판단 evidence로 쓰지 않도록 변경.
  - Pinterest title/alt/description/grid title/SEO title 같은 source metadata만 relevance evidence로 사용.
  - `text_relevance_reason`에 `query_ignored=true` 기록.
- `scripts/create_reference_training_session.py` 수정:
  - `record_text()`에서 `query`, `source_id`, `asset_id`, `path`, `relative_path`, `text_relevance_reason` 제외.
  - title/alt/description/Qwen review/기원님 피드백만 판단 evidence로 사용.
- `pipeline/03_reference_research` 수정:
  - `기능성` 안의 단일 글자 `금` 때문에 bullion 방향이 섞이던 오탐 제거.
  - reference direction은 감지된 event profile을 기준으로 구성.
- 새 holdout run 생성:
  - `runs/2026-06-02_16-44-06_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- 새 holdout 세션 생성:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_001/`
  - total 47
  - selected 0 / shortlist 23 / rejected 24

## 다음 작업

1. `cosmetics_skincare/pinterest_holdout_001`을 판단 훈련에서 리뷰.
2. selected 0이 너무 보수적인지, shortlist/rejected 경계가 맞는지 확인.
3. 리뷰 결과로 second correction summary 생성 후 gate를 다시 보정.

## 현재 상태 업데이트 (2026-06-03, holdout 리뷰 결과와 저해상도 게이트)

- `cosmetics_skincare/pinterest_holdout_001` 리뷰 완료.
- 쿼리/path evidence 제거 후 holdout 정확도:
  - 22/47, 46.8%
  - 이전 baseline 15.0% 대비 개선.
- 기원님 최종 분포:
  - selected 14
  - shortlist 20
  - rejected 13
- AI 초안 분포:
  - selected 0
  - shortlist 23
  - rejected 24
- 결론:
  - query leakage 제거는 효과가 있음.
  - 현재 judge는 과승인에서 과보수로 이동했으므로 selected gate 재조정 필요.
- 생성 파일:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_001/correction_summary.md`
- 저해상도/화질 깨짐 이슈 확인:
  - selected reference pool에 60x60 썸네일이 여러 장 유입됨.
  - `scripts/reference_pipeline.py`에 `reference_quality_defects()` 추가.
  - width 또는 height가 300px 미만이면 `low_resolution` 사유로 자동 rejected.

## 다음 작업

1. low-resolution gate 적용 후 새 holdout 30-50장을 다시 수집.
2. selected gate를 열어 기원님 selected 14개 패턴을 반영.
3. 필요하면 판단 훈련 UI에 `화질 깨짐`, `로컬감 부족`, `제품 약함`, `혜택 구조 좋음` 같은 사유 태그 버튼 추가.

## 현재 상태 업데이트 (2026-06-03, holdout 002 재수집)

- selected gate에 화장품 이벤트 레이아웃 단서 추가:
  - `광고`, `배너`, `프로모션`, `사은품`, `이벤트 페이지`, `gift`, `banner`.
- low-resolution gate 버그 수정:
  - 기존에는 dimension을 점수용 `numeric_score()`로 읽어 563px도 100으로 잘리는 문제가 있었음.
  - `numeric_value()`를 추가해 실제 픽셀 값으로 판단하도록 수정.
- 새 holdout run:
  - `runs/2026-06-02_16-59-22_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- 03_reference_research 결과:
  - selected references: 36
  - accepted/shortlist/rejected: 48/0/12
  - selected 중 low-res: 0
  - rejected low-res: 11
- 새 판단 세션:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_002/`
  - total 36
  - AI first pass: selected 2 / shortlist 21 / rejected 13

## 다음 작업

1. 콘솔 판단 훈련에서 `cosmetics_skincare/pinterest_holdout_002` 리뷰.
2. holdout 001 정확도 46.8% 대비 개선 여부 계산.
3. selected gate가 아직 보수적인지 또는 다시 과승인되는지 확인.

## 현재 상태 업데이트 (2026-06-03, holdout 002 리뷰와 중복/홈페이지 캡쳐 보정)

- `cosmetics_skincare/pinterest_holdout_002` 리뷰 완료.
- 정확도:
  - 19/36, 52.8%
  - holdout 001의 46.8% 대비 소폭 개선.
- 기원님 최종 분포:
  - selected 2
  - shortlist 31
  - rejected 3
- AI 초안 분포:
  - selected 2
  - shortlist 21
  - rejected 13
- 주요 오차:
  - rejected -> shortlist 11건으로 여전히 너무 엄격한 제외가 많음.
  - selected -> rejected 1건으로 홈페이지 캡쳐/상단 URL 노출 같은 위험 이미지가 selected로 들어갈 수 있음.
- 보정:
  - `visual-avoid-rules.json`에 website/browser screenshot, visible URL bar, homepage capture 계열 reject/avoid/negative hint 추가.
  - `create_reference_training_session.py`에 `--exclude-profile-history` 옵션 추가. 새 holdout 생성 시 같은 업종의 이전 세션 이미지 해시를 제외할 수 있음.
- 중복 확인:
  - 동일 run의 selected 36장 안에서는 중복 해시 0건.
  - `pinterest_session_001`, `pinterest_holdout_001`, `pinterest_holdout_002`를 합치면 중복 그룹 35개, 중복 아이템 81개.
  - 원인은 같은 브리프를 1/2/3차로 반복 실행하면서 비슷한 Pinterest 쿼리를 다시 사용한 영향으로 판단.

## 다음 작업

1. 다음 holdout은 `--exclude-profile-history`로 이전 세션 중복을 제외하고 생성.
2. 홈페이지 캡쳐/상단 URL/브라우저 화면 이미지는 selected 금지 기준으로 계속 검수.
3. rejected -> shortlist 오판 11건을 기준으로 화장품 이벤트 shortlist gate를 더 완화.

## 다음 테스트 인수인계 (2026-06-03)

- 다음 단계는 `cosmetics_skincare` 새 generalization holdout 30-50장 테스트.
- 새 세션명 권장: `pinterest_holdout_003`.
- 세션 생성 시 반드시 `--exclude-profile-history`를 사용해 기존 `pinterest_session_001`, `pinterest_holdout_001`, `pinterest_holdout_002` 이미지 재등장을 막는다.
- 판단 기준:
  - hard reject: 저해상도, 홈페이지/브라우저 캡쳐, 상단 URL/주소창 노출, 완전한 업종 오류, 심한 이미지 깨짐.
  - 애매하면 rejected보다 shortlist로 둔다.
- 자세한 인수인계는 [[09_HANDOFF]] 맨 아래 `2026-06-03 Handoff - next cosmetics generalization test` 참고.
## 현재 상태 업데이트 (2026-06-03, ComfyUI 제외 파이프라인 고도화)

- 판단 훈련 UI에 사유 태그 저장을 추가했다.
  - 태그: `low_resolution`, `website_capture`, `weak_local_fit`, `weak_product`, `good_benefit_hierarchy`, `usable_selected`, `foreign_sale_risk`, `fake_text_risk`, `good_layout`, `wrong_category`.
  - 빠른 비교 판정과 상세 교정 폼 모두에서 같은 태그를 저장한다.
- 교정 저장 시 자동 산출물 추가:
  - `kiwon_review_summary.md`
  - `correction_summary.md`
  - `learned_rules.json`
- 기존 cosmetics 세션 3개에 자동 요약을 backfill했다.
- `create_reference_training_session.py`에 `--qwen-vision` 옵션을 추가했다.
  - Qwen/Ollama 비전 평가를 `qwen_review`로 붙이고, cosmetics 판단에서 `local_hb_sale_fit`, `benefit_hierarchy`, `product_trust`, `website_capture_risk`, `text_artifact_risk`를 반영한다.
- 신규 스크립트:
  - `scripts/audit_planning_quality.py`: 01/02 브리프·기획 QA.
  - `scripts/compare_reference_sessions.py`: holdout/session 정확도 비교.
  - `scripts/summarize_reference_training_session.py`: 기존 세션 correction summary/learned rules backfill.
  - `scripts/project_hook_check.py`: 문법, UI JS, 선택 run audit을 묶은 hook 점검.
- `scripts/audit_visual_prompts.py`가 `cosmetics_skincare` profile을 인식해 H&B 세일/혜택 위계/웹페이지 캡처/가짜 텍스트를 점검한다.
- 검증:
  - `python scripts\project_hook_check.py --run runs\2026-06-02_16-59-22_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어` 통과.
  - 콘솔 `http://127.0.0.1:5177` 응답 200 확인.
  - Chrome headless로 판단 훈련 화면 로드, JS 오류 0, 사유 태그 DOM 20개 확인.

## 다음 작업

1. `pinterest_holdout_003` 생성 시 `--exclude-profile-history`와 필요하면 `--qwen-vision`을 같이 사용한다.
2. holdout 003 검수 후 `scripts/compare_reference_sessions.py --profile cosmetics_skincare`로 001/002/003 정확도 비교.
3. `learned_rules.json`의 반복 규칙을 cosmetics playbook/rubric에 반영한다.

## 현재 상태 업데이트 (2026-06-03, holdout 003 생성 완료)

- 새 reference run 생성:
  - `runs/2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- 01/02 단계 생성 및 승인 완료.
- `REFERENCE_RESEARCH_MODE=auto_search`로 03_reference_research 재생성 완료.
  - selected references: 20
  - accepted/shortlist/rejected: 79/0/14
  - clear reject reason: 14
  - low-resolution reject가 계속 작동함.
- Qwen/Ollama는 `http://127.0.0.1:11434`에 연결되지 않아 이번 세션은 `--qwen-vision` 없이 생성.
- 새 판단 세션:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_003/`
  - total 31
  - AI first pass: selected 2 / shortlist 17 / rejected 12
  - reviewed 0, 전부 기원님 검수 대기.
- 검증:
  - 콘솔 `http://127.0.0.1:5177` 응답 200 확인.
  - `scripts/project_hook_check.py --run runs/2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어` 통과.
  - `scripts/compare_reference_sessions.py --profile cosmetics_skincare`에서 holdout 003이 reviewed 0으로 등록됨 확인.

## 다음 작업

1. 콘솔 판단 훈련에서 `cosmetics_skincare/pinterest_holdout_003`을 빠른 비교 + 사유 태그로 검수.
2. 검수 후 `scripts/summarize_reference_training_session.py --profile cosmetics_skincare --session-id pinterest_holdout_003` 실행.
3. `scripts/compare_reference_sessions.py --profile cosmetics_skincare`로 001/002/003 정확도 비교.
4. 반복 오차만 cosmetics playbook/rubric에 반영.

## 현재 상태 업데이트 (2026-06-03, Reference Judge gate 보정)

- `cosmetics_skincare/pinterest_holdout_003` 상태 확인:
  - `kiwon_review_state.json` 없음.
  - reviewed 0/31.
  - `summarize_reference_training_session.py` 실행 결과 summary는 생성됐지만 학습 규칙은 비어 있음.
- `compare_reference_sessions.py --profile cosmetics_skincare` 실행:
  - holdout 001: 46.8%.
  - holdout 002: 52.8%.
  - holdout 003: `pending_review`로 표시되도록 수정. 미검수 세션을 0.0% 실패로 오해하지 않게 했다.
- rejected gate 완화:
  - `scripts/create_reference_training_session.py`에서 cosmetics rejected를 hard reject 중심으로 조정.
  - hard reject: 저해상도, 웹페이지/브라우저 캡처, 업종 오류, AI artifact, Qwen hard risk.
  - weak copy space나 부족한 metadata만으로는 rejected가 아니라 shortlist.
  - 003 source pool 기준 예상 분포: selected 3 / shortlist 72 / rejected 18.
- Qwen/Ollama 상태:
  - `http://127.0.0.1:11434` 연결 실패.
  - `ollama` 명령/프로세스 확인 안 됨.
  - 따라서 `pinterest_holdout_004`는 Qwen 연결 확인 전 생성하지 않음.

## 다음 작업

1. 콘솔 판단 훈련에서 `cosmetics_skincare/pinterest_holdout_003` 검수 완료.
2. 검수 후 summary/compare 재실행.
3. Qwen/Ollama를 켠 뒤 `pinterest_holdout_004`를 `--qwen-vision`으로 생성.
4. 004에서 selected 오판, hard reject 안정성, 전체 정확도 재측정.
## 현재 상태 업데이트 (2026-06-03, QA Packaging evidence manifest)

- 06_qa_packaging이 품질 근거 파일을 `qualityArtifacts`로 자동 수집한다.
- 점검 대상: `planning-quality/planning-quality-audit.json`, `03_reference_research/reference-quality-report.json`, `03_visual_candidates/prompt-audit.json`, `03_visual_candidates/generation-quality.json`, `04_admin_selection/selected-assets.json`.
- `final-package-manifest.json`의 각 파일 레코드에 `qualityEvidence`가 추가되어 선택 후보, 선택 사유, 품질 근거 파일 상태를 함께 볼 수 있다.
- 누락/실패한 근거 파일은 QA issue로 기록되고 `suggested_fix_stage`로 되돌릴 단계를 표시한다.
- 검증: `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`에서 06 직접 실행, 07 입력 검증, `scripts/project_hook_check.py` 통과.

## 현재 상태 업데이트 (2026-06-04, QA Evidence 콘솔 노출 + 선택 후보 기준 QA)

- 06_qa_packaging의 `prompt-audit.json`, `generation-quality.json` 판정이 전체 후보 기준이 아니라 선택된 candidate를 우선으로 보도록 정밀화됐다.
- 예: 전체 generation 실패가 있어도 선택된 후보가 `generated`이면 `generation_quality`는 pass, 선택 후보가 `placeholder`이면 warning, 선택 후보가 failed/error이면 error로 QA issue를 남긴다.
- `qualityEvidence.artifacts[]`에는 각 근거 파일의 `summary`도 함께 들어간다.
- 콘솔 API `/api/runs/<run-id>`가 `qa_report`, `final_package_manifest`, `qa_packaging`을 반환한다.
- 콘솔 최종 패키지 화면에 QA Evidence 패널과 선택 후보별 evidence 칩이 추가됐다.
- 검증: 06 직접 실행 결과 `generation_quality`가 selected candidate 기준 pass로 내려가는 것 확인, 콘솔 API evidence 반환 확인, `node --check ui/console/app.js`, `python scripts/project_hook_check.py` 통과.
- 추가 검증: `?view=package&run=<run-id>` 직접 진입을 지원하고, Chrome headless DOM에서 `QA Evidence`, `quality-artifact`, `candidate-evidence`, `생성 QA`, `QA 이슈` 렌더링을 확인했다.

## 다음 작업

1. 07_asset_archive가 `qualityEvidence`를 asset record/reuse score에 반영하도록 확장한다.
2. QA warning 자산을 `limited_reuse`로 낮추는 archive 정책을 추가한다.
## 현재 상태 업데이트 (2026-06-03, Console UI 판단 훈련 개선)

- 판단 훈련 UI가 세션 선택 단계에서 reviewed/accuracy/AI 분포/final 분포를 함께 표시한다.
- 세션 상단 요약에 검토 수, 정확도, AI 분포, 최종 분포, 과선택, 과탈락, 주요 transition, reason tag 통계를 추가했다.
- reference item/빠른 비교/상세 패널에서 AI decision, 기원님 final decision, transition을 동시에 보이게 했다.
- `rejected->shortlist`, `rejected->selected`, `selected->rejected` 같은 주요 오차를 자동 하이라이트한다.
- `low_resolution`, `website_capture`, `fake_text_risk`, `wrong_category` hard reject 태그는 빨간 강조로 표시한다.
- 검수 폼에 `summary 생성`, `compare 생성` 버튼을 연결했다.
- 서버 API:
  - `POST /api/training-sessions/<profile>/<session_id>/summary`
  - `POST /api/training-sessions/<profile>/compare`
- `_comparisons` 같은 보조 폴더는 training session 목록에서 제외한다.
- 콘솔 서버는 새 코드 반영을 위해 `http://127.0.0.1:5177`로 재시작 완료.

## 다음 할 일

1. `cosmetics_skincare/pinterest_holdout_003`을 새 UI에서 검수한다.
2. 검수 완료 후 UI 버튼으로 summary/compare를 생성한다.
3. reason tag 통계와 주요 transition만 골라 cosmetics playbook/rubric에 반영한다.
## 현재 상태 업데이트 (2026-06-04, Console UX 리디자인 1차)

- 사용자가 제공한 Figma marketing canvas 스타일 가이드를 내부 운영툴에 맞게 해석했다.
- 새 페이지 설계 문서 `knowledge/CONSOLE_UX_REDESIGN.md`를 추가했다.
- 콘솔 UI의 어두운 AI 대시보드 톤을 밝은 Creative Ops 작업대 톤으로 변경했다.
- 핵심 시각 방향:
  - light canvas
  - black/white monochrome core
  - pastel color-block sections
  - pill buttons
  - hairline borders
  - minimal shadow
- Dashboard를 Workboard로 재구성했다.
  - Active runs
  - Ready for action
  - Review sessions
  - Generated images
  - Work that needs a decision
  - Queue health
  - Recent production history
- 사이드바/페이지명은 업무 언어로 정리했다.
  - Workboard
  - New Event
  - Pipeline
  - References
  - Review Training
  - Prompt Sheet
  - Image Selection
  - Package
  - Settings
- Workboard에서는 불필요한 run progress block을 숨기고, Pipeline 화면에서만 보이도록 정리했다.
- 검증:
  - `node --check ui/console/app.js` 통과.
  - `python scripts\project_hook_check.py` 통과.
  - 브라우저에서 배경 `rgb(251, 250, 247)`, pill radius `999px`, Workboard 구조, JS error 0 확인.
## 현재 상태 업데이트 (2026-06-07, Meta Ad Reference MVP 1차)

- 로컬 콘솔에 `Ad Reference` 탭 추가.
- `services/ad_reference/meta_collector.py` 추가: Meta Ad Library 검색 URL 생성, Playwright 스크롤, 개별 광고 카드 캡처 및 텍스트/CTA/링크 추출.
- `scripts/collect_meta_ads.py` 추가: `references/meta_ads/searches/<검색-id>/collected-ads.json`과 `captures/` 저장, 선택형 Qwen 태깅 지원.
- 콘솔 API 추가: `GET /api/meta-ads`, `POST /api/meta-ads/collect`, `/meta-ad-assets/...`.
- 실수집 검증: `anua skincare`, KR, 광고 카드 2개 개별 캡처/JSON 저장 성공.

## 다음 할 일

1. Ad Reference 카드의 선택/보류/제외 상태와 shortlist 저장 기능 추가.
2. shortlist를 `reference-evidence.json`으로 변환.
3. 기존 OpenCLIP ranker를 Meta 광고 캡처에 연결.
4. `reference-evidence.json`을 01_event_brief, 02_content_planning, 03_reference_research 입력에 연결.

## 현재 상태 업데이트 (2026-06-07, Meta 원본 이미지 다운로드 + run 연결)

- Meta 광고 카드 캡처 대신 카드 내부 실제 CDN 이미지를 `images/`에 다운로드하도록 변경.
- 작은 프로필 이미지/아이콘 제외, 캐러셀 광고는 광고당 최대 10장 제한.
- 콘솔 `현재 작업 레퍼런스로 연결` 옵션 추가.
- 연결 시 다운로드 이미지를 현재 run의 `references/selected/`, `reference-manifest.json`, `selected-references.json`에 등록.
- 검증: Meta 광고 2개에서 원본 이미지 20개 다운로드, 임시 run에 20개 등록, `03_reference_research`에서 selected 20개 인식.

## 현재 상태 업데이트 (2026-06-07, Meta 검색 쿼리 벤치마크)

- 화장품 이벤트 기준 Meta 검색어 8종 테스트 완료.
- 결론: Pinterest의 디자인 묘사형 검색어를 Meta에 그대로 쓰지 않는다.
- Meta 권장 구조: 경쟁 브랜드 + 상품/성분 + 카테고리/혜택.
- 기준 파일 추가:
  - `assets/rules/meta-ad-query-rules.json`
  - `knowledge/META_AD_QUERY_STRATEGY.md`
- 벤치마크 스크립트 추가: `scripts/benchmark_meta_ad_queries.py`.

## 현재 상태 업데이트 (2026-06-07, 기존 화장품 브리프 Meta 실수집)

- 대상 run: `2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`.
- 검색어: `메디큐브`, `나이아신아마이드 세럼`, `스킨케어 세일`.
- 검색어별 광고 2개 수집, 원본 이미지 각 7개, 총 21개 다운로드 및 run 연결.
- 03_reference_research 재실행 완료: 전체 reference 41, selected 41.
- 비교 시트: `references/meta_ads/meta-brief-test-contact-sheet.jpg`.
- 관찰: 실제 프로모션의 혜택 위계와 CTA 구조에는 강하지만 모델/캐릭터/텍스트 중심 소재가 섞이므로 Judge 필터가 필요하다.

## 현재 상태 업데이트 (2026-06-07, Meta 광고 성격 선택)

- Meta Ad Reference에 광고 성격 선택 추가:
  - 클린 제품 비주얼
  - 단일 광고 이미지
  - 브랜드 캠페인
  - 프로모션 구조
  - 전체 원본
- `클린 제품 비주얼`은 Qwen의 `creative_type`, `product_focus`, `text_density` 판정이 있어야 run selected로 연결된다.
- `검색어와 광고주명 일치` 옵션 추가.
- 확인: `아누아`, `라운드랩` 브랜드 검색도 공식 광고주만 나오지 않고 리셀러/제휴 광고가 섞인다.

## 현재 상태 업데이트 (2026-06-07, 클린 제품 비주얼 실검증)

- Qwen/Ollama `qwen2.5vl:7b`를 실행해 Meta 클린 제품 비주얼 필터를 실검증.
- 1차: 광고 8개/원본 13개 중 2개 연결. 제품 사진 1개는 좋았지만 뷰티 앱 화면 1개가 잘못 통과.
- 카테고리 적합도, 화면 캡처 위험, 실제 화장품 용기, 박스-only, 카드뉴스 여부 필드를 추가.
- 이미지별 Qwen 판정으로 변경해 캐러셀 내부 이미지도 각각 판단.
- 엄격 재검증: 원본 17개 중 자동 연결 0개. 나쁜 이미지 자동 연결은 막았지만 recall이 낮음.
- 결론: Qwen 단독 자동 선별은 오판이 있어 `클린 제품 비주얼` 기본 gate는 정밀도 우선으로 유지. 다음 단계는 OpenCLIP/기존 Reference Judge와 결합.

## 현재 상태 업데이트 (2026-06-07, zip UI 통합)

- `자동화 프로젝트.zip`의 LoopStudio 콘솔 UI 구조를 현재 콘솔에 적용했다.
- `ui/console/index.html`, `ui/console/styles.css`를 좌측 그룹 내비게이션, 상단 작업 바, 지표 및 run 중심 화면으로 교체했다.
- 기존 콘솔 DOM ID와 `app.js` 연결은 유지해 작업 현황, 레퍼런스 검수, 판단 훈련, 이미지 선택 등 기존 기능이 계속 동작한다.
- 데스크톱 및 모바일 폭에서 가로 넘침과 브라우저 오류가 없음을 확인했다.

## 현재 상태 업데이트 (2026-06-07, 광고 레퍼런스 카드 요약)

- 광고 레퍼런스 카드의 긴 Meta 원문을 제거하고 광고주, 3줄 요약, CTA, 이미지 수만 표시하도록 변경했다.
- 전체 수집 원문과 외부 링크는 `자세히 보기` 모달에서 확인한다.
- 동일 Library ID 광고는 화면에서 중복 제거한다.
- Meta가 CTR/ROAS/매출을 공개하지 않으므로 실제 성과 대신 집행 기간을 `신규/지속/장기 집행` 신호로 표시한다.

## 현재 상태 업데이트 (2026-06-07, 신규 zip UI 재적용)

- 오후 11:24 갱신된 `자동화 프로젝트.zip`을 `.tmp/ui-redesign-source-2324`에 새로 풀어 변경점을 반영했다.
- 새 압축본의 시스템 메뉴 `활동 로그`를 실제 run/job 데이터 기반 화면으로 추가했다.
- 오류가 기록된 run 상세에는 완료 단계 유지 안내, 관련 로그, 작업 폴더 접근을 제공하는 복구 패널을 추가했다.
- 기존 광고 레퍼런스 요약 카드와 상세 모달은 유지했다.

## 현재 상태 업데이트 (2026-06-07, Vercel 프로덕션 배포)

- Vercel 프로젝트 `loopstudio-console`을 생성하고 프로덕션 별칭 `https://loopstudio-console.vercel.app`에 배포했다.
- Vercel 배포본은 run, 이벤트, 광고 레퍼런스 등 조회 기능을 제공하는 읽기 전용 콘솔이다.
- 로컬 워크플로 실행, 폴더 열기, ComfyUI 생성 등 PC 의존 POST 작업은 로컬 콘솔 전용으로 제한한다.
# 2026-06-13 남은 작업 정리 결과

- QA warning 승인 메모 gate, 자산 0개 archive 상태, 공통 테스트 runner, 콘솔 중복 함수 정리를 완료했다.
- 공통 검증: `scripts/run_project_tests.py` 27개 통과, `scripts/project_hook_check.py` 통과.
- 제품 고정 합성은 원본 제품 보존 기능 통과, 기본 배치 품질은 보완 필요.
- 한글 오버레이는 Unicode 렌더링 통과, 대비/줄바꿈/비율 배지 문제로 납품 품질 실패.
- OpenCLIP holdout: ROC AUC 0.9328, top-10 selected precision 0.80, baseline 대비 2.02x.
- 상세: `knowledge/QUALITY_VALIDATION_2026-06-13.md`
