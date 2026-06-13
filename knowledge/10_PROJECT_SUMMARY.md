# 프로젝트 정리: 이벤트 콘텐츠 자동화

작성일: 2026-05-27

## 한 줄 요약

이 프로젝트는 이벤트 입력과 브랜드 가이드를 받아서, 브리프 작성 → 콘텐츠 기획 → 레퍼런스 리서치 → 이미지 후보 생성 → 사람이 이미지 선택 → QA 패키징 → 자산 아카이브까지 이어지는 이벤트 콘텐츠 제작 자동화 파이프라인이다.

현재 핵심 방향은 GPT보다 똑똑한 기획툴이 아니라, 디자이너가 브랜드 이벤트 이미지를 만들 때 필요한 레퍼런스 수집/프롬프트/ComfyUI 후보 생성/선택/패키징을 한 흐름으로 관리하는 로컬 제작 콘솔이다.

## 현재 전체 흐름

```text
events/<event>/event-input.json
events/<event>/brand-guide.json
        ↓
01_event_brief
        ↓
02_content_planning
        ↓
03_reference_research
        ↓
04_visual_candidates
        ↓
05_admin_selection
        ↓
06_qa_packaging
        ↓
07_asset_archive
```

05_figma_assembly는 2026-05-18 기준 제거되었다. 기존 산출물 호환 때문에 물리 폴더 `03_visual_candidates`, `04_admin_selection`은 유지하지만, 새 실행 기준 단계명은 `04_visual_candidates`, `05_admin_selection`이다.

## 주요 폴더별 기능

| 폴더 | 역할 |
|---|---|
| `knowledge/` | 프로젝트 기준 문서. 목표, 워크플로, 브랜드 규칙, 프롬프트 규칙, 결정사항, 트러블슈팅, ComfyUI 메모를 관리한다. |
| `events/` | 새 이벤트의 입력 원본을 둔다. 보통 `event-input.json`, `brand-guide.json`이 들어간다. |
| `runs/` | 실제 실행 결과가 쌓이는 폴더. 각 런별 `run-status.json`, 단계별 산출물, 로그, 후보 이미지가 저장된다. |
| `pipeline/` | 01~07 단계별 핸들러와 입출력 스키마가 있다. 실제 자동화 로직의 중심이다. |
| `scripts/` | 실행 명령을 담당한다. `workflow.py`가 런 생성, 단계 실행, 승인, 레퍼런스 수집, QA 실패 라우팅을 관리한다. |
| `services/` | 외부 도구와 AI 연결 계층. LLM, 리서치, ComfyUI, 제품 라이브러리, 레퍼런스 비전 리뷰가 분리되어 있다. |
| `core/` | 공통 스키마, 채널/템플릿 레지스트리, JSON 유틸, 카테고리별 리스크 검토 로직이 있다. |
| `ui/console/` | 로컬 운영 콘솔 화면. 런 목록, 단계 실행, ComfyUI 상태, 이미지 선택, 최종 패키지 확인을 지원한다. |
| `assets/` | 승인/재사용 자산과 레퍼런스 기준, 글로벌 인덱스를 저장한다. |
| `products/` | 제품별 원본 이미지, 프롬프트 조각, 추천 ComfyUI 워크플로를 관리한다. |
| `docs/` | 기술 스펙, 레퍼런스 수집/AI 튜닝, QA, 제품 고정 광고 배경 워크플로 등 상세 설계 문서가 있다. |

## 단계별 기능

### 01_event_brief

입력된 이벤트 정보와 브랜드 가이드를 읽어 전략 브리프를 만든다.

주요 기능:

- 이벤트 목적, 타깃, 혜택, 일정, 채널, 핵심 메시지 정리
- 필수 문구와 금지어 통합
- 스킨케어, 랩그로운 다이아, 금거래소/귀금속 카테고리 리스크 감지
- 누락 정보와 승인 전 확인 질문 생성
- 출력: `brief.json`, `notes.md`

AI 관련:

