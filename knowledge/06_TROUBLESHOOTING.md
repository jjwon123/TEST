# 문제 해결 기록

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
