# 결정사항 기록

이 문서는 프로젝트의 중요한 결정을 날짜와 이유와 함께 남기는 곳이다. 나중에 AI가 작업할 때 가장 많이 참고해야 하는 문서 중 하나다.

## 기록 형식

```text
날짜:
결정:
이유:
영향:
관련 파일:
상태:
```

## 결정 목록

### 2026-06-11: Meta 검수 세트는 공식 광고와 협업 광고를 분리하고 편중을 제한한다

결정:

- 광고주명이 브랜드 별칭으로 시작하면 `direct`, 다른 계정의 협업 문구에 브랜드가 포함되면 `partner`로 저장한다.
- Meta 검수 세트는 브랜드당 최대 20장, 한 광고당 최대 5장, 협업 광고 최대 20장으로 제한한다.

이유:

- 단순 브랜드 포함 검색은 협업 광고를 공식 광고로 오판하고, 한 브랜드 또는 한 캐러셀이 검수 세트를 독점할 수 있다.

영향:

- Meta 검수 세트는 브랜드 다양성과 광고 단위 다양성을 유지하며, 협업 광고를 별도 위험 신호로 검수할 수 있다.

관련 파일:

- `services/ad_reference/brand_registry.py`
- `scripts/collect_meta_brand_registry.py`
- `scripts/create_meta_brand_review_session.py`

상태: 적용 완료

### 2026-05-18: Obsidian을 프로젝트 기억 저장소로 둔다

결정:

- Obsidian은 실행 도구가 아니라 기획, 기준, 지식, 결정사항을 저장하는 프로젝트 기억 저장소로 둔다.

이유:

- 이벤트 자동화는 코드보다 기준과 판단 흐름이 더 쉽게 흩어진다.
- 브랜드 톤, 프롬프트 규칙, 이미지 평가 기준, 실패 사례, 회의 기록을 한곳에서 찾을 수 있어야 한다.

영향:

- `knowledge/` 폴더를 만들고 Obsidian에서 읽을 기준 문서를 둔다.
- Codex/OpenCode/LM Studio는 이 문서를 참고해 작업한다.

관련 파일:

- `knowledge/00_INDEX.md`
- `knowledge/01_PROJECT_GOAL.md`
- `knowledge/02_WORKFLOW.md`

상태:

- 적용

### 2026-05-18: 기준 문서를 먼저 만들고 플러그인은 나중에 붙인다

결정:

- Obsidian 플러그인 세팅보다 기준 문서 구조를 먼저 만든다.

이유:

- Dataview, Tasks, Templater 같은 플러그인은 문서가 쌓인 뒤에 효과가 크다.
- 초기에는 구조가 복잡해지는 것보다 프로젝트 기준을 빠르게 고정하는 것이 중요하다.

영향:

- 우선 9개 핵심 문서만 만든다.
- 플러그인 추천은 이후 운영이 반복될 때 다시 정리한다.

상태:

- 적용

### 2026-05-18: 작업 후 기준 변화는 Obsidian 지식에 자동 반영한다

결정:

- Codex/OpenCode 작업 결과가 프로젝트 기준, 반복 운영 방식, 실패 해결법, 모델 테스트, 워크플로 구조에 영향을 주면 `knowledge/` 문서에 함께 반영한다.

이유:

- 실행 결과는 `runs/`에 남지만, 다음 작업에서 바로 참고해야 하는 판단 기준은 Obsidian에서 보여야 한다.
- 모든 로그를 문서화하면 지식베이스가 지저분해지므로 중요한 기준 변화만 기록한다.

영향:

- `00_DASHBOARD.md`를 추가해 빠른 링크와 기록 위치 판단 기준을 둔다.
- 단순 실행 로그, 임시 파일, 일회성 산출물은 `knowledge/`에 넣지 않는다.

관련 파일:

- `knowledge/00_DASHBOARD.md`
- `knowledge/00_INDEX.md`

상태:

- 적용

### 2026-05-18: `byextremeai/static-ads`는 완제품으로 쓰지 않는다

결정:

- `byextremeai/static-ads`는 완제품으로 복제하지 않고 패턴만 참고한다.

이유:

- 이 프로젝트의 도메인은 이벤트 콘텐츠 자동화이며, 고정 광고 템플릿 생성과 다르다.
- 단계 분리, 승인 게이트, JSON 중간 산출물, 개별 재생성, 버전 관리만 가져오는 편이 맞다.

영향:

- 프로젝트 도메인은 `event-content-pipeline`으로 재설계한다.
- 실행 헬퍼는 `scripts/workflow.py`가 담당하고, AI 생성 로직은 단계 실행 또는 하위 모듈로 분리한다.

관련 파일:

- `AGENTS.md`
- `PIPELINE.md`
- `scripts/workflow.py`

