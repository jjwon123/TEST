# 프로젝트 대시보드

## 현재 상태 업데이트 (2026-09-13, macOS·Git 이식 준비)

- 이미지 원본·ComfyUI 생성 결과 없이도 기획·문구·근거·검수 자동화를 이어갈 수 있도록
  루트 `README.md`, `docs/MAC_HANDOFF.md`, `.env.example`, `requirements.txt`,
  `scripts/start_brand_event_console.sh`를 추가했다.
- Git에는 이벤트·제품 설정, URL/평가 기반 레퍼런스 지식, 문구·기획 학습 데이터와 코드를
  포함한다. `runs/`, 수집·생성 이미지, 쿠키, API 키, 로컬 환경은 계속 제외한다.
- 다음 공유 전에는 기존 미커밋 변경을 검토해 필요한 코드·설정·학습 데이터만 커밋하고,
  수정된 `pinterest-board-collector` 서브모듈은 해당 저장소에서 별도 push해야 한다.

### 다음 작업

1. 회사 Git 원격을 정하고, 현재 작업 트리의 공유할 변경을 검토·커밋한다.
2. Mac에서 `docs/MAC_HANDOFF.md`의 초기 설치와 이미지 없는 스모크 테스트를 실행한다.
3. 실제 이미지 생성이 필요해지는 시점에만 ComfyUI와 이미지 자산 저장소를 별도로 복원한다.

> 2026-07-22 approval-gate correction: the copy-review form now starts its eight human rubric scores at 4 (the documented minimum for final approval) and explains that requirement. Server approval now blocks only critical/error-severity scorecard findings; warnings stay as visible review context. This removes a dead end where an operator could select final approval but could not advance because of hidden default scores or unresolved warnings from the earlier planning critic.
>
> 2026-07-20 UX flow correction: copy review is now a gate, not a stop screen. Approval opens the matched image-candidate run immediately; a revision request stays in the same copy-review case. The legacy planning approval also opens image-direction prompts automatically.
>
> 2026-07-20 UX flow correction: when all evidence cards are decided but the selected-evidence requirement is still short, the console explains the exact gap and offers “보류한 자료 다시 보기” instead of returning to a repeated “근거 검수 시작” mission.

> 2026-07-21 UX flow correction: the post-copy path is now continuous: reference collection and selection → image-direction prompts → image candidate generation → human image selection → QA packaging. Each completed background job advances to its next workspace automatically.

> 2026-07-21 UX correction: evidence review no longer asks the operator to write a product-proof record. A single official product-page URL triggers capture and creates one reviewable proof candidate; direct entry remains a fallback only when a page is unavailable.

> 2026-07-21 UX correction: a completed evidence review no longer blocks on a missing or rejected product-proof card. The console opens concept selection with a `no_unverified_product_claims` policy; it does not permit ingredient, efficacy, number, or result claims until an official page is captured and reviewed. The long direct-entry form is hidden from the normal mission flow.

> 2026-07-21 UX correction: when a benchmark copy review has no separately linked image run, final save uses the production run currently selected in the console (only `prompt_ready` or `reference_ready`). It opens the reference workspace directly instead of leaving a detached completion screen.

> 2026-07-22 UX correction: selecting a concept and generating copy immediately opens the step-3 copy-review mission for that same case; the operator is no longer left on the concept screen to find another CTA.

> 2026-07-22 reliability correction: console background jobs finish with `done`; the client now treats both `done` and legacy `completed` as a successful handoff, so reference, image, selection, and QA workspaces advance automatically.

> 2026-07-22 UX correction: a `quality_repair_required` planning case never exposes the invalid “select and create copy” CTA. The mission shows the exact quality issues and offers a tracked planning regeneration; after the job completes, the console reloads into the newly available step.

> 2026-07-22 quality-gate correction: planning warnings do not dead-end an otherwise evidence-ready concept. Only critic failures or explicit error-severity issues block selection; warnings stay visible for human copy review. Verified by clicking the real `education-barrier` step-2 CTA and observing its step-3 copy review (20 cards).

> 2026-07-22 journey handoff correction: when a completed benchmark copy review has no matching production run, the console creates the dedicated production bridge run and opens reference selection. Copy approval no longer stops at a detached completion screen.

> 2026-07-22 console freshness correction: console HTML, JavaScript, and bootstrap API responses now use `Cache-Control: no-store`; a reopened or refreshed console always receives the current CTA flow and current run status.

> 2026-07-18 UX correction: saving a copy review hands off to the matching prompt-ready event run's image-candidate stage, never to another benchmark review.

> 2026-07-18 UX correction: starting evidence review opens the event-scoped review in the current mission area; it no longer sends the user below the mission into advanced details.

> 2026-07-18 UX correction: evidence review is now a decision-only workspace. Raw ingestion controls and checkbox reason grids are hidden; source and hypothesis detail are opt-in per card.

> 2026-07-18 UX correction: evidence review progresses one card at a time. Each decision immediately exposes the next candidate, and a ready evidence set opens the refreshed concept-selection mission automatically.

## 현재 상태 업데이트 (2026-07-18, 제작 콘솔 UI/UX 재설계)

- 프로젝트 루트에 `DESIGN.md`를 추가하고 `oh-my-design`의 Nexon 디자인
  시스템을 LoopStudio 제작 콘솔 기준으로 적용했다.
  - 흰 캔버스, `#17191d` 잉크, `#00de5a` 단일 주요 행동
  - 카드 4px, 대형 컨테이너 8px, CTA 0px 라운드
  - 추천안의 금색 표현과 반복 녹색 상태를 제거했다.
- 콘솔 홈을 `제작 여정 → 현재 미션 → 콘셉트 3안 → 선택 근거 → 다음 행동`의
  한 흐름으로 재구성했다.
- 현재 데이터 상태에 따라 주요 행동이 바뀐다.
  - 콘셉트 미선택: `선택하고 카피 만들기`
  - 기존 선택 완료: `카피 검수 시작`
  - 근거 미완료: `근거 검수 시작`
- 전체 감사·근거 큐·배치 도구는 삭제하지 않고 `전체 작업과 고급 검수 보기`에
  기본 접힘으로 보존했다.
- 브리프 입력 부족 상태는 `부족한 브리프 정보 입력하기`로 연결한다.
- 데스크톱과 768px 모바일 화면을 브라우저에서 확인했다.
  - 콘셉트 선택, 브리프 화면 전환, 홈 복귀 정상
  - 브라우저 오류·경고 0
  - `design-qa.md` 최종 결과 `passed`
- 검증: 콘솔 UI 감사 15개, 마케팅 콘솔·기획 패킷 29개 통과.
- `카피 검수 시작`이 닫힌 고급 패널을 가리키던 문제를 수정했다.
  - 클릭 즉시 전용 카피 검수 화면으로 전환한다.
  - 채널 카피 4개, 직접 수정, 점수·사유·메모, 승인/수정 요청을 한 흐름으로
    처리한다.
- 최종 결정 패널의 checkbox 폭 상속 문제를 수정했다.
  - 사유 태그는 한 줄 단일 열로 보이며 한국어가 글자 단위로 깨지지 않는다.
  - 검수 저장 성공 시 다음 검수 또는 방금 검수 다시 보기 완료 화면을 표시한다.

### 다음 작업

1. 실제 운영자가 새 홈에서 장마철 카피 검수를 진행한다.
2. 미입력 브리프의 날짜와 필수 정보를 갱신한 뒤 새 운영 런을 만든다.
3. 모바일에서 제작 도구 전체 메뉴가 필요해지면 별도 메뉴 드로어를 추가한다.

## 현재 상태 업데이트 (2026-07-18, 병목 점검·전체 경로 실증 및 운영 복구)

- 전체 테스트 러너를 수동 목록에서 자동 발견 방식으로 바꿨다.
  - `tests/test_*.py`는 자동 발견하고, 파이프라인·서비스·UI 외부 계약 테스트만 명시한다.
  - 현재 `274개` 테스트가 모두 통과한다.
- 콘솔, ComfyUI, Ollama를 실제로 기동하고 HTTP `200`을 확인했다.
  - 콘솔: `http://127.0.0.1:5177/`
  - ComfyUI: `http://127.0.0.1:8188/system_stats`
  - Ollama: `http://127.0.0.1:11434/api/tags`
- Playwright 라이브 콘솔 감사와 전체 프로젝트 훅이 통과했다.
- 운영 자산과 런을 오염시키지 않는 `.tmp/archive-smoke/` 격리 환경에서
  1→7단계를 실증했다.
  - 기획 점수 `4.0`, QA `pass`, 선택 이미지 `4개`, 승인 아카이브 복사 `4개`.
  - 최종 상태 `archived`; 전역 `assets/` 대신 임시 아카이브 루트만 사용했다.
- 전체 실증을 `python scripts/smoke_test_full_pipeline.py`로 재실행 가능하게 고정했다.
  - 최신 결과: `.tmp/full-pipeline-smoke/latest-report.json`
  - 실제 기획 감사 `pass`, 프롬프트 감사 `12/12 pass`, 선택·아카이브·물리 복사 `4/4`.
  - 비차단 QA 경고는 사유가 있는 6단계 승인 기록이 있을 때만 아카이브한다.
- 최신 코드 실증용 새 런을 생성했다.
  - 런: `runs/2026-07-18_06-20-09_6월-장마철-수분-장벽-리셋-위크`
  - 현재 상태: `01_event_brief=needs_input`, `run_state=brief_input_required`
  - 이벤트 종료일 `2026-06-30`이 현재일보다 과거라 일정 갱신 전 승인을 막았다.
  - 사람 승인을 자동으로 대신하지 않아 이후 단계는 정상적으로 잠겨 있다.
- 브리프·기획 품질 병목을 보정했다.
  - 시즌 캠페인의 부가 증정 혜택이 이벤트 유형을 프로모션으로 뒤집지 않는다.
  - 요청 채널 그룹을 실제 산출 채널로 확장해 비교한다.
  - 채널 간 장문 재사용과 운영 근거 문구 노출을 제거했다.
  - 증정품을 주력 제품으로 오인하던 로컬 비평을 수정했다.
  - 시즌 화장품 프롬프트에 H&B 세일을 강제하던 감사 규칙과 한국어 깨짐
    차단어 누락을 수정했다.
  - 브리프의 `needs_input`이 런 상태에 전파되지 않던 문제를 수정하고,
    미해결 입력이 있는 1단계 승인을 서버에서도 차단했다.
- 대표 5건의 근거 큐, 파일럿 산출물, 검수 패킷, 목표 감사를 최신 코드로 재생성했다.
  - 근거 준비 `1/5`: 장마철
  - 근거 검수 필요 `4/5`
  - 카피 준비 `1/5`: 장마철
  - 최종 사람 평가 `0/5`
  - 치명 오류 `0`
- 현재 목표 감사 `fail`은 기능 오류가 아니라 사람 검수 게이트 때문에 정상이다.

### 다음 작업

1. 실제 집행할 이벤트의 시작·종료·발행일을 현재 또는 미래 일정으로 갱신한다.
2. 갱신한 일정으로 새 운영 런을 만들고 브리프를 사람이 승인한다.
3. 장마철은 사람이 선택한 `concept_01`의 채널별 카피를 검수한다.
4. 프로모션·교육 후보 각 3개와 브랜딩 후보 4개를 빠른 검수안으로 확인한다.
5. 탄력 세럼 후보 3개를 검수하고 공식 성분·사용법·시험 자료를 제품 proof로 추가한다.
6. 5건 최종 사람 평가를 완료한 뒤 목표 감사를 다시 실행한다.

## 현재 상태 업데이트 (2026-07-05, 대표 파일럿 5건 기준 통일)

- 근거 계획의 `priority=1`을 파일럿 5건의 단일 기준으로 고정했다.
  - 장마철 수분 장벽 리셋
  - 수분 앰플 증정 행사
  - 신제품 탄력 세럼 출시
  - 피부 장벽 이해 교육
  - 미니멀 스킨케어 브랜딩
- 감사, 검수 패킷, 파일럿 생성, 검수 CSV가 모두
  `services/ad_strategy/pilot_selection.py`를 사용한다.
- 데이터셋의 앞 5건을 임의로 자르는 동작을 제거했다.
- 근거가 준비되지 않은 이벤트는 콘셉트가 3개 있어도
  `evidence_review_required`로 차단한다.
- 입력에 명시된 이벤트 유형을 키워드 추정보다 우선한다.
  - 장마철 이벤트에 증정 혜택이 있어도 `seasonal`을 유지한다.
- 각 콘셉트의 근거를 `핵심 근거`와 `보조 근거`로 분리했다.
  - 전략 축을 만든 핵심 신호 ID와 보강용 신호 ID를 별도로 기록한다.
  - 콘솔에는 내부 ID 대신 근거 역할, 핵심 문장, 출처를 표시한다.
- 이벤트 유형 불일치나 근거 추적 손상은 비평 `fail`로 처리하고
  `quality_repair_required` 상태에서 선택을 차단한다.
- 로컬 콘셉트 비평을 고정 4점 방식에서 근거 기반 루브릭으로 교체했다.
  - 타깃 상황과 핵심 근거 연결
  - 제품·입력 혜택 연결
  - 전략 축·핵심 근거·CTA 차별성
  - 한국어·업종·금지 표현·미확인 주장
  - 채널 확장 준비도
- 자동 비평은 최대 4점이다. 5점은 사람 평가에서만 기록한다.
- `revise` 또는 `fail`이 남은 안은 `quality_repair_required`로 선택을 막는다.
- 과거 `connection_test` 기록을 메인 검수 큐에서도 완료로 세지 않는다.
- 현재 실제 파일럿 상태:
  - 콘셉트 선택 가능 `1/5`: 장마철
  - 근거 검수 필요 `4/5`
  - 최종 카피 준비 `0/5`
  - 최종 사람 평가 `0/5`
  - 치명 오류 `0`
- 목표 감사는 아직 `fail`이 맞다. 사람 선택과 카피 승인을 자동 생성하지
  않았다.

### 검증

- 전체 프로젝트 테스트 `223개` 통과.
- Playwright 라이브 UI 감사 통과.
- 검수 패킷·목표 감사·검수 CSV의 대표 5건 ID와 순서가 일치한다.
- 장마철 결과는 `eventType=seasonal`, 비평 `pass`, 콘셉트별 신호 3개다.
- 장마철 자동 비평 평균 `4.0/5`, 이슈 `0`.
- 메인 검수 데스크는 장마철 카드 1개를 `콘셉트 선택` 상태로 전면 표시한다.
- 품질 요약과 콘셉트 선택 버튼 3개가 Playwright 계약을 통과했다.
- 콘솔 서버: `http://127.0.0.1:5177/`, PID `29588`.

### 다음 작업

1. 장마철 콘셉트 3안 중 하나를 사람이 선택한다.
2. 프로모션·교육·브랜딩 근거 후보를 사람이 검수한다.
3. 탄력 세럼의 공식 제품 근거를 추가하고 검수한다.
4. 근거 준비 완료 이벤트만 채널 카피를 생성·수정·승인한다.
5. 5건 평균 4.0 이상, 무수정 승인율 50% 이상, 치명 오류 0을 확인한다.

## 현재 상태 업데이트 (2026-07-01, 이벤트 단위 빠른 근거 검수)

- 대표 이벤트 후보 3개를 하나씩 저장하지 않아도 되도록 `빠른 검수안`을
  추가했다.
- 추천 규칙:
  - 필수 근거 역할마다 점수가 가장 높은 후보 1개를 selected 제안.
  - 같은 역할의 나머지 후보는 shortlist 제안.
  - 이미 사람이 선택한 역할은 덮어쓰지 않음.
- 저장 안전장치:
  - 사람이 확인창에서 명시적으로 승인해야 API 호출.
  - 서버는 `humanConfirmed: true`가 없으면 거절.
  - 이벤트 범위를 벗어난 신호 ID는 거절.
  - 모든 후보에 사유 태그와 구체 메모 필수.
  - 전체 검증 후 한 번만 저장해 부분 반영 방지.
- 탄력 세럼은 빠른 검수안을 승인해도 제품 proof가 없으므로 ready가 되지
  않는다.
- 실제 브라우저에서 확인창 노출을 확인하고 취소했다.
  - 저장소의 대표 후보 15개는 모두 `unreviewed`로 유지.

### 검증

- 전체 프로젝트 테스트 `200개` 통과.
- Playwright UI 감사 통과.
- 빠른 검수 확인창 취소 후 selected `0`.
- 서버 PID `28084`, `http://127.0.0.1:5177/`.

### 사람이 할 일

1. `이벤트 근거 준비`에서 이벤트를 연다.
2. 후보 출처와 관찰 요약 3개를 읽는다.
3. `후보 3개 검수안 확인`을 누른다.
4. 선택·보류 수를 확인하고 동의할 때만 확인한다.

## 현재 상태 업데이트 (2026-07-01, 대표 5건 실제 근거 후보 수집)

- 대표 5개 이벤트에 실제 출처 기반 근거 후보 15개를 수집했다.
  - 시즌: 기상청, AAD, 소비자 리뷰 분석 보도
  - 증정 프로모션: 소비자 프로모션 실험 2건, 이벤트 입력 혜택
  - 탄력 세럼 출시: Euromonitor 소비자 조사, PubMed 체계적 문헌고찰
  - 장벽 교육: AAD 전문 안내, 피부 건강 소셜미디어 단면 조사
  - 미니멀 브랜딩: Euromonitor 소비자 조사, 투명성 관련 산업 인터뷰
- 저장 파일:
  `assets/rules/cosmetics-pilot-public-evidence-snapshot.json`
- 모든 후보는 `unreviewed`로 저장했다. 자동 selected는 `0건`이다.
- 신호 저장소는 `118 -> 133개`가 됐다.
- 근거 큐 상태:
  - 대표 5건 `needs_review`
  - 나머지 15건 `needs_collection`
  - ready `0`
- 출처 감사:
  - 후보 `15`, 이벤트 `5`, 오류 `0`, 주의 `3`
  - 주의 2건은 5년이 지난 기초 프로모션 연구.
  - 주의 1건은 가상 탄력 세럼의 제품 고유 근거가 없다는 의도적 차단.
- 자료 후보와 실제 미확정 입력을 분리했다.
  - 시즌·프로모션·교육·브랜딩은 역할별 후보가 모두 존재.
  - 탄력 세럼만 공식 성분·사용법·시험 자료가 추가로 필요.
- 독립 출처 수는 `public_web` 같은 저장 유형이 아니라 URL 도메인 기준으로
  계산한다.
- 콘솔 신호 카드에 기관명, 문서 제목, 발행일, 확인일, 조사 방법, 원문 링크를
  표시한다.

### 검증

- 전체 프로젝트 테스트 `197개` 통과.
- 실제 Playwright UI 감사 통과.
- 출처 snapshot 감사 통과.
- 서버 PID `25716`, `http://127.0.0.1:5177/`.

### 바로 다음 작업

1. 콘솔에서 대표 5건의 후보 3개씩을 사람이 읽고 선택·보류·거절한다.
2. 탄력 세럼은 공식 제품 자료가 없으므로 proof를 selected 처리하지 않는다.
3. 나머지 4건이 역할 3개·독립 출처 2곳을 충족하면 InsightBrief를 만든다.
4. 탄력 세럼 제품 입력을 확보한 뒤 5번째 InsightBrief를 만든다.
5. 대표 5건만 카피를 재생성하고 목표 감사를 다시 실행한다.

## 현재 상태 업데이트 (2026-07-01, 이벤트 근거 수집·검수 큐)

- 화장품 고정 평가 이벤트 20건의 근거 준비 계획을 구현했다.
  - 계획: `assets/rules/cosmetics-benchmark-evidence-plan.json`
  - 생성기: `scripts/build_cosmetics_evidence_queue.py`
  - 결과: `.tmp/model-benchmarks/cosmetics-evidence-queue.json`
- 시즌, 프로모션, 출시, 교육, 브랜딩 대표 1건씩 총 5건을 우선 파일럿으로
  고정했다.
- 이벤트 유형별로 서로 다른 근거 조합을 강제한다.
  - 시즌: 고객 문제 + 시기 명분 + 검색·시장 흐름
  - 프로모션: 고객 욕구 + 구매 저항 + 혜택 근거
  - 출시: 고객 문제 + 구매 저항 + 제품 근거
  - 교육: 고객 문제 + 제품 근거 + 채널 반응 구조
  - 브랜딩: 고객 욕구 + 구매 저항 + 채널 반응 구조
- 준비 완료 조건은 `selected 3개 이상 + 필수 근거 역할 충족 + 출처 종류
  2개 이상`이다. 개수만 채운 동일 유형 신호는 통과하지 않는다.
- 콘솔에 `이벤트 근거 준비` 작업 큐를 추가했다.
  - 각 카드에서 조사 질문, 검색어, 부족한 근거, 현재 진행률을 확인한다.
  - `수집·검수 시작`을 누르면 해당 이벤트 ID/topic 신호만 표시한다.
  - 다른 이벤트 신호와 전체 랜덤 가설은 화면에서 섞이지 않는다.
- 공개 URL 캡처 결과의 `sourceRef.eventId`를 수집 시점부터 저장한다.
- 과거 사람 검수 기록이 있어도 이벤트 근거가 불일치하면 완료로 세지 않고
  `근거 준비`로 되돌린다.

### 현재 실제 수치

- 저장 신호 `118개`
- 검증 전 랜덤 가설 `100개`
- 기존 selected `16개`는 HSGN 여름 톤케어 전용
- 새 20개 평가 이벤트 전용 근거:
  - 준비 완료 `0/20`
  - 신호 검수 필요 `0/20`
  - 근거 수집 필요 `20/20`
  - 우선 파일럿 준비 완료 `0/5`
- 자동 selected 또는 가짜 사람 검수는 생성하지 않았다.

### 검증

- 전체 프로젝트 테스트 `196개` 통과.
- 실제 Playwright UI 감사 통과.
- 인앱 브라우저에서 `신제품 탄력 세럼 출시` 선택 후:
  - 필요한 근거 `고객 문제 · 구매 저항 · 제품 근거`
  - 범위 내 신호 `0개`
  - 타 이벤트 신호 노출 `0개`
  - 근거 패킷 버튼 비활성
  - 가로 넘침 없음
- 콘솔 서버 PID `29200`, `http://127.0.0.1:5177/`.

### 다음 핵심 작업

1. 우선 파일럿 5건에 공개 URL 근거를 이벤트별로 수집한다.
2. 각 이벤트에서 필수 근거 역할 3개와 출처 2종 이상을 사람이 검수한다.
3. 준비 완료된 이벤트만 전용 InsightBrief를 생성한다.
4. 5건만 재생성해 이벤트 근거 `5/5`와 카피 차별성을 확인한다.
5. 이후 나머지 15건으로 확장하고 카피 사람 검수를 재개한다.

