# 운영 준비도 전체 검토 - 2026-06-14

## 검토 범위

사람이 직접 해야 하는 검수와 별도 제작 중인 ComfyUI 워크플로 품질은 제외했다.

이번 검토는 실제 운영 시 자동화 시스템이 입력을 안전하게 받고, 작업을 추적하고, 실패를 복구하며, 이전 판단을 다음 실행에 반영하는지를 기준으로 했다.

반복 감사:

```powershell
.venv\Scripts\python.exe scripts\audit_operational_readiness.py
```

출력:

- `.tmp/operations-readiness/latest-operations-readiness.json`
- `.tmp/operations-readiness/latest-operations-readiness.md`

## 현재 판정

자동화 기능은 많지만 운영 완성도는 아직 `부분 운영 가능`이다.

- 이벤트 입력/브리프/기획/레퍼런스/QA/아카이브 기능은 구현되어 있다.
- 신규 런의 일반 예외가 `in_progress`에 고착되는 문제는 수정했다.
- 콘솔 작업 이력은 디스크에 영속화하도록 수정했다.
- Meta 사람 최종 판단이 실제 03 레퍼런스 공급에 반영되도록 연결했다.
- 과거 stale/legacy run 상태는 reconcile 도구로 정리했다.
- 현재 자동 감사와 자산 무결성 감사는 모두 `pass`다.

## 이번 검토에서 발견한 주요 문제

### P0 - 운영 중 작업 고착

- 단계 핸들러가 `SchemaValidationError` 외 예외를 내면 run이 `in_progress`에 남을 수 있었다.
- 수정: 신규 실패는 stage를 `blocked`, run을 `failed`로 기록하고 `stage_failures`와 오류 로그를 남긴다.
- 수정: `scripts/reconcile_run_states.py`를 추가하고 과거 stale run 2개를 `failed/blocked`로 정리했다.

### P0 - 입력 계약 불일치

- 공식 event schema는 `objective`를 요구했지만 콘솔과 여러 실제 이벤트는 `purpose`를 생성했다.
- 수정: `objective|purpose` 호환 계약, 비어 있지 않은 이벤트명/브랜드명, run 생성 전 입력 검증을 추가했다.
- 콘솔 신규 이벤트는 canonical `objective`와 호환 `purpose`를 함께 기록한다.

### P1 - 완료된 판단이 다음 실행에 미반영

- `meta_brand_review_001`의 사람 최종 판단은 저장됐지만 Meta provider가 AI 원판정만 사용했다.
- 수정: 최종 `rejected`는 공급 후보에서 제외하고 최종 `selected`를 우선한다.
- 수정: 검수 20건 이상, 완료율 80% 이상, 같은 profile의 2개 이상 세션에서 반복된 규칙만 runtime으로 승격한다.
- 현재 승격 규칙: `cosmetics_skincare/soften_rejected_to_shortlist`, 5개 세션·검수 244건 근거.
- 승격 규칙은 향후 Reference Judge 첫 판단에 적용되며 hard reject 신호는 유지한다.

### P1 - 콘솔 작업 이력 유실

- 콘솔 재시작 시 메모리의 수집/단계 실행 job 상태가 사라졌다.
- 수정: `.tmp/console-jobs/jobs.json`에 최근 200개 job, 명령, PID, 결과, 로그 경로를 보존한다.
- 재시작 전 실행 중이던 job은 `interrupted`로 표시한다.

### P1 - 상태 계약과 실제 값 불일치

- 실제 코드가 쓰는 `reference_research`, `reference_ready`, `review_pending`이 공식 run-state 목록에 없었다.
- 수정: 공식 상태 목록과 문서를 실제 흐름에 맞췄다.
- 수정: 과거 `run_state=done` archive run 2개를 `archived`로 migration했다.

### P1 - 운영 게이트 부족

- QA 승인 전에도 `production-package/`를 만들 수 있는 run이 확인됐다.
- 패키지가 제작 인수인계 초안인지 최종 납품 패키지인지 상태가 모호하다.
- 수정: 앞으로 최종 `production-package`는 `06_qa_packaging=approved` 이후에만 생성된다.
- 수정: 기존 QA 승인 전 package 1개를 `production-package-legacy-draft`로 migration했다.