상태:

- 적용

---

### 2026-05-18: 05_figma_assembly 단계 제거

결정:

- `05_figma_assembly`를 파이프라인에서 제거한다.
- `04_admin_selection` 완료 후 `06_qa_packaging`으로 직행한다.

이유:

- ComfyUI와 자동화를 통합하는 방향으로 전환. Figma 조립은 수동 개입 병목.
- 이미지 생성(ComfyUI) → 선택(04) → QA(06)로 흐름이 단순해짐.

영향:

- `scripts/workflow.py` STAGES에서 05 제거, 04 → 06 직결
- `CLAUDE.md`, `AGENTS.md`, `knowledge/` 전반 반영
- `pipeline/05_figma_assembly/` 폴더는 디스크에 보존 (archive 참고용)

상태:

- 적용
## 2026-05-25 — 04_admin_selection 최소 구현

- 결정: 04_admin_selection은 ComfyUI 실생성 여부와 무관하게 `03_visual_candidates/image-prompts.json` 및 후보 매니페스트를 읽어 사람이 고른 후보를 `selected-assets.json`으로 확정한다.
- 결정: 04는 별도 승인 게이트가 아니라 사람 선택 자체를 완료 조건으로 보고, 완료 후 `06_qa_packaging`을 바로 unlock한다.
- 범위 제외: ComfyUI 실생성, Figma 조립, 제품 합성, 영상 생성은 이번 단계에 포함하지 않는다.
- 06 연결 준비: Figma 산출물이 없을 때도 `04_admin_selection/selected-assets.json`을 입력으로 최소 QA 리포트와 패키지 매니페스트를 만들 수 있게 한다.

## 2026-05-27 — MVP 단계명 재정리와 레퍼런스 리서치 stage 추가

- 결정: 프로젝트 포지션을 "GPT보다 똑똑한 기획툴"이 아니라 "브랜드 이벤트 이미지 제작용 로컬 제작 콘솔"로 고정한다.
- 결정: 기준 파이프라인을 `01_event_brief → 02_content_planning → 03_reference_research → 04_visual_candidates → 05_admin_selection → 06_qa_packaging → 07_asset_archive`로 정리한다.
- 이유: 실제 사용 흐름에서 레퍼런스 수집이 콘텐츠 기획과 이미지 후보 생성 사이의 독립 작업으로 중요하며, 기존 `03_visual_candidates` 안에 암묵적으로 붙어 있으면 콘솔 사용자가 작업 상태를 이해하기 어렵다.
- 구현: `03_reference_research` handler를 추가해 기본 실행은 레퍼런스 검색 계획/요약을 만들고, `REFERENCE_RESEARCH_MODE=auto_search`일 때 기존 자동 검색/선정 파이프라인을 실행하게 한다.
- 호환: 기존 런과 코드 경로를 깨지 않기 위해 물리 산출물 폴더 `03_visual_candidates`, `04_admin_selection`은 유지한다.
- 호환: `scripts/workflow.py`에서 기존 stage id `03_visual_candidates`, `04_admin_selection`은 새 기준 stage `04_visual_candidates`, `05_admin_selection`으로 alias 처리한다.

## 2026-05-27 — reference_research 산출물을 visual prompt에 직접 연결

- 결정: `03_reference_research/reference-research.json`을 단순 진행 요약이 아니라 04 후보 생성 프롬프트의 방향성 입력으로 사용한다.
- 이유: 레퍼런스 수집 단계가 실제 이미지 후보 품질에 영향을 주려면 선택 이미지 경로뿐 아니라 mood, composition, lighting, color, texture, avoid 방향이 구조화되어 04 단계에 전달되어야 한다.
- 구현: `reference-research.json`에 `moodKeywords`, `compositionKeywords`, `lightingKeywords`, `colorPalette`, `materialTexture`, `avoidKeywords`, `promptHints`, `negativePromptHints`, `selectedReferences`를 항상 생성한다.
- 구현: `04_visual_candidates`는 이 값을 읽어 positive prompt에는 `reference prompt hints`, negative prompt에는 `avoidKeywords`와 `negativePromptHints`를 반영한다.
- 추적: `visual-plan.json.reference_direction`과 `image-prompts.json.prompts[].reference_direction`에 원본 방향성을 남긴다.

## 2026-05-25 — 외부 브랜드 workflow를 단일 원본으로 사용

- 결정: `D:\CD\jewelry_ad_project\02_workflows`를 cosmetics/jewelry/bullion ComfyUI workflow의 단일 원본으로 사용한다.
- 결정: 프로젝트 내부 `services/comfyui/workflows`로 복사하지 않고 레지스트리에서 canonical path를 참조한다.
- 결정: 캔버스 workflow JSON은 사람이 관리하는 원본으로 유지하고, 자동 큐 실행에는 프롬프트/샘플러 값을 읽어 API prompt adapter에 주입한다.
- 이유: ComfyUI 워크플로 관리 위치를 하나로 유지하고, 자동화 프로젝트는 이벤트/제품 카테고리별 매핑과 실행 데이터 생성에 집중한다.