## 현재 상태 업데이트 (2026-06-30, 이벤트 근거 격리)

- 기존 `근거 연결 20/20`이 거짓 양성이었음을 확인했다.
  - 화장품 벤치마크 20건 전체가 동일한 HSGN 여름 톤케어 신호 13개를 사용했다.
  - 겨울 보습, 클렌저 출시, 멤버십 행사까지 같은 신호 ID 묶음이었다.
- 이벤트별 근거 격리를 구현했다.
  - 저장 위치: `design_brain_wiki/marketing_signals/insight-briefs/<event-id>.json`
  - 생성기는 `InsightBrief.eventId`가 현재 이벤트와 정확히 일치할 때만 사용.
  - 구체 이벤트의 신호 패킷은 `sourceRef.eventId` 정확 일치 또는 명시된
    `topic` 일치 신호만 포함.
  - `general` 패킷이나 다른 이벤트 패킷은 구체 이벤트 생성에 재사용하지 않음.
- 벤치마크 캐시는 근거 이벤트 ID가 다르면 자동 재생성 대상으로 판정한다.
- 목표 감사의 근거 기준을 ID 존재 여부에서 이벤트 정확 일치로 교체했다.
- 현재 정직한 감사 결과:
  - 이벤트 전용 근거 `0/20`
  - 통과 케이스 `0/20`
  - 치명 오류 `0`
  - 사람 평가 기록 `5/20`은 보존
- 오염된 기존 카피는 콘솔에서 `근거 준비 필요`로 표시한다.
  - 문구 편집과 최종 검수 폼을 숨김.
  - 서버도 이벤트 전용 근거가 없으면 벤치마크 검수 저장을 차단.
- 콘솔에는 `이벤트 전용 근거 0/20`을 별도 표시한다.

### 검증

- 전체 프로젝트 테스트 `191개` 통과.
- 실제 Playwright UI 감사 통과.
- 이벤트 범위가 다른 selected 신호 제외, 타 이벤트 InsightBrief 차단,
  오래된 캐시 무효화, 오염 결과 승인 차단 테스트 통과.

### 다음 핵심 작업

1. 대표 5개 이벤트부터 이벤트별 신호를 수집·검수한다.
2. 이벤트당 selected 신호 3개 이상으로 전용 InsightBrief를 만든다.
3. 해당 5건만 재생성해 `이벤트 전용 근거 5/5`를 먼저 확인한다.
4. 이후 20건으로 확장하고 카피 사람 검수를 재개한다.

## 현재 상태 업데이트 (2026-06-30, 검수 이어하기·피드백 품질 게이트)

- 메인 광고 기획 검수 데스크에 영구 진행률을 추가했다.
  - 카피 검수 `5/20`
  - 전략 검수 `0/30`
  - 실제 문구 교정 `0/1`
- `카피 검수 이어하기` 버튼으로 첫 미검수 이벤트에 바로 이동한다.
- 전략 또는 카피 저장 후 다음 미검수 카드로 자동 이동한다.
- 새로고침하거나 서버를 다시 열어도 진행률은 실제 저장된 검수 데이터를
  기준으로 다시 계산되므로 별도 세션 상태가 유실되지 않는다.
- 학습 가치가 없는 빈 피드백 저장을 차단했다.
  - 전략 `selected / shortlist / rejected`: 사유 태그 1개 이상과 구체 메모 필수.
  - 카피 승인/수정 요청: 사유 태그 1개 이상과 구체 메모 필수.
  - 이벤트 run 검수와 20건 벤치마크 검수 모두 동일 정책.
  - 전략 CSV도 `검증` 단계에서 사유 태그/메모 누락을 먼저 차단.
- 검증 실패는 카피 결과 파일을 수정하기 전에 발생해 부분 저장을 막는다.
- 현재 사람 검수 수치는 자동으로 변경하지 않았다.
- 콘솔 서버: PID `36660`, `http://127.0.0.1:5177/`.

### 검증

- 전체 프로젝트 테스트 `185개` 통과.
- 실제 콘솔 Playwright UI 감사 통과.
- 1280px 가로 넘침 0, 검수 진입 버튼과 진행률 노출 확인.

## 현재 상태 업데이트 (2026-06-28, 교정 학습 실증 감사)

- 사람이 수정한 카피가 다음 로컬 생성에 실제 반영되는지 확인하는 독립 감사를 추가했다.
- 콘솔 광고 기획 검수 데스크에 `교정 학습 확인` 버튼과 상태 요약을 추가했다.
  - `수정 데이터 필요`: 승인된 실제 수정문이 아직 없음.
  - `적용 확인 대기`: 수정문은 있으나 새 생성 적용 검증 전.
  - `학습 연결 통과`: 같은 이벤트를 새로 생성했을 때 교정 ID 적용 확인.
  - `적용 확인 필요`: 이벤트·채널·원문 일치 조건 때문에 일부 교정 미적용.
- 감사 스크립트:
  - `scripts/audit_copy_correction_loop.py --verify-application`
  - 결과: `.tmp/model-benchmarks/copy-correction-loop-audit.json`
- 단순 승인본은 학습 수정으로 세지 않는다. `originalCopy != editedCopy`인 승인
  레코드만 이벤트·채널별 최신 교정으로 검사한다.
- 현재 실데이터 결과는 `needs_human_correction`이다.
  - 저장 교정 `0`
  - 승인된 실제 수정 `0`
  - 이는 기능 실패가 아니라 아직 사람이 문구를 고쳐 저장하지 않은 상태다.
- 콘솔 서버를 새 코드로 재시작했다: PID `24048`, `http://127.0.0.1:5177/`.

### 검증

- 전체 프로젝트 테스트 `183개` 통과.
- 실제 콘솔 Playwright UI 감사 통과.
- 교정 감사 버튼/요약 노출, 가로 넘침 0 확인.

## 현재 체크포인트 (2026-06-28, 인수인계)

- 활성 목표: 화장품 고정 평가 이벤트 20건에서 치명 오류 0건, 사람 평가 평균 4.0 이상, 무수정 승인율 50% 이상 달성.
- 자동 생성 연결 상태:
  - 콘셉트 3안 `20/20`
  - 채널별 카피 패키지 `20/20`
  - 콘셉트 차별성 통과 `20/20`
  - 근거 연결 통과 `20/20`
  - 치명 오류 `0`
- 사람 검수 상태:
  - 카피 평가 `5/20`
  - 전략 `selected + shortlist 0/30`
  - 실제 `CopyCorrectionRecord` `0건`
- 따라서 목표 감사는 아직 `fail`이 정상이다. 남은 blocker는
  `STRATEGY_REVIEW_BELOW_30`, `PILOT_HUMAN_REVIEWS_INCOMPLETE`다.
- 콘솔 `http://127.0.0.1:5177/` 응답 `200` 확인.
- 마지막 검증:
  - 전체 테스트 `177개` 통과
  - Playwright UI 감사 통과
  - 1280px 가로 넘침, raw JSON, A/B 카드, 개발자 상태값 노출 없음

### 바로 이어서 할 일

1. 콘솔 `전략 검수 시작`에서 추천 상위 전략을 확인하고 `selected / shortlist` 합계 30건을 사람 판정으로 저장한다.
2. 이벤트 기획 검수 큐에서 남은 카피 15건을 직접 수정 또는 승인한다.
3. 최소 1건을 실제 수정 저장해 `CopyCorrectionRecord`를 만든다.
4. 같은 이벤트를 재생성하고 `correctionSearch.appliedIds` 반영을 확인한다.
5. `scripts/audit_cosmetics_pilot_goal.py --limit 20`을 다시 실행한다.

상세 구현과 파일별 변경은 `knowledge/09_HANDOFF.md`의 최신 인수인계 및
`C:\Users\jinkiwon\AppData\Local\Temp\codex-handoff-cosmetics-ad-planning-2026-06-28.md`를 따른다.

## 현재 상태 업데이트 (2026-06-28, 전략 30건 집중 검수 UX)

- 전략 검수 `0/30` 병목을 빠르게 처리하도록 콘솔을 개선했다.
- 메인 광고 기획 검수 데스크에 `전략 검수 시작` 버튼을 추가했다.
  - 클릭하면 고급 데이터 검수 영역을 열고 전략 집중 큐로 이동한다.
- 전략 검수 큐는 추천 점수 높은 3건씩 표시한다.
  - 저장 후 다음 미검수 전략이 자동으로 앞으로 온다.
- 각 카드에서 광고 원문 미리보기와 추상 전략을 나란히 비교한다.
  - 원문, 추상 훅, 설득 순서, 타깃 인사이트를 한 화면에서 확인.
- `추천대로 생성 예시 후보/참고 후보/거절 후보 저장` 버튼을 추가했다.
  - 확인창에서 사람이 명시적으로 승인해야 저장된다.
  - 추천 전략 필드, 루브릭 점수, 사유 태그, 검수 메모가 함께 반영된다.
  - 자동 selected 승격 정책은 여전히 금지다.
- CSV 검수 경로도 그대로 유지한다.

### 검증

- 실제 UI에서 전략 카드 3개, 추천 판정 버튼 3개, 메인 진입 버튼 1개 확인.
- 가로 넘침 0.
- 전체 테스트 177개 통과.
- Playwright UI 감사 통과.

## 현재 상태 업데이트 (2026-06-28, 로컬 교정 학습 루프 연결)

- `CopyCorrectionRecord`가 저장만 되고 로컬 생성에는 쓰이지 않던 빈칸을 수정했다.
- 로컬 결정론적 카피 생성기도 승인된 교정 데이터를 검색한다.
  - 업종과 브랜드를 기준으로 격리 검색.
  - 브랜드가 없는 생성은 다른 브랜드 교정을 가져오지 않는다.
  - 벤치마크는 `benchmark_cosmetics` 브랜드로 별도 격리.
- 직접 문구 재사용 정책:
  - 같은 이벤트·같은 채널이고 현재 생성 필드가 저장된 원문과 정확히 일치할 때만 승인 수정문을 재적용한다.
  - 다른 이벤트의 수정문은 직접 복사하지 않는다.
  - 결과에 `correctionSearch`, `correctionExampleIds`를 기록해 어떤 교정이 적용됐는지 추적한다.
- 외부 모델 경로는 기존처럼 승인 교정 예시를 구조화 입력에 포함한다.
- 테스트에서 같은 이벤트 수정문 재적용과 다른 이벤트 직접 복사 차단을 확인했다.

### 검증

- `.venv\Scripts\python.exe scripts\run_project_tests.py` 통과: 176 tests.
- Playwright 콘솔 UI 감사 통과.

## 현재 상태 업데이트 (2026-06-28, 카피 집중 검수·교정 데이터 저장)

- 20건 벤치마크 카피를 콘솔에서 직접 수정할 수 있게 했다.
  - 채널별 `헤드라인`, `첫 문장`, `본문`, `CTA`, 슬라이드 문장을 사람이 읽는 필드로 수정한다.
  - raw JSON 편집은 사용하지 않는다.
- 벤치마크 검수 저장 시 다음이 함께 처리된다.
  - 수정문을 `.tmp/model-benchmarks/cosmetics-external-results.json`에 반영.
  - 생성 원문은 각 출력의 `generatedCopy`로 보존.
  - 사람 점수, 승인 여부, 사유 태그, 메모, edits를 human review에 저장.
  - 채널별 `CopyCorrectionRecord`를 `design_brain_wiki/ad_strategy/copy-corrections.json`에 저장.
  - 같은 교정 ID를 다시 저장하면 중복 추가하지 않고 최신 승인 상태로 갱신.
- 최종 승인 조건을 강화했다.
  - 사람 루브릭 평균 4.0 미만이면 승인 불가.
  - QA issue가 남아 있으면 승인 불가.
- 이벤트 기획 검수 데스크는 미검수 3건씩 집중 표시한다.
  - 저장하면 다음 미검수 이벤트가 자동으로 앞으로 온다.
  - 완료 건은 최근 3건을 접이식으로 다시 볼 수 있다.
- Playwright UI 감사의 오래된 셀렉터를 실제 클래스명으로 수정했다.
  - 기획 카드, 콘셉트 카드, 카피 카드, 수정 필드, 검수 폼을 실제 DOM에서 검사한다.

### 실제 UI 감사 결과

- 기획 검수 카드 `3`
- 콘셉트 카드 `9`
- 카피 카드 `16`
- 카피 수정 필드 `200`
- 검수 폼 `3`
- 가로 넘침 `0`
- raw JSON/A-B/개발자 용어 노출 `0`

### 현재 남은 사람 작업

1. 집중 검수 큐에서 미평가 카피 15건을 수정 또는 승인한다.
2. 고급 데이터 검수에서 전략 30건을 `selected / shortlist`로 저장한다.
3. 20건 사람 평가가 끝난 뒤 파일럿 목표 감사를 다시 실행한다.

### 검증

- `.venv\Scripts\python.exe scripts\run_project_tests.py` 통과: 175 tests.
- `.venv\Scripts\python.exe scripts\audit_console_ui_playwright.py --url http://127.0.0.1:5177/ --timeout-ms 20000` 통과.
- 콘솔 서버 `http://127.0.0.1:5177/` 실행 중.

## 현재 상태 업데이트 (2026-06-21, 20건 카피 연결 확인 완료)

- 화장품 평가셋 20건 전체가 카피 패키지 생성까지 완료됐다.
  - 결과 상태: `complete 20/20`
  - `candidateReady 20/20`, `copyReady 20/20`, `humanReviewed 5/20`
  - 완료 20건 기준 `criticalErrorCount 0`
- 남아 있던 15건의 콘셉트 선택은 `connection_check_default`로 기록했다.
  - 이는 연결 확인용 기본 콘셉트 선택이며 사람 선호나 최종 승인으로 보지 않는다.
  - 사람 평가와 최종 승인은 여전히 별도 검수에서 저장해야 한다.
- 콘솔에 `선택 대기 카피 연결 확인` 버튼을 추가했다.
  - `scripts/run_ad_planning_pilot.py --limit 20 --select-pending-concepts`를 실행하는 흐름이다.
  - 자동 승인은 하지 않고, 카피 생성 연결만 확인한다.
- 독립 파일럿 감사는 아직 `fail`이 정상이다.
  - 이유: 사람 평가가 5/20이라 `PILOT_HUMAN_REVIEWS_INCOMPLETE`가 남아 있다.
  - 전략 검수도 아직 0/30이라 `STRATEGY_REVIEW_BELOW_30`가 남아 있다.

### 검증

- `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 20 --select-pending-concepts` 실행.
- `.venv\Scripts\python.exe scripts\audit_cosmetics_pilot_goal.py --limit 20` 결과: `copyReady 20`, `criticalErrorCount 0`, `humanReviewed 5`, status `fail`.
- `.venv\Scripts\python.exe scripts\run_project_tests.py` 통과: 172 tests.
- `.venv\Scripts\python.exe scripts\audit_console_ui_playwright.py --url http://127.0.0.1:5177/ --timeout-ms 20000` 통과.

## 현재 상태 업데이트 (2026-06-20, 전략 검수 추천 초안 + 20건 콘셉트 확장)

- 화장품 고정 평가셋 20건 전체에 대해 콘셉트 후보 3안을 생성했다.
  - 결과 상태: `concept_review_pending 15건`, `complete 5건`.
  - `candidateReady 20/20`, `copyReady 5/20`, `humanReviewed 5/20`.
  - 현재 치명 오류는 완료 5건 기준 `0`.
- 전략 검수 병목을 줄이기 위해 46개 레거시 Meta 전략에 `reviewRecommendation` 초안을 붙였다.
  - 자동으로 `selected`를 저장하지 않는다. 사람 검수 기준을 속이지 않기 위해 추천은 입력 보조로만 쓴다.
  - 추천 초안에는 `suggestedDecision`, 추천 점수, 추천 사유, 위험 플래그, 추천 전략 필드, 추천 루브릭 점수, 추천 reason tag가 포함된다.
- 전략 CSV 내보내기 30건에 추천 컬럼을 추가했다.
  - `suggestedDecision`, `recommendationScore`, `recommendationReasons`, `recommendationRisks`.
  - 빈 전략 필드와 점수 칸은 추천 초안으로 미리 채워 사람이 빠르게 검수할 수 있다.
- 콘솔 고급 데이터 검수 섹션을 개선했다.
  - 추천 점수 높은 검수 대기 전략 12개를 먼저 보여준다.
  - `추천값 입력칸에 채우기` 버튼을 추가했다.
  - 최종 승격은 여전히 사람이 `선택 / 참고 / 거절`을 눌러야 저장된다.
- 이벤트 기획 검수 데스크는 더 이상 5건만 자르지 않고 선택 대기/카피 검수 대기 전체를 우선순위로 보여준다.

### 현재 남은 blocker

1. `STRATEGY_REVIEW_BELOW_30`: 추천 초안은 준비됐지만 실제 selected/shortlist 저장은 아직 0/30이다.
2. `PILOT_HUMAN_REVIEWS_INCOMPLETE`: 20건 중 15건은 콘셉트 선택과 카피 검수가 남아 있다.

### 검증

- `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 20` 실행.
- `.venv\Scripts\python.exe scripts\run_project_tests.py` 통과: 170 tests.
- `node --check ui\console\app.js` 통과.
- `.venv\Scripts\python.exe scripts\audit_console_ui_playwright.py --url http://127.0.0.1:5177/ --timeout-ms 20000` 통과.

## 현재 상태 업데이트 (2026-06-20, 화장품 파일럿 5건 품질 감사 정렬)

- 화장품 광고 기획 파일럿 5건은 현재 `candidateReady 5/5`, `copyReady 5/5`, `humanReviewed 5/5`, `criticalErrorCount 0`, `averageHumanScore 4.0`, `unchangedApprovalRate 1.0`으로 통과 상태다.
- 벤치마크 요약과 파일럿 목표 감사의 기준을 맞췄다. 이제 내부 `scorecard.criticalErrorCount`가 남아 있으면 파일럿 감사도 실패한다.
- 콘셉트 단계 비평기가 아직 생성되지 않은 카피/채널을 검사해 `concept_critic_channel_mismatch`를 치명 오류로 남기던 문제를 수정했다.
- 오래된 캐시가 깨진 한글, JSON/구조 노출, 근거 부족, scorecard 치명 오류를 포함하면 자동 재생성 대상으로 본다.
- 전체 테스트 `scripts/run_project_tests.py` 170개 통과, `node --check ui\console\app.js` 통과, Playwright 콘솔 UI 감사 통과.

### 바로 다음 작업

1. 전략 검수 `selected / shortlist`를 30개 이상으로 올린다. 현재 파일럿의 주요 blocker는 `STRATEGY_REVIEW_BELOW_30`이다.
2. 화장품 평가셋을 5건에서 20건으로 확장해 같은 감사 기준을 적용한다.
3. HSGN/경쟁/트렌드/계절 신호를 더 모아 이벤트당 근거 신호 수를 늘린다.
4. 사람이 실제로 수정한 카피 쌍을 누적해 다음 생성의 교정 예시로 연결한다.

## 현재 상태 업데이트 (2026-06-20, 공개 마케팅 신호 수집 UI 연결)

- 광고 기획 품질 목표를 문구 생성이 아니라 `근거 신호 수집 -> 사람 검수 -> InsightBrief -> 콘셉트/카피 생성` 흐름으로 정리했다.
- 콘솔 `마케팅 신호 검수` 영역에 공개 관찰 도구를 추가했다.
  - `Snapshot 가져오기`: `assets/rules/hsgn-public-marketing-snapshot.json` 같은 공개 관찰 묶음을 검수 대기 신호로 가져온다.
  - `URL 캡처`: 브랜드/공개 페이지 URL을 입력하면 Playwright 기반 공개 페이지 텍스트를 추상화해 마케팅 신호 snapshot으로 저장하고 검수 CSV까지 갱신한다.
- 서버 job 모드에 `public_capture`를 추가했다. 실행 시 `scripts/collect_marketing_signals.py --capture-url ... --source-kind ... --snapshot-output .tmp/marketing-signals/public-capture-latest.json --export-review`로 동작한다.
- `--capture-url` 반복 입력과 `--capture-urls-file`을 지원해 공개 URL 여러 개를 한 번에 신호화할 수 있다.
- 공개 URL 캡처 QA를 보강했다.
  - HTML/JSON 조각, 깨진 텍스트, 너무 짧은 관찰은 `capture_quality_blocked`로 표시한다.
  - `capture_quality_blocked` 신호는 `auto_select`가 켜져도 자동 selected로 승격하지 않는다.
  - 사람이 selected로 바꾸더라도 InsightBrief에서는 blocked risk flag가 있는 신호를 제외한다.
- 검수 저장 정책을 강화했다.
  - 콘솔 버튼 또는 CSV import에서 `capture_quality_blocked` 신호를 selected로 저장하려 하면 자동으로 `shortlist`로 낮춘다.
  - reason tag에 `capture_quality_blocked`를 붙이고, 검수 메모에 “selected 대신 보류” 사유를 남긴다.
  - 콘솔 요약에 `사용 가능` selected 수와 `품질 차단` 신호 수를 별도 표시한다.
  - InsightBrief 버튼과 상태 문구는 selected 전체 수가 아니라 `selectedUsable` 기준으로 열린다.
- 차단 신호 정제 흐름을 추가했다.
  - 마케팅 신호 카드에서 `관찰 요약`, `타깃 정의`, `기획 인사이트`를 사람이 직접 정제해 저장할 수 있다.
  - 정제 저장 후 품질 차단 문제가 사라지면 `capture_quality_blocked` 계열 flag를 제거하고 `human_cleaned_public_signal`로 표시한다.
  - 정제된 신호는 다시 selected로 승격되어 `selectedUsable`에 포함될 수 있다.
- 마케팅 신호 -> InsightBrief -> 02 기획 산출물 연결 감사를 추가했다.
  - `scripts/audit_marketing_planning_loop.py --run <run> --minimum-signals 5`
  - 결과: `.tmp/model-benchmarks/marketing-planning-loop-audit.json`
  - HSGN run 감사 결과 `pass`: selectedUsable 16, InsightBrief ready, scorecard pass, criticalErrorCount 0, averageScore 4.0.
  - 콘셉트 3안과 카피 산출물 4개 모두 marketingSignalIds를 포함한다.
- 콘솔에서 `근거 연결 감사` 버튼으로 위 감사를 job으로 실행할 수 있게 했다.
  - API: `POST /api/marketing-planning-loop/audit`
  - job label: `marketing planning loop audit <minimumSignals>`
  - Playwright 감사가 버튼 노출을 확인한다.