### P1 - 아카이브와 인덱스 무결성

- `scripts/audit_asset_integrity.py`를 추가했다.
- approved/reusable 실제 파일, global index, event index, run archive manifest를 대조한다.
- 현재 실제 자산 감사는 `pass`다.
- 재아카이브 시 동일 파일은 중복 버전을 만들지 않고, 내용이 다른 충돌 파일은 실제 versioned 경로를 manifest/index에 기록한다.

## 완성도 기준

### 자동화 운영 MVP 완료

아래를 모두 만족하면 ComfyUI와 사람 작업을 제외한 자동화 운영 MVP 완료로 본다.

1. 잘못된 이벤트 입력은 run 생성 전에 차단된다.
2. 모든 단계 실패는 `blocked/failed`와 원인 기록을 남기며 재실행 가능하다.
3. 콘솔 재시작 후에도 작업 이력과 로그를 조회할 수 있다.
4. 24시간 이상 stale `in_progress` run이 0개다.
5. 모든 run state가 공식 상태 계약 안에 있다.
6. 사람 최종 판단과 승인된 learned rule이 다음 레퍼런스 판단에 반영된다.
7. 최종 production package는 QA 승인 전 생성되지 않는다.
8. archive 파일, approved 자산, global/event index가 서로 일치한다.
9. 공통 테스트 suite와 운영 준비도 감사가 통과한다.

### 실제 운영 완료

자동화 운영 MVP에 더해 실제 이벤트 반복 실행에서 아래를 만족해야 한다.

- 신규 이벤트 3건 이상이 동일한 절차로 종료된다.
- 실패 후 복구한 run도 최종 상태와 산출물 정합성이 유지된다.
- 이전 검수 결과가 다음 레퍼런스 선택 품질을 개선한다는 비교 지표가 있다.
- 운영자가 폴더/JSON을 직접 고치지 않고 콘솔과 명령으로 복구할 수 있다.

## 다음 자동화 우선순위

1. 반복 실제 이벤트 3건으로 자동화 운영 완성도 증명
2. 최소 1건의 실패 후 재실행·복구와 최종 정합성 증명
3. 화장품 Meta 개선 배치로 통과율·브랜드 커버리지 상승 확인

## 2026-06-14 후속 완료

- Meta 수집 단계별 회수율·브랜드 편중·creative type 지표를 구현했다.
- 운영 준비도와 Meta 경고를 콘솔 Workboard에 표시한다.
- Meta 수집 화면에서 업종별 최신 배치 지표와 경고를 확인할 수 있다.
- 최신 화장품 배치는 creative acceptance 6.0%, brand coverage 10.0%로 경고 상태다.
- 최신 주얼리 배치는 creative acceptance 95.2%, brand coverage 50.0%로 현재 경고가 없다.
- 반복 운영 증거 감사와 Workboard 표시를 추가했다.
- 자동화 구간은 서로 다른 이벤트 5종에서 완료됐고 동일 run 실패 후 복구는 1/1건으로 충족했다.
- 최종 성공은 2/3종이라 반복 실운영 완료 판정은 아직 `incomplete`다.
- 화장품 Meta 적응형 수집을 실제 검증했다.
  - 적응형 누적 creative acceptance 23.5%, brand coverage 16.7%.
  - 기존 대규모 기준 배치 대비 각각 +17.6%p, +6.7%p.
  - 기본 검증 배치는 5개 브랜드 × 광고 5개이며, 다음 브랜드는 누적 증거와 직전 배치 cooldown으로 결정한다.
- 누적 원본 77개 후 검증 브랜드 수집을 `secondary_campaign_reference`로 판정했다.
- 상품·성분 쿼리 자동 보완 수집을 완료했다.
  - reviewed 48 / clean product visual 24 / clean rate 50%.
  - 미검증 상품·성분 쿼리 대기 계획 0개.