## 2026-05-27 — live 생성 결과 품질 추적 파일을 stage 산출물로 둔다

- 결정: `04_visual_candidates` 실행 시 `03_visual_candidates/generation-quality.json`을 항상 생성한다.
- 이유: live/placeholder 여부, ComfyUI 제출 결과, 파일 존재/해상도/용량, `reference_direction` 반영 여부를 후보 선택 전에 한곳에서 확인해야 한다.
- 구현: 후보별 `generation_mode`, `generation_status`, `generation_error`, `image`, `reference_direction_checks`, `comfyui_submission`을 기록한다.
- 영향: 콘솔은 이후 이 파일을 읽어 "생성 성공/실패", "레퍼런스 방향 반영", "텍스트/카테고리 품질 이슈"를 선택 화면에 노출할 수 있다.

## 2026-05-27 — `qwen_candidate_2511` 기본 실행값을 Lightning 권장값으로 맞춘다

- 결정: local preset `qwen_candidate_2511`의 stage 기본값은 `8 steps / cfg 1.0 / heun / beta`로 둔다.
- 이유: 프리셋 자체가 Lightning LoRA 기반인데 일반 후보 생성 기본값 `28 steps / cfg 6.5 / dpmpp_2m`를 쓰면 live 검증 시간이 과도하게 길고 큐 stuck처럼 보인다.
- 영향: 기본 live 후보 생성 속도가 안정화된다. 더 높은 품질 실험은 별도 preset 또는 명시적 workflow 설정으로 분리한다.

## 2026-05-28 — 금/은/투자 이벤트용 reference quality gate 강화

- 결정: `03_reference_research`에서 금/은/투자/상담 이벤트를 `bullion_investment` profile로 감지하고, 일반 이벤트보다 엄격한 레퍼런스 필터를 적용한다.
- 이유: live 생성 결과가 귀여운 3D 캠핑, 캐릭터, 와인/패키지 오인식으로 흐른 원인은 ComfyUI보다 앞단 레퍼런스 방향성이 약했기 때문이다.
- 구현: 검색어를 `premium gold investment campaign visual`, `luxury financial consultation poster`, `gold bar premium product photography`, `bullion investment advertising` 등으로 교체한다.
- 구현: reference 평가에 `brandFit`, `eventFit`, `visualQuality`, `compositionUsefulness`, `promptUsefulness`, `seriousnessFit`, `productRelevance`, `riskLevel`을 남긴다.
- 구현: selected 기준은 `brandFit >= 7`, `eventFit >= 7`, `productRelevance >= 7`, `seriousnessFit >= 6`, `riskLevel <= 4`로 둔다.
- 구현: kids/toy/kawaii/camping/theme park/picnic/wine/random package/fake text 계열은 자동 reject 또는 shortlist로 내린다.
- 영향: 다음 gold/bullion 후보 생성은 "귀여운 이벤트 이미지"가 아니라 "프리미엄 금 투자 상담 비주얼"을 기준으로 시작한다.

## 2026-05-28 — `bullion_investment` positive prompt 하드 정화

- 결정: `04_visual_candidates`는 `reference-research.json.eventProfile.category == bullion_investment`일 때 positive prompt와 reference prompt hint에서 캐릭터/캠핑/장난감/와인/패키지 계열 토큰을 제거한다.
- 이유: "not cute", "no mascot"처럼 부정문으로 positive에 남긴 단어도 이미지 모델에는 해당 시각 개념을 활성화할 수 있다.
- 구현: `mascot`, `character`, `cute`, `camping`, `picnic`, `tent`, `toy`, `diorama`, `cartoon`, `kawaii`, `playful`, `wine`, `bottle`, `package box`는 positive에서 제거하고 negative에만 강하게 둔다.
- 영향: gold/bullion 후보 프롬프트는 프리미엄 금융/금 제품/상담 비주얼만 positive 방향으로 전달한다.
## 2026-05-28 - 이미지 생성 중단, 레퍼런스 기준 데이터 우선

- 결정: ComfyUI/LoRA 튜닝보다 먼저 브랜드/이벤트별 레퍼런스 판단 기준을 구조화한다.
- 이유: 최근 bullion_investment live 테스트 실패 원인은 모델 자체보다 캐릭터/장난감/귀여운 3D 방향의 fallback/레퍼런스 오염과 기준 데이터 부족에 가깝다.
- 적용: `assets/rules/brand-persona.json`, `event-rules.json`, `reference-rules.json`, `visual-avoid-rules.json`, `tone-rules.md`를 생성하고 `bullion_investment` 기준을 고정했다.
- 운영 원칙: 이미지 생성은 reference 기준, fallback 오염 제거, selected/rejected 사유 기록이 안정된 뒤 재개한다.