- 최신 근거 연결 감사 결과를 콘솔 광고 기획 검수 패널에 바로 표시한다.
  - bootstrap과 `GET /api/marketing-planning-loop/audit`가 `.tmp/model-benchmarks/marketing-planning-loop-audit.json`을 반환한다.
  - 표시 항목: 사용 가능 신호, 평균 점수, 치명 오류, 콘셉트 연결 수, 카피 연결 수.
- 콘솔 UI 감사 기준:
  - 1280px 화면에서 가로 넘침 없음.
  - 메인 화면에 raw JSON, A/B 비교, 개발자 상태값 노출 없음.
  - 마케팅 신호 job 버튼 6개 노출 확인.
- 검증:
  - `node --check ui\console\app.js` 통과.
  - `python -m unittest tests.test_ad_planning_engine tests.test_ad_planning_upgrade tests.test_ad_planning_quality_gate tests.test_public_marketing_signal_collector tests.test_marketing_intelligence_console tests.test_marketing_intelligence_signals tests.test_marketing_insight_brief tests.test_console_ui_playwright_audit tests.test_marketing_planning_loop_audit tests.test_ad_planning_pilot_runner` => 79개 통과.
  - `scripts\audit_console_ui_playwright.py --url http://127.0.0.1:5177/ --timeout-ms 20000` => pass.

### 다음 작업

1. HSGN 기준 공개 URL 5~10개를 캡처해 `unreviewed` 신호를 늘린다.
2. 콘솔에서 공개 신호를 `selected / shortlist / rejected`로 검수한다.
3. selected 신호 3개 이상으로 `InsightBrief`를 재생성한다.
4. HSGN 이벤트 5건을 다시 02단계까지 실행해 콘셉트 3안의 근거 분리와 최종 카피 설득력을 비교한다.
5. 공개 URL 캡처 결과에서 원문 복붙, 허위 주장, 깨진 텍스트가 들어오지 않는지 QA 항목을 더 세분화한다.

## 현재 상태 업데이트 (2026-06-20, Claude Code 전환 + 취향 모델 이미지 학습 루프)

- Codex→Claude Code 전환. 점검·실행은 메인 폴더+메인 venv에서만(worktree는 코드만).
- 미커밋 176개를 `checkpoint/wip-2026-06-20`로 보관. pipeline-health mojibake 오탐 버그 수정(fail→warning). 테스트 24→**153개** 통과.
- 레퍼런스 정확도 측정 하니스(`replay_reference_accuracy.py`) 신설. 베이스라인 2-class 62.7%(learned rules 효과 확인). Qwen 비전은 정확도 못 올림→보류.
- **취향 모델(이미지 학습) 루프 완성** = 기원님 핵심 목적: 경쟁 마케팅 이미지를 CLIP 임베딩+분류기로 학습. 단일 Meta 0.93 / 통합 240장 0.82. 신규 스크립트 5종(`train_taste_model`/`rank_images_by_taste`/`ingest_image_folder_session`/`pretag_session_with_taste`/`taste_labels`).
- source-mix 회귀 gate, 마케팅 신호 자동화(캘린더+올영CSV) 추가. 번들 chromium 설치, Pinterest 로그인 완료.
- 수집 우선순위: Meta(1) > Chrome 확장 gallery-dl 원본(2) > Playwright 검색(비추천).

### 다음 할 일 (병목 = 사람 라벨링)

1. 🙋 콘솔 판단 훈련에서 `cosmetics_skincare/meta_competitor_001`(Meta 광고 336장 + AI 추천 selected 45/shortlist 21) 라벨링. 추천 66장 우선.
2. `python scripts/train_taste_model.py` 재학습 → AUC 0.82 대비 향상 확인.
3. 결과로 수집 쿼리/임계값 조정, 선순환 반복.
4. 검수 외 코드 작업은 사실상 완료(상세 [[BACKLOG]]).

→ 상세: [[09_HANDOFF]], [[TASTE_MODEL_2026-06-20]], [[REFERENCE_ACCURACY_2026-06-20]]

## 현재 상태 업데이트 (2026-06-18, 마케팅 인텔리전스 데이터 플로우 목표 설정)

- 광고 기획 품질 병목을 단순 문장 생성 문제가 아니라 시장·고객·트렌드 근거 부족으로 재정의했다.
- 실제 마케터 수준의 기획에는 타깃 반응, 제품 랭킹, 계절/날씨, Meta/Instagram 흐름, Google/Naver 트렌드, 리뷰 언어, 경쟁 오퍼가 필요하다고 판단했다.
- 새 기준 문서 `knowledge/MARKETING_INTELLIGENCE_DATA_FLOW.md`를 추가했다.
- 장기 목표는 화장품 광고 기획용 `MarketingSignal` 1,000개 이상 누적이다.
- 1차 목표는 화장품 파일럿 5건에서 이벤트당 근거 신호 50개 이상, 콘셉트별 근거 신호 3개 이상, 훅/타깃/제품 연결 평균 4.0/5 이상이다.
- 이 과제는 하루에 한 번씩 시장/고객/트렌드 신호를 추가하는 장기 데이터 플로우로 운영한다.
- 1차 자동화로 `seed_random` 화장품 마케팅 신호 50개를 생성해 검수 대기열에 저장했다.
- 검수 CSV: `.tmp/marketing-signals/marketing-signal-review-sheet.csv`.
- 콘솔 대시보드에 `마케팅 신호 검수` 섹션을 추가했다.
- 화면에서 50개 신호 중 검수 대기 12개를 카드로 보고 `선택 / 보류 / 거절`을 저장할 수 있다.
- 브라우저 검증: 내부 코드 노출 0건, 텍스트 넘침 0건.
- selected 신호만 묶는 `InsightBrief` 게이트를 추가했다.
- 현재 selected 신호 0개라 `InsightBrief`는 `needs_signal_review`이며 `InsightBrief 만들기` 버튼은 비활성화된다.
- ready `InsightBrief`가 생기면 콘셉트 후보와 채널별 카피 근거에 `marketingSignalIds`와 마케팅 신호 문장이 기록되도록 연결했다.
- selected 신호가 부족하면 기획 점수표에 `marketing_signal_review_required` 경고가 남는다.

### 다음 큰 작업

1. 마케팅 신호 50개를 `선택 / 보류 / 거절`로 실제 검수한다.
2. selected 신호 3개 이상을 만든 뒤 `InsightBrief 만들기`를 실행한다.
3. ready `InsightBrief`로 파일럿 5건을 다시 실행해 훅/타깃/제품 연결 점수를 비교한다.
4. 올리브영 랭킹·리뷰 키워드 CSV 업로드 포맷을 만든다.
5. 날씨·계절 캘린더 신호를 자동 생성한다.

## 현재 상태 업데이트 (2026-06-17, 광고 카피 근거층 보강)

- 광고 기획 검수 데스크의 `문구 근거`가 `concept_01`, `benchmark` 같은 내부 값으로 보이던 문제를 수정했다.
- 채널별 카피 패키지에 타깃 설정 이유, 제품 역할, 혜택 역할, 채널 역할, 검증 사실을 함께 기록한다.
- 콘솔에서는 각 카피 카드에 `문구 근거`, `타깃`, `제품 역할`, `혜택 역할`, `채널 역할`을 분리해 보여준다.
- 기존 화장품 파일럿/벤치마크 캐시를 최신 근거 로직으로 재생성했다.
- 5177 콘솔 서버가 중복 실행되어 낡은 API 응답을 주던 상태를 정리하고 서버를 재시작했다.
- 검증: 브라우저에서 조사 오류 `직장인로`, `증정는` 0건, 근거 필드 노출 확인. 광고 기획 관련 unittest 31개 통과.

### 남은 품질 목표

1. 실제 설득력 향상은 `selected` 전략 사례 30건 이상 검수 후 다시 평가한다.
2. 현재 근거는 입력 브리프와 콘셉트 구조 기반이므로, 좋은/나쁜 광고 사례의 사람 평가 데이터를 더 채워야 한다.

## 현재 상태 업데이트 (2026-06-14, 검증된 Meta 제품 비주얼 03단계 자동 공급)

- ComfyUI 워크플로와 사람 검토·선택 작업은 이번 자동화 목표에서 제외한다.
- `services/ad_reference/meta_source_mix_provider.py`를 추가해 Qwen 검증이 끝난 일반 Meta 제품·성분 검색 결과를 화장품 이벤트의 `03_reference_research`에 자동 공급한다.
- 공급 조건은 검토 5건 이상, clean product rate 20% 이상인 제품·성분 검색어와 `clean_product_visual` 판정이다.
- SHA 중복을 제거하고 검색어당 최대 2개, 광고당 최대 1개, 기본 총 6개로 제한한다.
- 브랜드 Meta 참조와 source-mix 참조는 각각 `META_BRAND_REFERENCE_MODE`, `META_SOURCE_MIX_REFERENCE_MODE`로 독립 제어한다.
- 실제 보유 데이터 검증에서 추천 검색어 4종으로부터 clean product visual 6개를 임시 run에 정상 공급했다.
- 프로젝트 테스트 58개 통과.

### 남은 자동화 목표

1. 신규 화장품 이벤트 3건에서 source-mix 공급 수, 중복률, QA 경고율을 반복 측정한다.
2. 공급 품질이 낮아질 때 자동 경고하거나 provider를 자동 비활성화하는 회귀 gate를 추가한다.
3. 세 번째 최종 archive는 사람 선택·승인 뒤에만 가능하므로 자동 완료하지 않는다.

## 현재 상태 업데이트 (2026-06-14, 화장품 Meta 적응형 수집 전략)

- `services/ad_reference/collection_strategy.py`로 검수 완료 배치의 누적 증거를 사용해 다음 브랜드를 자동 추천한다.
- 적응형 전략은 검증된 통과 브랜드 1개를 앵커로 두고, 미통과 탐색 브랜드를 우선해 커버리지를 늘린다.
- 직전 배치 브랜드는 뒤로 보내며, 낮은 누적 광고주 일치율·프로모션 문구형 편중 브랜드는 자동 감점한다.
- 과거 Qwen 성격 검수 전 통과 기록, dry-run, 광고 0건 배치는 추천·최신 운영 지표를 오염시키지 않는다.
- 기본 검증 배치를 3×3에서 5개 브랜드 × 5개 광고로 변경했다.
- 정지 이미지만 수집하는 옵션은 실제 `SKIN1004` 테스트에서 광고 0건이라 기본값으로 사용하지 않는다.
- 실제 적응형 검증 배치 `2026-06-14_adaptive_cosmetics_validation`:
  - raw 25 / advertiser matched 14 / accepted 2 / excluded 6.
  - 광고주 일치율 56%, creative acceptance 25%, 브랜드 커버리지 40%.
- 적응형 누적 5배치·원본 광고 77개:
  - creative acceptance 23.5%, 브랜드 커버리지 16.7%.
  - 기존 20개 브랜드 기준 배치 대비 각각 +17.6%p, +6.7%p.
- 77개 누적 후에도 브랜드 커버리지 30% 미만이라 검증 브랜드 수집은 `secondary_campaign_reference`로 판정했다.
- `scripts/collect_meta_source_mix.py`가 표본이 부족한 상품·성분 쿼리를 자동 수집하고 Qwen 검수한다.
- 자동 보완 수집 계획을 모두 실행한 결과 Qwen 검수 48장 중 클린 제품 비주얼 24장, 전체 회수율 50%다.
- 검증 쿼리: `나이아신아마이드 세럼` 77.8%, `스킨케어 제품` 66.7%, `스킨케어 세럼` 40%, `스킨케어 크림` 38.9%.
- 콘솔에서 공급원 판정과 검증된 보완 쿼리를 확인하고, 쿼리 버튼으로 일반 Meta 수집 입력을 준비할 수 있다.
- 콘솔에서 적응형/레지스트리 순서, 전체/정지 이미지 소재 선택, 다음 추천, 기준 배치 비교를 확인한다.
- 프로젝트 테스트 54개, project hook, 실제 콘솔 렌더링 통과.

### 다음 작업

1. 검증된 상품·성분 쿼리를 신규 이벤트 레퍼런스 수집에 병행한다.
2. 세 번째 실제 이벤트를 최종 archive 상태까지 완료한다.

## 현재 상태 업데이트 (2026-06-14, 반복 실운영 증거 감사)

- `scripts/audit_repeated_operations.py`로 실제 run 이력의 반복 운영 증거를 자동 판정한다.
- 현재 자동화 구간 완료는 서로 다른 이벤트 5종으로 목표 3종을 충족했다.
- `scripts/run_recovery_rehearsal.py`로 테스트 이벤트 03 단계의 실제 실패 기록 후 동일 run 재실행 복구를 증명했다.
- 동일 run 실패 후 복구는 1/1건으로 충족했다.
- 최종 종료 성공은 서로 다른 이벤트 2/3종이라 실제 운영 완료 판정은 아직 `incomplete`다.
- Workboard에 `자동화 구간 반복 이벤트 5/3`, `최종 종료 이벤트 2/3`, `실패 후 복구 run 1/1`을 표시한다.
- Workboard가 세 번째 종료에 가장 가까운 실제 run을 자동 표시한다.
- 현재 최우선 종료 후보: `2026-06-13_05-01-36_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`, 다음 단계 `05_admin_selection`.
- 리포트: `.tmp/repeated-operations/latest-repeated-operations.{json,md}`.
- 프로젝트 테스트 48개와 project hook 통과, 브라우저 JS 오류 0.

### 남은 완료 조건

1. 세 번째 서로 다른 실제 이벤트를 최종 archive 상태까지 완료한다.
2. 완료 후 반복 운영 감사가 `pass`인지 확인한다.

## 현재 상태 업데이트 (2026-06-14, Meta 운영 지표 + Workboard 노출)

- 기존 Meta 검증 브랜드 배치 17개를 읽어 회수율·브랜드 커버리지·편중·creative type을 자동 계산한다.
- 리포트: `scripts/report_meta_brand_metrics.py`, `.tmp/meta-brand-metrics/latest-meta-brand-metrics.json`.
- 최신 화장품 배치: 광고주 일치율 60.0%, 성격 검수 통과율 6.0%, 브랜드 커버리지 10.0%, 통과 이미지 4장.
- 최신 주얼리 배치: 광고주 일치율 43.1%, 성격 검수 통과율 95.2%, 브랜드 커버리지 50.0%, 통과 이미지 60장.
- 화장품 병목은 광고주 검색 실패보다 `promotion_text_heavy` 62장 편중과 낮은 통과 브랜드 수다.
- 콘솔 Workboard에 운영 준비도와 Meta 경고를, Meta 광고 수집 화면에 업종별 지표 카드를 표시한다.
- 공통 project hook이 Meta 지표 리포트도 매번 갱신한다.
- 검증: 프로젝트 테스트 46개, 운영 준비도 감사, 자산 무결성 감사, project hook 모두 통과. 브라우저 JS 오류 0.

### 다음 작업

1. 세 번째 실제 이벤트를 최종 archive 상태까지 완료한다.
2. 반복 운영 감사 최종 `pass`를 확인한다.
3. 화장품 Meta 수집 쿼리/브랜드 전략을 바꾸고 통과율·커버리지 개선 여부를 새 배치로 비교한다.

## 현재 상태 업데이트 (2026-06-14, 자동화 운영 준비도 전체 검토)

- 사람 직접 검수와 별도 제작 중인 ComfyUI 워크플로를 제외하고 운영 준비도를 감사했다.
- 신규 단계 일반 예외가 `in_progress`에 고착되지 않고 `blocked/failed`와 오류 원인을 남기도록 수정했다.
- run 생성 전 event/brand 입력 스키마 검증을 추가하고 `objective|purpose` 계약 불일치를 정리했다.
- 콘솔 job 이력을 `.tmp/console-jobs/jobs.json`에 영속화하고 재시작 중단 작업을 `interrupted`로 표시한다.
- Meta provider가 사람 최종 판단을 사용하도록 연결해 final rejected 제외, final selected 우선순위를 적용했다.
- 실제 run state인 `reference_research`, `reference_ready`, `review_pending`을 공식 상태 계약에 추가했다.
- 자동 감사: `scripts/audit_operational_readiness.py`.
- `scripts/reconcile_run_states.py --all --apply`로 과거 stale run 2개와 legacy archive run 2개를 이력 보존 방식으로 정리했다.
- learned rules 안전 승격 경로를 연결했다. 현재 `cosmetics_skincare/soften_rejected_to_shortlist` 1개만 5개 세션·244건 검수 근거로 승격됐다.
- 기존 QA 전 package 1개를 `production-package-legacy-draft`로 migration했다.
- `scripts/audit_asset_integrity.py`를 추가했으며 실제 자산 감사 `pass`.
- 현재 운영 준비도 감사 `pass`: terminal run 4개, invalid event 0개, learned rule consumer 1개.
- 공통 project hook에 운영 준비도 감사와 자산 무결성 감사를 연결했다.
- 상세: [[OPERATIONS_READINESS_REVIEW_2026-06-14]]

### 다음 작업

1. 반복 실제 이벤트 3건으로 운영 완성도를 검증한다.
2. 화장품 Meta 지표 개선 배치를 만든다.

## 현재 상태 업데이트 (2026-06-13, Qwen 경쟁사 Meta 130장 분류 완료)

- Ollama `qwen2.5vl:7b`로 경쟁사 Meta 이미지 130장을 실제 분류했다.
- 확장 배치: `2026-06-13_qwen_competitor_cosmetics_expanded`, `2026-06-13_qwen_competitor_jewelry_expanded`.
- 결과: accepted 64장, excluded 66장, 미분류·검수 보류 0장.
- 고유 SHA 기준: 전체 121장, accepted 61장, excluded 60장.
- 성격 분포: 프로모션 문구형 62, 주얼리 제품 34, 모델·라이프스타일 17, 브랜드 캠페인 11, 클린 제품 5, 주얼리 제작 1장.
- 모든 이미지가 제외된 광고도 개별 Qwen 판정과 제외 사유를 `accepted-ads.json.excludedItems`에 보존하도록 수정했다.
- 기존 배치를 네트워크 재수집 없이 다시 분류하는 `scripts/reclassify_meta_brand_batch.py`를 추가했다.
- 검증: 프로젝트 테스트 27개 통과, pipeline health audit `pass`, project hook `pass`.

### 다음 작업

1. accepted 고유 이미지 61장으로 신규 검수 세션을 만들고 사람 판단과 Qwen 판정을 비교한다.
2. 화장품 Meta 수집의 프로모션 문구형 편중을 낮출 브랜드·쿼리 전략을 보강한다.
3. accepted 이미지의 브랜드별 편중을 제한한다.

## 현재 상태 업데이트 (2026-06-13, 전체 남은 작업 분석)

- 결론: 운영 콘솔·레퍼런스 판단·placeholder 제어 흐름은 정상이고, 실제 제작 자산 완료 경로는 아직 부분 준비다.
- 서비스 상태: 콘솔/ComfyUI/Ollama 정상, OpenCLIP/CUDA 사용 가능.
- 검증: pipeline health `pass`, hook check `pass`, 자동 테스트 총 24개 통과.
- 판단 데이터:
  - `meta_brand_review_001` 100/100 완료.
  - 현재 H&B 브리프 적합 레퍼런스 큐 117/117 완료.
- 신규 Qwen 경쟁사 수집:
  - 화장품 10개 브랜드 accepted image 1장.
  - 주얼리 10개 브랜드 accepted image 5장.
  - 총 6장이라 신규 100장 검수 세션은 아직 만들 수 없다.
- 최우선 남은 작업:
  1. ComfyUI live 단일 후보 생성/회수 안정화.
  2. generated 후보로 05→06→07 실제 E2E 완료 및 approved asset 1개 이상 생성.
  3. Meta 재수집 회수율 개선.
- 상세: [[PROJECT_REMAINING_STATUS_2026-06-13]]

## 현재 상태 업데이트 (2026-06-13, Meta 검수 저장 기능 점검 완료)

- `meta_brand_review/meta_brand_review_001` 사람 검수 저장을 콘솔/API에서 점검했다.
- selected / shortlist / rejected 저장, API 재조회, 브라우저 새로고침 후 판단 유지가 모두 정상이다.
- 새로고침 시 마지막 선택 세션은 유지되지 않고 기본 `reference_learning/all`로 돌아가지만, 저장된 판단은 유지된다.
- 최종 검수 완료: 100/100, selected 19 / shortlist 52 / rejected 29, accuracy 0.52.
- 최신 완료 상태로 summary/compare 생성을 다시 실행했고 모두 정상 종료했다.
- 생성 결과:
  - `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/kiwon_review_summary.md`
  - `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/correction_summary.md`
  - `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/learned_rules.json`
  - `design_brain_wiki/training_sessions/meta_brand_review/_comparisons/session-comparison.json`

### 다음 작업

1. Meta 재수집 결과로 새 검수 세션을 만들 때 동일 저장 경로를 사용한다.
2. 필요하면 새로고침 후 마지막 선택 세션을 복원하는 UX를 추가한다.

## 현재 상태 업데이트 (2026-06-13, 전체 파이프라인 감사)

- 전체 감사 기준 결론은 `placeholder E2E는 동작, live 제작은 부분 준비`다.
- 대표 run에 Meta 레퍼런스 8장을 연결했고 01~07 제어 흐름을 검증했다.
- 실패 후보 선택과 실패 QA 승인 문제를 차단했다.
- 04 재생성 시 05~07의 오래된 완료/승인 상태를 자동으로 `locked` 처리하도록 수정했다.
- 최종 `scripts/audit_full_pipeline_health.py` 결과는 `pass`다.
- Qwen/Ollama는 실제 이미지 판정까지 정상이며 시작 스크립트의 오래된 고정 경로를 제거했다.
- 최우선 보완은 ComfyUI live 성능/회수와 Qwen 기반 Meta 100장 재수집이다.
- 상세: [[FULL_PIPELINE_AUDIT_2026-06-13]]

## 현재 상태 업데이트 (2026-06-13, 경쟁사 레지스트리 Meta 재수집)

- Meta 재수집은 `assets/rules/meta-brand-registry.json`의 화장품·주얼리 경쟁사 목록을 기준으로 시작한다.
- 신규 수집 이미지는 품질 통과 후 광고 성격을 자동 분류한다.
- `promotion_text_heavy`, `card_news`, `reject_noise`는 수집 단계에서 제외한다.
- Qwen 실패 또는 미실행 이미지는 자동 선택하지 않고 `unclassified/review`로 보류한다.
- 표본 재수집:
  - 화장품 3개 브랜드: 원본 광고 6개, 광고주 일치 4개, 품질 통과 이미지 9개.
  - 주얼리 3개 브랜드: 원본 광고 4개, 광고주 일치 3개, 품질 통과 이미지 1개.
