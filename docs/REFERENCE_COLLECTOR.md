# Reference Collector

Pinterest 보드 이미지를 로컬 레퍼런스 인박스로 저장하는 MVP 도구다. public board를 먼저 대상으로 한다.

## Run Pipeline Hook

이벤트 run 안에 레퍼런스 수집 구간을 붙일 수 있다. 흐름은 `검색 계획 생성 -> Pinterest 보드 큐 등록 -> 원본 다운로드 -> reference-manifest.json 생성`이다.

### One Command Pipeline

검색 결과 자동 수집, 큐에 들어간 보드/핀 원본 다운로드, 자동 선별, manifest 저장, 03 이미지 후보 단계 갱신까지 한 번에 실행한다.

```txt
.venv\Scripts\python.exe scripts/workflow.py --run runs/[run-dir] --run-reference-pipeline --reference-query-limit 6 --reference-per-query-limit 24 --reference-select-count 30 --reference-update-03
```

검색 페이지는 건너뛰고 큐에 등록된 보드/핀만 처리:

```txt
.venv\Scripts\python.exe scripts/workflow.py --run runs/[run-dir] --run-reference-pipeline --reference-no-search --reference-select-count 30 --reference-update-03
```

특정 큐 source만 처리:

```txt
.venv\Scripts\python.exe scripts/workflow.py --run runs/[run-dir] --run-reference-pipeline --reference-no-search --reference-source [source-id] --reference-select-count 30 --reference-update-03
```

특정 source에서 이미지가 하나도 내려오지 않으면 명령은 실패한다. 이때 기존에 성공한 `selected` reference와 03 handoff는 보존되고, 실패 원인은 `reference-collection-plan.json`의 `fallback_summary`와 `reference-manifest.json`의 `selection.error`에 남는다.

큐에 등록된 보드/핀은 건너뛰고 Pinterest 검색 결과만 처리:

```txt
.venv\Scripts\python.exe scripts/workflow.py --run runs/[run-dir] --run-reference-pipeline --reference-no-queued --reference-query-limit 6 --reference-per-query-limit 24 --reference-select-count 30 --reference-update-03
```

검증:

```txt
.venv\Scripts\python.exe scripts/verify_reference_pipeline.py --run runs/[run-dir] --require-03
```

특정 source가 실제 선택과 03 handoff까지 이어졌는지 검증:

```txt
.venv\Scripts\python.exe scripts/verify_reference_pipeline.py --run runs/[run-dir] --require-03 --require-source [source-id]
```

### Fully Automated Search Pass

보드에 사람이 저장하기 전 단계까지 자동화하려면 Pinterest 검색 결과 페이지를 직접 읽고, 후보 이미지를 다운로드한 뒤, 해상도/여백/밝기/대비 기준으로 1차 선별한다.

```txt
.venv\Scripts\python.exe scripts/workflow.py --run runs/[run-dir] --auto-search-references --reference-query-limit 6 --reference-per-query-limit 24 --reference-select-count 30
```

결과:

```txt
runs/[run-dir]/references/candidates/[source-id]/
runs/[run-dir]/references/ranked-candidates.json
runs/[run-dir]/references/selected/
runs/[run-dir]/references/selected-references.json
runs/[run-dir]/references/reference-manifest.json
```

작게 테스트:

```txt
.venv\Scripts\python.exe scripts/workflow.py --run runs/[run-dir] --auto-search-references --reference-query-limit 1 --reference-per-query-limit 3 --reference-select-count 2
```

기본 자동 선별은 `deterministic_image_quality_v1`이다. 즉 이미지를 열어 크기, 밝은 여백, 대비, 종횡비를 점수화하고, Pinterest가 제공한 파일명/설명 텍스트에서 이벤트 카테고리 관련 단어를 찾아 `text_relevance_score`를 더한다.

Ollama의 Qwen-VL이 켜져 있으면 이미지 자체를 읽고 이벤트 목표/타깃/레퍼런스 기준으로 다시 평가할 수 있다.

```txt
.venv\Scripts\python.exe scripts/workflow.py --run runs/[run-dir] --auto-search-references --reference-query-limit 6 --reference-per-query-limit 24 --reference-select-count 30 --reference-reviewer qwen --reference-review-limit 40
```

추가 결과:

```txt
runs/[run-dir]/references/qwen-reviewed-candidates.json
```

Qwen 리뷰는 `decision`, `role`, `score`, `event_fit`, `category_fit`, `copy_space`, `reason`, `risk`를 기록한다. Ollama/Qwen이 꺼져 있거나 리뷰가 실패하면 다운로드와 휴리스틱 선별 결과는 유지된다.

### Handoff to 03 Visual Candidates

`03_visual_candidates`는 `runs/[run-dir]/references/reference-manifest.json`이 있으면 선택된 reference asset을 읽는다. 선택 레퍼런스는 아래 산출물에 trace로 남는다.

