# 문제 해결 기록

## 2026-07-18 - "근거 검수 시작"을 눌러도 아무 일도 일어나지 않는 것처럼 보임

- 원인: 검수 시작 뒤 이동하는 `#marketingSignalReview`가 접힌 `전체 작업과 고급 검수 보기` 안에 있어, 스크롤 대상이 화면에 표시되지 않았다.
- 해결: `focusEvidenceEvent()`가 검수 데이터를 불러온 뒤 해당 details를 자동으로 열고 검수 패널로 스크롤한다.
- 검증: 로컬 콘솔에서 버튼 클릭 후 검수 패널 1개, details open 상태, 브라우저 오류 0개를 확인했다.

## 브리프는 `needs_input`인데 런은 일반 승인 대기로 표시됨

날짜: 2026-07-18

- 증상: `strategic-brief.json`은 `needs_input`이고 만료 일정 질문도 있지만
  `run-status.json`은 `review_pending / brief_review`로 남았다.
- 원인: 01 핸들러가 산출물 상태와 무관하게 고정 상태를 반환했다.
- 해결: 미해결 질문을 `needs_input / brief_input_required`로 전파하고,
  `approve_stage`에서도 미해결 브리프 승인을 거절한다.
- 추가: `brief_input_required`를 공식 런 상태 레지스트리에 등록했다.
- 검증: 실제 2026-07-18 장마철 런을 재실행해 상태 전파를 확인했고,
  운영 준비 감사와 회귀 테스트가 통과했다.

## QA 경고를 승인했는데 아카이브가 `done_no_assets`로 끝남

날짜: 2026-07-18

### 원인

- 6단계는 비차단 경고를 승인 메모와 함께 승인할 수 있었지만 7단계는
  QA 상태가 정확히 `pass`가 아니면 모든 프레임을 제거했다.

### 해결

- `approvals.json`에 사유가 있는 `06_qa_packaging=approved` 기록이 있을 때만
  `warn` 자산을 아카이브한다.
- 아카이브 레코드에는 `qa_status=warn`을 보존한다.
- 미승인 경고와 `fail`은 계속 전부 차단한다.

### 검증

- 승인 경고 허용·미승인 경고 차단 회귀 테스트를 추가했다.
- `scripts/smoke_test_full_pipeline.py`에서 `warn` 승인 후 물리 파일 `4개`가
  격리 아카이브로 복사되는 것을 확인했다.

## 시즌 화장품 프롬프트가 H&B 세일 누락 경고를 냄

날짜: 2026-07-18

- 원인: 화장품 프로필 전체에 `korean h&b sale`을 요구하고, 일반 프로필은
  존재하는 필수 방향 4개보다 큰 최소 적중 수 5개를 요구했다.
- 해결: H&B 세일 강제 조건을 제거하고 최소 적중 수가 실제 방향 수를 넘지
  않게 했다. 생성 부정 프롬프트에는 `broken korean text`를 추가했다.
- 결과: 대표 시즌 스모크 프롬프트 `12/12 pass`.

## 고정 전체 테스트 러너가 신규 테스트를 누락함

날짜: 2026-07-18

### 증상

- `scripts/run_project_tests.py`는 `234개`를 통과했지만 `unittest discover`는
  `239개`를 통과했다.
- 고정 러너가 전체 테스트라고 표시되지만 최근 추가된 루트 테스트 파일 5개가
  `TEST_MODULES`에 등록되지 않았다.

### 원인

- 고정 모듈 목록을 수동 관리하면서 근거 큐·출처 감사·제품 proof·공개 신호 수집
  관련 테스트 등록이 빠졌다.

### 해결

- 루트 `tests/test_*.py`를 `unittest` 자동 발견으로 전환했다.
- 자동 발견 범위 밖의 파이프라인·서비스·UI 계약 테스트만 명시 목록으로 유지한다.
- 전체 범위를 포함해 총 `266개`가 통과한다.
- `scripts/project_hook_check.py`도 수정된 고정 러너로 통과했다.

### 재발 방지

- 새 루트 테스트는 별도 목록 등록 없이 자동 포함된다.
- `tests/` 밖의 새 계약 테스트만 외부 모듈 목록에 등록한다.

## 증정 혜택이 시즌 캠페인을 프로모션으로 바꿈

날짜: 2026-07-18

- 원인: 이벤트 목적보다 오퍼의 `증정` 키워드를 먼저 판정했다.
- 해결: 명시 유형 → 이벤트명·목적의 주 의도 → 부가 오퍼 순으로 판정하고,
  확정 유형을 브리프 산출물에도 저장한다.
- 회귀: 시즌+증정은 `seasonal`, 증정 자체가 주 목적이면 `promotion`을 유지한다.

## 만료된 이벤트가 브리프 승인 대기처럼 보임

날짜: 2026-07-18

- 원인: 필수 날짜 존재만 검사하고 종료일이 현재보다 과거인지 확인하지 않았다.
- 해결: ISO 종료일이 지난 경우 `needs_input`과 일정 갱신 질문을 생성한다.
- 운영: 과거 일정을 임의로 연장하지 말고 실제 집행 일정을 입력한 뒤 새 런을 만든다.

## 채널 불일치와 반복 카피가 정상 기획을 차단함

날짜: 2026-07-18

- 원인: `instagram`, `blog` 같은 채널 그룹을 확장 산출물과 직접 비교했고,
  카드·피드·블로그에 같은 장문을 재사용했다.
- 해결: 채널 레지스트리로 요청 그룹을 확장한 뒤 비교하고, 채널별 첫 문장·제목·
  본문 방향을 분리했다. 운영 근거 문구도 사용자 카피에서 차단한다.

## 이벤트 후보를 하나씩 저장해야 해서 검수가 멈춤

날짜: 2026-07-01

해결:

- 필수 역할별 최고 후보를 선택하고 중복 역할은 보류하는 빠른 검수안을 제공.
- 사람이 확인창을 승인해야만 저장.
- 서버가 이벤트 범위와 사유 완결성을 재검증한 뒤 한 번에 저장.

주의:

- 확인창을 취소하면 API 호출과 데이터 변경이 없어야 한다.
- 현재 실제 테스트에서도 취소 후 15개 모두 unreviewed로 유지됐다.

## 검수 후보가 있는데도 `확보할 자료`가 모두 부족하다고 표시됨

날짜: 2026-07-01

원인:

- selected가 아닌 모든 필수 역할을 자료 없음으로 간주했다.

해결:

- `검수 전 역할`과 `후보 자체가 없는 역할`을 별도로 계산한다.
- `아직 부족함`은 selected 게이트 진행률을 표시한다.
- `확보할 자료`는 unreviewed 후보까지 포함해도 해당 역할이 없을 때만 표시한다.

현재 대표 5건 중 실제 추가 자료가 필요한 항목은 탄력 세럼의 제품 고유
성분·사용법·시험 자료뿐이다.