- Ollama 0.30.6과 `qwen2.5vl:7b`를 2026-06-13 복구 설치했다.
- 실제 Medicube 표본 판정에서 `promotion_text_heavy`로 분류되고 자동 제외되는 것까지 확인했다.
- 기존 표본 10장은 `--no-creative-review`로 수집한 파일이라 재분류 전까지 `needsCreativeReview` 상태다.
- 표본 폴더:
  - `references/meta_ads/brand_registry_runs/2026-06-13_competitor_cosmetics_sample`
  - `references/meta_ads/brand_registry_runs/2026-06-13_competitor_jewelry_sample`

### 다음 작업

1. 경쟁사 표본을 자동 성격 분류와 함께 재수집 또는 재분류.
2. 통과 성격만으로 신규 100장 검수 세션을 만든 뒤 실제 브리프에 연결.

## 현재 상태 업데이트 (2026-06-11, Meta 병렬 개선 완료)

- Meta 100장 출처 대조 결과 Pinterest 실제 혼입은 0장이다. Pinterest처럼 보인 이미지는 Meta의 카드뉴스·프로모션 문구형 소재였다.
- `03_reference_research` Meta provider가 성격 검수 파일을 읽도록 연결해 `promotion_text_heavy` 34장, `card_news` 10장, `reject_noise`를 기본 제외한다.
- 화장품 Meta 후보는 성격 필터 적용 전 62장에서 적용 후 18장으로 줄어든다.
- 콘솔 API 기준 `meta_brand_review_001` 사람 검수 저장 기록은 0건이므로, 선택·제외 클릭 저장 여부를 다음 검수에서 확인해야 한다.
- 코드 리뷰 후 Meta reference 중복 import, 빈 브랜드명 일치 점수, 콘솔 완료 필터·상태 탭 충돌을 수정했다.
- 브랜드 수집기는 동시 batch 충돌 방지, 브랜드별 즉시 manifest 저장, `resume`/`retry-failed`, `failed-brands.json`을 지원한다.
- `meta_brand_review_001` 100장 성격 검수 결과: 프로모션 문구형 34, 카드뉴스 10, 모델·라이프스타일 19, 주얼리 제품 16장이다.
- 화장품 62장 중 프로모션 문구형과 카드뉴스가 44장이라 clean product·brand campaign 학습 풀에서는 기본 제외하는 기준을 잡았다.
- 콘솔 판단 훈련에 브랜드, 업종, 광고주 유형, 품질, 위험 신호, 완료 여부 필터를 추가했다.
- `03_reference_research`는 Meta 브랜드 검수 후보를 브리프 기준으로 검색하며 `direct` 우선, `partner`·`review` 감점 후 기존 Pinterest 결과와 병합한다.
- 테스트 런에서 Meta 후보 62개 중 direct/standard 8개를 선택·import했고 기존 Pinterest 및 Meta reference를 유지했다.
- 레지스트리 확장 조사: 화장품 20개, 주얼리 20개 후보를 `knowledge/META_BRAND_EXPANSION_CANDIDATES.md`에 정리했다.
- 통합 검증: 수집기 테스트 5개, provider 테스트 5개, UI 계약 테스트 3개, 브라우저 상태 동기화, `project_hook_check.py` 통과.

## 현재 상태 업데이트 (2026-06-11, Meta 브랜드 검수 100장)

- Meta 브랜드 광고 원본 풀 132장 중 검수 세션 100장을 구성했다.
- 공식 광고주 `direct` 88장, 협업 광고주 `partner` 12장을 분리 표기했다.
- 화장품·스킨케어 62장, 주얼리·럭셔리 38장, 총 23개 브랜드다.
- 브랜드당 최대 20장, 한 광고당 최대 5장으로 편중을 제한했다.
- 100장 모두 이미지 파일 정상, SHA 중복 0장이다.
- 세션: `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001`
- 다음 검수 핵심: 화장품 할인 문구형 프로모션 카드를 레퍼런스로 유지할지 제외할지 판단한다.

## 현재 상태 업데이트 (2026-06-10, 레퍼런스 학습 브리프 재정리)

- 범용 1,000장 수량 목표 대신 현재 H&B 나이아신아마이드 뷰티 브리프 적합성을 우선하도록 변경했다.
- 원본 2,072개 중 브리프 기본 게이트 통과 후보는 117개다.
- 최종 후보는 Pinterest/search 59개, Meta Ad Library 58개다.
- 다른 업종, 로컬/샘플/훈련 시드, 해외 Meta 광고, 저해상도, 웹 캡처, 명백한 다른 카테고리를 기본 제외한다.
- 기준 문서: `knowledge/REFERENCE_LEARNING_BRIEF.md`

## 현재 상태 업데이트 (2026-06-10, Meta 검증 브랜드 레지스트리)

- 화장품·스킨케어 20개, 주얼리·럭셔리 20개 브랜드 레지스트리를 추가했다.
- 브랜드 검색 결과 중 광고주명이 등록 별칭과 일치한 광고만 별도 저장한다.
- 콘솔 Meta 광고 수집 화면에서 업종별 브랜드 묶음을 1~30개 소량 수집할 수 있다.
- Medicube 테스트: 원본 광고 3개 → 광고주 일치 1개 → 이미지 7개.
- Cartier 테스트: 원본 광고 3개 → 광고주 일치 2개 → 허용 이미지 1개.
- 상세: `knowledge/META_BRAND_REGISTRY.md`

이 문서는 Obsidian에서 가장 먼저 보는 현재 상태판이다. 자세한 기준은 각 문서에 두고, 여기에는 자주 열어야 하는 링크와 최근 업데이트 포인트만 남긴다.

## 핵심 기준

- [[01_PROJECT_GOAL]]: 프로젝트 목표와 범위
- [[02_WORKFLOW]]: 1~7단계 실행 흐름
- [[03_BRAND_GUIDE]]: 브랜드 기준 작성/적용 원칙
- [[04_PROMPT_RULE]]: 텍스트/이미지 프롬프트 작성 기준
- [[10_PROJECT_SUMMARY]]: 전체 프로젝트 구조와 AI 구성 요약
- [[CONSOLE_UI_HANDOFF]]: 콘솔 UI 현재 상태와 다음 작업
- [[REFERENCE_LEARNING_1000]]: 1,000장 레퍼런스 학습 데이터셋과 검수 운영 기준

## 현재 상태 업데이트 (2026-06-08, Reference Learning 1000)

- Pinterest/search 18개 검색군에서 신규 이미지 484장을 수집했다.
- 레퍼런스 원본 2,072개를 인덱싱하고 정확 중복 804개, 근접 중복 49개를 검수 큐에서 제외했다.
- 최종 검수 가능한 고유 이미지 1,219장으로 1,000장 목표를 달성했다.
- 기존 검수 완료 198장, 새 검수 큐 1,021장을 50장 단위 21개 배치로 생성했다.
- 각 배치는 Pinterest, Meta, 업종 profile이 가능한 한 섞이도록 라운드로빈 구성했다.
- 콘솔 판단 훈련 상단에서 목표 달성, 중복 제거, 검수 진행률, 다음 미검수 배치를 확인할 수 있다.

## 운영 기록

- [[07_DECISIONS]]: 중요한 결정과 이유
- [[06_TROUBLESHOOTING]]: 실패 사례와 해결법
- [[05_MODEL_TEST]]: LM Studio, 이미지 모델, 워크플로 테스트
- [[08_COMFYUI_NOTES]]: ComfyUI 운영 메모

## 자동 업데이트 원칙

Codex/OpenCode 작업 후 프로젝트 기준에 영향을 주는 내용만 `knowledge/`에 반영한다.

업데이트 대상:

- 새 결정
- 새 기준
- 반복될 가능성이 있는 실패와 해결법
- 모델/ComfyUI 테스트 결과
- 워크플로 구조 변경
- 사람이 다음 작업에서 반드시 알아야 하는 맥락

업데이트하지 않는 대상:

- 단순 실행 로그
- 일회성 중간 산출물
- 임시 파일
- 후보 이미지 전체 목록
- run 폴더에 이미 보관되는 세부 결과

## 기록 위치 빠른 판단

```text
결정의 이유              -> 07_DECISIONS.md
브랜드/디자인 기준       -> 03_BRAND_GUIDE.md
프롬프트 규칙            -> 04_PROMPT_RULE.md
단계 흐름 변경           -> 02_WORKFLOW.md
에러/실패/해결법         -> 06_TROUBLESHOOTING.md
모델 테스트              -> 05_MODEL_TEST.md
ComfyUI 노드/워크플로    -> 08_COMFYUI_NOTES.md
실행 결과 원본           -> runs/
이벤트 입력 원본         -> events/
승인 자산                -> assets/
```

## 현재 상태 업데이트 (2026-05-25)

- 04_admin_selection 최소 구현 완료: 콘솔/CLI 선택값을 `04_admin_selection/selected-assets.json`과 `selection-notes.md`로 확정한다.
- `selected-assets.json` 구조 확정: `eventId`, `selectedAssets[]`, `regenerationRequests[]`, `summary`, `approvalStatus`.
- 04 완료 시 run 상태는 `qa_pending`, 현재 단계는 `06_qa_packaging`으로 넘어간다.
- 06_qa_packaging은 Figma 산출물이 없어도 `selected-assets.json` 기반의 최소 QA/패키지 매니페스트를 받을 수 있도록 연결 준비 완료.
- 최신 테스트 런에서 04 → 06 → `production-package` 생성까지 확인 완료.
- 아직 제외: ComfyUI 실생성 연결, 제품 합성, 영상 생성.

## 현재 상태 업데이트 (2026-05-25, 외부 워크플로 연결 후)

- `D:\CD\jewelry_ad_project\02_workflows`의 cosmetics/jewelry/bullion 워크플로를 ComfyUI 레지스트리에 연결.
- 03 후보 생성 시 제품 카테고리별 workflow 자동 매핑 준비 완료.
- hsgn cosmetic 최신 런에서 03→04→06→07 스모크 테스트 완료.
- 최종 패키지 화면은 파일 목록 대신 선택 후보 카드/이미지 미리보기/프롬프트 펼쳐보기를 보여주도록 개선.
- 남은 핵심: live ComfyUI 생성 안정화, 제품 합성/텍스트 오버레이 후처리, 이벤트/레퍼런스/프롬프트 품질 장기 검수.

## 현재 상태 업데이트 (2026-05-27, MVP 단계 기준 정리)

- 프로젝트 포지션을 "GPT보다 똑똑한 기획툴"이 아니라 "브랜드 이벤트 이미지 제작용 로컬 콘솔"로 재정의.
- 기준 단계명을 `01_event_brief → 02_content_planning → 03_reference_research → 04_visual_candidates → 05_admin_selection → 06_qa_packaging → 07_asset_archive`로 정리.
- `03_reference_research` stage 추가: 기본은 레퍼런스 검색 계획/요약, `REFERENCE_RESEARCH_MODE=auto_search`일 때 자동 검색/선정 실행.
- 기존 산출물 호환을 위해 물리 폴더 `03_visual_candidates`, `04_admin_selection`은 유지.
- workflow alias 추가: 기존 `03_visual_candidates`, `04_admin_selection` 명령은 각각 새 `04_visual_candidates`, `05_admin_selection`으로 매핑.

## 현재 상태 업데이트 (2026-05-27, ComfyUI live 생성 검증)

- 테스트 런 `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`에서 `instagram_cardnews_01__key_visual` 그룹 live 생성 성공.
- `qwen_candidate_2511` 후보 3장 생성/회수 완료: 1024x1024 PNG, `generation_status=generated`.
- `generation-quality.json` 추가: 후보별 live/placeholder 여부, 생성 에러, 파일 정보, ComfyUI prompt id, `reference_direction` 반영 체크를 기록한다.
- `product_input.png` fallback 오류와 과한 qwen 샘플링 기본값을 수정.
- 품질상 다음 과제는 baked-in 깨진 텍스트 억제와 bullion/gold 카테고리 고정.

## 현재 상태 업데이트 (2026-05-28, reference 품질 필터 강화)

- 금/은/투자/상담 이벤트를 `bullion_investment` profile로 감지해 레퍼런스 검색어와 선정 기준을 강화.
- 검색어가 프리미엄 금 투자/금융 상담/골드바/자산관리 캠페인 중심으로 생성되도록 수정.
- `reference-quality-filter.json` 기준 추가: `brandFit`, `eventFit`, `seriousnessFit`, `productRelevance`, `riskLevel`.
- kids/toy/kawaii/camping/theme park/picnic/wine/random package/fake text 방향은 금 투자 이벤트에서 reject 또는 shortlist 처리.
- 이미지 프롬프트에는 `blank space for Korean headline`, `no readable text`, `no fake typography`를 기본 포함.
- live 생성 전 `scripts/audit_visual_prompts.py`로 prompt audit을 생성한다.
- 테스트 런 prompt audit 결과: total 15, passed 15, warning 0, failed 0.

## 다음 할 일

1. audit 통과 프롬프트 기준으로 1~3장 live 테스트
2. 강화된 reference 기준으로 auto_search 재실행
3. 콘솔 선택 화면에 `generation-quality.json`/`reference-quality-filter.json`/`prompt-audit.json` 품질 상태 노출
4. 제품 합성/텍스트 오버레이 후처리 품질 검수
5. 이미지 평가 기준 체크리스트 정리

→ 상세: [[09_HANDOFF]]
## 현재 상태 업데이트 (2026-05-28, 브랜드/이벤트별 레퍼런스 룰 구조화)

- 이미지 생성 추가 테스트를 중단하고 기준 데이터 오염 제거를 우선순위로 전환.
- `assets/rules/brand-persona.json`, `event-rules.json`, `reference-rules.json`, `visual-avoid-rules.json`, `tone-rules.md` 생성.
- `bullion_investment` 허용 방향: premium gold investment, financial consultation, wealth management, luxury product photography, gold bar/coin/bullion, calm trust, minimal poster layout, dark navy/gold/white, blank Korean headline area.
- `bullion_investment` 금지 방향: mascot/cute/toy/kawaii/character/camping/picnic/theme park/wine bottle/package box/fake text/unreadable typography/childish 3d/game-like UI.
- 실패 live 후보 3장을 `assets/reference_training/bullion_investment/bad/`에 저장하고 bad tags를 기록.
- `03_reference_research`가 룰 파일을 읽어 `search_queries`, `qualityFilter`, `referenceDecisions`, `promptHints`, `negativePromptHints`에 반영하도록 수정.
- `03_visual_candidates`에서 bullion fallback이 `qwen_image_edit_1024.png`로 흐르지 않도록 neutral bullion 샘플 입력 이미지로 분기.

## 다음 할 일

1. `REFERENCE_RESEARCH_MODE=auto_search`로 룰 기반 selected/shortlist/rejected 분포 확인
2. good reference를 `assets/reference_training/bullion_investment/good/`에 직접 추가
3. selected reference가 안정된 뒤 04_visual_candidates placeholder audit -> 소량 live 테스트 순서로 재개

## 현재 상태 업데이트 (2026-05-30, bullion_investment good seed 및 03 품질 리포트)

- `assets/reference_training/bullion_investment/good/`에 good reference seed 10장 저장.
- `assets/reference_training/bullion_investment/good/metadata.json` 작성: filename, tags, whyGood, usefulFor 구조.
- `core/utils/reference_training.py` 추가: good/bad seed metadata를 읽고 candidate의 goodScore/badScore/scoreDelta를 계산.
- `scripts/reference_pipeline.py`가 `bullion_investment` selection gate에서 `training_alignment`를 반영.
- `03_reference_research`가 `reference-quality-report.json/md`를 생성하도록 확장.
- 검증 run: `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`.
- 결과: selected 8, rejected 5, selected bad signal 0, fallback clean true, status pass.
- bad seed 3장은 모두 rejected.

## 다음 할 일

1. good seed에 실제 캠페인/포스터형 reference를 추가해 product-only 편향 보완
2. 03 report pass 상태 유지 확인
3. 그 다음 04_visual_candidates는 placeholder/prompt audit부터 재개
4. live ComfyUI는 마지막에 1~3장만 소량 테스트

## 현재 상태 업데이트 (2026-05-30, good seed 2차 보강 완료)

- good seed를 30장으로 확장:
  - `product_reference`: 10장
  - `finance_mood_reference`: 10장
  - `poster_layout_reference`: 10장
- `metadata.json`에 `category`, `tags`, `whyGood`, `usefulFor` 구조 반영.
- `reference-quality-report`에 `goodSeedCoverage`, `selectedCategoryCoverage`, `selectedCoverage` 추가.
- selector가 good seed category를 round-robin으로 섞어 product-only 편향을 줄이도록 수정.
- 검증 결과:
  - status: pass
  - selected: 12
  - selected bad signal: 0
  - fallback clean: true
  - selected category coverage: product 4 / finance mood 4 / poster layout 4
  - selected role coverage: product_identity 8 / mood 8 / composition 12 / lighting 8 / headline_space 8
- ComfyUI live 생성은 여전히 중단 상태.

## 다음 할 일

1. `reference-quality-report` pass 상태에서 04_visual_candidates를 placeholder로만 생성
2. `prompt-audit`로 fake text/character/cute/camping 계열 차단 확인
3. 사람이 selected reference 방향을 확인한 뒤 live ComfyUI 소량 테스트
## 현재 상태 업데이트 (2026-05-30, Senior Designer Brain Wiki 1차 구축)

- 프로젝트 1차 목표를 "이미지 생성기"가 아니라 "브랜드/이벤트/레퍼런스를 판단하는 시니어 디자이너 에이전트"로 재정의.
- `design_brain_wiki/` 생성 완료.
- 생성된 축:
  - `01_design_principles`
  - `02_brand_strategy`
  - `03_reference_judgement`
  - `04_channel_usability`
  - `05_industry_playbooks`
  - `06_case_studies`
  - `07_my_taste_dataset`
  - `08_feedback_language`
  - `99_sources`
- 공식/신뢰 출처 기반으로 Design Council, IDEO, NN/g, Apple HIG, Material Design, IBM Carbon, Pentagram, COLLINS, Wolff Olins, Landor, Interbrand 기준을 AI 판단 질문/평가 항목/피드백 문장으로 변환.
- 공통 judge schema와 rubric 추가:
  - `design_brain_wiki/00_JUDGE_SCHEMA.md`
  - `design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json`
- ComfyUI는 계속 downstream 실행 단계로 유지. 지금 우선순위는 위키 기준을 Reference Judge/03_reference_research에 연결하는 것.

## 다음 작업

1. `03_reference_research`가 `design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json`과 관련 MD 기준을 읽도록 연결.
2. `reference-quality-report`에 senior designer feedback 문장과 wiki rule source를 기록.
3. 기원님이 직접 고른 good/bad/shortlist 판단을 `design_brain_wiki/07_my_taste_dataset`과 `assets/reference_training`에 누적.
4. 위키 기준 통과 후에만 04_visual_candidates placeholder/prompt audit로 이동.
## 현재 상태 업데이트 (2026-05-31, Wiki Judge 샘플 테스트 구축)

- `design_brain_wiki` 품질 검증용 샘플 테스트 세트 생성.
- 테스트 대상 3개 업종:
  - `bullion_investment`
  - `cosmetics_skincare`
  - `jewelry_luxury`
- 각 업종마다 good / bad / ambiguous 후보를 섞어 selected / shortlist / rejected 판단을 검증.
- 생성 파일:
  - `design_brain_wiki/tests/README.md`
  - `design_brain_wiki/tests/reference_judge_sample_set.json`
  - `scripts/run_reference_judge_wiki_tests.py`
  - `design_brain_wiki/tests/output/reference-judge-test-report.json`
  - `design_brain_wiki/tests/output/reference-judge-test-report.md`
- 최신 실행 결과:
  - total: 18
  - accuracy: 1.0
  - feedback depth rate: 1.0
  - status: pass

## 다음 작업

1. 이 evaluator를 `03_reference_research/reference-quality-report`에 연결.
2. 실제 collected reference 20장에 대해 wiki source, decision reason, senior designer feedback을 남기기.
3. 테스트 실패 시 전체 위키를 늘리지 말고 부족한 문서만 보강.
## 현재 상태 업데이트 (2026-05-31, Senior Designer Brain Wiki v0.2 확장)

- 정정: 현재 위키는 완성본이 아니라 `v0.1 골격 + 1차 테스트 세트`다.
- v0.2 확장 작업 추가:
  - studio case bank 50개 생성.
  - Pentagram 10 / COLLINS 10 / Wolff Olins 10 / Landor 10 / Interbrand 10.
  - 핵심 3개 업종 deep playbook 생성:
    - `bullion_investment`
    - `cosmetics_skincare`
    - `jewelry_luxury`
  - `industry_boundary_matrix` 추가.
  - 기원님 피드백 100개 누적 bank 추가.
  - good/bad/shortlist 레퍼런스 300장 성장 계획 추가.
- 현재 파일 수: `design_brain_wiki` 73개.
- 현재 case bank 수: 50개.

## 다음 작업

1. 기원님 실제 피드백 문장을 `kiwon_feedback_bank_100.md`에 채우기.
2. 실제 레퍼런스 이미지를 업종별 100장씩 good/shortlist/bad로 분류.
3. `03_reference_research`가 case bank/deep playbook을 근거로 피드백을 남기게 연결.
4. 실제 collected reference 100-300장 검증으로 v0.3 이동.
## 현재 상태 업데이트 (2026-05-31, bullion_investment 판단 훈련 세션 001)

- `bullion_investment` 실제 reference training seed 기반 30장 판단 훈련 세션 생성.
- 위치: `design_brain_wiki/training_sessions/bullion_investment/session_001/`
- 생성 파일:
  - `references/` 30장
  - `ai_judgement.json`
  - `ai_judgement.md`
  - `kiwon_review_template.md`
  - `correction_log.md`
  - `wiki_update_suggestions.md`
  - `README.md`
- 판단 방식: 로컬 Qwen/Ollama 비전 모델 호출 없음. 기존 seed metadata + design_brain_wiki 기준 기반 1차 판단.
- 결과:
  - total: 30
  - selected: 7
  - shortlist: 20
  - rejected: 3
- 주의: 초기 생성에서 `no fake text`, `no character` 태그를 위험 신호로 오독하는 문제가 있어 `scripts/create_bullion_training_session.py`에서 `no ...` 태그를 risk detection에서 제외하도록 수정 후 재생성.

## 다음 작업

1. 기원님이 `kiwon_review_template.md`에 agree/disagree/unsure와 교정 이유 입력.
2. `correction_log.md`에 과승인/과거절/추상 피드백 패턴 기록.
3. `wiki_update_suggestions.md` 기반으로 bullion playbook, feedback phrase, reference judge rubric 수정.
4. 이후 같은 방식으로 session_002를 실제 외부 수집 reference 30장으로 진행.
## 현재 상태 업데이트 (2026-05-31, 판단 훈련 UI 추가)