```txt
runs/[run-dir]/03_visual_candidates/visual-plan.json
runs/[run-dir]/03_visual_candidates/image-prompts.json
runs/[run-dir]/03_visual_candidates/candidate-manifest.json
```

기록되는 주요 필드:

```txt
reference_asset.asset_id
reference_asset.relative_path
reference_asset.source_id
reference_asset.query
reference_asset.score
reference_asset.quality_score
reference_asset.text_relevance_score
reference_asset.review_decision
reference_asset.review_score
```

1. 이벤트 입력의 `references`를 기반으로 검색어와 Pinterest 검색 URL을 만든다.

```txt
python scripts/workflow.py --run runs/[run-dir] --plan-references
```

생성 위치:

```txt
runs/[run-dir]/references/reference-collection-plan.json
```

2. 검색 URL로 Pinterest에서 핀을 고르고 보드에 저장한 뒤, 그 보드 URL을 큐에 넣는다.

```txt
python scripts/workflow.py --run runs/[run-dir] --add-reference-source "https://www.pinterest.com/USER/BOARD/" --reference-label skincare-clean --reference-limit 30
```

이미 로컬에 저장된 보드 이미지 폴더를 같은 파이프라인 소스로 넣을 수도 있다. Pinterest 로그인/접근 문제로 라이브 보드가 막힐 때, 브라우저 확장이나 수동 다운로드로 받은 폴더를 `assets/references/inbox/[folder-name]/`에 둔 뒤 import한다.

```txt
python scripts/workflow.py --run runs/[run-dir] --import-local-reference-source assets/references/inbox/[folder-name] --reference-label local-board-[name] --reference-limit 30
```

import된 소스는 `reference-collection-plan.json`과 `reference-manifest.json`에 함께 기록되므로, 이후에는 일반 보드 source처럼 특정 source만 골라 자동 선별하고 03단계로 넘길 수 있다.

```txt
python scripts/workflow.py --run runs/[run-dir] --run-reference-pipeline --reference-no-search --reference-source local-board-[name] --reference-select-count 30 --reference-update-03
```

3. 큐에 들어간 보드/섹션/핀 URL을 원본 이미지로 다운로드한다.

```txt
python scripts/workflow.py --run runs/[run-dir] --collect-references
```

4. 다운로드된 보드/핀 이미지를 읽고 점수화해 선택본으로 저장한다.

```txt
python scripts/workflow.py --run runs/[run-dir] --select-collected-references --reference-select-count 30
```

특정 source만 선별:

```txt
python scripts/workflow.py --run runs/[run-dir] --select-collected-references --reference-source [source-id] --reference-select-count 30
```

Qwen-VL로 이벤트 적합성까지 읽어서 선별:

```txt
python scripts/workflow.py --run runs/[run-dir] --select-collected-references --reference-source [source-id] --reference-reviewer qwen --reference-review-limit 40 --reference-select-count 30
```

결과:

```txt
runs/[run-dir]/references/raw/[source-id]-originals/
runs/[run-dir]/references/reference-manifest.json
```

Pinterest에서 검색 결과를 보드에 저장하는 단계는 로그인/봇 차단/계정 상태에 따라 변수가 커서 현재는 사람이 직접 큐레이션한다. 다운로드와 manifest 생성은 파이프라인 명령으로 자동 처리한다.

## Recommended: Chrome Extension

Pinterest 로그인/robot 문제를 줄이려면 Chrome 확장 프로그램 방식이 가장 낫다. 사용자가 평소 쓰는 Chrome에서 Pinterest에 직접 로그인한 뒤, 보드 페이지에서 버튼을 누르는 방식이다.

설치 보조:

```txt
install_pin_collector_extension.bat
```

설치 폴더:

```txt
tools/pinterest-board-collector-extension
```

설치/사용 방법:

```txt
tools/pinterest-board-collector-extension/README.md
```

확장 프로그램은 `Start Safe Download` 한 번으로 수집, 백그라운드 다운로드, 중복 건너뛰기, `metadata.json` 저장까지 처리한다.

Python/Playwright 수집기는 실험용으로 남겨둔다.

## Original Downloads: gallery-dl

원본 사이즈가 중요하면 `gallery-dl` 엔진을 쓰는 쪽이 더 정확하다. gallery-dl의 Pinterest extractor는 페이지 DOM의 preview 이미지가 아니라 Pinterest API의 원본 이미지 필드를 사용한다.

쉬운 실행:

```txt
reference_collect_originals.bat
```

동작:

- Pinterest board / section / pin URL 입력
- Chrome 로그인 쿠키 사용 가능
- 기본 20개 제한
- 요청 사이 sleep 적용
- 429 발생 시 5~10분 대기
- metadata JSON 저장

저장 위치:

```txt
assets/references/inbox/[folder-name]-originals/
```

수동 명령 예:

```powershell
.venv\Scripts\python.exe -m gallery_dl `
  --cookies-from-browser chrome `
  --directory "assets\references\inbox\light-d-originals" `
  --range 1-20 `
  --sleep-request 2-5 `
  --sleep 4-8 `
  --sleep-429 300-600 `
  --write-metadata `
  --write-info-json `
  --windows-filenames `
  "https://www.pinterest.com/USER/BOARD/"
```