## 과거 검수 5건이 완료로 보이지만 모두 근거 준비 필요임

날짜: 2026-07-01

증상:

- 카드에는 `근거 준비 필요`가 표시되지만 헤더에는 `완료 5`, `근거 준비 0`으로
  표시된다.

원인:

- 근거 차단 이벤트를 미검수 목록 안에서만 집계했다.
- 과거 사람 검수 기록이 있으면 이벤트 근거 불일치와 무관하게 완료로 셌다.

해결:

- 근거 차단은 사람 검수 여부와 독립적으로 전체 이벤트에서 먼저 분리한다.
- 근거가 준비된 이벤트의 사람 검수만 완료로 집계한다.
- 근거 불일치 이벤트의 다음 작업을 카피 승인 대신 전용 근거 수집·재생성으로
  표시한다.

현재 정상 표시는 `검수 가능 0 · 근거 준비 5 · 완료 0`이다.

## 서로 다른 이벤트가 같은 마케팅 신호 ID를 사용함

날짜: 2026-06-30

증상:

- 벤치마크 근거 감사는 `20/20`이지만 겨울, 출시, 교육, 프로모션 카피가
  모두 비슷한 여름 고객 인사이트를 사용한다.

원인:

- 단일 `insight-brief.json`을 업종만 맞으면 모든 이벤트에서 재사용했다.
- 감사도 `marketingSignalIds`가 비어 있지 않은지만 확인했다.

해결:

- 이벤트별 `insight-briefs/<event-id>.json`을 저장한다.
- 생성 시 `InsightBrief.eventId == brief.event_id`를 강제한다.
- 신호 패킷은 정확한 `sourceRef.eventId` 또는 명시적 `topic`으로 제한한다.
- 감사에서 concept/copy의 `marketingEvidenceEventId`와 현재 이벤트를 대조한다.
- 불일치 결과는 콘솔 편집·승인을 차단한다.

확인:

```powershell
.venv\Scripts\python.exe scripts\audit_cosmetics_pilot_goal.py --limit 20
```

현재 기존 캐시는 `eventEvidenceMatched: 0/20`이 정상이다.

## 교정 학습 확인이 `수정 데이터 필요`로 표시됨

날짜: 2026-06-28

- 의미: 저장된 카피 검수 중 `originalCopy`와 `editedCopy`가 실제로 다른
  승인 레코드가 아직 없다.
- 단순히 점수만 저장하거나 원문 그대로 승인한 결과는 교정 학습 데이터로
  세지 않는다.
- 해결:
  1. 이벤트 기획 검수에서 `문구 직접 수정`을 연다.
  2. 헤드라인, 본문 또는 CTA를 실제로 수정한다.
  3. 점수와 사유를 확인하고 `검수 저장`을 누른다.
  4. `교정 학습 확인`을 실행한다.
- `적용 확인 필요`가 나오면 correction record의 `eventId`, `channelId`,
  `brandName`, `originalCopy`가 현재 로컬 생성 원문과 일치하는지 확인한다.
- 상세 결과:
  `.tmp/model-benchmarks/copy-correction-loop-audit.json`

## Playwright UI 감사가 기획 카드를 실제로 세지 못함

날짜: 2026-06-28

증상:

- 콘솔 UI 감사가 통과했지만 `planningCases`, `conceptCards`, `copyCards`가 실제 화면과 다르게 0으로 잡힐 수 있었다.
- 마케팅 신호 카드가 존재해 `planningDeskVisible` 조건이 우연히 통과했다.

원인:

- 감사기가 제거된 옛 클래스 `.planning-review-case`, `.concept-card`, `.copy-card`를 조회했다.
- 현재 UI 클래스는 `.planning-case-card`, `.planning-concept-card`, `.planning-copy-card`다.

해결:

- Playwright snapshot 셀렉터를 현재 실제 클래스명으로 교체했다.
- 카피 카드가 있으면 `[data-benchmark-copy-edit]` 수정 필드와 `.planning-review-form` 검수 폼도 존재해야 통과하도록 강화했다.

검증:

- 실제 DOM에서 기획 카드 3, 콘셉트 카드 9, 카피 카드 16, 수정 필드 200, 검수 폼 3을 확인했다.
- 1280px 가로 넘침 0, raw JSON/A-B/개발자 용어 노출 0.

## 콘셉트 비평기가 카피 미생성을 채널 불일치 치명 오류로 처리함

날짜: 2026-06-20

증상:

- 화장품 파일럿 5건의 화면 감사와 파일럿 목표 감사는 통과처럼 보였지만, 벤치마크 요약에는 `criticalErrors: 10`이 남았다.
- 결과 파일의 scorecard를 확인하면 `concept_critic_channel_mismatch`가 남아 있었다.

원인:

- 콘셉트 후보 생성 직후에는 아직 카피 패키지가 없다.
- 그런데 로컬 콘셉트 비평기가 빈 카피 패키지를 `score_planning`에 넣어 요청 채널과 생성 채널이 다르다고 판단했다.
- 결과적으로 콘셉트 단계의 비평 결과에 카피/채널 오류가 섞였고, 최종 scorecard에도 치명 오류로 전파됐다.

해결:

- `scripts/benchmark_ad_planning.py`의 로컬 비평을 분리했다.
- 카피 출력이 없을 때는 콘셉트 개수, 전략 축 중복, 3안 차별성, 마케팅 근거 준비 상태만 검사한다.
- 완성 결과에 scorecard 치명 오류가 있으면 stale cache로 보고 재생성한다.
- `scripts/audit_cosmetics_pilot_goal.py`가 내부 `scorecard.criticalErrorCount`까지 검사하도록 보강했다.

검증:

- `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5` 결과 `criticalErrors: 0`.
- `.venv\Scripts\python.exe scripts\audit_cosmetics_pilot_goal.py --limit 5` 결과 `pass`.
- 전체 테스트 170개와 Playwright 콘솔 UI 감사 통과.

## 모든 이미지가 제외된 Meta 광고의 Qwen 판정 상세가 사라짐

- 증상: manifest에는 `excludedImages` 숫자가 증가하지만 `accepted-ads.json`에서 제외 이미지의 `creativeType`, `qwenReview`, 제외 사유를 확인할 수 없었다.
- 원인: 광고의 모든 media가 제외되면 수집기가 해당 광고 레코드 전체를 건너뛰었다.
- 해결:
  - 모든 이미지가 제외된 광고를 `accepted-ads.json.excludedItems`에 보존한다.
  - 기존 배치는 `scripts/reclassify_meta_brand_batch.py --batch-id <batch-id>`로 네트워크 재수집 없이 재분류한다.
- 검증: 경쟁사 확장 배치 130장 모두의 Qwen 유형과 gate를 집계할 수 있고, 미분류 보류는 0장이다.