- 로컬 콘솔 `http://127.0.0.1:5177`에 `판단 훈련` 탭 추가.
- 목적: 기원님이 `kiwon_review_template.md`를 직접 편집하지 않고, 웹 화면에서 이미지와 AI 판단을 보며 교정 입력.
- 추가 API:
  - `GET /api/training-sessions`
  - `GET /api/training-sessions/<profile>/<session_id>`
  - `POST /api/training-sessions/<profile>/<session_id>/review`
  - `GET /training-assets/<profile>/<session_id>/<filename>`
- 저장 파일:
  - `kiwon_review_state.json`
  - `kiwon_review_summary.md`
- 화면 기능:
  - 30장 리스트 보기.
  - 이미지 미리보기.
  - AI decision/confidence/reason/usableElements/riskSignals/wikiSources 확인.
  - `맞음 / 틀림 / 애매` 선택.
  - `correctDecision`, `kiwonReason`, `ruleToUpdate` 저장.
- 검증:
  - `python -m py_compile scripts/console_server.py scripts/create_bullion_training_session.py` 통과.
  - `node --check ui/console/app.js` 통과.
  - `/api/bootstrap`에서 training session 1개 확인.
  - `session_001` 상세 30개 항목 확인.
## 현재 상태 업데이트 (2026-05-31, Reference Review Progress 정리)

- 현재 1차 목표는 이미지 생성이 아니라 `Senior Designer Brain Wiki -> Reference Judge -> Direction Director` 구축이다.
- ComfyUI live 생성은 보류 상태다. 레퍼런스 판단 기준과 기원님 교정 데이터가 쌓인 뒤 다시 연결한다.
- `design_brain_wiki/` v0.2 초안은 구축됨:
  - studio case bank 50개
  - bullion/cosmetics/jewelry deep playbook
  - reference judge rubric/schema
  - 샘플 judge test 18개 pass
- 단, 위키는 완성본이 아니라 `골격 + 1차 테스트 + v0.2 자료 확장` 상태다.
- 판단 훈련 UI가 로컬 콘솔 `http://127.0.0.1:5177`에 추가됨.
- 중요 정정:
  - `design_brain_wiki/training_sessions/bullion_investment/session_001/`은 실제 Pinterest 레퍼런스 세션이 아니다.
  - 기존 `assets/reference_training/bullion_investment/good|bad` seed 이미지를 가져온 seed test 세션이다.
  - 다음에는 seed test와 실제 Pinterest/search reference review 세션을 분리해야 한다.

## 다음 작업

1. `session_001`을 seed test로 명확히 라벨링.
2. 기존 run의 `references/candidates` 또는 새 수집 결과에서 실제 레퍼런스 30장을 가져와 `pinterest_session_001` 생성.
3. 콘솔 판단 훈련 UI에서 seed session / real reference session을 구분 표시.
4. 실제 레퍼런스 세션에서 selected / shortlist / rejected, confidence, 이유, 위험 요소, wiki 기준, seniorDesignerFeedback 생성.
5. 기원님 교정 입력을 받아 correction log와 wiki update suggestions로 누적.
## 현재 상태 업데이트 (2026-05-31, Pinterest 실제 레퍼런스 세션 분리 완료)

- 문제 정정: `session_001`은 Pinterest 세션이 아니라 seed test였으므로 `sessionType: seed_test`로 라벨링.
- `03_reference_research` auto_search를 `.venv` Python으로 재실행해 실제 Pinterest 검색 결과를 수집.
- 수집 확인:
  - 검색 URL: `https://kr.pinterest.com/search/pins/?q=...`
  - 이미지 URL: `i.pinimg.com`
  - pin URL: `https://kr.pinterest.com/pin/...`
- `scripts/reference_pipeline.py` 수정: Pinterest collector의 `metadata.jsonl`에서 `pin_url`, `image_url`, `downloaded_url`, `sha256`를 선정 후보까지 보존.
- `scripts/create_bullion_training_session.py` 수정: seed 폴더뿐 아니라 run의 실제 `reference-quality-filter.json`에서 30장 세션을 만들 수 있음.
- 생성 세션:
  - `design_brain_wiki/training_sessions/bullion_investment/pinterest_session_001/`
  - total 30
  - selected 4 / shortlist 5 / rejected 21
  - 30장 모두 `sourceIsPinterest: true`
- 콘솔 판단 훈련 UI에서 session type과 Pinterest pin 링크를 표시하도록 수정.

## 다음 작업

1. 기원님이 `bullion_investment/pinterest_session_001`을 콘솔에서 리뷰.
2. selected 4장이 너무 적은지, rejected 21장이 너무 엄격한지 교정 로그로 확인.
3. 다음 세션은 query_limit/per_query_limit을 늘리거나 직접 curated board URL을 넣어 selected 후보 품질을 높인다.
## 현재 상태 업데이트 (2026-05-31, 한국어 Pinterest 검색 + 빠른 비교 판정 UI)

- `bullion_investment` Pinterest 검색어를 한국어 우선으로 교체.
  - 예: `한국 금 투자 상담 카드뉴스 디자인`, `한국 금거래소 이벤트 배너 디자인`, `실물 금 투자 상담 인스타 카드뉴스`, `금 시세 상담 카드뉴스 디자인`.
  - 영문 쿼리는 한국 레퍼런스가 부족할 때 쓰는 보조 쿼리로 뒤쪽에만 유지.
- 새 실제 수집 세션 생성:
  - `design_brain_wiki/training_sessions/bullion_investment/pinterest_kr_session_001/`
  - total 30
  - selected 10 / shortlist 10 / rejected 10
  - 30장 모두 Pinterest/search 출처.
- 판단 훈련 UI 개선:
  - 두 장을 동시에 보여주는 `빠른 비교 판정` 패널 추가.
  - `왼쪽 좋음`, `오른쪽 좋음`, `둘 다 후보`, `둘 다 제외`, `건너뛰기`로 바로 저장 후 다음 쌍으로 이동.
  - 세션 순서는 selected/shortlist/rejected가 섞여 나오도록 조정.

## 다음 작업

1. 콘솔 `판단 훈련`에서 `bullion_investment/pinterest_kr_session_001`을 빠른 비교 방식으로 리뷰.
2. 한국어 검색이어도 외국 자료가 섞이는 항목을 `rejected`로 빠르게 교정.
3. 교정 결과에서 반복되는 부족 기준을 bullion playbook과 reference judge rubric에 반영.
## 현재 상태 업데이트 (2026-06-03, pinterest_kr_session_001 교정 요약 생성)

- `pinterest_kr_session_001` 리뷰 결과를 분석해 `correction_summary.md` 생성.
- 위치: `design_brain_wiki/training_sessions/bullion_investment/pinterest_kr_session_001/correction_summary.md`
- 핵심 결과:
  - 전체 일치율: 11/30, 36.7%.
  - AI selected 일치율: 2/10, 20.0%.
  - AI shortlist 일치율: 0/10, 0.0%.
  - AI rejected 일치율: 9/10, 90.0%.
  - 기원님 최종 판단: selected 5 / shortlist 0 / rejected 25.
- 주요 결론: AI가 한국어 검색어 적합성과 `부분 참고` 신호를 selected/shortlist 근거로 과대평가했다.

## 다음 작업

1. `bullion_investment_v0_2.md`에 한국형 금거래소/금투자 카드뉴스 selected/rejected 기준 추가.
2. `REFERENCE_JUDGE_RUBRIC.json`에 role coverage, searchQueryFit 분리, partial reference selected 금지 기준 반영.
3. feedback phrase 문장을 `부분 참고` 같은 추상 표현 대신 구체 근거형 문장으로 보강.
## 현재 상태 업데이트 (2026-06-03, 화장품 여름 H&B 세일 이벤트 브리프/기획 생성)

- 새 이벤트 생성: `events/summer-hb-beauty-sale-hsgn/`
- 이벤트명: `여름 H&B 뷰티 세일 나이아신아마이드 집중 케어`
- 방향: 올영세일 직접 모방이 아니라 한국 H&B 스토어 대형 세일 감성, 여름 스킨케어, 혜택/증정/할인 중심.
- 금지어에 `올리브영`, `올영`을 넣어 직접 브랜드 모방을 차단.
- 생성 run: `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어/`
- 01_event_brief:
  - 최초 생성 후 skincare 카테고리 리스크에서 타깃 정의가 인구통계 중심이라는 blocking 감지.
  - 타깃을 피부 고민/구매 상황/정보 탐색 채널 기준으로 보강.
  - 재생성 후 Category risk `clear`, blocking false.
  - 01 승인 완료.
- 02_content_planning:
  - deliverables 5개 생성.
  - image needs 5개.
  - quality status `approval_ready`.
  - 현재 02는 `review_pending`.

## 다음 작업

1. 02_content_planning 승인.
2. `cosmetics_skincare`용 한국어 Pinterest 검색 기준 확인/보강.
3. 03_reference_research 실행 후 화장품 판단 훈련 세션 생성.

## 현재 상태 업데이트 (2026-06-03, 화장품 Pinterest 레퍼런스 100장 수집)

- `cosmetics_skincare` 프로필을 rulebook에 추가하고 한국어/H&B/스킨케어 세일 중심 검색어를 우선 사용하도록 보강.
- `bullion_investment` 오탐을 줄이기 위해 단일 글자 `금`, `은` 및 일반 `상담` 키워드 감지를 제거하고 더 구체적인 금 투자 키워드로 교체.
- 화장품 여름 H&B 세일 run에서 02_content_planning 승인 완료.
- 03_reference_research를 `auto_search`로 재실행해 Pinterest/search 레퍼런스 100장을 선택.
- 현재 run 상태:
  - run: `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어/`
  - status: `reference_ready`
  - current_stage: `04_visual_candidates`
  - selected references: 100
- 콘솔 서버 확인: `http://127.0.0.1:5177`

## 다음 작업

1. 100장 중 실제 한국 H&B 세일 감성에 맞는지 빠른 리뷰.
2. 화장품용 판단 훈련 세션을 만들고 selected/shortlist/rejected 교정 기록 수집.
3. 통과한 레퍼런스를 기준으로 04_visual_candidates를 진행.

## 현재 상태 업데이트 (2026-06-03, 화장품 판단 훈련 세션 생성)

- 사용자가 `수집 + Qwen 검수`를 작은 값으로 한 번 실행해 최신 reference manifest가 1장으로 덮인 상태를 확인.
- 03_reference_research를 다시 100장 설정으로 복구 실행.
  - `REFERENCE_QUERY_LIMIT=8`
  - `REFERENCE_PER_QUERY_LIMIT=20`
  - `REFERENCE_SELECT_COUNT=100`
- 선택 레퍼런스 폴더 100장 복구 확인.
- 새 범용 세션 생성 스크립트 추가:
  - `scripts/create_reference_training_session.py`
- 생성 세션:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_session_001/`
  - total 30
  - selected 10 / shortlist 17 / rejected 3
  - source run: `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- 콘솔 `/api/training-sessions`에서 세션 노출 확인.
- 이후 운영 기준을 수정: 레퍼런스 검수는 계속 판단 훈련 데이터가 되어야 하므로, 화장품 세션을 30장 샘플이 아니라 전체 100장으로 재생성.
  - total 100
  - selected 41 / shortlist 56 / rejected 3

## 다음 작업

1. 콘솔 `판단 훈련`에서 `cosmetics_skincare/pinterest_session_001` 선택.
2. 빠른 비교 판정으로 100장 교정.
3. 교정 완료 후 correction_summary 생성 및 cosmetics playbook/rubric 업데이트.

## 현재 상태 업데이트 (2026-06-03, 화장품 100장 교육 테스트)

- `cosmetics_skincare/pinterest_session_001` 100장 리뷰 완료 확인.
- baseline AI 판단 일치율:
  - overall 15/100, 15.0%
  - AI selected match 9/41, 22.0%
  - AI shortlist match 5/56, 8.9%
  - AI rejected match 1/3, 33.3%
- 기원님 최종 분포:
  - selected 29
  - shortlist 12
  - rejected 59
- 생성 파일:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_session_001/correction_summary.md`
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_session_001/learned_replay_test.md`
- 반영 파일:
  - `design_brain_wiki/05_industry_playbooks/deep/cosmetics_skincare_v0_2.md`
  - `design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json`
- 결론:
  - 같은 100장에 대해서는 기원님 리뷰를 적용해 replay 100% 가능.
  - 새 이미지 generalization은 아직 미검증.
  - 메타데이터/검색어/기본 점수만으로는 기원님 판단을 잘 분리하지 못함.

## 다음 작업

1. 새 화장품 holdout reference 30-50장을 수집해 업데이트된 기준으로 재판정.
2. 빠른 비교 UI에 제외/선택 사유 태그를 추가해 더 구체적인 학습 신호 수집.
3. 가능하면 Qwen/비전 모델에서 `localHBSaleFit`, `benefitHierarchy`, `productTrust`, `foreignSaleRisk`를 이미지 기반으로 평가하게 연결.

## 현재 상태 업데이트 (2026-06-03, 검색어/메타데이터 evidence 분리)

- 화장품 Pinterest 검색어를 단순 쿼리로 교체.
  - 예: `스킨케어 이벤트 배너`, `화장품 이벤트 배너`, `뷰티 이벤트 배너`, `스킨케어 배너 디자인`, `화장품 카드뉴스 디자인`.
- `scripts/reference_pipeline.py` 수정:
  - `text_relevance_score`가 검색어, 파일명, path를 판단 evidence로 쓰지 않도록 변경.
  - Pinterest title/alt/description/grid title/SEO title 같은 source metadata만 relevance evidence로 사용.
  - `text_relevance_reason`에 `query_ignored=true` 기록.
- `scripts/create_reference_training_session.py` 수정:
  - `record_text()`에서 `query`, `source_id`, `asset_id`, `path`, `relative_path`, `text_relevance_reason` 제외.
  - title/alt/description/Qwen review/기원님 피드백만 판단 evidence로 사용.
- `pipeline/03_reference_research` 수정:
  - `기능성` 안의 단일 글자 `금` 때문에 bullion 방향이 섞이던 오탐 제거.
  - reference direction은 감지된 event profile을 기준으로 구성.
- 새 holdout run 생성:
  - `runs/2026-06-02_16-44-06_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- 새 holdout 세션 생성:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_001/`
  - total 47
  - selected 0 / shortlist 23 / rejected 24

## 다음 작업

1. `cosmetics_skincare/pinterest_holdout_001`을 판단 훈련에서 리뷰.
2. selected 0이 너무 보수적인지, shortlist/rejected 경계가 맞는지 확인.
3. 리뷰 결과로 second correction summary 생성 후 gate를 다시 보정.

## 현재 상태 업데이트 (2026-06-03, holdout 리뷰 결과와 저해상도 게이트)

- `cosmetics_skincare/pinterest_holdout_001` 리뷰 완료.
- 쿼리/path evidence 제거 후 holdout 정확도:
  - 22/47, 46.8%
  - 이전 baseline 15.0% 대비 개선.
- 기원님 최종 분포:
  - selected 14
  - shortlist 20
  - rejected 13
- AI 초안 분포:
  - selected 0
  - shortlist 23
  - rejected 24
- 결론:
  - query leakage 제거는 효과가 있음.
  - 현재 judge는 과승인에서 과보수로 이동했으므로 selected gate 재조정 필요.
- 생성 파일:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_001/correction_summary.md`
- 저해상도/화질 깨짐 이슈 확인:
  - selected reference pool에 60x60 썸네일이 여러 장 유입됨.
  - `scripts/reference_pipeline.py`에 `reference_quality_defects()` 추가.
  - width 또는 height가 300px 미만이면 `low_resolution` 사유로 자동 rejected.

## 다음 작업

1. low-resolution gate 적용 후 새 holdout 30-50장을 다시 수집.
2. selected gate를 열어 기원님 selected 14개 패턴을 반영.
3. 필요하면 판단 훈련 UI에 `화질 깨짐`, `로컬감 부족`, `제품 약함`, `혜택 구조 좋음` 같은 사유 태그 버튼 추가.

## 현재 상태 업데이트 (2026-06-03, holdout 002 재수집)

- selected gate에 화장품 이벤트 레이아웃 단서 추가:
  - `광고`, `배너`, `프로모션`, `사은품`, `이벤트 페이지`, `gift`, `banner`.
- low-resolution gate 버그 수정:
  - 기존에는 dimension을 점수용 `numeric_score()`로 읽어 563px도 100으로 잘리는 문제가 있었음.
  - `numeric_value()`를 추가해 실제 픽셀 값으로 판단하도록 수정.
- 새 holdout run:
  - `runs/2026-06-02_16-59-22_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- 03_reference_research 결과:
  - selected references: 36
  - accepted/shortlist/rejected: 48/0/12
  - selected 중 low-res: 0
  - rejected low-res: 11
- 새 판단 세션:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_002/`
  - total 36
  - AI first pass: selected 2 / shortlist 21 / rejected 13

## 다음 작업

1. 콘솔 판단 훈련에서 `cosmetics_skincare/pinterest_holdout_002` 리뷰.
2. holdout 001 정확도 46.8% 대비 개선 여부 계산.
3. selected gate가 아직 보수적인지 또는 다시 과승인되는지 확인.

## 현재 상태 업데이트 (2026-06-03, holdout 002 리뷰와 중복/홈페이지 캡쳐 보정)

- `cosmetics_skincare/pinterest_holdout_002` 리뷰 완료.
- 정확도:
  - 19/36, 52.8%
  - holdout 001의 46.8% 대비 소폭 개선.
- 기원님 최종 분포:
  - selected 2
  - shortlist 31
  - rejected 3
- AI 초안 분포:
  - selected 2
  - shortlist 21
  - rejected 13
- 주요 오차:
  - rejected -> shortlist 11건으로 여전히 너무 엄격한 제외가 많음.
  - selected -> rejected 1건으로 홈페이지 캡쳐/상단 URL 노출 같은 위험 이미지가 selected로 들어갈 수 있음.
- 보정:
  - `visual-avoid-rules.json`에 website/browser screenshot, visible URL bar, homepage capture 계열 reject/avoid/negative hint 추가.
  - `create_reference_training_session.py`에 `--exclude-profile-history` 옵션 추가. 새 holdout 생성 시 같은 업종의 이전 세션 이미지 해시를 제외할 수 있음.
- 중복 확인:
  - 동일 run의 selected 36장 안에서는 중복 해시 0건.
  - `pinterest_session_001`, `pinterest_holdout_001`, `pinterest_holdout_002`를 합치면 중복 그룹 35개, 중복 아이템 81개.
  - 원인은 같은 브리프를 1/2/3차로 반복 실행하면서 비슷한 Pinterest 쿼리를 다시 사용한 영향으로 판단.

## 다음 작업

1. 다음 holdout은 `--exclude-profile-history`로 이전 세션 중복을 제외하고 생성.
2. 홈페이지 캡쳐/상단 URL/브라우저 화면 이미지는 selected 금지 기준으로 계속 검수.
3. rejected -> shortlist 오판 11건을 기준으로 화장품 이벤트 shortlist gate를 더 완화.

## 다음 테스트 인수인계 (2026-06-03)

- 다음 단계는 `cosmetics_skincare` 새 generalization holdout 30-50장 테스트.
- 새 세션명 권장: `pinterest_holdout_003`.
- 세션 생성 시 반드시 `--exclude-profile-history`를 사용해 기존 `pinterest_session_001`, `pinterest_holdout_001`, `pinterest_holdout_002` 이미지 재등장을 막는다.
- 판단 기준:
  - hard reject: 저해상도, 홈페이지/브라우저 캡쳐, 상단 URL/주소창 노출, 완전한 업종 오류, 심한 이미지 깨짐.
  - 애매하면 rejected보다 shortlist로 둔다.
- 자세한 인수인계는 [[09_HANDOFF]] 맨 아래 `2026-06-03 Handoff - next cosmetics generalization test` 참고.
## 현재 상태 업데이트 (2026-06-03, ComfyUI 제외 파이프라인 고도화)

- 판단 훈련 UI에 사유 태그 저장을 추가했다.
  - 태그: `low_resolution`, `website_capture`, `weak_local_fit`, `weak_product`, `good_benefit_hierarchy`, `usable_selected`, `foreign_sale_risk`, `fake_text_risk`, `good_layout`, `wrong_category`.
  - 빠른 비교 판정과 상세 교정 폼 모두에서 같은 태그를 저장한다.
- 교정 저장 시 자동 산출물 추가:
  - `kiwon_review_summary.md`
  - `correction_summary.md`
  - `learned_rules.json`
- 기존 cosmetics 세션 3개에 자동 요약을 backfill했다.
- `create_reference_training_session.py`에 `--qwen-vision` 옵션을 추가했다.
  - Qwen/Ollama 비전 평가를 `qwen_review`로 붙이고, cosmetics 판단에서 `local_hb_sale_fit`, `benefit_hierarchy`, `product_trust`, `website_capture_risk`, `text_artifact_risk`를 반영한다.
- 신규 스크립트:
  - `scripts/audit_planning_quality.py`: 01/02 브리프·기획 QA.
  - `scripts/compare_reference_sessions.py`: holdout/session 정확도 비교.
  - `scripts/summarize_reference_training_session.py`: 기존 세션 correction summary/learned rules backfill.
  - `scripts/project_hook_check.py`: 문법, UI JS, 선택 run audit을 묶은 hook 점검.
- `scripts/audit_visual_prompts.py`가 `cosmetics_skincare` profile을 인식해 H&B 세일/혜택 위계/웹페이지 캡처/가짜 텍스트를 점검한다.
- 검증:
  - `python scripts\project_hook_check.py --run runs\2026-06-02_16-59-22_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어` 통과.
  - 콘솔 `http://127.0.0.1:5177` 응답 200 확인.
  - Chrome headless로 판단 훈련 화면 로드, JS 오류 0, 사유 태그 DOM 20개 확인.

## 다음 작업

1. `pinterest_holdout_003` 생성 시 `--exclude-profile-history`와 필요하면 `--qwen-vision`을 같이 사용한다.
2. holdout 003 검수 후 `scripts/compare_reference_sessions.py --profile cosmetics_skincare`로 001/002/003 정확도 비교.
3. `learned_rules.json`의 반복 규칙을 cosmetics playbook/rubric에 반영한다.

## 현재 상태 업데이트 (2026-06-03, holdout 003 생성 완료)

