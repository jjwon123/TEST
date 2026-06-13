# 프로젝트 남은 작업 현황 - 2026-06-13

## 한 줄 결론

운영 콘솔, 레퍼런스 판단, placeholder 기반 01~07 제어 흐름은 작동한다.  
실제 제작 완료 기준으로는 `ComfyUI live 생성 → 사람 선택 → QA pass → 재사용 자산 아카이브`의 안정적인 성공 사례가 아직 필요하다.

## 현재 확인된 상태

### 정상 작동

- 콘솔 `5177`, ComfyUI `8188`, Ollama `11434` 응답 정상.
- OpenCLIP/CUDA 사용 가능: RTX 3060, `open_clip 3.3.0`.
- 전체 파이프라인 자동 감사 `pass`.
- 프로젝트 hook check `pass`.
- 루트 자동 발견 테스트 11개 통과.
- 별도 provider/classifier/UI 계약 테스트 13개 통과.
- `meta_brand_review_001` 사람 검수 100/100 완료.
  - selected 19 / shortlist 52 / rejected 29
  - summary/compare 생성 완료
- 현재 H&B 브리프 적합 레퍼런스 큐는 콘솔 기준 117/117 검수 완료.
- QA fail/error/blocker 승인 차단과 upstream 재실행 시 downstream 무효화가 작동한다.
- 아카이브 reuse score와 `reusable / limited_reuse / not_reusable` 분류 로직은 구현되어 있다.

### 부분 작동

- 대표 E2E run은 placeholder 후보 15장 기준으로 제어 흐름만 통과했다.
- 대표 run 현재 상태:
  - 01/02 approved
  - 03/04 done
  - 05 not_started
  - 06/07 locked
  - 실제 아카이브 자산 0개
- Meta 경쟁사 Qwen 재수집 배치는 완료됐지만 통과 회수율이 매우 낮다.
  - 화장품 10개 브랜드: raw ads 30, advertiser match 12, accepted images 1, excluded images 10
  - 주얼리 10개 브랜드: raw ads 27, advertiser match 12, accepted images 5, excluded images 1
  - 합계 accepted images 6장으로 신규 100장 검수 세션 생성 불가
- 제품 고정 합성 및 Korean text overlay preset/workflow는 존재하지만 실제 품질 승인 기록이 부족하다.
- OpenCLIP은 설치/health 확인은 됐지만 대표 E2E 랭킹 효과는 검증하지 않았다.

## 남은 작업 우선순위

### P0 - 실제 제작 완료 경로

1. ComfyUI live 단일 후보 smoke test 안정화
   - 단일 후보용 경량 preset을 사용한다.
   - timeout 후 prompt/job 상태 추적과 결과 회수를 구현한다.
   - 완료 조건: 단일 generated 후보가 제한 시간 안에 회수되고 `generation-quality.json`에 정상 기록.

2. generated 후보 1개로 05 → 06 → 07 실제 E2E 완료
   - placeholder가 아닌 generated 후보를 사람 선택한다.
   - QA pass 후 approved/archive 자산이 최소 1개 생성되어야 한다.
   - 완료 조건: `assets/approved/` 기록 1개 이상, archive status와 자산 수가 일치.

3. Meta 재수집 회수율 개선
   - 현재 strict gate 통과가 20개 브랜드에서 6장뿐이다.
   - 검색어/광고주 alias/ads-per-brand/creative gate를 단계별로 측정한다.
   - batch 이름의 `100`은 목표치일 뿐 실제 accepted 수가 아님을 콘솔에 표시한다.
   - 완료 조건: 통과 이미지로 신규 검수 세션을 만들 수 있는 충분한 풀 확보.

### P1 - 운영 안전성과 품질

4. ComfyUI timeout 복구와 queue 가시화
   - 장시간 running job을 콘솔에서 식별하고 회수/실패/재시도 상태를 구분한다.

5. QA warning 승인 정책
   - 현재 warning QA는 빈 note로도 승인 가능하다.
   - warning 승인 시 확인 메모를 필수화한다.

6. 빈 아카이브 완료 상태 구분
   - 07이 `done`이어도 자산 0개일 수 있다.
   - `done_no_reusable_assets` 또는 명확한 archive summary 상태를 추가한다.

7. 제품 고정 합성 및 Korean text overlay 품질 검수
   - 제품 형태/라벨 보존, 목업 합성 자연스러움, 한글 타이포 가독성 체크리스트를 만든다.
   - preset 존재가 아니라 승인 가능한 실제 출력으로 검증한다.

8. Git 기준선 확립
   - 현재 저장소 파일 대부분이 Git에서 미추적 상태다.
   - 변경 추적과 복구가 어려우므로 첫 기준 commit/백업 정책이 필요하다.

### P2 - 품질 고도화와 유지보수

9. OpenCLIP + Qwen + Reference Judge 결합 검증
   - OpenCLIP이 실제 selected/shortlist 품질을 개선하는지 holdout으로 측정한다.

10. 공통 테스트 suite 구성
    - `unittest discover`는 루트 tests 11개만 찾는다.
    - provider/classifier/UI 계약 테스트 13개를 한 명령으로 실행하도록 묶는다.

11. 콘솔 기술 부채 정리
    - `ui/console/app.js`에 `setView`, `renderDashboard`, `renderTrainingPreview`, `renderTrainingReviewForm` 중복 선언이 남아 있다.
    - 기능 회귀 테스트를 둔 뒤 정리한다.
    - 새로고침 후 마지막 선택 검수 세션 복원은 UX 개선 항목이다.

12. Meta 광고 수집 카드 직접 판단 저장
    - 판단 훈련 세션 저장은 정상이다.
    - 별도 Meta 광고 수집 카드에서 selected/shortlist/rejected를 직접 저장하고 `reference-evidence.json`으로 연결하는 흐름은 미완성이다.

## MVP 완료 기준

아래 조건을 모두 만족하면 로컬 제작 MVP 완료로 본다.

1. 실제 이벤트 1개가 live generated 후보를 만든다.
2. 사람이 콘솔에서 후보를 선택한다.
3. QA pass 또는 메모가 있는 warning 승인 정책을 통과한다.
4. 07 완료 후 approved asset이 최소 1개 존재한다.
5. upstream 재생성 시 downstream stale 처리가 유지된다.
6. Meta/레퍼런스 입력이 사람 검수 결과와 함께 다음 브리프에 연결된다.
7. 공통 테스트 suite와 pipeline health audit가 모두 통과한다.

## 범위 밖

- 영상 생성은 현재 MVP 범위 밖이다.
- Vercel은 조회 전용이며 로컬 실행/쓰기 기능을 대체하지 않는다.
- LM Studio는 현재 Ollama/Qwen 경로가 정상이라 별도 필요성이 생기기 전까지 우선순위가 낮다.