이 문서는 프로젝트에서 발생한 에러, 실패 사례, 해결 방법을 쌓는 곳이다.

## 기록 원칙

- 에러 메시지를 가능한 그대로 남긴다.
- 발생 조건과 해결 방법을 분리한다.
- 임시 해결과 근본 해결을 구분한다.
- 같은 문제가 반복되면 상위 기준 문서나 코드에 반영한다.

## 기록 템플릿

```text
날짜:
영역:
증상:
재현 방법:
원인:
임시 해결:
근본 해결:
관련 파일:
상태:
```

## 자주 볼 영역

- JSON 스키마 불일치
- 한글 인코딩 깨짐
- 이미지 후보 파일명 불일치
- Figma export 누락
- ComfyUI 워크플로 파일 경로 오류
- LM Studio 응답 포맷 깨짐
- 웹 UI와 단계 산출물 구조 불일치
- run 폴더와 루트 단계 폴더 산출물 혼동

## 현재 관찰된 이슈

### 광고 기획 콘솔에서 문구 근거가 설득력 없이 보임

날짜: 2026-06-17

증상:

- 최종 카피 카드의 `문구 근거`가 `concept_01`, `benchmark`, `선택한 콘셉트 기반`처럼 내부 값에 가깝게 보였다.
- 일부 캐시 결과에서 `직장인로`, `증정는` 같은 조사 오류가 노출됐다.
- 화면은 기획안처럼 보이지만 왜 그 문장을 썼는지 설득 근거가 약했다.

원인:

- 카피 패키지의 `strategyBasis`가 선택 콘셉트 ID 중심으로 저장됐다.
- UI가 근거를 한 줄로만 보여주고, 타깃·제품·혜택·채널 역할을 분리하지 않았다.
- 5177 콘솔 서버가 중복 실행되어 최신 파일을 재생성해도 오래된 API 응답이 섞였다.

해결:

- `strategyBasis`를 타깃 설정 이유, 제품 역할, 혜택 역할, 채널 역할을 연결한 설명 문장으로 변경했다.
- `planningEvidence`에 `target`, `productRole`, `offerRole`, `channelRole`, `verifiedFacts`를 저장한다.
- 콘솔 카피 카드에서 근거를 `문구 근거 / 타깃 / 제품 역할 / 혜택 역할 / 채널 역할`로 분리해 표시한다.
- `.tmp/model-benchmarks/`의 벤치마크 파일을 최신 로직으로 재생성하고, 중복 콘솔 서버를 정리했다.

검증:

- API와 브라우저에서 `직장인로`, `증정는` 0건.
- 광고 기획 관련 unittest 31개 통과.

### 한글 문서 인코딩 표시 깨짐

날짜: 2026-05-18

증상:

- PowerShell에서 일부 기존 Markdown 파일의 한글이 깨져 보인다.

영향:

- 실제 파일 내용 또는 터미널 출력 인코딩 문제일 수 있다.
- 기준 문서를 새로 만들 때는 UTF-8 Markdown으로 유지한다.

다음 확인:

- Obsidian에서 정상 표시되는지 확인한다.
- 필요하면 기존 `AGENTS.md`, `PIPELINE.md`의 인코딩을 백업 후 UTF-8로 정리한다.

### ComfyUI live 생성에서 `product_input.png` 400 오류

날짜: 2026-05-27

증상:

- `COMFYUI_GENERATION_MODE=live`로 `qwen_candidate_2511` 실행 시 `/prompt`가 HTTP 400을 반환.
- 에러 핵심: `image - Invalid image file: product_input.png`

원인:

- 제품 라이브러리가 없는 이벤트에서 `product_image` 기본값이 `product_input.png`로 떨어졌다.
- 현재 ComfyUI input에는 `qwen_image_edit_1024.png`가 유효한 fallback으로 존재한다.

해결:

- 제품 이미지가 없으면 `product_image`를 `image_need.product_image → image_need.base_image → qwen_image_edit_1024.png` 순서로 고르게 수정.
- ComfyUI HTTP 400 응답 본문을 `generation_error`에 그대로 남기도록 client 에러 처리를 보강.

관련 파일:

- `pipeline/03_visual_candidates/handlers/generate_visual_candidates.py`
- `services/comfyui/client.py`

상태:

- 해결

### ComfyUI live 생성 timeout 및 과한 샘플링 설정

날짜: 2026-05-27

증상:

- `qwen_candidate_2511` live 생성이 300초 대기 제한을 넘겨 pipeline에서는 실패로 기록됐지만 ComfyUI queue에는 job이 남음.
- 첫 실패 시 샘플링 값이 `28 steps / cfg 6.5 / dpmpp_2m`로 들어가 실행이 매우 느려짐.

원인:

- local preset `qwen_candidate_2511`의 권장값은 Lightning 기준 `8 steps / cfg 1.0 / heun`인데 stage fallback 기본값이 일반 SDXL용 값이었다.
- ComfyUI client 기본 history 대기 시간이 300초로 짧았다.

해결:

- `qwen_candidate_2511` stage 기본값을 `8 steps / cfg 1.0 / heun / beta`로 고정.
- ComfyUI client 기본 timeout을 1200초로 확대.
- stuck queue는 `/interrupt` 후 `/queue {"clear": true}`로 정리.

상태:

- 해결. 같은 테스트 그룹 3장 live 생성 성공 확인.

### prompt는 clean인데 live 결과에 mascot/character가 남음

날짜: 2026-05-28

증상:

- `bullion_investment` profile에서 positive prompt forbidden hit 0, prompt audit 15/15 pass.
- 그런데 live 결과 3장 모두 mascot/character가 남고, 일부는 fake/broken text와 random package/toy-like visual이 남음.

원인:

- `qwen_candidate_2511`은 image-edit workflow라 입력 이미지 영향을 크게 받는다.
- 제품 라이브러리가 없는 gold 이벤트에서 `product_image`와 `base_image`가 `qwen_image_edit_1024.png`로 들어간다.
- 이 fallback 이미지가 캐릭터/장난감 맥락을 포함하는 것으로 보이며, negative prompt만으로는 제거되지 않는다.

해결 방향:

- `bullion_investment`에서는 `qwen_image_edit_1024.png` fallback 사용 금지.
- neutral bullion/gold-bar input을 별도로 만들거나, 제품 입력이 없는 경우 bullion 전용 workflow/text-to-image 경로로 분기.
- live 재테스트는 1~3장만 수행.

관련 파일:

- `pipeline/03_visual_candidates/handlers/generate_visual_candidates.py`
- `runs/2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트/04_visual_candidates/live-small-test-report.md`

상태:

- 미해결. 다음 구현 필요.
## 2026-05-28 - bullion_investment live 생성이 캐릭터/장난감 방향으로 오염됨

### 증상

- `instagram_cardnews_01__key_visual` live 후보 3장이 모두 mascot/character, toy-like 3D, fake text 방향으로 생성됨.