- 새 reference run 생성:
  - `runs/2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- 01/02 단계 생성 및 승인 완료.
- `REFERENCE_RESEARCH_MODE=auto_search`로 03_reference_research 재생성 완료.
  - selected references: 20
  - accepted/shortlist/rejected: 79/0/14
  - clear reject reason: 14
  - low-resolution reject가 계속 작동함.
- Qwen/Ollama는 `http://127.0.0.1:11434`에 연결되지 않아 이번 세션은 `--qwen-vision` 없이 생성.
- 새 판단 세션:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_003/`
  - total 31
  - AI first pass: selected 2 / shortlist 17 / rejected 12
  - reviewed 0, 전부 기원님 검수 대기.
- 검증:
  - 콘솔 `http://127.0.0.1:5177` 응답 200 확인.
  - `scripts/project_hook_check.py --run runs/2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어` 통과.
  - `scripts/compare_reference_sessions.py --profile cosmetics_skincare`에서 holdout 003이 reviewed 0으로 등록됨 확인.

## 다음 작업

1. 콘솔 판단 훈련에서 `cosmetics_skincare/pinterest_holdout_003`을 빠른 비교 + 사유 태그로 검수.
2. 검수 후 `scripts/summarize_reference_training_session.py --profile cosmetics_skincare --session-id pinterest_holdout_003` 실행.
3. `scripts/compare_reference_sessions.py --profile cosmetics_skincare`로 001/002/003 정확도 비교.
4. 반복 오차만 cosmetics playbook/rubric에 반영.

## 현재 상태 업데이트 (2026-06-03, Reference Judge gate 보정)

- `cosmetics_skincare/pinterest_holdout_003` 상태 확인:
  - `kiwon_review_state.json` 없음.
  - reviewed 0/31.
  - `summarize_reference_training_session.py` 실행 결과 summary는 생성됐지만 학습 규칙은 비어 있음.
- `compare_reference_sessions.py --profile cosmetics_skincare` 실행:
  - holdout 001: 46.8%.
  - holdout 002: 52.8%.
  - holdout 003: `pending_review`로 표시되도록 수정. 미검수 세션을 0.0% 실패로 오해하지 않게 했다.
- rejected gate 완화:
  - `scripts/create_reference_training_session.py`에서 cosmetics rejected를 hard reject 중심으로 조정.
  - hard reject: 저해상도, 웹페이지/브라우저 캡처, 업종 오류, AI artifact, Qwen hard risk.
  - weak copy space나 부족한 metadata만으로는 rejected가 아니라 shortlist.
  - 003 source pool 기준 예상 분포: selected 3 / shortlist 72 / rejected 18.
- Qwen/Ollama 상태:
  - `http://127.0.0.1:11434` 연결 실패.
  - `ollama` 명령/프로세스 확인 안 됨.
  - 따라서 `pinterest_holdout_004`는 Qwen 연결 확인 전 생성하지 않음.

## 다음 작업

1. 콘솔 판단 훈련에서 `cosmetics_skincare/pinterest_holdout_003` 검수 완료.
2. 검수 후 summary/compare 재실행.
3. Qwen/Ollama를 켠 뒤 `pinterest_holdout_004`를 `--qwen-vision`으로 생성.
4. 004에서 selected 오판, hard reject 안정성, 전체 정확도 재측정.
## 현재 상태 업데이트 (2026-06-03, QA Packaging evidence manifest)

- 06_qa_packaging이 품질 근거 파일을 `qualityArtifacts`로 자동 수집한다.
- 점검 대상: `planning-quality/planning-quality-audit.json`, `03_reference_research/reference-quality-report.json`, `03_visual_candidates/prompt-audit.json`, `03_visual_candidates/generation-quality.json`, `04_admin_selection/selected-assets.json`.
- `final-package-manifest.json`의 각 파일 레코드에 `qualityEvidence`가 추가되어 선택 후보, 선택 사유, 품질 근거 파일 상태를 함께 볼 수 있다.
- 누락/실패한 근거 파일은 QA issue로 기록되고 `suggested_fix_stage`로 되돌릴 단계를 표시한다.
- 검증: `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`에서 06 직접 실행, 07 입력 검증, `scripts/project_hook_check.py` 통과.

## 현재 상태 업데이트 (2026-06-04, QA Evidence 콘솔 노출 + 선택 후보 기준 QA)

- 06_qa_packaging의 `prompt-audit.json`, `generation-quality.json` 판정이 전체 후보 기준이 아니라 선택된 candidate를 우선으로 보도록 정밀화됐다.
- 예: 전체 generation 실패가 있어도 선택된 후보가 `generated`이면 `generation_quality`는 pass, 선택 후보가 `placeholder`이면 warning, 선택 후보가 failed/error이면 error로 QA issue를 남긴다.
- `qualityEvidence.artifacts[]`에는 각 근거 파일의 `summary`도 함께 들어간다.
- 콘솔 API `/api/runs/<run-id>`가 `qa_report`, `final_package_manifest`, `qa_packaging`을 반환한다.
- 콘솔 최종 패키지 화면에 QA Evidence 패널과 선택 후보별 evidence 칩이 추가됐다.
- 검증: 06 직접 실행 결과 `generation_quality`가 selected candidate 기준 pass로 내려가는 것 확인, 콘솔 API evidence 반환 확인, `node --check ui/console/app.js`, `python scripts/project_hook_check.py` 통과.
- 추가 검증: `?view=package&run=<run-id>` 직접 진입을 지원하고, Chrome headless DOM에서 `QA Evidence`, `quality-artifact`, `candidate-evidence`, `생성 QA`, `QA 이슈` 렌더링을 확인했다.

## 다음 작업

1. 07_asset_archive가 `qualityEvidence`를 asset record/reuse score에 반영하도록 확장한다.
2. QA warning 자산을 `limited_reuse`로 낮추는 archive 정책을 추가한다.
## 현재 상태 업데이트 (2026-06-03, Console UI 판단 훈련 개선)

- 판단 훈련 UI가 세션 선택 단계에서 reviewed/accuracy/AI 분포/final 분포를 함께 표시한다.
- 세션 상단 요약에 검토 수, 정확도, AI 분포, 최종 분포, 과선택, 과탈락, 주요 transition, reason tag 통계를 추가했다.
- reference item/빠른 비교/상세 패널에서 AI decision, 기원님 final decision, transition을 동시에 보이게 했다.
- `rejected->shortlist`, `rejected->selected`, `selected->rejected` 같은 주요 오차를 자동 하이라이트한다.
- `low_resolution`, `website_capture`, `fake_text_risk`, `wrong_category` hard reject 태그는 빨간 강조로 표시한다.
- 검수 폼에 `summary 생성`, `compare 생성` 버튼을 연결했다.
- 서버 API:
  - `POST /api/training-sessions/<profile>/<session_id>/summary`
  - `POST /api/training-sessions/<profile>/compare`
- `_comparisons` 같은 보조 폴더는 training session 목록에서 제외한다.
- 콘솔 서버는 새 코드 반영을 위해 `http://127.0.0.1:5177`로 재시작 완료.

## 다음 할 일

1. `cosmetics_skincare/pinterest_holdout_003`을 새 UI에서 검수한다.
2. 검수 완료 후 UI 버튼으로 summary/compare를 생성한다.
3. reason tag 통계와 주요 transition만 골라 cosmetics playbook/rubric에 반영한다.
## 현재 상태 업데이트 (2026-06-04, Console UX 리디자인 1차)

- 사용자가 제공한 Figma marketing canvas 스타일 가이드를 내부 운영툴에 맞게 해석했다.
- 새 페이지 설계 문서 `knowledge/CONSOLE_UX_REDESIGN.md`를 추가했다.
- 콘솔 UI의 어두운 AI 대시보드 톤을 밝은 Creative Ops 작업대 톤으로 변경했다.
- 핵심 시각 방향:
  - light canvas
  - black/white monochrome core
  - pastel color-block sections
  - pill buttons
  - hairline borders
  - minimal shadow
- Dashboard를 Workboard로 재구성했다.
  - Active runs
  - Ready for action
  - Review sessions
  - Generated images
  - Work that needs a decision
  - Queue health
  - Recent production history
- 사이드바/페이지명은 업무 언어로 정리했다.
  - Workboard
  - New Event
  - Pipeline
  - References
  - Review Training
  - Prompt Sheet
  - Image Selection
  - Package
  - Settings
- Workboard에서는 불필요한 run progress block을 숨기고, Pipeline 화면에서만 보이도록 정리했다.
- 검증:
  - `node --check ui/console/app.js` 통과.
  - `python scripts\project_hook_check.py` 통과.
  - 브라우저에서 배경 `rgb(251, 250, 247)`, pill radius `999px`, Workboard 구조, JS error 0 확인.
## 현재 상태 업데이트 (2026-06-07, Meta Ad Reference MVP 1차)

- 로컬 콘솔에 `Ad Reference` 탭 추가.
- `services/ad_reference/meta_collector.py` 추가: Meta Ad Library 검색 URL 생성, Playwright 스크롤, 개별 광고 카드 캡처 및 텍스트/CTA/링크 추출.
- `scripts/collect_meta_ads.py` 추가: `references/meta_ads/searches/<검색-id>/collected-ads.json`과 `captures/` 저장, 선택형 Qwen 태깅 지원.
- 콘솔 API 추가: `GET /api/meta-ads`, `POST /api/meta-ads/collect`, `/meta-ad-assets/...`.
- 실수집 검증: `anua skincare`, KR, 광고 카드 2개 개별 캡처/JSON 저장 성공.

## 다음 할 일

1. Ad Reference 카드의 선택/보류/제외 상태와 shortlist 저장 기능 추가.
2. shortlist를 `reference-evidence.json`으로 변환.
3. 기존 OpenCLIP ranker를 Meta 광고 캡처에 연결.
4. `reference-evidence.json`을 01_event_brief, 02_content_planning, 03_reference_research 입력에 연결.

## 현재 상태 업데이트 (2026-06-07, Meta 원본 이미지 다운로드 + run 연결)

- Meta 광고 카드 캡처 대신 카드 내부 실제 CDN 이미지를 `images/`에 다운로드하도록 변경.
- 작은 프로필 이미지/아이콘 제외, 캐러셀 광고는 광고당 최대 10장 제한.
- 콘솔 `현재 작업 레퍼런스로 연결` 옵션 추가.
- 연결 시 다운로드 이미지를 현재 run의 `references/selected/`, `reference-manifest.json`, `selected-references.json`에 등록.
- 검증: Meta 광고 2개에서 원본 이미지 20개 다운로드, 임시 run에 20개 등록, `03_reference_research`에서 selected 20개 인식.

## 현재 상태 업데이트 (2026-06-07, Meta 검색 쿼리 벤치마크)

- 화장품 이벤트 기준 Meta 검색어 8종 테스트 완료.
- 결론: Pinterest의 디자인 묘사형 검색어를 Meta에 그대로 쓰지 않는다.
- Meta 권장 구조: 경쟁 브랜드 + 상품/성분 + 카테고리/혜택.
- 기준 파일 추가:
  - `assets/rules/meta-ad-query-rules.json`
  - `knowledge/META_AD_QUERY_STRATEGY.md`
- 벤치마크 스크립트 추가: `scripts/benchmark_meta_ad_queries.py`.

## 현재 상태 업데이트 (2026-06-07, 기존 화장품 브리프 Meta 실수집)

- 대상 run: `2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`.
- 검색어: `메디큐브`, `나이아신아마이드 세럼`, `스킨케어 세일`.
- 검색어별 광고 2개 수집, 원본 이미지 각 7개, 총 21개 다운로드 및 run 연결.
- 03_reference_research 재실행 완료: 전체 reference 41, selected 41.
- 비교 시트: `references/meta_ads/meta-brief-test-contact-sheet.jpg`.
- 관찰: 실제 프로모션의 혜택 위계와 CTA 구조에는 강하지만 모델/캐릭터/텍스트 중심 소재가 섞이므로 Judge 필터가 필요하다.

## 현재 상태 업데이트 (2026-06-07, Meta 광고 성격 선택)

- Meta Ad Reference에 광고 성격 선택 추가:
  - 클린 제품 비주얼
  - 단일 광고 이미지
  - 브랜드 캠페인
  - 프로모션 구조
  - 전체 원본
- `클린 제품 비주얼`은 Qwen의 `creative_type`, `product_focus`, `text_density` 판정이 있어야 run selected로 연결된다.
- `검색어와 광고주명 일치` 옵션 추가.
- 확인: `아누아`, `라운드랩` 브랜드 검색도 공식 광고주만 나오지 않고 리셀러/제휴 광고가 섞인다.

## 현재 상태 업데이트 (2026-06-07, 클린 제품 비주얼 실검증)

- Qwen/Ollama `qwen2.5vl:7b`를 실행해 Meta 클린 제품 비주얼 필터를 실검증.
- 1차: 광고 8개/원본 13개 중 2개 연결. 제품 사진 1개는 좋았지만 뷰티 앱 화면 1개가 잘못 통과.
- 카테고리 적합도, 화면 캡처 위험, 실제 화장품 용기, 박스-only, 카드뉴스 여부 필드를 추가.
- 이미지별 Qwen 판정으로 변경해 캐러셀 내부 이미지도 각각 판단.
- 엄격 재검증: 원본 17개 중 자동 연결 0개. 나쁜 이미지 자동 연결은 막았지만 recall이 낮음.
- 결론: Qwen 단독 자동 선별은 오판이 있어 `클린 제품 비주얼` 기본 gate는 정밀도 우선으로 유지. 다음 단계는 OpenCLIP/기존 Reference Judge와 결합.

## 현재 상태 업데이트 (2026-06-07, zip UI 통합)

- `자동화 프로젝트.zip`의 LoopStudio 콘솔 UI 구조를 현재 콘솔에 적용했다.
- `ui/console/index.html`, `ui/console/styles.css`를 좌측 그룹 내비게이션, 상단 작업 바, 지표 및 run 중심 화면으로 교체했다.
- 기존 콘솔 DOM ID와 `app.js` 연결은 유지해 작업 현황, 레퍼런스 검수, 판단 훈련, 이미지 선택 등 기존 기능이 계속 동작한다.
- 데스크톱 및 모바일 폭에서 가로 넘침과 브라우저 오류가 없음을 확인했다.

## 현재 상태 업데이트 (2026-06-07, 광고 레퍼런스 카드 요약)

- 광고 레퍼런스 카드의 긴 Meta 원문을 제거하고 광고주, 3줄 요약, CTA, 이미지 수만 표시하도록 변경했다.
- 전체 수집 원문과 외부 링크는 `자세히 보기` 모달에서 확인한다.
- 동일 Library ID 광고는 화면에서 중복 제거한다.
- Meta가 CTR/ROAS/매출을 공개하지 않으므로 실제 성과 대신 집행 기간을 `신규/지속/장기 집행` 신호로 표시한다.

## 현재 상태 업데이트 (2026-06-07, 신규 zip UI 재적용)

- 오후 11:24 갱신된 `자동화 프로젝트.zip`을 `.tmp/ui-redesign-source-2324`에 새로 풀어 변경점을 반영했다.
- 새 압축본의 시스템 메뉴 `활동 로그`를 실제 run/job 데이터 기반 화면으로 추가했다.
- 오류가 기록된 run 상세에는 완료 단계 유지 안내, 관련 로그, 작업 폴더 접근을 제공하는 복구 패널을 추가했다.
- 기존 광고 레퍼런스 요약 카드와 상세 모달은 유지했다.

## 현재 상태 업데이트 (2026-06-07, Vercel 프로덕션 배포)

- Vercel 프로젝트 `loopstudio-console`을 생성하고 프로덕션 별칭 `https://loopstudio-console.vercel.app`에 배포했다.
- Vercel 배포본은 run, 이벤트, 광고 레퍼런스 등 조회 기능을 제공하는 읽기 전용 콘솔이다.
- 로컬 워크플로 실행, 폴더 열기, ComfyUI 생성 등 PC 의존 POST 작업은 로컬 콘솔 전용으로 제한한다.
# 2026-06-13 남은 작업 정리 결과

- QA warning 승인 메모 gate, 자산 0개 archive 상태, 공통 테스트 runner, 콘솔 중복 함수 정리를 완료했다.
- 공통 검증: `scripts/run_project_tests.py` 27개 통과, `scripts/project_hook_check.py` 통과.
- 제품 고정 합성은 원본 제품 보존 기능 통과, 기본 배치 품질은 보완 필요.
- 한글 오버레이는 Unicode 렌더링 통과, 대비/줄바꿈/비율 배지 문제로 납품 품질 실패.
- OpenCLIP holdout: ROC AUC 0.9328, top-10 selected precision 0.80, baseline 대비 2.02x.
- 상세: `knowledge/QUALITY_VALIDATION_2026-06-13.md`
# 2026-06-14 제품 합성/한글 오버레이 후속 개선

- 제품 고정 합성은 alpha 실제 경계 기준으로 투명 여백을 제거해 제품 존재감을 개선했다.
- 한글 오버레이는 비율 배지 기본 제거, 밝은 배경용 진한 텍스트, 굵은 제목, 넓은 제목 영역을 적용했다.
- 실제 개선 출력 검수 통과. 프로젝트 테스트 30개 및 project hook 통과.
- 상세: `knowledge/QUALITY_VALIDATION_2026-06-13.md`
# 현재 상태 업데이트 (2026-06-14, 6월 이벤트 이미지 외 E2E 품질 테스트)

- 신규 테스트 이벤트 `june-monsoon-barrier-care`를 생성하고 01~04를 실행했다.
- 최초 규칙 기반 01/02 결과는 입력 문장 반복과 범용 채널 역할에 치우쳐 C급에 가까웠으며, 기존 planning audit가 이를 잘못 `pass` 처리하는 문제를 확인했다.
- 브리프 메시지를 `공감 진입 / 핵심 제안 방향 / 제품 역할 정의 / 전환 이유 / 기획 원칙`으로 구조화했다.
- 콘텐츠 플랜에 채널별 목적과 카드뉴스 장별 `message_intent`를 추가하고, 낮은 전략 가공 수준을 planning audit가 경고하도록 개선했다.
- 브랜드 비주얼 가이드가 일반 카테고리 프로필보다 우선하도록 레퍼런스 방향을 수정했다. 테스트 이벤트 프롬프트에서 기존 오렌지 H&B 세일 방향이 제거되고 브랜드 팔레트 `#E8F0ED / #F7F4EF / #334640`가 반영됐다.
- 현재 테스트 결과: planning audit `pass`, reference quality `warning`, prompt audit 12개 모두 `warning`, 이미지 생성은 placeholder.

### 다음 작업

1. reference quality warning을 해소하도록 이벤트별 레퍼런스 유사도와 카테고리 커버리지를 개선한다.
2. prompt audit의 고정 `korean h&b sale` 요구와 `broken korean text` 누락 경고를 이벤트 유형에 맞게 조정한다.
3. 실제 등록 제품이 없는 이벤트에서 product source가 비어 있는 상태를 명확한 입력 경고로 표시한다.
# 현재 상태 업데이트 (2026-06-14, Meta 광고 기획 학습 MVP)

- 기존 Meta `collected-ads.json`의 광고 원문에서 카피 설득 구조를 추상화하는 `services/ad_strategy/library.py`를 추가했다.
- `scripts/build_meta_ad_strategy_library.py`로 46개 광고 전략 패턴을 `design_brain_wiki/ad_strategy/meta-ad-strategy-library.json`에 저장했다.
- 경쟁사 원문은 저장·재사용하지 않고 hook type, persuasion sequence, offer mechanics, CTA, tone, copy blueprint와 출처 해시만 보존한다.
- 01 브리프가 유사 광고 전략 패턴을 검색하고 현재 이벤트용 훅/캠페인 구조로 재작성한다.
- 02 콘텐츠 기획이 채널별 `copy_intent`와 `copy_blueprint`에 해당 결과를 사용한다.
- 6월 장마철 이벤트 재검증에서 기존 내부 지시문형 문구가 고객 질문형 훅과 설득 구조로 개선됐다.
- 광고 기획 학습 관련 회귀 테스트 6개 포함, 관련 테스트 총 16개 통과.

### 다음 작업

1. Meta 신규 수집 완료 후 광고 전략 라이브러리를 자동 갱신하도록 수집 job과 연결한다.
2. 사람이 좋은/나쁜 기획 패턴을 검수하는 콘솔 화면과 선택 기록을 추가한다.
3. 검수 결과를 기반으로 검색 점수와 패턴 우선순위를 학습한다.
# 현재 상태 업데이트 (2026-06-14, 실사용급 광고 기획·카피 엔진 1차 구현)

- 01단계에 `strategic-brief.json`을 추가했다.
- 02단계가 서로 다른 전략 축의 콘셉트 3안을 생성하고, 콘셉트 선택 후 요청 채널별 완성 카피 패키지를 생성한다.
- 콘셉트 승인과 최종 카피 승인 두 내부 게이트를 모두 통과해야 02단계를 승인할 수 있다.
- 검수된 전략 사례와 카피 교정 기록 스키마·저장소를 추가했다.
- 기존 Meta 전략 패턴은 `unreviewed`로 격리되며 자동 생성 검색에서 제외된다.
- 콘솔 진행 상세 화면에서 콘셉트 선택, 카피 확인, 최종 승인, 02단계 승인이 가능하다.
- 실제 검증 run `2026-06-14_12-39-06_6월-장마철-수분-장벽-리셋-위크`에서 조기 승인 차단과 전체 승인 흐름을 확인했고 planning audit는 `pass`다.
- 전체 프로젝트 테스트 69개와 project hook이 통과했다.
- 로컬 모델은 블라인드 비교 품질비 80% 이상, 치명 오류 0일 때만 `eligible`이 되는 승격 평가기를 추가했다.

### 다음 작업

1. 콘솔에서 화장품·주얼리 전략 사례를 업종별 100~150개 직접 검수한다.
2. 외부 텍스트 모델과 로컬 instruct 모델을 동일 벤치마크 입력으로 비교한다.
3. 직접 수정 카피 50쌍 이상 축적 후 QLoRA 실험 여부를 결정한다.
# 현재 상태 업데이트 (2026-06-14, 광고 기획 실전 QA 테스트)

- `june-monsoon-barrier-care`를 새 런 `2026-06-14_12-46-22_6월-장마철-수분-장벽-리셋-위크`로 01~02 재실행했다.
- 최초 실전 결과에서 조사 오류 `은(는)`, 내부 작성용 문구, 동일 문장 반복을 발견했지만 기존 점수표가 `pass`로 처리하는 문제를 확인했다.
- 생성기에서 조사 오류와 내부 작성용 문구를 제거하고, 제품명 선택과 카드뉴스 전환 문장·블로그 섹션 문장을 개선했다.
- planning QA가 어색한 한국어와 동일 문장 3회 이상 반복을 `warning`으로 감지하도록 보강했다.
- 재테스트 결과 남은 반복 카피를 `repetitive_copy`로 감지하며 planning audit도 `planning_quality_warning`을 표시한다.
- 전체 프로젝트 테스트 71개와 project hook 통과.