- `services/llm/client.py`를 통해 LLM 요청 구조를 만든다.
- 기본값은 실제 LLM 호출 없이 로컬 deterministic draft로 동작한다.
- `LLM_PROVIDER_URL`을 설정하면 HTTP JSON 방식의 외부 LLM provider를 붙일 수 있다.

### 02_content_planning

승인된 브리프를 채널별 콘텐츠 제작 계획으로 바꾼다.

주요 기능:

- 인스타그램, 블로그, 커뮤니티 등 채널 정책 해석
- 채널별 산출물, 비율, 템플릿, 슬라이드 역할 결정
- 이미지 필요 항목(`image_needs`) 생성
- 채널별 카피 의도와 CTA 방향 설정
- 출력: `content-plan.json`, `notes.md`

AI 관련:

- 01과 동일하게 LLM 요청 구조는 준비되어 있다.
- 기본 실행은 로컬 규칙 기반이며, `LLM_PROVIDER_URL`이 있을 때 외부 LLM 결과를 사용할 수 있다.

### 03_reference_research

콘텐츠 기획 이후 이미지 제작에 참고할 레퍼런스를 준비하는 단계다.

주요 기능:

- 이벤트/채널 기준 Pinterest 검색 쿼리 생성
- 기존 수집 레퍼런스 상태 요약
- 필요 시 자동 검색/다운로드/선정 실행
- 출력: `reference-collection-plan.json`, `reference-research.json`, `notes.md`

AI 관련:

- 기본 stage 실행은 AI 없이 계획/요약만 만든다.
- `REFERENCE_RESEARCH_MODE=auto_search`와 `REFERENCE_REVIEWER=qwen`을 설정하면 Qwen-VL 레퍼런스 리뷰를 사용할 수 있다.

### 04_visual_candidates

콘텐츠 계획을 바탕으로 이미지 후보 생성용 프롬프트와 후보 매니페스트를 만든다.

주요 기능:

- 산출물별 이미지 후보 3개씩 생성 계획
- ComfyUI용 positive/negative prompt 구성
- 제품 이미지, 레퍼런스 이미지, 채널 규격, 텍스트 안전 영역 반영
- 후보 그룹별 재생성 명령 생성
- placeholder 모드에서는 미리보기 PNG를 임시 생성
- live 모드에서는 ComfyUI에 실제 이미지 생성을 요청
- 출력 물리 경로: `03_visual_candidates/visual-plan.json`, `image-prompts.json`, `candidate-manifest.json`, `notes.md`

AI 관련:

- ComfyUI 연동 단계다.
- 기본 모드: `COMFYUI_GENERATION_MODE=placeholder`
- 실생성 모드: `COMFYUI_GENERATION_MODE=live`
- 기본/연결 워크플로:
  - `qwen_candidate_2511`
  - `product_locked_ad_background_v1`
  - `cosmetics/cosmetic_product_hero`
  - `cosmetics/cosmetic_lifestyle_scene`
  - `jewelry/jewelry_product_hero`
  - `bullion/bullion_product_hero`
- 관련 모델/워크플로 문서에는 Qwen Image Edit 2511 계열이 중심 방향으로 정리되어 있다.

### 05_admin_selection

사람이 이미지 후보를 보고 선택, 탈락, 보류, 재생성을 결정하는 단계다.

주요 기능:

- 콘솔 또는 CLI에서 저장한 선택값 읽기
- 후보별 상태를 `selected`, `rejected`, `hold`, `regenerate`로 정규화
- 선택 자산과 재생성 요청 생성
- 산출물별 선택 누락 여부 확인
- 출력 물리 경로: `04_admin_selection/selected-assets.json`, `selection-notes.md`

AI 관련:

- 직접 AI 판단을 하지 않는다.
- 사람 검토를 기준으로 다음 단계에 넘기는 관리자 게이트다.

### 06_qa_packaging

선택된 자산 또는 조립된 산출물을 QA하고 최종 패키지 매니페스트를 만든다.

주요 기능:

- 선택 자산 기반 최소 패키징 지원
- Figma 산출물이 있으면 내보내기 파일, 카피 추적, 금지어, 필수 문구, CTA 위치 등을 검사
- QA 이슈에 `suggested_fix_stage`를 붙여 어느 단계로 되돌릴지 표시
- 출력: `qa-report.json`, `final-package-manifest.json`, `qa-packaging.json`, `notes.md`