## 2026-05-30 - bad만으로는 부족하므로 good seed를 기준에 포함

- 결정: `bullion_investment` reference 판단에 good/bad seed dataset을 모두 사용한다.
- 이유: bad dataset은 피해야 할 방향을 알려주지만, good dataset이 있어야 선택해야 할 방향이 생긴다.
- 적용: `assets/reference_training/bullion_investment/good/`에 로컬 금/은/precious-metal 계열 seed 10장을 저장하고 `metadata.json`을 작성했다.
- 게이트: 03 품질 리포트가 pass이고 selected bad signal이 0일 때만 04 프롬프트/이미지 후보 단계로 넘어간다.

## 2026-05-30 - good seed는 product/mood/layout으로 분리

- 결정: `bullion_investment` good seed를 `product_reference`, `finance_mood_reference`, `poster_layout_reference`로 분리한다.
- 이유: product reference만 늘리면 selector가 금화/골드바 제품컷만 좋은 reference로 학습할 수 있다.
- 적용: good seed를 30장 구조로 확장하고, selected reference도 category coverage를 검사한다.
- 선택 원칙: selected는 product identity, finance trust mood, poster/headline layout이 모두 들어가야 한다.
## 2026-05-30 - 1차 GOAL을 Senior Designer Brain Wiki로 재정의

- 결정: 프로젝트의 1차 목표를 이미지 생성 자동화가 아니라 `Senior Designer Brain Wiki` 구축으로 둔다.
- 이유: 최근 ComfyUI 실패의 핵심 원인은 모델 파인튜닝 부족보다 브랜드/이벤트/레퍼런스 판단 기준 부족과 fallback 오염이었다. 먼저 AI가 좋은/나쁜 레퍼런스를 설명 가능한 기준으로 판단하게 만들어야 한다.
- 적용: `design_brain_wiki/` 폴더를 생성하고 디자인 원칙, 브랜드 전략, 레퍼런스 판단, 채널 사용성, 업종별 playbook, 공식 사례 연구, 기원님 taste dataset, feedback language를 MD/JSON으로 구조화했다.
- 판단 기준: 자료는 링크 모음으로 저장하지 않고 `자료 원문/링크 -> 핵심 요약 -> 디자인 판단 질문 -> 평가 항목 -> good/bad 적용 -> AI 피드백 문장 예시` 형식으로 변환한다.
- 후속: Reference Judge는 `assets/rules`, `assets/reference_training`, `design_brain_wiki`를 함께 읽어 selected/shortlist/rejected와 이유를 산출해야 한다.
## 2026-05-31 - Senior Designer Brain Wiki는 샘플 Judge 테스트를 통과해야 03에 연결

- 결정: `design_brain_wiki`를 바로 운영 파이프라인에 넣기 전에, 업종별 샘플 reference judge 테스트를 먼저 통과시킨다.
- 이유: 파일을 많이 만든 것만으로는 AI 판단력이 좋아졌는지 알 수 없다. selected/shortlist/rejected 판단과 피드백 문장 수준을 샘플 세트로 검증해야 한다.
- 적용: `design_brain_wiki/tests/reference_judge_sample_set.json`에 `bullion_investment`, `cosmetics_skincare`, `jewelry_luxury` 각각 good/bad/ambiguous 후보를 섞은 테스트 세트를 만들었다.
- 적용: `scripts/run_reference_judge_wiki_tests.py`는 위키 rubric을 읽고 후보별 decision, score, role, senior designer feedback, feedback depth를 평가한다.
- 통과 기준: decision accuracy와 feedback depth rate가 모두 1.0에 도달해야 한다.
- 현재 결과: 총 18개 후보, accuracy 1.0, feedback depth rate 1.0, status pass.
## 2026-05-31 - Wiki는 완성이 아니라 v0.2 확장 단계로 재정의

- 결정: 현재 `design_brain_wiki`는 완성본이 아니라 `v0.1 골격 + 1차 테스트 세트`로 본다.
- 이유: 샘플 18개 테스트 통과는 자체 제작한 작은 시험지를 통과한 수준이다. 실제 시니어 디자이너 에이전트가 되려면 더 많은 공식 사례, 업종별 경계 기준, 기원님 판단 데이터, 실제 레퍼런스 검증 로그가 필요하다.
- 적용: `design_brain_wiki/VERSION_STATUS.md`를 추가해 v0.1/v0.2/v0.3/v1.0 상태를 분리했다.
- 적용: v0.2 확장으로 studio case bank 50개, 핵심 업종 deep playbook 3개, 기원님 피드백 100개/레퍼런스 300장 축적 계획을 추가했다.
- 원칙: 앞으로 "완료"라고 부르지 않고, 버전별로 `골격`, `자료 확장`, `실전 검증`, `운영 Judge`를 구분한다.
## 2026-05-31 - bullion_investment 판단 훈련은 기원님 교정 루프를 기준으로 한다