### 다음 작업

1. 결정론적 baseline 카피는 아직 실사용 승인 수준이 아니므로 승인하지 않고 수정 데이터로 축적한다.
2. 검수 완료 전략 사례를 업종별로 채운 뒤 외부 텍스트 모델과 동일 입력 블라인드 비교를 시작한다.
3. 주얼리 실제 이벤트 입력을 추가해 동일한 실전 QA 테스트를 진행한다.
# 현재 상태 업데이트 (2026-06-14, 화장품 광고 기획 품질 업그레이드)

- OpenAI Responses API + Structured Outputs 기반 역할 분리 생성 계층을 추가했다.
- 역할은 `strategist`, `critic`, `copywriter`이며 run별 호출 상한은 기본 8회다.
- 기본 모델은 `gpt-5.5`, 환경변수는 `OPENAI_API_KEY`, `OPENAI_PLANNING_MODEL`, `OPENAI_MAX_CALLS_PER_EVENT`, `OPENAI_REQUEST_TIMEOUT_SECONDS`다.
- 외부 모델 미연결·오류·호출 예산 초과는 `provider_unavailable` 치명 오류로 처리하며 결정론적 baseline은 승인할 수 없다.
- 기획 평균 점수 4점 미만 또는 일반 품질 경고가 남으면 02단계를 승인할 수 없다.
- 전략 검수 API/UI, 8항목 사람 채점, 직접 수정 카피 저장, 품질 대시보드 지표를 추가했다.
- 화장품 고정 평가셋 20건과 벤치마크 실행기를 추가했다.
- 현재 벤치마크: 20건 준비, 사람 검수 0건, 치명 오류 0건, 상태 `incomplete`.
- 실제 파일럿 run `2026-06-14_12-58-52_6월-장마철-수분-장벽-리셋-위크`에서 API 키 미설정 시 승인 차단을 확인했다.
- 전체 테스트 75개, project hook, 콘솔 브라우저 검증 통과.

### 다음 작업

1. `OPENAI_API_KEY`를 실행 환경에 설정하고 화장품 5건 외부 모델 파일럿을 실행한다.
2. 콘솔에서 기존 Meta 전략 46건을 검수해 최소 30건을 selected/shortlist로 분류한다.
3. 파일럿 카피를 직접 채점·수정한 뒤 20건 고정 평가셋을 완료한다.
# 현재 상태 업데이트 (2026-06-15, 광고 기획 블라인드 벤치마크 콘솔 보강)

- 화장품 고정 평가셋 20건이 결정론적 기준선과 외부 모델 결과를 분리 저장하고, 출처를 숨긴 A/B 비교를 제공하도록 확장했다.
- `scripts/benchmark_ad_planning.py --run-external --limit <N>`으로 누락된 외부 결과만 점진 생성하며, 케이스별 결과를 즉시 저장한다.
- 사람 평가에는 8개 루브릭, 승인 여부, 수정 여부, A/B 선호, 사유 태그를 저장한다.
- 외부 벤치마크도 3안 생성 후 콘솔에서 사람이 콘셉트를 선택해야 채널 카피를 생성한다.
- 종합 리포트는 외부 생성 완료 수, 치명 오류, 평균 사람 점수, 무수정 승인율, 외부 선호도, 호출 수, 평균 지연, 예상 비용을 집계한다.
- 전략 검수 콘솔은 원문 출처와 추상 전략을 나란히 확인하고 8개 루브릭을 개별 입력하도록 보강했다.
- 모의 외부 모델 기반 생성→비평→부분 재작성→재비평 회귀 테스트를 추가했다.
- 전략 원문 46건을 원본 수집 파일에서 읽어 검수 화면에 제공하되 생성 저장소에는 복사하지 않는다.
- 블라인드 선호, 최종 승인, 사람 수정 여부를 분리 입력하며 8개 루브릭이 모두 없으면 평가 저장을 거부한다.
- 전체 프로젝트 테스트 82개와 project hook이 통과했다.
- 실제 외부 파일럿 시도 결과: `OPENAI_API_KEY` 미설정으로 `provider_unavailable / missing_api_key / callsUsed 0`, 외부 생성 완료 0/20, 사람 평가 0/20.
- 현재 목표는 미달성 상태이며 외부 모델 실결과와 사람 검수가 필요하다.

### 다음 우선순위

1. OpenAI API 키가 제공된 환경에서 외부 모델 파일럿 5건을 생성한다.
2. 콘솔에서 5건 블라인드 검수 후 치명 오류와 평균 점수를 확인한다.
3. 파일럿 기준 미달 항목을 프롬프트·QA에 반영한 뒤 20건으로 확장한다.
4. Meta 전략 46건 중 최소 30건을 `selected` 또는 `shortlist`로 검수한다.
# 현재 상태 업데이트 (2026-06-15, 광고 기획 치명 오류 QA 및 목표 감사 강화)

- `services/ad_strategy/quality_gate.py`를 추가해 실제 카피 본문만 대상으로 결정론적 품질 검사를 수행한다.
- 자동 차단:
  - 입력에 없는 가격·할인·기간·효능·혜택 주장
  - 경쟁사 원문과 문장 유사도 90% 이상 표현
  - 화장품·주얼리 업종 표현 혼용
  - 요청 채널과 생성 채널 불일치
  - 콘셉트 또는 카피 비평 모델의 최종 `fail`
- 수정 전 경고:
  - 채널별 필수 필드 및 글자 수 초과
  - 결과 메타데이터 누락·잘못된 `characterCount`
  - 내부 작성용 문구
  - 약한 제품·오퍼·CTA 연결
  - 채널 간 동일 긴 문장 재사용
  - 해결되지 않은 비평 모델 `revise`
- 구조화 모델 응답은 Responses API 결과를 받은 뒤 로컬 JSON Schema 검증을 다시 통과해야 한다.
- 비평 후 재작성은 `targetIds`로 지정된 콘셉트·채널만 교체하며 나머지는 코드에서 보존한다.
- 콘셉트 비평과 카피 비평을 모두 최종 QA에 반영한다.
- 교정 기록은 이벤트·브랜드·업종·채널·모델·전략 ID·전후 카피·QA·승인 여부가 모두 있어야 저장된다.
- 승인된 교정 예시는 동일 브랜드를 우선하고 다른 브랜드 교정은 검색에서 제외한다.
- 전략 `selected` 승격은 핵심 추상 전략 완성 + 8개 루브릭 평균 4점 이상일 때만 허용한다.
- `scripts/audit_ad_planning_goal.py` 결과: 목표 핵심 조건 1/7, 준비 조건 포함 1/8, 상태 `incomplete`.
- 전체 프로젝트 테스트 97개와 project hook 통과.

### 현재 목표 증거

- 고정 평가셋: 20/20
- 외부 결과: 0/20
- 사람 평가: 0/20
- 치명 오류 평가 완료: 0/20
- selected + shortlist 전략: 0/30
- OpenAI API 키: 미설정

### 다음 우선순위

1. OpenAI API 키가 설정된 환경에서 외부 콘셉트 파일럿 5건을 생성한다.
2. 콘솔에서 전략 46건 중 우선 30건을 보정·채점해 `selected` 또는 `shortlist`로 분류한다.
3. 파일럿 콘셉트 선택 후 카피 생성·블라인드 검수·직접 수정을 진행한다.
4. 파일럿 치명 오류 0건 확인 후 평가셋 20건으로 확장한다.
## 현재 상태 업데이트 (2026-06-16, 광고 기획 리뷰 패킷 추가)

- ComfyUI/이미지 제작은 이번 진행 범위에서 제외하고, 화장품 광고 기획·카피 품질 목표의 검수 준비를 보강했다.
- `scripts/export_ad_planning_review_packet.py`를 추가해 고정 평가셋 20건, 파일럿 5건, 전략 검수 30건 목표를 한 번에 볼 수 있는 리뷰 패킷을 생성한다.
- 생성 산출물:
  - `.tmp/model-benchmarks/ad-planning-review-packet.json`
  - `.tmp/model-benchmarks/ad-planning-review-packet.md`
- 현재 패킷 상태:
  - API 키: 미설정
  - 고정 평가셋: 20/20
  - 파일럿 외부 결과: 0/5
  - 파일럿 사람 평가: 0/5
  - selected + shortlist 전략: 0/30
  - 차단 사유: `OPENAI_API_KEY_MISSING`, `STRATEGY_REVIEW_BELOW_30`, `PILOT_EXTERNAL_RESULTS_INCOMPLETE`, `PILOT_HUMAN_REVIEWS_INCOMPLETE`
- 목표 감사는 여전히 `incomplete`이며 핵심 조건 1/7만 통과한다.
- 검증: 프로젝트 테스트 100개 통과, project hook 통과, `git diff --check` 통과.

### 다음 우선순위

1. `OPENAI_API_KEY`를 설정한 환경에서 화장품 파일럿 5건 외부 모델 생성을 실행한다.
2. 콘솔 또는 리뷰 패킷을 기준으로 Meta 전략 46건 중 최소 30건을 `selected` 또는 `shortlist`로 검수한다.
3. 파일럿 5건의 콘셉트 선택, 카피 생성, 블라인드 평가, 수정 여부 기록을 완료한다.
4. 파일럿에서 치명 오류 0건과 평균 사람 평가 4.0 이상을 확인한 뒤 20건 전체로 확장한다.
## 현재 상태 업데이트 (2026-06-16, 광고 기획 리뷰 패킷 콘솔 연동)

- ComfyUI/이미지 제작 제외 범위에서 광고 기획 파일럿 리뷰 패킷을 콘솔 bootstrap/API/UI에 연결했다.
- 콘솔 bootstrap에 `planningReviewPacket`을 추가했고, 별도 조회 API `/api/planning-review-packet`을 추가했다.
- 대시보드에서 파일럿 외부 결과, 사람 평가, selected/shortlist 전략 수, blocker를 바로 확인할 수 있다.
- 전략 검수, 벤치마크 콘셉트 선택, 벤치마크 평가 저장 후에도 최신 리뷰 패킷이 UI 상태에 반영된다.
- 현재 상태는 여전히 `blocked_waiting_for_api_key`:
  - API 키 없음
  - 파일럿 외부 결과 0/5
  - 파일럿 사람 평가 0/5
  - selected + shortlist 전략 0/30
- 검증: 프로젝트 테스트 101개 통과, project hook 통과, `node --check ui\console\app.js` 통과, `git diff --check` 통과.
## 현재 상태 업데이트 (2026-06-16, 전략 검수 CSV 시트 추가)

- 광고 전략 30건 검수 병목을 줄이기 위해 `scripts/manage_ad_strategy_review_sheet.py`를 추가했다.
- 기본 export 산출물은 `.tmp/model-benchmarks/ad-strategy-review-sheet.csv`이며, 현재 30행이 생성되어 있다.
- CSV는 광고 원문 프리뷰, 추상 전략 필드, `score_` 접두사 루브릭 8개, 사유 태그, 검수 메모를 포함한다.
- Import는 기본적으로 검증만 수행하고 저장하지 않는다. 실제 반영은 `--import-sheet --apply`를 명시해야 한다.
- 빈 시트 dry-run 결과: 30행 모두 skipped, errors 0.
- 리뷰 패킷 JSON에 `reviewArtifacts.strategyReviewSheet` 경로를 추가했고, 콘솔 패널에도 전략 검수 시트 경로를 표시한다.
- 검증: 프로젝트 테스트 105개 통과, project hook 통과, `git diff --check` 통과.
## 현재 상태 업데이트 (2026-06-16, 광고 기획 파일럿 실행 오케스트레이터)

- ComfyUI/이미지 제작 제외 범위에서 광고 기획 파일럿 실행을 하나의 명령으로 묶었다.
- `scripts/run_ad_planning_pilot.py`를 추가했다.
  - API 키가 있으면 `benchmark_ad_planning.py --run-external --limit 5`에 해당하는 외부 생성 흐름을 실행한다.
  - API 키가 없으면 외부 생성은 건너뛰고 리뷰 패킷, 전략 검수 시트, 벤치마크 리포트, 목표 감사를 갱신한다.
  - 실행 요약은 `.tmp/model-benchmarks/ad-planning-pilot-run.json`에 저장한다.
- 콘솔에 `POST /api/planning-pilot/run`을 추가했고, 대시보드 리뷰 패킷 패널에 `파일럿 5건 실행/갱신` 버튼을 추가했다.
- 현재 실행 결과:
  - status: `blocked_waiting_for_api_key`
  - externalGenerationAttempted: false
  - 파일럿 외부 결과 0/5
  - 파일럿 사람 평가 0/5
  - 전략 시트 30행, dry-run errors 0
  - 목표 감사 1/7
- 검증: 프로젝트 테스트 108개 통과, project hook 통과, `git diff --check` 통과.
## 현재 상태 업데이트 (2026-06-16, 광고 전략 CSV 검수 콘솔 반영)

- ComfyUI/이미지 제작 제외 범위에서 광고 기획 품질 목표의 사람 검수 병목을 줄이기 위해 전략 검수 CSV 작업을 콘솔 job으로 연결했다.
- 콘솔 리뷰 패킷 패널에 다음 버튼을 추가했다.
  - `Strategy CSV export 30`: 검수 대상 전략 30건을 `.tmp/model-benchmarks/ad-strategy-review-sheet.csv`로 내보낸다.
  - `Strategy CSV validate`: CSV를 dry-run으로 검증하고 저장하지 않는다.
  - `Strategy CSV apply`: 검증된 CSV 내용을 실제 전략 저장소에 반영한다.
- 서버 API `POST /api/ad-strategy/review-sheet`가 `export`, `import_dry_run`, `import_apply` 모드를 처리한다.
- CSV export 결과: 30 rows, errors 0.
- CSV dry-run import 결과: 30 rows skipped, errors 0.
- 현재 목표 감사는 여전히 `incomplete`이며, API 키·사람 평가·전략 selected/shortlist 검수가 필요하다.
- 검증: 프로젝트 테스트 111개 통과, 콘솔 JS 문법 검사 통과, `git diff --check` 통과.

### 다음 우선순위

1. CSV에서 30건 전략을 실제로 채점하고 `selected` 또는 `shortlist` 비율을 채운다.
2. `Strategy CSV validate`로 errors 0을 확인한 뒤 `Strategy CSV apply`를 실행한다.
3. `OPENAI_API_KEY` 설정 후 파일럿 5건 외부 모델 생성을 실행한다.
4. 파일럿 5건 사람 평가와 수정문 저장을 완료한다.

## 현재 상태 업데이트 (2026-06-16, 벤치마크 사람 평가 CSV 추가)

- 화장품 고정 평가셋의 사람 평가를 CSV로 내보내고 검증/반영할 수 있게 했다.
- 새 도구: `scripts/manage_ad_planning_benchmark_review_sheet.py`
  - 기본 export: `.tmp/model-benchmarks/ad-planning-benchmark-review-sheet.csv`
  - 기본 import dry-run: 저장 없이 8개 루브릭, A/B 선택, 승인/수정 여부 검증
  - `--apply`: `cosmetics-human-reviews.json`에 실제 사람 평가 저장
- 파일럿 실행기 `scripts/run_ad_planning_pilot.py --limit 5`가 이제 전략 검수 CSV와 벤치마크 리뷰 CSV를 모두 생성하고 dry-run 상태를 요약한다.
- 리뷰 패킷 `reviewArtifacts`에 `benchmarkReviewSheet` 경로를 추가했다.
- 콘솔 리뷰 패킷 패널에 다음 버튼을 추가했다.
  - `Benchmark CSV export 5`
  - `Benchmark CSV validate`
  - `Benchmark CSV apply`
- 현재 실제 상태:
  - 벤치마크 리뷰 CSV 5 rows 생성
  - dry-run import: skipped 5, errors 0
  - 사람 평가 저장 0/5
  - 목표 감사는 여전히 `incomplete`
- 검증: 관련 테스트 포함 프로젝트 테스트 117개 통과.

### 다음 우선순위

1. API 키 설정 후 외부 모델 파일럿 5건을 생성한다.
2. 생성 결과가 생기면 벤치마크 CSV를 다시 export한다.
3. 사람이 A/B 선호, 8개 루브릭, 승인/수정 여부를 채운다.
4. `Benchmark CSV validate`로 errors 0 확인 후 `Benchmark CSV apply`를 실행한다.
## 현재 상태 업데이트 (2026-06-17, OpenAI API 비사용 전환 및 Codex/Claude 스킬화)

- 광고 기획 품질 업그레이드의 기본 전제를 `OpenAI API 필수`에서 `local provider + Codex/Claude 스킬 + 사람 검수`로 전환했다.
- Codex 자동 발견 스킬 `C:\Users\jinkiwon\.codex\skills\ad-planning-copy-engine`를 추가했다.
  - 3개 콘셉트 분리 규칙, 화장품 광고 QA 루브릭, JSON 출력 스키마, Claude Skill 호환 지침, 구조 검증 스크립트를 포함한다.
- `scripts/run_ad_planning_pilot.py --limit 5`는 이제 기본적으로 API 키 없이 local provider 후보 생성을 실행한다.
- 최신 파일럿 결과:
  - provider: `local`
  - candidateGenerated: 5/20
  - pilotCandidateReady: 5/5
  - human reviews: 0/5
  - selected + shortlist strategies: 0/30
  - blockers: `STRATEGY_REVIEW_BELOW_30`, `PILOT_HUMAN_REVIEWS_INCOMPLETE`
- OpenAI 관련 코드는 호환/선택 모드로 남기되 기본 실행 조건이나 목표 달성 조건으로 사용하지 않는다.

### 다음 우선순위

1. 콘솔에서 local 후보 5건의 콘셉트 3안을 보고 선택한다.
2. 선택 후 local copy package를 생성하고, 깨진 한국어/약한 연결성을 스킬 출력과 비교해 수정한다.
3. 전략 CSV 30건을 검수해 selected/shortlist 목표를 채운다.
4. Codex/Claude 스킬로 만든 고품질 JSON을 benchmark review sheet에 반영해 사람 평가 루프를 돌린다.
## 현재 상태 업데이트 (2026-06-17, local 광고 기획 한국어 템플릿 정상화)

- `services/ad_strategy/planning_engine.py`의 깨진 한국어 템플릿을 실사용 가능한 한국어 콘셉트/카피 문장으로 교체했다.
- local provider 파일럿 후보 5건을 재생성했고, 콘셉트명·타깃 인사이트·핵심 약속이 정상 한국어로 출력된다.
- QA는 깨진 문자열, 과도한 질문형, 반복 카피를 `awkward_korean`/`repetitive_copy`로 계속 잡는다.
- 최신 파일럿 상태:
  - provider: `local`
  - candidateGenerated: 5/20
  - pilotCandidateReady: 5/5
  - blockers: `STRATEGY_REVIEW_BELOW_30`, `PILOT_HUMAN_REVIEWS_INCOMPLETE`
- 검증:
  - `scripts/run_project_tests.py`: 117 passed
  - `scripts/project_hook_check.py`: pass
  - `scripts/audit_ad_planning_goal.py`: expected `incomplete`

### 다음 우선순위

1. 파일럿 5건에서 사람이 콘셉트 1안을 선택한다.
2. 선택된 콘셉트로 local copy package를 생성하고 사람 평가/수정문을 저장한다.
3. 전략 CSV 30건 selected/shortlist 검수를 완료한다.
4. Codex/Claude 스킬 산출 JSON과 local deterministic 결과를 비교해 낮은 점수 패턴을 교정 데이터로 축적한다.

## 현재 상태 업데이트 (2026-06-17, 광고 기획 콘솔 검수 데스크 전면 개편)

- 메인 대시보드를 `광고 기획 검수 데스크` 중심으로 재구성했다.
- 사용자 화면에서 A/B 블라인드 비교, raw JSON 카피 출력, `Provider/Blockers/meta_strategy_*` 같은 개발자용 상태값을 제거했다.
- 파일럿 5건은 이벤트별 카드로 표시하며, 콘셉트 3안과 채널별 카피 패키지를 사람이 읽는 기획안 형태로 보여준다.
- 전략 검수와 CSV 작업은 `고급 정보 / 데이터 검수` 접힘 영역으로 이동했다.
- 단일 검수 저장을 위해 `blindPreferred`는 선택 입력으로 완화했다.
- 브라우저 검증 결과:
  - planning case card 5개
  - concept card 15개
  - copy card 12개
  - 금지 문구 0개
  - A/B 노출 0개
  - JSON 노출 0개
  - dashboard overflow 0개

### 다음 우선순위

1. 파일럿 5건에서 콘셉트 선택과 카피 검수 저장을 실제로 진행한다.
2. 낮은 점수/수정 요청 메모를 correction record로 축적한다.
3. 전략 CSV 30건 selected/shortlist 검수를 완료한다.
# 현재 상태 업데이트 (2026-06-18, 마케팅 신호 추천 검수 큐 추가)

- 마케팅 신호 검수 큐에 `reviewRecommendation`을 추가했다.
- 추천 점수는 강도, 최신성, 신뢰도, 근거 유형, 콘셉트/카피 연결 가능성을 합산한다.
- 콘솔 카드에는 `우선 검토 / 검토 후보 / 보조 후보` 라벨과 10점 만점 점수, 추천 이유를 표시한다.
- 미검수 큐는 추천 점수가 높은 신호부터 정렬된다.
- 현재 첫 추천 후보는 `우선 검토 10/10`이며 추천 이유는 `타깃 감정/저항을 바로 설명할 수 있음`이다.
- Playwright 콘솔 감사에 추천 이유 박스 노출 검사를 추가했고 현재 `pass`.

### 다음 우선순위

1. 마케팅 신호 검수 화면에서 `우선 검토` 카드부터 최소 3개를 `선택`한다.
2. 선택 후 `InsightBrief 만들기`를 실행한다.
3. ready InsightBrief로 파일럿 5건을 다시 생성한다.

# 현재 상태 업데이트 (2026-06-18, 마케팅 신호 수집 job 콘솔 연결)

- 마케팅 신호 검수 화면에 수집/CSV 작업 버튼을 추가했다.
  - `랜덤 신호 50개 더 모으기`
  - `검수 CSV 내보내기`
  - `CSV 검증`
  - `CSV 반영`
- 서버 API `POST /api/marketing-signals/job`을 추가했다.
  - `random_seed`: 랜덤 가설 신호 50개 추가 수집 후 CSV export
  - `export`: 검수 CSV export
  - `import_dry_run`: CSV 검증
  - `import_apply`: CSV 검증 후 저장소 반영