### 원인

- 프롬프트 audit은 통과했지만 `qwen_image_edit_1024.png` fallback/base image 자체가 캐릭터 3D 맥락을 끌고 간 것으로 판단.
- bullion_investment의 레퍼런스 선택/탈락 기준이 코드에 일부 흩어져 있었고, 브랜드별 기준 데이터셋이 부족했다.

### 해결

- 실패 후보 3장을 `assets/reference_training/bullion_investment/bad/`에 bad reference로 저장했다.
- `assets/rules/visual-avoid-rules.json`에 mascot/cute/toy/kawaii/character/camping/picnic/theme park/wine bottle/package box/fake text/childish 3d/game-like UI 계열을 hard reject로 고정했다.
- `03_visual_candidates`에서 `bullion_investment`가 오염된 `qwen_image_edit_1024.png` fallback을 쓰지 않고 금/은 샘플 자산으로 대체하도록 차단했다.
## 2026-05-31 - 판단 훈련 세션이 Pinterest가 아니라 seed 이미지를 가져옴

### 증상

- `design_brain_wiki/training_sessions/bullion_investment/session_001/`을 실제 Pinterest 레퍼런스 30장 리뷰 세션으로 이해하고 있었지만, 실제로는 `assets/reference_training/bullion_investment/good|bad` seed 이미지를 복사한 세션이었다.
- 이 상태로 위키를 교정하면 실제 외부 레퍼런스 판단 기준이 아니라 seed 기준만 강화되는 문제가 있었다.

### 원인

- `scripts/create_bullion_training_session.py`가 run의 `references/` 산출물을 읽지 않고 seed metadata만 읽었다.
- `scripts/reference_pipeline.py`의 ranking 단계가 Pinterest collector의 `metadata.jsonl`을 보존하지 않아 selected 후보에서 `pin_url` 확인이 어려웠다.

### 해결

- `session_001`을 `sessionType: seed_test`로 라벨링했다.
- `create_bullion_training_session.py`에 `--run`, `--require-pinterest`, `--session-id` 옵션을 추가했다.
- `reference_pipeline.py`가 `metadata.jsonl`에서 `pin_url`, `image_url`, `downloaded_url`, `sha256`를 후보 record에 보존하도록 수정했다.
- 실제 검색 수집물로 `pinterest_session_001`을 생성했다.

### 검증

- `.venv\Scripts\python.exe`로 `03_reference_research` auto_search 성공.
- `pinterest_session_001` 결과:
  - total 30
  - selected 4 / shortlist 5 / rejected 21
  - 30/30 `sourceIsPinterest: true`
  - 항목별 `pinUrl` 기록됨.

### 주의

- 기본 `python`에는 Playwright가 없어 auto_search가 `ModuleNotFoundError: No module named 'playwright'`로 실패한다.
- Pinterest 자동 수집은 `.venv\Scripts\python.exe` 또는 Playwright가 설치된 런타임으로 실행해야 한다.
## 2026-05-31 - Pinterest 수집 자료가 한국 자료보다 해외 자료에 치우침

### 증상

- `pinterest_session_001`의 실제 Pinterest 자료가 금 투자 이벤트임에도 해외 금융/골드 이미지 중심으로 수집됐다.
- 사용자가 원한 한국 카드뉴스/배너/블로그 대표 이미지 감성과 거리가 있었다.

### 원인

- `assets/rules/reference-rules.json`의 `bullion_investment.searchQueries`가 `premium gold investment campaign visual`, `luxury financial consultation poster` 같은 영문 쿼리 중심이었다.
- Pinterest 검색 URL도 해당 영문 쿼리로 생성되어 한국 로컬 레퍼런스 우선 조건이 반영되지 않았다.

### 해결

- searchQueries를 한국어 우선으로 교체했다.
- `.venv` Python으로 `03_reference_research` auto_search를 재실행했다.
- 새 세션 `pinterest_kr_session_001` 생성:
  - total 30
  - selected 10 / shortlist 10 / rejected 10
  - 30/30 Pinterest/search 출처.

### 남은 주의

- Pinterest는 한국어 쿼리에서도 해외 이미지나 번역된 이미지가 섞일 수 있다.
- 최종 기준은 자동 selected가 아니라 기원님 빠른 비교 교정 결과로 잡아야 한다.

## 2026-06-03 - Qwen/Ollama reference reviewer가 로컬에서 연결되지 않음

### 증상

- `http://127.0.0.1:11434/api/tags` 요청이 실패했다.
- `ollama` 명령이 PATH와 일반 설치 경로에서 발견되지 않았다.
- `Get-Process`에서도 Ollama/Qwen 관련 프로세스가 확인되지 않았다.

### 영향

- `pinterest_holdout_004`를 "Qwen 켠 상태"로 생성할 수 없다.
- `--qwen-vision`을 붙인 reference training session 생성은 Qwen 서버가 켜질 때까지 보류해야 한다.

### 임시 대응

- heuristic/wiki judge는 계속 실행 가능하다.
- 004 생성 전에는 반드시 Qwen/Ollama 연결을 먼저 확인한다.
- 확인 명령:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing
where.exe ollama
```

## 2026-06-11 - Meta 브랜드 수집 배치 중단 또는 동시 실행

### 증상

- 같은 초에 시작한 브랜드 수집 작업이 같은 배치 경로를 사용한다.
- 수집 도중 프로세스가 중단되면 완료된 브랜드 결과를 알기 어렵고 처음부터 다시 실행해야 한다.
- 실패 브랜드만 다시 수집하기 어렵다.

### 해결

- 새 배치는 경로를 원자적으로 확보하며 충돌 시 `-02`, `-03` 접미사를 붙인다.
- 각 브랜드 시작/완료/실패 직후 `brand-collection-manifest.json`과 `failed-brands.json`을 원자적으로 갱신한다.
- 브랜드별 `collected-ads.json`, `accepted-ads.json`도 임시 파일 작성 후 교체한다.
- 완료 브랜드를 건너뛰고 재개:

```powershell
.venv\Scripts\python.exe scripts\collect_meta_brand_registry.py --profile cosmetics_skincare --batch-id <batch-id> --resume
```

- 실패 브랜드만 재시도:

```powershell
.venv\Scripts\python.exe scripts\collect_meta_brand_registry.py --profile cosmetics_skincare --batch-id <batch-id> --retry-failed
```

### 주의

- `--resume`과 `--retry-failed`에는 기존 배치 디렉터리 이름을 `--batch-id`로 지정해야 한다.
- 중단 당시 `collecting` 상태인 브랜드는 `--resume`에서 다시 수집한다.

## 2026-06-13 - Qwen/Ollama가 있는데 실행되지 않는 것처럼 보임

### 원인

- Ollama 서버와 `qwen2.5vl:7b` 모델은 정상이어도 현재 PowerShell PATH에서 `ollama` 명령이 안 잡힐 수 있다.
- 기존 시작 스크립트는 `C:\tmp\ollama\ollama.exe`와 `C:\tmp\ollama-models`를 고정해 현재 Windows 설치 위치와 모델 저장소를 놓칠 수 있었다.
- Ollama Qwen-VL 레퍼런스 검수와 ComfyUI Qwen Image Edit 이미지 생성은 별도 서비스다.

### 해결 및 확인

- 시작 스크립트는 `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`를 우선 자동 탐지하게 수정했다.
- 모델 저장소 강제 지정을 제거해 Ollama 기본 저장소를 사용한다.

```powershell
start_reference_ai.bat
.venv\Scripts\python.exe scripts\reference_vision.py health
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