AI 관련:

- 현재는 규칙 기반 QA다.
- LLM 판단보다 스키마, 정책, 금지어, 필수 문구, 파일 존재 여부 중심으로 검증한다.

### 07_asset_archive

QA 통과 자산을 승인/재사용 자산으로 정리하고 글로벌 인덱스에 반영한다.

주요 기능:

- QA 통과 자산만 아카이브
- 재사용 점수 계산
- `assets/approved/`, `assets/reusable/`로 파일 복사
- `assets/indexes/global-index.json` 업데이트
- 이벤트별 인덱스 생성
- 출력: `asset-archive.json`, `reuse-notes.md`

AI 관련:

- 현재는 정책 기반 점수화다.
- 학습 모델보다 채널, 템플릿, 이벤트 특정성, QA 통과 여부를 기준으로 재사용 가능성을 판단한다.

## 로컬 콘솔 기능

실행 명령:

```powershell
start_brand_event_console.bat
```

접속:

```text
http://127.0.0.1:5177
```

주요 기능:

- 런 목록과 현재 상태 확인
- 새 이벤트 실행
- 단계 실행/승인
- ComfyUI 상태 확인
- 이미지 후보 선택/보류/탈락/재생성 요청
- 04 선택 완료 실행
- 최종 패키지 화면에서 선택 후보 카드, 이미지 미리보기, 프롬프트 확인

주요 API:

```text
GET  /api/bootstrap
GET  /api/runs
GET  /api/runs/{run_id}
GET  /api/comfy/status
POST /api/run-event
POST /api/runs/{run_id}/comfy/generate
POST /api/runs/{run_id}/stage
POST /api/open-path
```

## 현재 들어간 AI/모델/자동화 요소

### 1. Codex / LLM 작업 구조

사용 위치:

- 01_event_brief
- 02_content_planning

상태:

- 실제 LLM provider 없이도 실행 가능하도록 로컬 draft가 기본이다.
- `LLM_PROVIDER_URL`, `LLM_PROVIDER_TOKEN` 환경변수로 외부 LLM provider를 붙일 수 있게 설계되어 있다.
- 현재 핵심 산출물은 스키마와 규칙 기반으로 안정적으로 생성된다.

### 2. Research provider 구조

사용 위치:

- 01_event_brief
- 02_content_planning

상태:

- 기본은 저장된 `research-evidence.json` 스냅샷을 매칭한다.
- `RESEARCH_PROVIDER_URL`, `RESEARCH_PROVIDER_TOKEN`을 설정하면 외부 리서치 provider를 붙일 수 있다.
- 실시간 웹 검색 엔진 자체가 기본 내장된 상태는 아니다.

### 3. ComfyUI

사용 위치:

- 04_visual_candidates

상태:

- 후보 생성 프롬프트와 ComfyUI payload 생성은 연결되어 있다.
- placeholder 모드와 live 모드가 분리되어 있다.
- live 모드는 ComfyUI 서버 `http://127.0.0.1:8188` 실행이 필요하다.
- 외부 브랜드별 workflow canonical path 연결은 완료되어 있다.
- 남은 핵심 작업은 live 생성 안정화, 제품 합성, 텍스트 오버레이 후처리 품질 검수다.

관련 워크플로/모델:

- Qwen Image Edit 2511 계열
- `qwen-image-edit-2511-Q3_K_M.gguf`
- `qwen_2.5_vl_7b_fp8_scaled.safetensors`
- `qwen_image_vae.safetensors`
- KoreanTextOverlay 커스텀 노드
- ProductLockedAd 커스텀 노드

### 4. Qwen-VL 이미지 레퍼런스 리뷰

사용 위치:

- `services/visual_reference/qwen_reviewer.py`
- 레퍼런스 수집/선정 파이프라인

상태:

- Ollama 서버 기준 기본 모델은 `qwen2.5vl:7b`다.
- 기본 host는 `http://127.0.0.1:11434`다.
- 이미지 레퍼런스를 보고 `selected`, `shortlist`, `rejected` 판단과 점수/이유/리스크를 JSON으로 받는 구조다.