- 결정: `bullion_investment` 위키 품질 검증은 파일 수가 아니라 30장 단위 판단 세션과 기원님 교정 로그로 진행한다.
- 적용: `design_brain_wiki/training_sessions/bullion_investment/session_001/` 생성.
- 산출물: AI 1차 판단, 기원님 리뷰 템플릿, 교정 로그, wiki update suggestion을 한 세트로 둔다.
- 원칙: AI의 selected/shortlist/rejected는 정답이 아니라 기원님이 교정할 초안이다.
- 다음 기준: 기원님 교정 후 과승인, 과거절, 추상 피드백, 업종 playbook 누락을 위키에 반영한다.
## 2026-05-31 - seed test와 실제 Pinterest reference session을 분리한다

- 결정: `session_001` 같은 seed 기반 세션과 `pinterest_session_001` 같은 실제 수집 레퍼런스 세션을 명시적으로 구분한다.
- 이유: seed 이미지는 기준 검증에는 유용하지만, 실제 Pinterest/search 레퍼런스 판단력 검증과 위키 교정에는 부족하다.
- 적용: training session JSON에 `sessionType`을 기록한다.
- 적용: 실제 레퍼런스 세션 생성은 run의 `references/reference-quality-filter.json`을 입력으로 사용하고, 필요하면 `--require-pinterest`로 Pinterest 출처를 강제한다.
- 운영 원칙: 위키 보강의 주 근거는 실제 수집 세션과 기원님 교정 로그로 삼고, seed 세션은 smoke test로만 본다.
## 2026-05-31 - 한국 이벤트 레퍼런스는 한국어 Pinterest 검색어를 우선한다

- 결정: `bullion_investment` 검색 쿼리는 한국어 카드뉴스/배너/금거래소/상담 이벤트 표현을 우선 사용한다.
- 이유: 영문 `premium gold investment` 계열 검색어는 해외 금융/투자 그래픽으로 쏠려 한국 카드뉴스와 블로그 배너 감성이 약하다.
- 적용: `assets/rules/reference-rules.json`의 searchQueries를 한국어 우선으로 교체하고, 영문은 보조 쿼리로 뒤쪽에 둔다.
- 운영 원칙: 한국 로컬 이벤트는 한국어 검색어로 먼저 수집하고, 해외 레퍼런스는 제품컷/무드 보조 자료로만 사용한다.

## 2026-05-31 - 판단 훈련은 두 장 빠른 비교 방식을 기본 UX로 둔다

- 결정: 판단 훈련 UI에 두 장 비교 후 즉시 저장/다음 이동하는 빠른 판정 흐름을 추가한다.
- 이유: 리스트에서 이미지 하나씩 클릭하는 방식은 30장 이상 리뷰할 때 느리고, 사용자가 좋은/나쁜 기준을 즉각적으로 교정하기 어렵다.
- 적용: `왼쪽 좋음`, `오른쪽 좋음`, `둘 다 후보`, `둘 다 제외`, `건너뛰기` 액션을 추가했다.
- 운영 원칙: 개별 상세 입력은 유지하되, 1차 교정은 빠른 비교로 처리한다.

## 2026-06-03 - cosmetics_skincare도 한국어 Pinterest 검색 프로필을 별도로 둔다

- 결정: 화장품/H&B/스킨케어 세일 이벤트는 `cosmetics_skincare` 프로필로 감지하고, 한국어 Pinterest/search 쿼리를 우선 사용한다.
- 이유: 일반 이벤트 검색이나 해외 뷰티 레퍼런스는 올영세일 같은 한국 H&B 세일의 카드뉴스/배너/혜택 강조 감성을 충분히 반영하지 못한다.
- 적용: `assets/rules/event-rules.json`, `reference-rules.json`, `brand-persona.json`, `visual-avoid-rules.json`에 화장품 기준을 추가했다.
- 운영 원칙: 한국 로컬 H&B 이벤트는 한국어 검색어로 1차 수집하고, 해외 레퍼런스는 제품 무드나 질감 보조 자료로만 사용한다.

## 2026-06-03 - 업종 감지는 짧고 모호한 키워드를 피한다