### ComfyUI live timeout

- CLI가 timeout되어도 ComfyUI job은 계속 실행될 수 있다.
- `http://127.0.0.1:8188/queue`를 확인하고 필요하면 `/interrupt` 후 pending queue를 clear한다.
- 이번 감사에서는 Qwen Image Edit 2511 3장 그룹이 20분 내 완료되지 않아 중단하고 queue를 비웠다.
# 2026-06-14 - 신규 이벤트가 과거 H&B 세일 비주얼 방향을 상속함

- 증상: 차분한 장마철 장벽 케어 이벤트인데 03 레퍼런스와 04 프롬프트에 `orange accent`, `discount badge`, `Korean H&B sale` 방향이 포함됐다.
- 원인: `cosmetics_skincare` 공통 프로필의 prompt hints와 color palette가 이벤트별 브랜드 비주얼보다 우선 적용됐다.
- 해결: `run_reference_research._build_reference_direction()`에서 이벤트 references와 브랜드 visual mood/color가 있으면 공통 프로필 prompt hints를 제외하고 브랜드 팔레트를 우선 적용하도록 변경했다.
- 검증: 테스트 이벤트의 04 첫 프롬프트에서 `orange accent`가 제거되고 `#E8F0ED`가 포함됨을 확인했다.
- 남은 문제: prompt audit 자체는 아직 cosmetics 프로필에 `korean h&b sale`을 고정 요구하여 warning을 발생시킨다.
# 광고 카피가 낮은 품질인데 planning scorecard가 pass인 경우

- 증상: 조사 placeholder, 내부 작성용 문구, 동일 문장 반복이 있는데 `planning-scorecard.json`이 `pass`.
- 원인: 기존 QA가 금지어, 질문형 반복, 콘셉트 축 중복만 검사하고 한국어 자연스러움과 문장 반복을 검사하지 않았다.
- 해결: `score_planning()`에 `awkward_korean`, `repetitive_copy` 검사를 추가하고 전체 planning audit에 scorecard warning을 전달한다.
- 확인: `python scripts\run_project_tests.py`, `python scripts\project_hook_check.py`.
# 02 기획이 provider_unavailable로 차단되는 경우

- `OPENAI_API_KEY`가 설정되어 있는지 확인한다.
- 기본 모델은 `OPENAI_PLANNING_MODEL=gpt-5.5`다.
- `provider-budget.json`에서 호출 상한 8회가 소진됐는지 확인한다.
- 네트워크·응답 구조 오류는 planning 산출물의 `providerExecution`에서 확인한다.
- 외부 모델 장애 시 결정론적 초안을 승인하는 방식으로 우회하지 않는다.
# 2026-06-15 광고 기획 목표 감사가 `incomplete`인 경우

- 실행: `.venv\Scripts\python.exe scripts\benchmark_ad_planning.py`
- 실행: `.venv\Scripts\python.exe scripts\audit_ad_planning_goal.py`
- 리포트: `.tmp/model-benchmarks/ad-planning-goal-audit.json`
- 외부 결과가 0건이면 `criticalErrors: 0`이어도 `critical_errors_zero_on_all_cases`는 실패가 정상이다.
- `OPENAI_API_KEY`가 없으면 외부 생성은 `provider_unavailable / missing_api_key`로 기록되며 호출 예산은 소비하지 않는다.
- 전략을 `selected`로 저장할 때는 타깃 인사이트·후킹 방식·설득 순서·CTA 방식과 8개 루브릭 평균 4점 이상이 필요하다.
# 2026-06-16 - 광고 기획 리뷰 패킷이 blocked_waiting_for_api_key인 경우

### 증상

- `.venv\Scripts\python.exe scripts\export_ad_planning_review_packet.py` 결과가 `blocked_waiting_for_api_key`이다.
- `.tmp/model-benchmarks/ad-planning-review-packet.json`의 blocker에 `OPENAI_API_KEY_MISSING`가 포함된다.
- `scripts\benchmark_ad_planning.py --run-external --limit 5`를 실행해도 외부 결과가 `provider_unavailable`로 남는다.

### 원인

- OpenAI 외부 텍스트 모델 호출에 필요한 `OPENAI_API_KEY`가 현재 PowerShell 환경에 없다.
- 이 상태에서는 결정론적 baseline만 만들 수 있으며, baseline은 승인 가능한 광고 기획 결과가 아니라 비교 기준선이다.

### 처리

```powershell
if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) { 'OPENAI_API_KEY_MISSING' } else { 'OPENAI_API_KEY_AVAILABLE' }
```

- API 키가 설정된 같은 터미널에서 파일럿을 실행한다.

```powershell
.venv\Scripts\python.exe scripts\benchmark_ad_planning.py --run-external --limit 5
.venv\Scripts\python.exe scripts\export_ad_planning_review_packet.py
```

- 이후 콘솔 또는 `.tmp/model-benchmarks/ad-planning-review-packet.md`를 보고 콘셉트 선택과 사람 평가를 진행한다.
# 2026-06-16 - 전략 검수 CSV import에서 errors가 나오는 경우

### 증상

- `.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --import-sheet` 결과의 `errors`가 비어 있지 않다.

### 확인

- `decision`이 `selected`, `shortlist`, `rejected`, `unreviewed` 중 하나인지 확인한다.
- `selected`, `shortlist`, `rejected`는 8개 `score_...` 점수가 모두 필요하다.
- `selected`는 `targetInsight`, `hookMechanism`, `persuasionSequence`, `ctaType`이 비어 있으면 실패한다.
- `selected`는 8개 점수 평균이 4.0 이상이어야 한다.
- 전략 필드 `channelFit`과 루브릭 점수 `score_channelFit`을 혼동하지 않는다.

### 처리

- 오류 행을 수정한 뒤 먼저 dry-run을 다시 실행한다.
- errors 0일 때만 `--apply`를 붙여 실제 저장한다.
# 2026-06-16 - 광고 기획 파일럿 실행이 `blocked_waiting_for_api_key`인 경우

### 증상