- 실제 랜덤 신호를 50개 추가 수집해 현재 `MarketingSignal`은 100개가 되었다.
- 최신 검수 CSV는 `.tmp/marketing-signals/marketing-signal-review-sheet.csv`이며 100행이다.
- 현재 selected 신호는 아직 0개이므로 `InsightBrief`는 계속 `needs_signal_review` 상태다.
- Playwright 콘솔 감사에 `[data-signal-job]` 버튼 4개 이상 노출 검사를 추가했고 현재 `pass`.

### 다음 우선순위

1. 100개 신호 중 최소 3개 이상을 `선택`으로 검수한다.
2. 선택 신호 3개 이상이 되면 `InsightBrief 만들기`를 실행한다.
3. ready InsightBrief로 파일럿 5건의 콘셉트/카피를 다시 생성해 근거 품질 변화를 본다.

# 현재 상태 업데이트 (2026-06-18, Playwright 콘솔 UI 감사 추가)

- 콘솔 UI가 다시 개발자 상태판처럼 깨지는 문제를 막기 위해 Playwright 기반 화면 감사를 추가했다.
- 신규 감사 스크립트: `scripts/audit_console_ui_playwright.py`.
- 검사 기준은 1280px 화면에서 개발자 용어 노출, raw JSON 노출, A/B 비교 잔존, 깨진 한글, 가로 넘침을 자동 확인하는 것이다.
- 현재 실행 결과: `CONSOLE_UI_AUDIT pass`.
- 최신 리포트: `.tmp/console-ui-audit/latest-console-ui-playwright.json`, `.tmp/console-ui-audit/latest-console-ui-playwright.md`.
- 일반 unittest에는 판정 로직만 포함하고, 실제 브라우저 감사는 콘솔 서버가 켜진 상태에서 필요할 때 실행한다.

### 다음 우선순위

1. 마케팅 신호 50개를 실제로 `선택 / 보류 / 거절` 검수한다.
2. selected 신호 3개 이상을 만든 뒤 `InsightBrief 만들기`를 실행한다.
3. ready `InsightBrief`로 파일럿 5건을 재생성해 문구 근거가 설득력 있게 붙는지 본다.
4. UI 수정 후에는 `python scripts/audit_console_ui_playwright.py --url http://127.0.0.1:5177/`를 돌려 회귀를 막는다.
## 2026-06-20 — HSGN 근거 기반 기획 품질 1차 업그레이드

- HSGN 여름 톤 케어 이벤트용 `MarketingSignal` 13개를 `selected` 상태로 추가했다.
- `design_brain_wiki/marketing_signals/insight-brief.json`은 `eventId=hsgn-summer-tone-care-2026`, `status=ready`, `selectedSignalCount=13` 상태다.
- `services/ad_strategy/planning_engine.py`를 깨진 한국어 템플릿 없는 근거 기반 콘셉트/카피 엔진으로 교체했다.
- `services/ad_strategy/quality_gate.py`를 정상 한국어 QA 게이트로 교체해 허위 혜택, 업종 혼용, 채널 필드, 반복 카피, 글자 수를 안정적으로 검사한다.
- HSGN run `runs/2026-06-20_01-26-50_hsgn-여름-톤-케어-집중-이벤트`의 02단계를 재생성하고 `concept_02`를 선택했다.
- 현재 HSGN 02 scorecard: `pass`, critical error 0, averageScore 4.0, issues 0.
- 최종 카피 본문에서 `카피는`, `입력된 성분명`, `만들지 않는다`, `근거 신호`, `인스타그램 피드는` 같은 내부 작성용 문구 노출 0건을 확인했다.
- 검증: `.venv\Scripts\python.exe -m unittest tests.test_ad_planning_engine tests.test_ad_planning_upgrade tests.test_ad_planning_quality_gate tests.test_marketing_insight_brief` 37개 통과.

### 다음 작업

1. HSGN 02 카피를 사람이 최종 검수하고 `copy-review.json` 승인 또는 수정 기록을 저장한다.
2. Playwright는 현재 콘솔 UI 감사에는 통과했지만, 외부 트렌드/브랜드/상품 신호 수집 파이프라인은 별도 구현이 필요하다.
3. HSGN 외 화장품 파일럿 5건에도 이벤트별 `InsightBrief`를 분리 적용해 평균 4.0/5, 치명 오류 0건을 유지하는지 확인한다.
## 2026-06-20 — 공개 웹 관찰 기반 MarketingSignal 수집기 1차 구현

- `services/marketing_intelligence/public_signal_collector.py`를 추가했다.
- 공개 페이지/트렌드/날씨/경쟁 광고 관찰을 원문 복사용 데이터가 아니라 `normalizedInsight` 중심의 `MarketingSignal`로 변환한다.
- `scripts/collect_marketing_signals.py`에 `--public-snapshot`, `--capture-url`, `--source-kind`, `--auto-select-public` 옵션을 추가했다.
- `scripts/console_server.py`의 마케팅 신호 job에 `public_snapshot` 모드를 추가했다.
- HSGN 공개 관찰 샘플 `assets/rules/hsgn-public-marketing-snapshot.json`을 추가하고 실제 저장소에 5개 신호를 수집했다.
- 현재 공개 관찰 신호 5개는 모두 `unreviewed`이며, 사람이 selected로 승격하기 전까지 생성 근거로 사용되지 않는다.
- HSGN 현재 02 scorecard는 계속 `pass`, criticalErrorCount 0, issues 0 상태다.
- 검증: `.venv\Scripts\python.exe -m unittest tests.test_ad_planning_engine tests.test_ad_planning_upgrade tests.test_ad_planning_quality_gate tests.test_public_marketing_signal_collector tests.test_marketing_intelligence_console tests.test_marketing_intelligence_signals tests.test_marketing_insight_brief` 52개 통과.

### 다음 작업

1. 콘솔에서 공개 관찰 신호 5개를 selected/shortlist/rejected로 검수한다.
2. selected 공개 신호를 포함해 HSGN InsightBrief를 재생성하고 카피 품질 변화를 비교한다.
3. Playwright `--capture-url`을 실제 공개 브랜드/상품/트렌드 페이지에 적용해 snapshot을 자동 생성하는 job UI를 붙인다.
# 현재 상태 업데이트 (2026-06-22, 공유 repo 수집기 범위 확장)

- `pinterest-playwright-collector/` 공유 repo에 원래 프로젝트의 추가 Pinterest/Playwright/Meta 수집 도구를 확장 반영했다.
  - 추가 커밋: `cd72716 Add Meta and expanded Playwright collectors`
  - GitHub push 완료: `https://github.com/kiwonjin-hash/kiwon.git`
- 추가 포함:
  - Pinterest 검색 학습 수집: `scripts/collect_reference_learning_1000.py`
  - Meta Ad Library Playwright 수집: `scripts/collect_meta_ads.py`, `services/ad_reference/meta_collector.py`
  - Meta query benchmark, brand registry batch 수집, source-mix 수집 보조
  - `assets/rules/meta-brand-registry.json`
  - `meta_collect.bat`, `meta_brand_registry_collect.bat`
  - `docs/INVENTORY.md`에 포함/제외 범위 정리
- 제외 범위:
  - 메인 이벤트 workflow, 콘솔 UI Playwright 감사, ComfyUI workflow, 원 프로젝트 wiki/run 구조에 묶인 학습 세션 생성 스크립트.
- 검증:
  - 공유 repo의 Pinterest/Meta 관련 Python 수집 스크립트 전체 `py_compile` 통과.

# 현재 상태 업데이트 (2026-06-22, Pinterest Playwright 수집기 분리)

- Pinterest/Playwright 기반 이미지 수집기를 공유용 독립 저장소로 추출했다.
  - 위치: `pinterest-playwright-collector/`
  - 별도 git 저장소 초기화 완료.
  - 초기 커밋: `f8eb967 Initial Pinterest Playwright collector`
- 포함 범위:
  - Playwright 기반 Pinterest board/search/pin 이미지 수집기
  - Pinterest 로그인 세션 저장/확인 스크립트
  - Chrome remote debugging 기반 세션 저장 배치
  - gallery-dl original download 보조 모드
  - Windows 설치/실행 배치와 README
- 메인 이벤트 자동화 파이프라인 의존성은 제거하고, `reference_collect.bat` 중심의 standalone 실행 흐름으로 정리했다.
- 검증:
  - `python -m py_compile scripts\collect_references.py scripts\collect_references_easy.py scripts\pinterest_login.py scripts\save_pinterest_session_from_chrome.py scripts\check_pinterest_session.py scripts\collect_pinterest_originals.py services\reference_collector\pinterest.py` 통과.
## 2026-07-01 - 제품 공식 근거 입력 경로 구현

- 화장품 파일럿 5건의 공개 근거 후보 15건은 수집 완료됐지만 아직 모두 `unreviewed`다.
- 기존 제품 라이브러리의 `hydrating_serum`, `hsgn_niacinamide`는 `launch-serum` 탄력 세럼의 공식 근거가 아니므로 재사용하지 않았다.
- 콘솔의 이벤트 근거 검수 화면에 `공식 제품 근거 추가` 폼을 구현했다.
  - 브랜드 공식 페이지: HTTPS URL 필수
  - 내부 자료: 확인 가능한 문서 번호 필수
  - 확인된 사실, 기획 해석, 대상 고객, 주장 제한, 확인 방법 필수
  - 확인된 사실에 없는 수치를 기획 해석에 추가하면 저장 차단
- 저장된 제품 근거는 `proof` 후보이자 `unreviewed`로만 들어가며, 사람 검수 전에는 InsightBrief와 카피 생성 근거로 쓰이지 않는다.
- 전체 자동 테스트 206개 및 JavaScript 문법 검사 통과.
- 라이브 콘솔 UI 감사 통과. 탄력 세럼 이벤트에서 제품 근거 폼 표시, 빈 입력 한국어 차단, 1280px 가로 넘침 0건, 가짜 제품 근거 저장 0건을 확인했다.
- 콘솔 서버: `http://127.0.0.1:5177/`, 현재 재시작 PID 32696.

### 현재 실제 막힘

1. 대표 5건의 근거 후보 15건을 사람이 선택/보류/거절해야 한다.
2. `신제품 탄력 세럼 출시`는 실제 공식 성분·사용법·시험 자료 또는 검증된 내부 문서가 아직 없어 제품 근거가 비어 있다.
3. 위 두 항목이 끝나기 전에는 전용 InsightBrief와 최종 카피 재생성을 진행하지 않는다.

### 다음 작업

1. 콘솔에서 각 이벤트의 `수집·검수 시작`을 눌러 후보를 읽고 `후보 3개 검수안 확인`을 확정한다.
2. `신제품 탄력 세럼 출시`에서 실제 공식 제품 자료를 입력하고 생성된 제품 근거 후보를 검수한다.
3. 5건 모두 근거 준비 완료가 되면 이벤트별 InsightBrief를 만들고 카피를 재생성한다.
4. 5건 품질 감사 후 목표 통과 시 20건으로 확장한다.
## 2026-07-02 - 장마철 이벤트 근거→콘셉트 연결 완료

- 대표 5건 중 `장마철 수분 장벽 리셋`의 공개 근거 3건이 사람 선택 완료 상태임을 확인했다.
- 이벤트 전용 InsightBrief를 생성했다.
  - 상태: `ready`
  - 선택 신호: 3개
  - 근거 역할: 고객 문제 / 시기 명분 / 시장 흐름
  - 다른 이벤트 신호 혼입: 0건
- InsightBrief에 `evidenceDetails`를 추가해 근거 유형, 타깃 상황, 추상 인사이트, 출처, 확인일, 주장 제한을 구조적으로 전달한다.
- 장마철 콘셉트 3안을 새 근거로 재생성했다.
  - 불편의 원인을 다시 보는 루틴
  - 복잡함을 덜어낸 선택 기준
  - 지금 계절에 맞춘 리셋 타이밍
- 3안이 추천안으로 표시되지만 자동 선택하지 않는다. 사람 선택 전 카피 생성은 계속 차단된다.
- 기존 `connection_test` 평가는 최종 사람 평가에서 제외했다. 현재 공식 사람 평가 수는 0건이다.
- 근거 검수가 완료되면 InsightBrief와 콘셉트 3안을 자동 갱신한다.
- 근거가 다시 부족해지면 기존 콘셉트 선택과 카피를 즉시 무효화한다.
- 메인 화면 행동은 `기획 검수 시작`, `기획안 최신화` 두 개로 단순화했다.
- 라이브 UI 감사 통과: 추천 이유·주의사항·출처 표시, 선택 버튼 3개, 카피 카드 0개, 1280px 가로 넘침 0건.
- 콘솔 서버: `http://127.0.0.1:5177/`, PID 10652.

### 현재 다음 작업

1. 장마철 이벤트의 추천 3안을 포함해 콘셉트 하나를 사람이 선택한다.
2. 나머지 대표 4건의 근거 후보 12건을 사람 검수한다.
3. 탄력 세럼은 공식 제품 proof를 추가 검수해야 준비 완료가 된다.
4. 선택 후 생성되는 채널 카피를 사람이 채점·수정·승인한다.

## 2026-07-02 - 최신 인수인계 체크포인트

- 활성 목표는 계속 진행 중이다.
  - 화장품 고정 평가 20건
  - 치명 오류 0건
  - 사람 평가 평균 4.0/5 이상
  - 무수정 승인율 50% 이상
- 외부 OpenAI API는 사용하지 않는다. Codex의
  `ad-planning-copy-engine` 스킬과 로컬 결정론적 엔진을 사용한다.
- 근거 후보 카드에 추천 판정, 추천 이유, 자료 한계를 추가했다.
  - 오래된 연구, 해외 조사, 단면 연구, 전문가 인터뷰, 공개 카테고리
    자료의 한계를 구분한다.
  - 빠른 검수안은 필수 근거 역할별 최고 점수만 `selected`로 제안하고
    중복 역할 후보는 `shortlist`로 제안한다.
  - 추천은 자동 저장 또는 자동 콘셉트 선택이 아니다.
- 실제 근거 큐:
  - 대표 5건 중 준비 완료 `1/5`
  - 장마철 `selected 3`, 전용 InsightBrief와 콘셉트 3안 생성 완료
  - 프로모션·교육은 후보 각 3개 검수 대기
  - 브랜딩은 후보 4개 검수 대기
  - 탄력 세럼은 후보 3개와 별개로 제품 공식 proof가 부족
- 전체 저장 신호는 `134개`다. 저장소 전체의 selected 수에는 과거 HSGN
  데이터가 섞여 있으므로 파일럿 진행률로 해석하지 않는다.
- 최종 사람 카피 평가는 `0건`이다. 과거 `connection_test` 기록은 공식
  평가에서 제외한다.

### 다음 작업 전 필수 수정

근거 계획의 대표 5건과 일부 파일럿 스크립트가 고르는 첫 5건이 다르다.

- 올바른 대표 5건:
  `season-monsoon-barrier`, `promotion-gift`, `launch-serum`,
  `education-barrier`, `branding-minimal`
- 현재 데이터셋 첫 5건:
  장마철, 여름 브라이트닝, 겨울 건조, 봄 민감, 증정 프로모션

`audit_cosmetics_pilot_goal.py`, `export_ad_planning_review_packet.py`,
`run_ad_planning_pilot.py`가 모두 근거 계획의 priority 1 목록을 공통으로
사용하도록 먼저 통일한다. 이 수정 전에는 5건 목표 감사 결과를 최종
판정으로 사용하지 않는다.

### 다음 실행 순서

1. 공통 대표 파일럿 선택기를 구현하고 관련 테스트를 추가한다.
2. 전체 테스트와 Playwright 콘솔 감사를 다시 실행한다.
3. 콘솔 서버를 최신 코드로 재시작한다.
4. 장마철 추천 콘셉트는 사람이 직접 선택한다.
5. 나머지 대표 4건의 근거를 사람이 확정한다.
6. 대표 5건의 카피를 생성·수정·승인한 뒤 목표 감사를 실행한다.

## 2026-07-05 - 카피 생성·비평 품질 보완 완료

- 위의 공통 대표 파일럿 선택기와 이벤트 전용 근거 게이트는 구현 완료됐다.
- 로컬 카피 생성은 Python 딕셔너리 길이가 아니라 화면에 보이는 실제 문장
  길이를 `characterCount`로 기록한다.
- 카드뉴스 전환 문구는 다음 슬라이드 제목을 사용해 같은 문장을 반복하지
  않는다.
- 제품명이 모음으로 끝나도 `토너를`, `토너와`, `토너는`처럼 자연스러운
  조사를 사용한다.
- 실제 생성 경로와 벤치마크 경로가 동일한 근거 기반 로컬 비평기를 사용한다.
- 약한 제품 연결, 근거 누락, 채널 재사용, 반복 문장, 조사 오류, 과도한
  질문형은 관련 루브릭을 낮추고 `revise`로 차단한다.
- 전체 unittest `231개`와 라이브 Playwright 콘솔 감사가 통과했다.
- 서버는 `http://127.0.0.1:5177/`에서 최신 코드로 실행 중이다.

### 현재 사람 작업

1. `장마철 수분 장벽 리셋`의 콘셉트 3안 중 하나를 선택한다.
2. 생성된 채널별 카피를 수정 또는 승인한다.
3. 프로모션·신제품·교육·브랜딩 대표 4건의 이벤트 전용 근거를 검수한다.
4. 대표 5건의 사람 평가가 끝난 뒤 목표 감사를 다시 실행한다.

## 2026-07-12 - 광고 기획 통합 검증 게이트 추가

- 검수 준비용 통합 스키마를 추가했다.
  - `core/schemas/ad-planning-output.schema.json`
- 누락되어 있던 검증 명령을 구현했다.
  - `python scripts/validate_ad_planning_output.py <json-file>`
  - `python scripts/validate_ad_planning_output.py --run-dir runs/<run-id>`
- 검증 항목:
  - `needs_input → 콘셉트 선택 → 카피 검수 → 승인` 상태 전이
  - 콘셉트 정확히 3안과 쌍별 전략 차이 2개 이상
  - 사람 선택 ID와 카피 패키지 선택 ID 일치
  - 요청하지 않은 채널 및 채널 중복 차단
  - 화면 표시 문자열 기준 글자 수 일치
  - 깨진 한글·JSON·HTML·프로그래밍 구조 차단
  - 승인 시 경고 0, 치명 오류 0, 평균 4.0 이상, 사람 승인 기록
- `02_content_planning` 단계 승인은 위 통합 검증을 추가로 통과해야 한다.
- 전체 unittest `237개`, Playwright 라이브 UI 감사 `pass`.
- 현재 실제 목표 감사는 변함없이 `candidate 1/5`, `copy 0/5`, 사람 평가
  `0/5`, 치명 오류 `0`이다.

### 현재 다음 작업

1. 장마철 콘셉트 1개를 사람이 선택한다.
2. 생성 카피를 수정 또는 승인한다.
3. 나머지 4건의 이벤트 전용 근거를 사람이 검수한다.

## 2026-07-12 - 메인 화면 영어 운영 문구 제거

- 실제 인앱 브라우저에서 상단 파이프라인과 최근 작업을 다시 확인했다.
- 광고 기획 카드 밖에 남아 있던 `Brief`, `Plan`, `References`,
  `Candidates`, `Selection`, `QA`, `Archive`를 한국어 단계명으로 교체했다.
- `Continue Plan`, `Generate and select image candidates`,
  `Review selected references`, `Build output package` 같은 다음 작업 문구도
  사람이 바로 이해할 수 있는 한국어 행동 문장으로 바꿨다.
- 사용자 화면의 `QA Evidence`, `qa-checklist.json` 표기도 각각 품질 검사
  근거와 품질 검사 항목으로 정리했다.
- Playwright 감사가 메인 화면의 영어 운영 문구를 별도 실패 조건으로
  검사한다.
- 전체 unittest `238개`, 라이브 Playwright 감사 `pass`.
- 실제 브라우저 재확인 결과 금지 영어 운영 문구 `0건`.

## 2026-07-12 - 메인 검수 행동을 한 건으로 축소

- 광고 기획 검수 데스크 상단에 `지금 할 일 1개` 카드를 추가했다.
- 현재 우선 행동은 `장마철 수분 장벽 리셋 콘셉트 선택`이다.
- 버튼 `콘셉트 3안 보러 가기`가 바로 이벤트 기획 검수 카드로 이동한다.
- 상태가 바뀌면 같은 자리가 자동으로 다음 행동을 표시한다.
  - 콘셉트 선택
  - 최종 채널 문구 검수
  - 이벤트 근거 검수
  - 기획안 품질 보완
- 전체 진행률, 파일럿 목표 감사, 근거 연결 감사, 교정 학습 감사는
  `전체 진행률과 목표·학습 진단 보기` 아래 기본 접힘 상태로 이동했다.
- Playwright 감사는 숨겨진 복제 패널을 제외하고 실제 보이는 핵심 행동이
  정확히 1개인지 검사한다.
- 전체 unittest `239개`, 라이브 Playwright 감사 `pass`.
> 2026-07-25 journey verification: a real console run (`2026-07-25_07-14-17_production-branding-minimal`) was clicked through references → prompts → image candidates → image selection → QA package. The flow now resumes at the next unfinished decision after refresh. Reference selection automatically approves the non-human 03 gate, and the final QA screen exposes one `QA 확인 후 패키지 만들기` action that records the QA approval and creates the production package.
>
> Known test-data note: this verification run used placeholder image candidates because ComfyUI was offline. The final QA stayed `warn` (four evidence notices), but it can be explicitly approved and packaged; it is not presented as a clean image-production pass.

## 2026-07-26 ComfyUI live connection check

- The console's visual-candidate pipeline is verified against the canonical workflow root `D:\CD\jewelry_ad_project\02_workflows\api\`.
- `jewelry/jewelry_product_hero_v2` resolves to `jewelry_product_hero_v2.api.json`; product upload, queue submission, output download, and candidate-manifest write-back use this production path.
- A detached live regeneration is running for `2026-06-20_15-11-07_여름-다이아-하이주얼리-캠페인`, group `instagram_cardnews_01__key_visual`. Wait for the three outputs and manifest update before treating it as a live-image pass.

## 2026-07-26 Brand-aware ComfyUI routing

- Product category now determines the ComfyUI brand route: jewelry uses its canonical API keeper graph, while cosmetics materializes its approved product-hero canvas workflow into a queueable API graph at runtime.
- This preserves jewelry's high-jewelry identity rules and cosmetics' label-preservation/clean-skincare rules before campaign-specific direction is appended.

## 2026-07-26 HSGN innovation launch live test

- New test event `hsgn-innovation-niacinamide-launch` completed the actual journey from brief through reference selection and candidate creation.
- Test selection uses the evidence-backed “product name and concentration as a choice criterion” concept; no efficacy, clinical, discount, or gift claim was added.
- Its Instagram card-news key-visual group is queued for live ComfyUI generation with the cosmetics-specific product-hero workflow and the original hsgn packshot.
