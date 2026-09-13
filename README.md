# 이벤트 콘텐츠 자동화 프로젝트

이 저장소는 이벤트 입력을 받아 **근거 검수 → 콘셉트·채널 문구 → 레퍼런스 방향 → 이미지 후보 → 사람 검수 → QA·아카이브**로 이어지는 콘텐츠 제작 콘솔입니다.

이 문서는 새 컴퓨터의 작업자나 AI 에이전트가 프로젝트를 안전하게 이어받기 위한 시작점입니다. 기준 문서와 데이터는 모두 저장소 안에 있으며, 비밀값과 대용량 이미지는 의도적으로 포함하지 않습니다.

## 먼저 읽을 문서

1. [`AGENTS.md`](AGENTS.md) — 작업 규칙, 단계와 기록 위치
2. [`knowledge/00_DASHBOARD.md`](knowledge/00_DASHBOARD.md) — 현재 상태와 사람에게 남은 일
3. [`knowledge/09_HANDOFF.md`](knowledge/09_HANDOFF.md) — 구현 이력, 알려진 병목, 다음 우선순위
4. [`docs/MAC_HANDOFF.md`](docs/MAC_HANDOFF.md) — macOS 설치·실행·이전 범위

AI 에이전트는 코드나 데이터를 바꾸기 전에 위 순서대로 읽고, 작업 완료 후에는 `knowledge/`의 해당 문서도 갱신합니다.

## Git으로 전달되는 것

| 영역 | 위치 | 용도 |
| --- | --- | --- |
| 이벤트·제품 설정 | `events/`, `products/`, `assets/rules/` | 이벤트 입력, 제품 정보, 안전·기획 규칙 |
| 학습·근거·문구 기준 | `design_brain_wiki/`, `knowledge/` | 레퍼런스 URL·평가, 마케팅 신호, 검수 기록, 의사결정 |
| 자동화 코드 | `pipeline/`, `services/`, `scripts/`, `core/`, `ui/` | 콘솔과 파이프라인 |
| 스키마·정책 | `core/schemas/`, `core/policies/`, `core/templates/` | 검증과 산출물 계약 |

## Git에서 의도적으로 제외되는 것

- 생성 이미지와 제품·레퍼런스 원본 이미지 (`*.png`, `*.jpg`, `*.webp` 등)
- 이벤트별 실행 산출물과 상태 (`runs/`)
- 수집된 레퍼런스 파일 (`references/`, `assets/references/`)
- API 키·브라우저 로그인 쿠키·로컬 가상환경 (`.env`, `.venv/`)

따라서 새 Mac에서는 **레퍼런스의 URL·선정 이유·평가·프롬프트 방향**과 문구·기획 학습 내용은 그대로 이어지지만, 이미지 원본을 꼭 재사용해야 하는 실행 런은 별도 저장소에서 복원하거나 다시 수집해야 합니다.

## macOS 빠른 시작

```bash
git clone --recurse-submodules <회사-저장소-URL>
cd "자동화 프로젝트"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
# .env에 필요한 키 또는 제공자 URL을 입력
bash scripts/start_brand_event_console.sh
```

브라우저에서 <http://127.0.0.1:5177>을 엽니다. 자세한 설정과 이미지 없이 검증하는 방법은 [`docs/MAC_HANDOFF.md`](docs/MAC_HANDOFF.md)를 따릅니다.

## 일상 운영 명령

```bash
# 새 이벤트 런 생성
python scripts/workflow.py --setup --event events/<이벤트명>

# 단계 실행 및 사람 승인
python scripts/workflow.py --run runs/<run-id> --stage <단계>
python scripts/workflow.py --run runs/<run-id> --approve <단계>

# 회귀 테스트
python scripts/run_project_tests.py
```

이미지를 만들지 않는 환경에서는 `COMFYUI_GENERATION_MODE=placeholder`를 유지합니다. 이 모드는 이미지 후보의 구조·프롬프트·선택 흐름을 확인할 수 있지만, 실제 생성 이미지로 승인해서는 안 됩니다.

## 저장소 경계

`pinterest-board-collector`는 Git 서브모듈입니다. clone 뒤 `git submodule update --init --recursive`로 맞춥니다. `pinterest-playwright-collector`는 현재 별도 작업 저장소이므로, 그 기능까지 옮길 때는 독립 저장소로 push/clone하거나 정식 서브모듈로 등록해야 합니다.

현재 작업 트리에 미커밋 변경이 있을 수 있습니다. 공유 전에 `git status`를 확인하고, 코드·설정·학습 데이터만 검토하여 커밋하세요. 이미지, `.env`, 쿠키, `runs/`는 커밋하지 않습니다.