- `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5` 결과가 `blocked_waiting_for_api_key`다.
- `.tmp/model-benchmarks/ad-planning-pilot-run.json`에서 `apiKeyAvailable: false`, `externalGenerationAttempted: false`로 표시된다.
- 콘솔의 파일럿 5건 실행/갱신 job은 성공했지만 외부 모델 결과가 0/5로 남는다.

### 원인

- 현재 PowerShell 세션에 `OPENAI_API_KEY`가 없다.
- 이 상태에서는 외부 모델 품질 기준선을 만들 수 없으므로 결정론적 baseline을 승인 가능한 광고 기획으로 대체하지 않는다.

### 처리

```powershell
if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) { 'OPENAI_API_KEY_MISSING' } else { 'OPENAI_API_KEY_AVAILABLE' }
```

- API 키를 설정한 같은 세션에서 다시 실행한다.

```powershell
.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5
```

- 콘솔 버튼으로 실행한 job이 실패하면 `.tmp/console-jobs/<job-id>.log`와 `.tmp/console-jobs/jobs.json`을 확인한다.
- 외부 모델 결과가 생긴 뒤에도 사람 콘셉트 선택, 최종 카피 평가, 수정문 저장이 끝나기 전에는 목표 감사가 `pass`가 될 수 없다.

# 2026-06-16 - 전략 CSV 콘솔 반영 job이 실패하는 경우

### 증상

- 콘솔에서 `Strategy CSV validate` 또는 `Strategy CSV apply`를 눌렀는데 job이 failed가 된다.
- `.tmp/console-jobs/<job-id>.log`에 CSV 검증 오류가 기록된다.

### 확인

- `decision`은 `selected`, `shortlist`, `rejected`, `unreviewed` 중 하나여야 한다.
- `selected`, `shortlist`, `rejected`는 8개 `score_...` 컬럼이 모두 1~5점이어야 한다.
- `selected`는 `targetInsight`, `hookMechanism`, `persuasionSequence`, `ctaType`이 비어 있으면 안 된다.
- `selected`는 8개 점수 평균이 4.0 이상이어야 한다.
- 루브릭 점수 컬럼은 `channelFit`이 아니라 `score_channelFit`이다.

### 처리

```powershell
.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --import-sheet
```

- dry-run의 `errors`를 모두 수정한 뒤에만 apply를 실행한다.

```powershell
.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --import-sheet --apply
```

# 2026-06-16 - 벤치마크 리뷰 CSV import에서 errors가 나오는 경우

### 증상

- `Benchmark CSV validate` 또는 아래 명령이 실패한다.

```powershell
.venv\Scripts\python.exe scripts\manage_ad_planning_benchmark_review_sheet.py --import-sheet
```

### 확인

- `blindPreferred`는 반드시 `A` 또는 `B`여야 한다.
- 8개 `score_...` 컬럼이 모두 있어야 하며 각 값은 1~5점이어야 한다.
- `approved`와 `edited`는 `true/false`, `yes/no`, `1/0` 형식으로 입력할 수 있다.
- 빈 행은 skipped로 처리되며 오류가 아니다.
- 외부 모델 결과가 없으면 `variantA` 또는 `variantB`가 `not available`일 수 있으므로, 실제 평가는 외부 모델 생성 후 CSV를 다시 export해서 진행한다.

### 처리

1. CSV의 오류 행을 수정한다.
2. dry-run을 다시 실행해 `errors: []`를 확인한다.
3. 그 뒤에만 apply를 실행한다.

```powershell
.venv\Scripts\python.exe scripts\manage_ad_planning_benchmark_review_sheet.py --import-sheet --apply
```
## 2026-06-17 - OpenAI API를 쓰지 않는 경우

### 정상 상태

- `OPENAI_API_KEY`가 없어도 광고 기획 파일럿은 local provider로 실행된다.
- `.tmp/model-benchmarks/ad-planning-pilot-run.json`의 `provider`가 `local`이고 `pilotCandidateReady`가 증가하면 정상이다.

### 실행

```powershell
.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5
```

### 남는 blocker 의미

- `STRATEGY_REVIEW_BELOW_30`: 전략 CSV에서 selected/shortlist 검수가 30건 미만이다.
- `PILOT_HUMAN_REVIEWS_INCOMPLETE`: 후보 생성 후 사람이 콘셉트 선택/카피 평가를 아직 완료하지 않았다.
- `PILOT_CANDIDATE_RESULTS_INCOMPLETE`: local 후보 생성 자체가 부족하다.

### 스킬 검증

```powershell
.venv\Scripts\python.exe C:\Users\jinkiwon\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\jinkiwon\.codex\skills\ad-planning-copy-engine
```
## 2026-06-17 - local 후보 한국어가 깨져 보이는 경우

### 확인

```powershell
.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5
```

`.tmp/model-benchmarks/cosmetics-external-results.json`의 `provider`가 `local`이고 콘셉트명이 정상 한국어인지 확인한다.

### 기대 예시

- `일상의 불편을 다시 정의하는 캠페인`
- `선택 근거를 또렷하게 보여주는 캠페인`
- `나에게 맞는 순간으로 연결하는 캠페인`

### 계속 경고가 남는 경우

- `awkward_korean`: 깨진 문자열, 과도한 질문형, 반복 문장이 남았다.
- `repetitive_copy`: 채널 간 또는 슬라이드 간 동일 문장이 너무 많이 반복된다.
- 경고가 남으면 사람 수정 후 correction record로 저장한다.

## 2026-06-17 - 콘솔에 개발자용 상태값이나 JSON이 보이는 경우

### 증상

- 메인 검수 화면에 `Provider`, `Blockers`, `meta_strategy_*`, `concept_selection_pending`, `reason_to_believe` 같은 문자열이 보인다.
- 카피 카드에 JSON 원문이 그대로 보이거나 A/B 비교 카드가 나타난다.
- 긴 카피가 카드 밖으로 가로로 넘친다.

### 처리

1. 브라우저를 새로고침한다. 캐시가 남으면 `http://127.0.0.1:5177/?ui_refresh=<timestamp>`로 다시 연다.
2. 콘솔 메인에 `광고 기획 검수 데스크`가 보이는지 확인한다.
3. `node --check ui\console\app.js`로 JS 문법을 확인한다.
4. 문제 문구가 계속 보이면 `ui/console/app.js`의 planning desk renderer가 아니라 예전 benchmark renderer가 호출되는지 확인한다.

### 정상 기준

- 메인 검수 화면의 금지 문구 노출 0건.
- A/B 카드 노출 0건.
- JSON 문자열 노출 0건.
- 1280px 화면에서 가로 overflow 0건.
# Playwright 콘솔 감사 문제 해결 (2026-06-18)

## 증상

- `scripts/audit_console_ui_playwright.py` 실행 시 Playwright 브라우저 실행 오류가 날 수 있다.

## 원인

- Playwright Python 패키지는 설치되어 있어도 전용 Chromium 바이너리가 없을 수 있다.

## 해결