- 결정: `bullion_investment` 감지에서 단일 글자 `금`, `은` 및 일반 `상담` 같은 모호한 키워드를 제거한다.
- 이유: 화장품 기능성 문구의 `미백`, 일반 고객 상담 표현 등이 금 투자 이벤트로 오탐될 수 있다.
- 적용: `금 투자`, `금 시세`, `실물 금`, `투자 상담`처럼 업종 의도가 분명한 키워드 중심으로 감지한다.
- 운영 원칙: 새 업종 프로필을 추가할 때도 한 글자 키워드나 여러 업종에서 흔한 단어는 단독 감지 기준으로 쓰지 않는다.

## 2026-06-03 - 판단 훈련 세션 생성은 업종 공통 스크립트로 확장한다

- 결정: `bullion_investment` 전용 세션 생성 스크립트와 별도로, run-collected reference를 업종별 판단 훈련 세션으로 만드는 범용 스크립트를 둔다.
- 이유: 화장품, 주얼리 등도 같은 빠른 비교 교정 루프를 사용해야 하며, 세션 생성이 특정 업종명에 묶이면 반복 확장이 어렵다.
- 적용: `scripts/create_reference_training_session.py`를 추가하고 `cosmetics_skincare/pinterest_session_001`을 생성했다.
- 운영 원칙: 레퍼런스 검수는 계속 판단 훈련 데이터가 되므로, 실제 수집된 이미지를 가능한 한 모두 세션에 넣는다. 빠른 검증은 30장 샘플로 시작할 수 있지만, 운영 세션은 전체 수집분을 교정 대상으로 둔다.

## 2026-06-03 - 검색어는 source metadata이지 판단 evidence가 아니다

- 결정: reference judge는 `query`, `source_id`, `path`, `filename`, `text_relevance_reason`을 selected/shortlist/rejected 판단 evidence로 쓰지 않는다.
- 이유: 검색어와 파일명은 이미 수집 의도를 포함하므로, 판단에 넣으면 "검색어가 맞다"를 "이미지가 좋다"로 오해한다.
- 적용: 수집 단계의 text relevance는 Pinterest title/alt/description 등 source metadata만 보며, 훈련 세션 judge도 title/alt/Qwen/기원님 피드백 중심으로 evidence를 구성한다.
- 운영 원칙: query는 출처 추적과 검색 품질 분석에만 쓰고, 좋은 레퍼런스 판단은 이미지에서 온 설명/비전 결과/사람 피드백을 기준으로 한다.

## 2026-06-03 - 홈페이지 캡쳐와 상단 URL 노출 이미지는 화장품 selected 금지 신호로 둔다

- 결정: `cosmetics_skincare` 레퍼런스에서 홈페이지 캡쳐, 브라우저 화면, 상단 URL/주소창 노출 이미지는 selected로 쓰지 않는다.
- 이유: 이런 이미지는 디자인 레퍼런스라기보다 웹페이지 스크린샷에 가깝고, 원본 링크/브랜드/레이아웃을 그대로 가져올 위험이 크다.
- 적용: `assets/rules/visual-avoid-rules.json`에 website/browser screenshot, visible URL bar, address bar, homepage capture 계열 reject/avoid/negative hint를 추가했다.
- 운영 원칙: 이벤트 배너/카드뉴스로 참고 가능한 부분이 있어도 URL 바나 브라우저 헤더가 보이면 최소 shortlist 이하로 두고, 생성 프롬프트에는 홈페이지 캡쳐 느낌을 넘기지 않는다.

## 2026-06-03 - holdout 테스트는 이전 세션 이미지를 제외하고 일반화 성능을 본다

- 결정: 같은 업종 holdout을 반복할 때는 이전 판단 세션에 들어간 이미지 해시를 제외할 수 있게 한다.
- 이유: 같은 브리프와 비슷한 Pinterest 쿼리를 1/2/3차로 반복하면 새 판단 테스트처럼 보여도 실제로는 같은 이미지가 다시 섞인다.
- 적용: `scripts/create_reference_training_session.py`에 `--exclude-profile-history` 옵션을 추가했다.
- 운영 원칙: 같은 세션 안의 중복과 이전 세션 재등장을 분리해서 본다. 학습/리뷰 누적에는 재등장이 허용될 수 있지만, generalization holdout은 이전 세션 이미지를 제외한다.
## 2026-06-03 - Reference Judge 고도화는 검수 사유 태그와 learned rules를 1차 데이터 계약으로 사용

- 결정: 기원님 검수 결과를 단순 selected/shortlist/rejected로만 저장하지 않고 `reasonTags`를 함께 저장한다.
- 이유: 메타데이터와 검색어만으로는 취향/품질 판단을 일반화하기 어렵고, 반복 오판 패턴을 rule/playbook으로 환원하려면 구조화된 사유가 필요하다.
- 적용:
  - 콘솔 판단 훈련 UI에 사유 태그 버튼 추가.
  - 저장 시 `correction_summary.md`, `learned_rules.json` 자동 갱신.
  - 다음 holdout 비교는 `compare_reference_sessions.py`로 정확도/전이 패턴을 비교한다.