### 5. OpenCLIP + 경량 분류기

사용 위치:

- `services/visual_reference/clip_ranker.py`
- `scripts/reference_vision.py`

상태:

- OpenCLIP `ViT-B-32`, pretrained `laion2b_s34b_b79k`를 사용한다.
- 이미지 임베딩을 만들고, 피드백 데이터로 LogisticRegression 분류기를 학습할 수 있다.
- Qwen-VL을 바로 fine-tuning하기보다 CLIP 랭킹/피드백 튜닝을 먼저 하는 방향이다.

### 6. LM Studio

상태:

- `knowledge/`에는 LM Studio 테스트/연결 기준을 정리할 예정으로 남아 있다.
- 현재 코드의 기본 LLM 연결 방식은 `LLM_PROVIDER_URL` HTTP provider 구조다.
- 즉, LM Studio는 프로젝트 기준상 고려 대상이지만, 현재 핵심 실행 경로에 고정 통합되어 있지는 않다.

### 7. Midjourney / DALL-E

상태:

- 워크플로 문서에는 사람이 이미지 생성에 사용할 수 있는 외부 생성 도구 예시로 언급되어 있다.
- 현재 자동 실행 경로의 중심은 ComfyUI다.
- Midjourney/DALL-E API 자동 연동은 현재 코드상 핵심 통합으로 보이지 않는다.

## 현재 완료된 것

- 01 브리프 생성 구현
- 02 콘텐츠 기획 구현
- 03 레퍼런스 리서치 stage 구현
- 04 비주얼 후보/프롬프트/후보 매니페스트 생성 구현
- 05 관리자 이미지 선택 최소 구현
- 06 선택 자산 기반 QA 패키징 구현
- 07 자산 아카이브와 글로벌 인덱스 구현
- 콘솔에서 이미지 선택과 최종 패키지 확인 흐름 개선
- hsgn cosmetic 테스트에서 기존 03 → 04 → 06 → 07 스모크 패스 확인
- 외부 cosmetics/jewelry/bullion ComfyUI workflow 레지스트리 연결

## 아직 남은 핵심 작업

- ComfyUI live 이미지 생성 안정화
- 제품 원본을 안전하게 고정한 합성 품질 검수
- Korean text overlay 후처리 품질 개선
- 이벤트/레퍼런스/프롬프트 품질 장기 검수
- LM Studio 연결 기준 정리
- 이미지 평가 체크리스트 정리
- 영상 생성은 아직 제외 상태

## 자주 쓰는 명령어

새 런 생성:

```powershell
python scripts\workflow.py --setup --event events\<이벤트명>
```

단계 실행:

```powershell
python scripts\workflow.py --run runs\<run-id> --stage <단계>
```

단계 승인:

```powershell
python scripts\workflow.py --run runs\<run-id> --approve <단계>
```

ComfyUI live 재생성:

```powershell
$env:COMFYUI_GENERATION_MODE='live'
python scripts\workflow.py --run runs\<run-id> --stage 04_visual_candidates --mode regenerate --group <group-id>
```

콘솔 실행:

```powershell
start_brand_event_console.bat
```

## 판단 기준

이 프로젝트는 "AI가 모든 결정을 대신하는 자동화"가 아니라, 사람이 승인해야 하는 지점은 유지하면서 반복적인 기획, 프롬프트 생성, 후보 관리, QA, 아카이브를 자동화하는 구조다.

현재 들어간 AI는 크게 네 종류다.

1. LLM provider 연결 구조: 브리프/기획을 고도화할 수 있는 자리
2. ComfyUI: 이미지 생성과 제품 합성 실행 엔진
3. Qwen-VL: 레퍼런스 이미지 검토/선정 보조
4. OpenCLIP: 레퍼런스 이미지 랭킹과 피드백 기반 경량 학습

현재 안정적으로 돌아가는 부분은 규칙 기반 파이프라인이고, 앞으로 품질을 좌우할 부분은 ComfyUI live 생성과 이미지 평가 기준 고도화다.
