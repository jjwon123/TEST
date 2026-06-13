# 전체 파이프라인 감사 - 2026-06-13

## 결론

- Meta 레퍼런스 수집, Qwen-VL 분류, 브리프, 콘텐츠 기획, placeholder 후보, 선택, QA, 아카이브까지의 제어 흐름은 실행된다.
- 실제 제작 준비 상태는 아직 `부분 준비`다. ComfyUI live 생성과 재생성 이후 downstream 상태 정합성은 보완이 필요하다.
- 최종 자동 감사 결과는 `pass`이며 보고서는 `.tmp/pipeline-health/latest-pipeline-health.json`에 있다.

## 검증 근거

- 대표 run: `runs/2026-06-13_05-01-36_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- Meta 경쟁사 레퍼런스 8장을 `03_reference_research`에 연결했다.
- Ollama `qwen2.5vl:7b` 실제 이미지 판정에 성공했다.
- console `5177`, ComfyUI `8188`, Ollama `11434` 응답을 확인했다.
- ComfyUI queue는 감사 종료 시 running 0, pending 0이다.

## 단계별 상태

| 단계 | 결과 | 메모 |
|---|---|---|
| 01_event_brief | 통과 | 생성 및 승인 |
| 02_content_planning | 통과 | 생성 및 승인 |
| 03_reference_research | 통과 | Meta 레퍼런스 8장 선택 |
| 04_visual_candidates | 부분 통과 | placeholder 흐름 통과, live 그룹은 20분 내 완료되지 않음 |
| 05_admin_selection | 게이트 보강 | 생성 실패 후보 선택 차단 |
| 06_qa_packaging | 게이트 보강 | fail/error/blocker가 있으면 승인 차단 및 수정 단계 라우팅 |
| 07_asset_archive | 실행됨 | placeholder 중심이라 재사용 자산 0개 |

## 감사 중 수정한 문제

- 존재하지 않던 cosmetics/jewelry ComfyUI workflow ID를 실제 registry ID로 수정했다.
- prompt audit 출력 위치를 QA가 읽는 물리 폴더와 일치시켰다.
- 생성 실패 후보를 콘솔/API/selection handler에서 선택하지 못하게 했다.
- QA `severity=error|blocker`도 수정 대상으로 라우팅한다.
- 실패 QA는 승인하지 못하게 했다.
- Qwen/Ollama 시작 스크립트가 현재 Windows 설치 위치를 자동 탐지하게 했다.
- 반복 점검용 `scripts/audit_full_pipeline_health.py`를 추가했다.

## 남은 보완 우선순위

### P0/P1

1. ComfyUI live 생성 성능과 복구
   - RTX 3060에서 Qwen Image Edit 2511 3장 그룹이 20분 내 완료되지 않았다.
   - 단일 후보 smoke test, 경량 preset, timeout 이후 job 추적/회수 기능이 필요하다.
2. 완료 상태와 빈 아카이브 구분
   - 07이 done이어도 재사용 자산이 0개일 수 있다.
   - `done_no_reusable_assets` 또는 완료 차단 정책이 필요하다.
3. Meta 100장 재수집
   - Qwen 복구 후 경쟁사 레지스트리 기준으로 새 100장 분류 배치를 다시 만들어야 한다.
4. QA warning 승인 정책
   - warning 승인 시 확인 메모를 필수화하는 것이 안전하다.

### P2

- `python -m unittest discover`가 루트 테스트 일부만 찾는다. pipeline/service 테스트를 포함하는 공통 suite가 필요하다.
- OpenCLIP 랭킹은 이번 대표 E2E에서 실제 검증하지 않았다.
- 콘솔의 기존 `meta_brand_review_001` 사람 검수 상태와 파일 기반 감사 결과의 구분을 명확히 해야 한다.

## 추가 수정 확인

- 04 등 upstream 단계를 다시 실행하면 downstream 상태를 `locked`로 되돌리고 `stale_stages`에 원인을 기록한다.
- 대표 run 재검증 결과 05는 `not_started`, 06과 07은 `locked`로 정상 무효화됐다.

## 반복 검증 명령

```powershell
.venv\Scripts\python.exe scripts\audit_full_pipeline_health.py
.venv\Scripts\python.exe scripts\reference_vision.py health
.venv\Scripts\python.exe scripts\project_hook_check.py
```
