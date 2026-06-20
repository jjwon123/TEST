# 문제 해결 기록

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