## 2026-06-03 - Qwen 비전 평가는 ComfyUI와 분리된 Reference Judge 보강 옵션으로 둔다

- 결정: `create_reference_training_session.py --qwen-vision` 옵션으로 Qwen/Ollama 비전 평가를 선택적으로 붙인다.
- 이유: ComfyUI 이미지 생성과 무관하게 레퍼런스 판단 정확도만 높일 수 있고, Qwen이 꺼져 있을 때도 기존 heuristic/session 생성은 계속 가능해야 한다.
- 적용:
  - cosmetics profile에서 `local_hb_sale_fit`, `benefit_hierarchy`, `product_trust`, `layout_usability`, `website_capture_risk`, `text_artifact_risk`를 판단 evidence로 사용한다.
  - hard reject 신호가 강하면 selected로 올리지 않는다.

## 2026-06-03 - cosmetics rejected gate는 hard reject 중심으로 완화한다

- 결정: `cosmetics_skincare` 판단 세션에서 rejected는 저해상도, 웹페이지/브라우저 캡처, 업종 오류, AI artifact, Qwen hard risk 같은 안정적 결함에만 강하게 적용한다.
- 이유: holdout 002에서 AI rejected 13건 중 11건이 기원님 기준 shortlist로 올라갔다. selected 오판을 줄이면서도 부분 참고 가치가 있는 이미지를 버리지 않으려면 rejected보다 shortlist를 우선해야 한다.
- 적용: `scripts/create_reference_training_session.py`에서 cosmetics의 weak copy space나 불충분한 metadata만으로 rejected를 만들지 않도록 수정했다.
- 운영 원칙: selected gate는 계속 엄격하게 유지하고, hard reject가 아닌 애매한 이미지는 사람 검수용 shortlist로 남긴다.
## 2026-06-03 - QA packaging evidence manifest

- 결정: 06_qa_packaging은 최종 패키지에 필요한 품질 근거 파일을 `qualityArtifacts`로 수집하고, 각 최종 파일 레코드에 `qualityEvidence`를 붙인다.
- 포함 파일: `planning-quality/planning-quality-audit.json`, `03_reference_research/reference-quality-report.json`, `03_visual_candidates/prompt-audit.json`, `03_visual_candidates/generation-quality.json`, `04_admin_selection/selected-assets.json`.
- 이유: 나중에 이미지 생성까지 연결됐을 때 선택된 후보가 어떤 레퍼런스, 프롬프트, 생성 품질, 사람 선택 근거를 통과했는지 QA manifest에서 한 번에 추적하기 위해서다.
- 누락/실패 처리: `selected-assets.json` 누락은 blocker로 보고, 나머지 품질 근거 누락이나 warning/fail 상태는 QA issue로 기록해 수정 단계로 라우팅한다.

## 2026-06-04 - Selected candidate evidence first

- 결정: QA evidence 판정은 전체 후보 통계보다 사람이 선택한 candidate 상태를 우선한다.
- 이유: 전체 후보 15개 중 12개가 실패했더라도 최종 선택 후보 1개가 정상 generated라면 최종 패키지 위험은 다르게 봐야 한다.
- 적용: `generation-quality.json`과 `prompt-audit.json`은 selected candidate item이 있으면 그 item의 상태로 pass/warning/fail을 우선 판정한다.
- 콘솔: `/api/runs/<run-id>`가 06 산출물인 `qa_report`, `final_package_manifest`, `qa_packaging`을 반환하고, 최종 패키지 화면에서 evidence 상태를 보여준다.
## 2026-06-07 - Meta Ad Library provider MVP 추가

- Pinterest reference provider를 제거하지 않고 `meta_ad_library` provider를 병행한다.
- 1차 범위는 `Ad Reference` 콘솔 탭, Playwright 카드 캡처, 광고 카피/CTA/링크/캡처 JSON 저장, 선택형 Qwen 태깅까지로 제한한다.
- OpenCLIP 랭킹, 사람 shortlist 저장, `reference-evidence.json` 변환, 01/02/03 자동 주입은 다음 단계로 분리한다.
- 경쟁사 광고 원본을 복제하지 않고 구조, 카피 패턴, 레이아웃 힌트만 참고한다.

## 2026-06-07 - Meta 광고는 카드 캡처가 아닌 원본 이미지 다운로드로 사용

