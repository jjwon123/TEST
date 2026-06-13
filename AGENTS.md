# 이벤트 콘텐츠 자동화 프로젝트

## 작업 시작 전 필독

1. `knowledge/00_DASHBOARD.md` — 현재 상태, 다음 할 일
2. `knowledge/09_HANDOFF.md` — 구현 현황, 콘솔/ComfyUI 상태, 다음 우선순위

모든 프로젝트 기준은 `knowledge/` 폴더에 있다. Obsidian에서 `knowledge/` 폴더를 열면 전체 구조가 보인다.

---

## 스킬 명령어

```
/이벤트-자동화      전체 1~5단계 실행 (새 이벤트 시작 시)
/01-브리프          1단계만 실행
/02-콘텐츠기획      2단계만 실행
/03-이미지프롬프트  3단계만 실행
/04-이미지선택      4단계만 실행 (이미지 검토·선택)
/05-QA              5단계만 실행
```

---

## 핵심 실행 명령

```powershell
# 새 런 생성
python scripts\workflow.py --setup --event events\<이벤트명>

# 단계 실행
python scripts\workflow.py --run runs\<run-id> --stage <단계>

# 단계 승인
python scripts\workflow.py --run runs\<run-id> --approve <단계>

# 비주얼 그룹 재생성
$env:COMFYUI_GENERATION_MODE='live'
python scripts\workflow.py --run runs\<run-id> --stage 03_visual_candidates --mode regenerate --group <group-id>

# 콘솔 시작
start_brand_event_console.bat   # → http://127.0.0.1:5177
```

---

## 단계 구조

```
01_event_brief → 02_content_planning → 03_visual_candidates
  → [ComfyUI 이미지 생성, 사람 검토]
  → 04_admin_selection → 06_qa_packaging → 07_asset_archive
```

> 05_figma_assembly 제거됨 (2026-05-18). 04 완료 시 06으로 직행.

---

## 작업 후 기록 규칙

작업이 끝나면 아래 기준으로 `knowledge/` 파일에 직접 기록한다.

| 내용 | 파일 |
|------|------|
| 새 결정 또는 방향 변경 | `07_DECISIONS.md` |
| 단계 흐름·구조 변경 | `02_WORKFLOW.md` |
| ComfyUI 노드·워크플로 | `08_COMFYUI_NOTES.md` |
| 에러·실패·해결법 | `06_TROUBLESHOOTING.md` |
| 현재 상태·다음 할 일 변경 | `00_DASHBOARD.md` + `09_HANDOFF.md` |

기록하지 않는 것: 단순 실행 로그, 일회성 중간 산출물, `runs/`에 이미 있는 세부 결과.

---

## 폴더 역할

```
knowledge/   ← 프로젝트 기준 (Obsidian 볼트)
events/      ← 이벤트 입력 데이터
pipeline/    ← 단계별 핸들러 + 스펙
runs/        ← 실행 결과 (run-status.json, 산출물)
scripts/     ← workflow.py, console_server.py
services/    ← ComfyUI 연동 계층
core/        ← 공유 스키마, 채널 레지스트리
```