## Easy Mode

프로젝트 루트의 `reference_collect.bat`을 더블클릭한다.

물어보는 값:

- `Board URL`: Pinterest 보드 주소
- `Folder name`: 저장 폴더명. 비워두면 URL에서 자동 생성
- `How many images?`: 저장할 이미지 개수. 기본 100
- `Show browser while collecting?`: 브라우저 창을 보고 싶으면 `y`

저장 위치:

```txt
assets/references/inbox/[folder-name]/
```

수집기는 기본적으로 Pinterest의 실제 보드 피드 응답이 확인될 때만 저장한다. 보드가 private이거나 비로그인 상태에서 접근되지 않으면 추천 이미지를 대신 저장하지 않고 중단한다.

## Private Boards

private/secret 보드는 먼저 프로젝트 루트의 `chrome_pinterest_login.bat`을 더블클릭한다.

1. 가능하면 기존 Chrome 창을 모두 닫는다.
2. 열린 일반 Chrome 창에서 Pinterest에 로그인한다.
3. 필요한 경우 수집할 보드를 한 번 연다.
4. 터미널 창으로 돌아와 Enter를 누른다.

Google 로그인이 `브라우저 또는 앱이 안전하지 않을 수 있습니다`로 막히면, Playwright 자동화 창이 아니라 이 `chrome_pinterest_login.bat` 방식을 사용한다.

이전 자동화 로그인 방식도 남겨두었지만, Google OAuth가 막을 수 있다.

```txt
pinterest_login.bat
```

기본 권장 방식:

```txt
chrome_pinterest_login.bat
```

로그인 세션은 아래 파일에 로컬 저장된다.

```txt
assets/references/pinterest-storage-state.json
```

`chrome_pinterest_login.bat`은 세션 저장 후 `scripts/check_pinterest_session.py`를 자동 실행해 Pinterest 쿠키가 실제로 저장됐는지 보여준다. 따로 확인하려면 아래 명령을 실행한다.

```txt
.venv\Scripts\python.exe scripts\check_pinterest_session.py
```

특정 보드 URL이 이 세션으로 접근되는지까지 확인:

```txt
.venv\Scripts\python.exe scripts\check_pinterest_session.py --url "https://www.pinterest.com/USER/BOARD/"
```

그 다음 `reference_collect.bat`을 다시 실행하면 이 세션을 자동으로 사용한다.

<!-- legacy flow:
1. 열린 브라우저에서 Pinterest에 로그인한다.
2. 필요한 경우 수집할 보드를 한 번 연다.
3. 터미널 창으로 돌아와 Enter를 누른다.

로그인 세션은 아래 파일에 로컬 저장된다.

```txt
assets/references/pinterest-storage-state.json
```

그 다음 `reference_collect.bat`을 다시 실행하면 이 세션을 자동으로 사용한다.
-->

## Basic Usage

```powershell
.venv\Scripts\python.exe scripts\collect_references.py `
  --url "https://www.pinterest.com/username/board-name/" `
  --out assets\references\inbox\board-name `
  --limit 200
```

결과:

- 이미지 파일: `assets/references/inbox/[board-name]/`
- 메타데이터: `metadata.jsonl`
- 실행 요약: `collection-summary.json`

각 metadata record에는 원본 보드 URL, pin URL, 이미지 URL, 실제 다운로드 URL, sha256, 저장 경로가 남는다.

## Dry Run

다운로드 없이 추출만 확인한다.

```powershell
.venv\Scripts\python.exe scripts\collect_references.py `
  --url "https://www.pinterest.com/username/board-name/" `
  --out assets\references\inbox\board-name `
  --limit 50 `
  --dry-run
```

## Browser

기본은 설치된 Google Chrome을 Playwright channel로 사용한다. 문제가 있으면 Edge로 바꾼다.

```powershell
.venv\Scripts\python.exe scripts\collect_references.py `
  --url "https://www.pinterest.com/username/board-name/" `
  --out assets\references\inbox\board-name `
  --browser-channel msedge `
  --headful
```

## Access Problems

다음 메시지가 나오면 Pinterest가 해당 보드를 public 보드 피드로 보여주지 않은 것이다.

```txt
Pinterest board is not accessible
Could not find Pinterest BoardFeedResource items
```

이 경우 보드 URL이 틀렸거나, 보드가 private/secret이거나, 로그인 세션이 필요한 상태일 수 있다. 기존 버전처럼 화면에 보이는 추천 이미지를 강제로 저장하려면 `--allow-page-fallback`을 붙일 수 있지만, 레퍼런스 수집에는 권장하지 않는다.

## Next Step

수집된 이미지는 승인/반려 분류 후 `assets/references/feedback.jsonl`로 쌓고, `scripts/reference_vision.py`의 OpenCLIP/scikit-learn 학습 입력으로 사용한다.