- Meta 광고 카드 캡처는 수집 증거와 디버깅 용도로만 유지한다.
- 실제 레퍼런스 자산은 광고 카드 내부 CDN 이미지 URL에서 다운로드한다.
- 캐러셀 광고는 광고당 최대 10장까지 다운로드한다.
- 콘솔 수집 시 `현재 작업 레퍼런스로 연결`이 켜져 있으면 다운로드 이미지를 해당 run의 `references/selected/`와 `reference-manifest.json`에 `meta_ad_library` 출처로 등록한다.
- 등록된 이미지는 기존 `03_reference_research`와 이후 비주얼 프롬프트 단계가 Pinterest 레퍼런스와 동일하게 읽는다.

## 2026-06-07 - Meta 검색 쿼리는 Pinterest 검색 쿼리와 분리

- Pinterest는 `배너 디자인`, `카드뉴스 디자인` 같은 디자인 결과물 묘사형 검색을 사용한다.
- Meta Ad Library는 실제 광고주/광고 카피 검색이므로 `경쟁 브랜드`, `상품·성분`, `카테고리+혜택` 조합을 사용한다.
- 기본 Meta 검색 구성은 경쟁 브랜드 1~2개, 상품/성분 1개, 카테고리+혜택 1~2개로 한다.
- Meta 검색 결과는 실제 광고이지만 자동으로 좋은 레퍼런스는 아니므로 기존 Reference Judge 검수를 필수로 유지한다.

## 2026-06-07 - Meta 검색과 광고 성격 필터를 분리

- 검색어는 `누구/무엇의 광고를 찾는지`를 결정한다.
- 광고 성격 프로필은 `어떤 용도로 쓸 소재를 연결할지`를 결정한다.
- 기본 프로필은 `클린 제품 비주얼`이며 Qwen 판정 없이는 자동 selected로 연결하지 않는다.
- 단일 이미지 광고도 텍스트가 많은 가격 전단일 수 있으므로 `클린 제품 비주얼`과 분리한다.
- 경쟁 브랜드 공식/직접 광고주만 필요할 때 선택적으로 광고주명 일치 필터를 사용한다.

## 2026-06-08 - 레퍼런스 후보와 자동 제외 사례를 분리

- 실제 제작 레퍼런스 후보와 명확한 탈락 사례를 같은 목록에서 섞어 검수하지 않는다.
- Meta 광고 라이브러리 페이지 전체 캡처는 실제 광고 소재가 아니므로 `website_capture` 자동 제외 사례로 분류한다.
- 이미지 짧은 변 500px 미만은 제작 레퍼런스 품질 기준에 부족하므로 `low_resolution` 자동 제외 사례로 분류한다.
- 50장 배치는 저장 구조로만 유지하고, 사람 검수 UI는 전체 미완료 항목을 제한 없이 이어서 보여준다.
- 완료한 항목은 미완료 목록에서 즉시 제거하고 완료 탭에서만 확인한다.
# 2026-06-10 - 레퍼런스 학습은 수량보다 브리프 적합성을 우선

- `Reference Learning 1000`의 1,000장 수량 목표를 운영 기준에서 제외한다.
- 현재 활성 브리프와 업종, 시장, 출처, 이미지 무결성 기준을 통과한 이미지만 판단 훈련 화면에 노출한다.
- 프로젝트 생성 이미지, 로컬 inbox, 샘플, 다른 업종 훈련 시드는 기본 후보에서 제외한다.
- Meta Ad Library의 KR 검색 결과라도 해외 언어 중심 광고는 제외한다.
- 기존 사람 검수 기록은 보존한다.

## 2026-06-10 - Meta 수집은 업종별 검증 브랜드 레지스트리를 우선

- 화장품·스킨케어 20개와 주얼리·럭셔리 20개 브랜드를 초기 레지스트리로 둔다.
- 범용 키워드보다 브랜드 검색과 광고주명 엄격 일치를 우선한다.
- 브랜드 단위 수집 결과는 운영 run selected에 바로 넣지 않고 별도 보관한다.
- 업종별 1~3개 소량 수집으로 안정성을 확인한 뒤 브랜드를 계속 추가한다.
- 브랜드 광고 안에서도 제품·프로모션·디바이스·럭셔리 캠페인 역할이 다르므로 후속 브리프 역할 필터를 유지한다.

## 2026-06-13 - placeholder E2E와 live 제작 준비를 구분한다

- 생성 실패 후보는 selected로 저장하지 않는다.
- QA fail 또는 error/blocker issue가 있으면 06 승인을 차단하고 수정 단계로 라우팅한다.
- 선택된 ComfyUI workflow ID는 registry에 실제 존재해야 한다.
- placeholder 기반 01~07 통과는 제어 흐름 검증으로만 취급하며 live 생성 준비 완료의 근거로 쓰지 않는다.
- 07 완료라도 재사용 자산이 0개면 정상 제작 완료와 구분한다.