- 감사 스크립트는 Playwright 번들 Chromium이 없으면 설치된 Chrome, Edge 순서로 자동 재시도한다.
- 그래도 실패하면 `python -m playwright install`로 브라우저를 설치한다.

## UI 감사 실패 기준

- 메인 화면에 `meta_strategy`, `concept_selection_pending`, `provider`, `blockers`, `hook`, `cta` 같은 개발자 코드가 노출됨.
- raw JSON 문자열이 그대로 보임.
- `안 A / 안 B` 또는 A/B 비교가 다시 나타남.
- 1280px 화면에서 가로 넘침이 생김.
- 깨진 한글 또는 대체 문자가 보임.
## 2026-06-20 - 파일럿 목표 감사가 깨진 한글 때문에 실패하는 경우

- 증상:
  - `scripts/audit_cosmetics_pilot_goal.py --limit 5` 결과가 `fail`.
  - 후보 준비, 카피 준비, 사람 평가는 5/5인데 `criticalErrorCount`가 5로 표시된다.
- 원인:
  - 파일럿 평가셋, 생성 캐시, 사람 리뷰 메모 일부에 mojibake 형태의 깨진 한글이 남아 있다.
  - 예: `?λ쭏`, `罹`, `怨`, `寃` 같은 문자가 사용자용 이벤트명이나 카피 후보에 섞이는 경우.
- 해결:
  - `services/ad_strategy/text_quality.py`의 공용 검사기가 깨진 한글/raw JSON/HTML/프로그래밍 구조를 잡는다.
  - `services/ad_strategy/quality_gate.py`는 최종 카피에서 이 문제가 보이면 `critical`로 차단한다.
  - 평가셋과 리뷰 파일을 정상 UTF-8 한국어로 정리한 뒤 `scripts/run_ad_planning_pilot.py --limit 5`를 다시 실행한다.
  - 근거 신호가 비어 있는 케이스는 ready `InsightBrief` 상태에서 재생성해야 한다.
## 2026-07-01 - 제품 근거가 없어 이벤트가 준비 완료되지 않는 경우

### 증상

- `신제품 탄력 세럼 출시`에 `제품 근거`가 부족하다고 표시된다.
- 공개 조사 자료가 있어도 이벤트 근거 준비가 완료되지 않는다.

### 원인

- 시장·고객 연구는 개별 제품의 성분, 사용법, 인체적용시험 결과를 증명하지 않는다.
- 제품 라이브러리에 유사 세럼이 있어도 이벤트 제품과 동일하다는 확인이 없다.

### 해결

1. 이벤트의 `수집·검수 시작`을 누른다.
2. `공식 제품 근거 추가`에서 브랜드 공식 HTTPS URL 또는 내부 문서 번호를 입력한다.
3. 출처에서 직접 확인한 사실과 주장하지 말아야 할 범위를 함께 적는다.
4. 저장된 제품 근거 카드를 원문과 대조해 선택/보류/거절한다.

### 저장이 차단되는 경우

- 공식 페이지 URL이 HTTPS가 아님
- 내부 자료인데 문서 번호가 없음
- 확인 사실·기획 해석·주장 제한·확인 방법이 지나치게 짧음
- 기획 해석에 확인 사실에는 없는 수치가 추가됨
- 치료, 완치, 영구 효과 등 고위험 효능 표현이 포함됨

### UI 감사에서 Playwright 미설치 오류가 나는 경우

- 프로젝트 파일을 변경하지 않고 `.tmp/playwright-runtime`에 Python Playwright를 임시 설치한 뒤 `PYTHONPATH`로 연결해 감사할 수 있다.
- 2026-07-01 기준 이 방식으로 라이브 콘솔 감사가 통과했다.
## 2026-07-02 - 연결 테스트 승인이 사람 평가로 잡히는 경우

### 증상

- 실제로 최종 검수하지 않았는데 사람 평가 수나 무수정 승인율이 올라간다.
- 검수 메모에 `연결 단계 확인용`이 들어 있다.

### 해결

- `reasonTags`에 `connection_test`가 있거나 `conceptSelectionSource`가 `connection_check_default`이면 최종 평가에서 제외한다.
- 벤치마크와 검수 패킷을 다시 계산해 공식 사람 평가 수를 확인한다.

## 2026-07-02 - 새 근거를 검수했는데 예전 카피가 남는 경우

- 근거가 준비 완료되면 해당 이벤트를 `force_refresh`해 콘셉트 선택 대기로 되돌린다.
- 새 근거가 이전 선택 뒤에 들어왔으면 기존 선택과 카피를 폐기한다.
- 근거가 다시 부족해지면 `evidence_review_required` 상태인지 확인한다.

## 2026-07-05 - 파일럿 5건이 화면·CSV·감사에서 서로 다른 경우

### 원인

- 각 스크립트가 `cases[:5]`처럼 벤치마크 배열의 앞 5건을 따로 선택했다.
- 근거 계획의 시즌·프로모션·출시·교육·브랜딩 대표 5건과 달라졌다.

### 해결

- 모든 파일럿 경로에서 `services/ad_strategy/pilot_selection.py`를 사용한다.
- 올바른 순서는 장마철, 증정 프로모션, 탄력 세럼 출시, 장벽 교육,
  미니멀 브랜딩이다.
- 패킷의 `pilotCaseIds`, 감사의 `pilotCaseIds`, 검수 CSV의 `caseId` 순서를
  함께 비교한다.

### 콘셉트는 있는데 준비 완료가 아닌 경우

- `marketingEvidenceStatus`가 `ready`인지 확인한다.
- `marketingEvidenceEventId`가 현재 케이스 ID와 같은지 확인한다.
- 둘 중 하나라도 다르면 `evidence_review_required`가 정상이며, 근거 검수를
  마치기 전 콘셉트를 선택하지 않는다.

## 2026-07-05 - 시즌 이벤트가 프로모션으로 잘못 분류되는 경우

### 증상

- 장마철·여름 이벤트인데 콘셉트 결과의 `eventType`이 `promotion`이다.
- 이벤트에 사은품이나 증정 혜택이 함께 들어 있다.

### 원인

- 혜택 키워드 추정이 명시된 이벤트 유형보다 먼저 적용됐다.

### 해결

- benchmark brief와 실제 brief에 `event_type`을 전달한다.
- `detect_event_type()`은 유효한 명시값을 먼저 반환한다.
- 비평 결과에 `event_type_mismatch`가 있으면 선택하지 않고 다시 생성한다.

## 2026-07-05 - 콘셉트 근거 ID는 3개지만 실제 설명은 1개인 경우

- `primarySignalIds`가 전략 축을 만든 핵심 근거다.
- `supportingSignalIds`는 맥락을 보강하는 근거다.
- 두 목록의 합이 `signalIds`와 일치해야 한다.
- 핵심 근거가 없거나 전체 신호가 3개 미만이면 `concept_evidence_thin`으로
  수정 대상이 된다.

