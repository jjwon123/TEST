# macOS 이식 및 AI 인수인계

## 목적과 범위

이 이식은 **이미지 파일 없이** 이벤트 콘텐츠 자동화를 이어가는 방식이다.

- 포함: 이벤트·제품 설정, 근거 URL과 평가, 마케팅 신호, 문구·기획 학습 데이터, 프롬프트 규칙, 콘솔·파이프라인 코드
- 제외: ComfyUI 생성 결과, 제품/레퍼런스 원본 이미지, 실행 중인 `runs/`, 로그인 쿠키, API 키

이미지 없는 Mac에서도 근거 검수, 콘셉트·문구 생성/검수, 설정 변경, QA 규칙 점검, 새 레퍼런스 수집 계획을 진행할 수 있다. 실제 이미지 생성·기존 이미지 재사용은 별도 이미지 저장소 또는 ComfyUI 환경이 준비된 뒤에만 진행한다.

## AI 작업 시작 절차

다른 컴퓨터의 AI는 다음 순서를 따른다.

1. 루트의 `AGENTS.md`를 읽는다.
2. `knowledge/00_DASHBOARD.md`와 `knowledge/09_HANDOFF.md`로 현재 상태·다음 작업을 확인한다.
3. 해당 이벤트는 `events/<이벤트명>/`에서, 제품은 `products/`에서 확인한다.
4. 근거·학습·문구 기준은 `design_brain_wiki/`와 `assets/rules/`에서 찾는다.
5. 구현을 바꾼 뒤 관련 테스트를 실행하고, 결정/구조/문제/현재 상태를 `knowledge/`에 기록한다.

사람 승인과 실제 효능·성분 주장 검증은 자동화하지 않는다. 이벤트 근거는 사람이 `선택 / 보류 / 제외`하고, 제품 고유 주장은 공식 제품 자료가 있어야 한다.

## Mac 초기 설치

필수 도구는 Git, Python 3.10 이상, Node.js(콘솔 UI 검사 시), Chrome 또는 Playwright Chromium이다.

```bash
git clone --recurse-submodules <회사-저장소-URL>
cd "자동화 프로젝트"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium

cp .env.example .env
set -a; source .env; set +a
bash scripts/start_brand_event_console.sh
```

콘솔 주소는 <http://127.0.0.1:5177>이다. 실행할 때마다 `.env`를 shell에 불러오거나, 사용하는 터미널/서비스의 환경 변수로 등록한다. 이 프로젝트는 `.env` 파일을 자동으로 읽지 않는다.

## 환경 변수

`.env.example`은 안전한 빈 템플릿이다. 실제 키와 쿠키는 Git에 넣지 않는다.

| 목적 | 변수 | 필요 시점 |
| --- | --- | --- |
| 구조화된 기획 모델 | `OPENAI_API_KEY` | 외부 OpenAI 기획 모델을 사용할 때 |
| 범용 LLM HTTP 제공자 | `LLM_PROVIDER_URL`, `LLM_PROVIDER_TOKEN` | 별도 사내/외부 제공자를 연결할 때 |
| 외부 리서치 제공자 | `RESEARCH_PROVIDER_URL`, `RESEARCH_PROVIDER_TOKEN` | 실시간 리서치 API를 연결할 때 |
| 로컬 레퍼런스 AI | `REFERENCE_REVIEW_HOST`, `REFERENCE_REVIEW_MODEL` | Ollama/Qwen 검수를 사용할 때 |
| 이미지 후보 모드 | `COMFYUI_GENERATION_MODE` | `placeholder` 또는 실제 ComfyUI 생성 |

키가 비어 있으면 관련 기능은 안전한 로컬 초안 또는 스냅샷 처리로 폴백한다. 키가 없다는 이유로 이벤트 사실이나 사람 승인을 만들어 내면 안 된다.

## 이미지 없이 운영하기

기본값은 아래처럼 둔다.

```bash
export COMFYUI_GENERATION_MODE=placeholder
```

- 01 브리프, 02 기획, 근거 큐, 콘셉트/문구 검수, QA 규칙은 정상적으로 작업한다.
- 03 단계는 프롬프트와 후보 메타데이터/플레이스홀더를 만든다.
- 플레이스홀더는 실제 생성물이 아니므로 최종 이미지 선택·아카이브 승인의 근거로 사용하지 않는다.
- 실제 이미지가 필요해지면 ComfyUI, 모델, 커스텀 노드, 원본 제품 이미지와 레퍼런스 이미지 저장소를 별도 복원한다.

현재 실제 이미지 생성 코어는 기본적으로 `http://127.0.0.1:8188`의 로컬 ComfyUI를 사용한다. Mac에서 Windows의 ComfyUI를 원격 사용하려면 네트워크 접근뿐 아니라 생성 클라이언트의 URL 설정도 별도로 정리·검증해야 한다.

## Ollama와 레퍼런스 수집

로컬 AI 레퍼런스 검수가 필요하면 Mac에 Ollama를 설치하고 모델을 내려받는다.

```bash
ollama serve
ollama pull qwen2.5vl:7b
```

그 뒤 `REFERENCE_REVIEW_HOST=http://127.0.0.1:11434`를 사용한다. 메모리와 모델 호환성은 Mac 사양에 따라 확인한다.

Pinterest/브라우저 수집은 새 Mac에서 다시 로그인해야 한다. 저장된 쿠키 파일은 보안상 Git 제외 대상이다. 원본 레퍼런스 이미지가 필요하면 합법적으로 접근 가능한 원본 URL에서 다시 수집하거나 별도 승인된 자산 저장소를 사용한다.

## Git 공유 전 점검

```bash
git status
git submodule status
python scripts/run_project_tests.py
```

커밋 대상은 코드, JSON/Markdown 설정, 이벤트 입력, 학습·근거 기록이다. 아래는 커밋하지 않는다.

- `.env`, API 키, 브라우저 쿠키
- `.venv/`, `node_modules/`, `.tmp/`
- `runs/`, `references/`, `assets/references/`
- 이미지·영상·압축 파일

`pinterest-board-collector`는 수정된 경우 그 저장소 안에서 별도로 커밋하고 원격에 push한 뒤, 메인 저장소의 서브모듈 포인터를 커밋한다. `pinterest-playwright-collector`는 별도 Git 저장소라 메인 프로젝트를 push해도 자동으로 전달되지 않는다.

## 빠른 검증

```bash
# Python 단위·계약 테스트
python scripts/run_project_tests.py

# 콘솔 문법 확인
node --check ui/console/app.js

# 이미지 생성 없이 전체 흐름 스모크 테스트
python scripts/smoke_test_full_pipeline.py
```

마지막 스모크 테스트는 격리된 임시 결과를 만들며, 사람의 콘텐츠 승인이나 실제 이미지 생성을 대체하지 않는다.