## 2026-07-05 - 근거 준비가 끝났는데 카드가 완료 또는 근거 부족으로 보이는 경우

### 원인

- 콘셉트 단계에서 최종 카피까지 요구하는 `evidenceConnected`를 사용했다.
- 과거 `connection_test`의 `reviewedAt`을 최종 사람 검수로 잘못 셌다.

### 해결

- 콘셉트 단계는 `candidateReady.evidenceReady`를 사용한다.
- `humanReviewStatus=pending`, `connection_test`,
  `connection_check_default`는 완료로 세지 않는다.
- 준비 완료·미선택 이벤트가 검수 데스크 첫 카드에 나오고 선택 버튼 3개가
  보이는지 확인한다.

## 2026-07-05 - Playwright 감사가 숨겨진 카피 카드 때문에 실패하는 경우

- 전체 DOM의 `.planning-copy-card` 수만 세면 숨겨진 다른 화면의 카드까지
  포함될 수 있다.
- 감사기는 각 `.planning-case-card` 내부에서 카피, 편집 필드, 검수 폼,
  근거 차단, 품질 차단을 함께 확인해야 한다.
- 준비 완료 콘셉트 카드에는 자동 품질 요약과 선택 버튼이 모두 있어야 한다.

## 2026-07-05 - 글자 수가 실제 카피보다 크거나 수정 후 달라지는 경우

### 원인

- `len(str(copy))` 또는 JSON 문자열 길이로 딕셔너리의 괄호와 필드명까지
  함께 셌다.

### 해결

- `copy_character_count()`로 중첩 카피 안의 사용자 표시 문자열만 모아 센다.
- 최초 생성, 외부 구조화 결과 파싱, 콘솔 수정 저장에서 모두 같은 함수를
  사용한다.

## 2026-07-05 - `토너을`, `토너은` 또는 카드뉴스 전환 반복이 생기는 경우

- 제품명 뒤 조사를 문자열로 고정하지 말고 `_particle()`로 선택한다.
- `으로/로`는 받침 `ㄹ` 예외도 처리한다.
- 카드뉴스의 `transition`은 공통 문장 대신 다음 슬라이드 제목을 사용한다.
- 채널 내부에서 같은 문장이 3회 반복되면 `repetitive_copy`로 수정
  요청한다.

## 2026-07-12 - 파일은 모두 approved인데 02단계 승인이 거절되는 경우

### 확인

```powershell
python scripts\validate_ad_planning_output.py --run-dir runs\<run-id>
```

### 주요 원인

- `concept-review.json`의 선택 ID와 `copy-package.json`의 `conceptId`가 다름.
- 콘셉트 3안이 제목만 다르고 전략 항목 두 개 이상이 갈리지 않음.
- 입력에서 요청하지 않은 채널 결과가 포함됨.
- `characterCount`가 실제 표시 문장 길이와 다름.
- 점수 평균은 4.0 이상이어도 경고가 남아 있음.
- 사람 선택 사유 태그나 검수 메모가 비어 있음.

검증기의 `path`와 한국어 메시지에 표시된 산출물을 수정한 뒤 다시 승인한다.

## 2026-07-12 - 기획 카드는 한국어인데 상단·최근 작업은 영어인 경우

### 원인

- 광고 기획 패널만 한국어화하고 공용 `stageLabel()`과 `nextActionKo()`가
  영어를 다시 반환했다.

### 해결

- 단계 ID는 `stageLabel()`에서 한국어 단계명으로 변환한다.
- 서버의 영문 `next_action`은 `nextActionKo()`에서 한국어 행동 문장으로
  변환한다.
- `scripts/audit_console_ui_playwright.py`의
  `operationLabelsLocalized`가 메인 화면 전체의 알려진 영어 운영 문구를
  검사하는지 확인한다.

## 2026-07-12 - 메인에서 무엇을 눌러야 할지 다시 모호한 경우

- `[data-primary-planning-action]` 중 실제 보이는 요소가 정확히 1개인지
  확인한다.
- 숨겨진 다른 화면의 동일 패널은 `display`, `visibility`,
  `getClientRects()` 기준으로 감사 집계에서 제외한다.
- 목표·근거·교정 감사는 `.planning-diagnostics` 안에 있고 기본 닫힘이어야
  한다.
- 라이브 감사의 `primaryPlanningActionVisible`이 실패하면 핵심 행동 카드의
  중복 또는 누락을 먼저 수정한다.

## 2026-07-18 - `카피 검수 시작`을 눌러도 화면이 바뀌지 않는 경우

### 원인

- 홈 재설계에서 기존 `planningReviewDesk`를 닫힌 `studio-diagnostics` 안으로
  이동했지만 `openPlanningReview()`는 바깥 details를 열지 않고 숨겨진 패널만
  스크롤·포커스했다.
- 결과적으로 클릭 이벤트는 실행됐지만 사용자가 보는 화면과 다음 행동은
  바뀌지 않았다.

### 해결

- 홈 CTA는 숨겨진 고급 패널을 여는 대신 `missionMode=copy_review`로 전환한다.
- 전용 검수 화면에서 `카피 읽기 → 필요한 문구 수정 → 판단 근거 남기기 →
  검수 저장` 순서를 표시한다.
- 채널별 카피 카드와 최종 결정 폼을 같은 화면에 배치한다.
- 검수 화면에 `scroll-margin-top`을 지정해 고정 상단 바에 제목이 가리지 않게
  한다.

### 확인

- 클릭 후 `[data-copy-review-case]`가 1개 보여야 한다.
- `.copy-review-guide li` 4개, 카피 카드 4개, 최종 결정 패널 1개가 보여야 한다.
- 사유 태그 없이 저장하면 `카피 검수는 사유 태그 1개 이상과 구체 메모가
  필요합니다.` 안내가 나와야 한다.

## 2026-07-18 - 카피 검수 오른쪽 사유 태그가 글자 단위로 줄바뀌는 경우

### 원인

- 전역 `select,input,textarea { width:100% }` 규칙이 checkbox에도 적용됐다.
- 좁은 최종 결정 패널의 2열 태그 카드에서 checkbox가 행 전체 폭을 차지해
  한국어 라벨이 밀렸다.

### 해결

- 사유 태그는 단일 열로 바꾸고 checkbox에는 `width:auto`, 16px 높이,
  0 padding을 명시한다.
- 저장 성공 후 토스트만 보여주지 말고 완료 화면에서 다음 검수 또는 방금 검수
  다시 보기를 선택하게 한다.
> 2026-07-18 — 근거 검수 완료 후 멈춤: 완료된 검수 화면만 다시 열고 기획안을 새로고침하지 않아 다음 미션으로 이어지지 않았다. 근거 검수는 한 카드씩 판정하고, 마지막 판정 시 기획안을 갱신해 콘셉트 선택으로 전환하도록 수정했다.
