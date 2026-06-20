# 현재 구현 상태 & 인수인계

## 2026-06-20 Handoff - Claude Code 전환 + 취향 모델(이미지 학습) 루프 구축

### 환경/전환

- 작업 도구를 Codex → Claude Code로 전환. AGENTS.md와 CLAUDE.md는 내용 동일(수동 동기화).
- 점검·실행은 반드시 메인 폴더(`자동화 프로젝트`) + 메인 venv(`.venv\Scripts\python.exe`)에서. worktree는 코드만 있고 runs/venv/이미지가 없어 깨진 것처럼 보인다.
- 6/13 이후 미커밋이던 작업 176개(수정 108 + 신규 68)를 `checkpoint/wip-2026-06-20` 브랜치로 체크포인트 커밋(유실 위험 제거).

### 코드 점검/수정

- pipeline-health `looks_mojibake()` 오탐 수정: 정상 한글 물음표(≥10개)를 mojibake로 판정하던 버그 → U+FFFD 치환문자 카운트로 교체. health fail→warning.
- 전체 테스트 24개 → **153개**로 정비(메인 기준). 러너 모듈 정합성 확인. 신기능(ad_planning/marketing_intelligence)은 콘솔 API로 연결됨(파이프라인 단계 아닌 검수 데스크, 설계 의도).

### 레퍼런스 판단 정확도 (측정·진단)

- 신규 `scripts/replay_reference_accuracy.py`로 재현 가능 측정. 베이스라인 244건: 3-class 43.4% / 2-class 62.7%(learned rules). learned rules가 정확도 올림(+13%p) 확인.
- **Qwen 비전은 반증**: pure도 하이브리드도 메타데이터를 못 넘음(과제외로 역전). 비전 통합 보류. 상세 [[REFERENCE_ACCURACY_2026-06-20]].

### 취향 모델 = 이미지 학습 (기원님 핵심 목적, 본 세션의 메인)

- 목적: 경쟁 마케팅 이미지를 학습해 좋은 마케팅/브랜딩을 체화. 방식 = OpenCLIP 임베딩 + 분류기(linear probe).
- 파이프라인 신규:
  - `services/visual_reference/taste_labels.py` — 검수 세션 selected/rejected → good/bad 라벨 수집.
  - `scripts/train_taste_model.py` — 여러 세션 통합 학습 + 교차검증 AUC + 모델 저장.
  - `scripts/rank_images_by_taste.py` — 저장 모델로 신규 이미지 취향 점수 순위.
  - `scripts/ingest_image_folder_session.py` — 임의 폴더(Meta/확장)를 콘솔 라벨 세션으로 변환.
  - `scripts/pretag_session_with_taste.py` — 세션에 AI 1차 추천(점수→decision) 부여.
- 검증: 단일 Meta 세션 ROC AUC **0.93**, 통합 7세션 240장 **0.82**(top-10 lift 2.18x). 텍스트/Qwen 판단(50%대)보다 월등. 상세 [[TASTE_MODEL_2026-06-20]].

### 수집 경로 정리

- **Meta Ad Library(1순위)**: `collect_meta_ads.py`, 시스템 Edge로 동작(로그인 불필요). 검증 성공.
- **Chrome 확장(`pinterest-board-collector`, 2순위)**: gallery-dl 원본 = 최고 품질, 수동.
- **Playwright Pinterest 검색**: 썸네일 저화질 + 취약 → 취향학습엔 비추천. (Pinterest 로그인 세션은 `pinterest_login.py`로 생성 완료, usable)
- 번들 chromium은 `playwright install`로 1217 설치 완료(폴백 외 경로 정상화).

### source-mix / 마케팅 신호

- `source_mix_regression_gate()` 추가: 표본 충분한데 추천 쿼리 0개면 공급 자동 비활성화, 저품질 시 경고.
- 마케팅 신호 자동화: `generate_calendar_signals.py`(계절/날씨 결정적 생성), `import_oliveyoung_ranking.py`(랭킹/리뷰 CSV import).

### 현재 상태 / 다음 우선순위

- 라벨 대기 세션 생성됨: `cosmetics_skincare/meta_competitor_001` = 그동안 쌓인 Meta 경쟁사 광고 **336장** 통합 + AI 1차 추천(selected 45 / shortlist 21 / rejected 270).
- 검수 외 코드 작업은 사실상 완료. 진행 병목은 **사람 라벨링**.
- 다음 순서:
  1. 🙋 콘솔 판단 훈련에서 `meta_competitor_001` 라벨링(AI 추천 66장 우선).
  2. `python scripts/train_taste_model.py` 재학습 → AUC 0.82 대비 향상 확인.
  3. 그 결과로 수집 쿼리/임계값 조정, 선순환 반복.
- 전체 보류 항목은 [[BACKLOG]] 참고(🤖 코드 vs 🙋 사람 검수 구분).

## 2026-06-18 Handoff - 마케팅 인텔리전스 데이터 플로우 계획

### 결정

- 현재 광고 기획 품질의 핵심 병목은 모델 문장력이 아니라 근거 데이터 부족이다.
- 실제 퍼포먼스 마케터 수준의 기획을 위해 시장, 고객, 트렌드, 계절, 날씨, 채널 반응, 경쟁 메시지, 리뷰 언어를 별도 데이터 플로우로 쌓는다.
- 새 기준 문서: `knowledge/MARKETING_INTELLIGENCE_DATA_FLOW.md`.

### 목표

- 장기: 화장품 광고 기획용 `MarketingSignal` 1,000개 이상 누적.
- 1차: 화장품 파일럿 5건에서 이벤트당 근거 신호 50개 이상 연결.
- 콘셉트 3안은 각각 3개 이상의 서로 다른 근거 신호를 사용해야 한다.
- 최종 카피는 문장만 보여주지 않고 타깃 반응, 시장 맥락, 제품 역할, 오퍼 역할, 채널 이유를 함께 보여준다.

### 다음 구현 순서

1. `MarketingSignal` 스키마와 저장소를 추가한다.
2. 올리브영 랭킹/리뷰 키워드 CSV 업로드 포맷을 만든다.
3. 날씨와 계절 캘린더 신호를 자동 생성한다.
4. 생성 전 `InsightBrief` 산출물을 만들고 02 콘텐츠 기획에 연결한다.
5. 화장품 파일럿 5건을 근거 신호 기반으로 재실행한다.

### 1차 진행 완료

- `core/schemas/marketing-signal.schema.json` 추가.
- `services/marketing_intelligence/repository.py` 추가.
- `scripts/collect_marketing_signals.py` 추가.
- `tests/test_marketing_intelligence_signals.py` 추가.
- `seed_random` 화장품 신호 50개 생성 완료.
- 저장소: `design_brain_wiki/marketing_signals/signals.json`.
- 검수 CSV: `.tmp/marketing-signals/marketing-signal-review-sheet.csv`.

### 2차 진행 완료

- `scripts/console_server.py`에 마케팅 신호 패킷/API 추가.
- `GET /api/marketing-signals`, `POST /api/marketing-signals/review` 추가.
- `ui/console/app.js` 대시보드에 `마케팅 신호 검수` 섹션 추가.
- 50개 신호 중 검수 대기 12개를 카드로 노출하고 `선택 / 보류 / 거절` 저장 가능.
- `tests/test_marketing_intelligence_console.py` 추가.
- 브라우저 검증: 신호 카드 12개, 전체 50개, 검수 대기 50개, 내부 코드 노출 0건, 텍스트 넘침 0건.

### 3차 진행 완료

- `core/schemas/insight-brief.schema.json` 추가.
- `services/marketing_intelligence/insight_brief.py` 추가.
- `scripts/build_marketing_insight_brief.py` 추가.
- `POST /api/marketing-signals/insight-brief` 추가.
- 콘솔에 `기획 근거 패킷` 상태 박스와 `InsightBrief 만들기` 버튼 추가.
- selected 신호가 3개 미만이면 InsightBrief는 `needs_signal_review`로 차단된다.
- 현재 selected 신호 0개라 버튼은 비활성화 상태다.
- 전체 프로젝트 테스트 125개 통과.

### 4차 진행 완료

- `services/ad_strategy/planning_engine.py`가 ready `InsightBrief`를 읽어 콘셉트와 카피 근거에 연결한다.
- 콘셉트 후보에 `marketingEvidence`, `marketingSignalIds`, `marketingEvidenceStatus`가 기록된다.
- 카피 패키지에는 채널별 `planningEvidence.marketingSignals`, `marketingSignalIds`, `marketingEvidenceStatus`가 기록된다.
- selected 신호가 부족하면 scorecard에 `marketing_signal_review_required` warning을 남긴다.
- 테스트: 전체 프로젝트 테스트 127개 통과.

### 다음 액션

1. 콘솔에서 50개 신호를 `선택 / 보류 / 거절`로 실제 검수한다.
2. CSV로 검수할 경우 `python scripts\collect_marketing_signals.py --import-review --apply`로 반영한다.
3. selected 신호 3개 이상을 만든 뒤 `InsightBrief 만들기`로 ready 패킷을 생성한다.
4. ready `InsightBrief`로 파일럿 5건을 다시 실행해 카피 품질 변화를 본다.
5. 올리브영 랭킹/리뷰 키워드 CSV 업로드 수집기를 붙인다.

## 2026-06-17 Handoff - 광고 카피 근거층 보강

### 완료

- `services/ad_strategy/planning_engine.py`의 카피 패키지 출력에 `planningEvidence`를 추가했다.
- `strategyBasis`는 더 이상 `concept_01` 같은 내부 ID가 아니라 타깃, 제품 역할, 혜택 역할, 채널 역할을 연결한 설명 문장으로 생성된다.
- `ui/console/app.js`의 최종 카피 카드가 근거를 `문구 근거 / 타깃 / 제품 역할 / 혜택 역할 / 채널 역할`로 나누어 보여준다.
- 기존 `.tmp/model-benchmarks/`의 화장품 파일럿/벤치마크 결과를 최신 로직으로 재생성했다.
- 콘솔 서버 중복 실행으로 오래된 API 응답이 섞이던 문제를 정리하고 5177 서버를 재시작했다.

### 검증

- 브라우저 검증: `문구 근거`, `타깃`, `제품 역할`, `혜택 역할`, `채널 역할` 노출 확인.
- 브라우저 검증: `직장인로`, `증정는` 조사 오류 0건.
- 테스트: `python -m unittest tests.test_ad_planning_engine tests.test_ad_planning_upgrade tests.test_ad_planning_benchmark_review_sheet` 31개 통과.

### 남은 이슈

- 아직 `selected` 전략 사례가 30건 미만이라 근거가 구조적으로는 읽히지만, 실제 설득력은 사람 검수 데이터가 더 필요하다.
- 다음 품질 상승 작업은 광고 전략 30건 이상 선별과 화장품 파일럿 5건 사람 평가 보강이다.

## 2026-06-14 Handoff - 검증된 Meta source mix를 03단계에 자동 공급

### 완료

- `services/ad_reference/meta_source_mix_provider.py` 추가.
- 화장품 이벤트에서 검증된 제품·성분 검색어의 Qwen `clean_product_visual` 결과를 `03_reference_research` manifest에 자동 import한다.
- 검토 5건 이상, clean product rate 20% 이상인 검색어만 사용한다.
- SHA 중복 제거, 검색어당 2개, 광고당 1개, 기본 총 6개 제한을 적용한다.
- `reference-evidence.json`에 `meta_source_mix` 선택 정책, 검색어 수율, Qwen 점수, import 상태를 기록한다.
- 브랜드 참조와 source-mix 참조는 독립적으로 켜고 끌 수 있다.
- 실제 데이터 임시 run 검증: 4개 검증 검색어에서 6개 import.
- 프로젝트 테스트 58개 통과.

### 다음 순서

1. 신규 화장품 이벤트 3건에서 source-mix 실운영 지표를 수집한다.
2. 반복 결과가 기준 이하이면 자동 비활성화하는 회귀 gate를 추가한다.
3. 사람 선택이 필요한 세 번째 archive는 자동화 범위에서 제외한다.

## 2026-06-14 Handoff - 화장품 Meta 적응형 수집

### 완료

- `services/ad_reference/collection_strategy.py` 추가.
- 검수 완료된 실제 배치만 누적해 브랜드별 `retain`, `explore`, `media_gap`, `deprioritize_promotion_heavy`, `audit_alias`를 판정한다.
- 적응형 실행은 통과 앵커 1개 + 커버리지 확대 후보를 우선하고 직전 배치 브랜드를 뒤로 보낸다.
- `scripts/collect_meta_brand_registry.py --strategy adaptive|registry`, `--media-type all|image` 추가.
- 콘솔에 브랜드 선택 전략, 소재 유형, 다음 추천, 권장 5×5 배치, 적응형 누적 성과와 기준 대비를 표시한다.
- 소표본, 광고주 일치 후 정지 이미지 0건 경고를 추가했다.

### 실제 검증

- 3×3 smoke 3회와 이미지 전용 smoke 1회로 전략·회전·실패 패턴을 확인했다.
- 이미지 전용 `SKIN1004`는 raw 0이라 기본값은 `all`로 유지한다.
- 최종 5×5 검증 배치:
  - `references/meta_ads/brand_registry_runs/2026-06-14_adaptive_cosmetics_validation`
  - raw 25 / matched 14 / accepted 2 / excluded 6 / errors 0.
  - match 56% / creative acceptance 25% / brand coverage 40%.
- 적응형 누적: 5배치, unique brand 12, raw 77, accepted 4, excluded 13.
  - creative acceptance 23.5%, brand coverage 16.7%.
  - 기준 배치 대비 +17.6%p / +6.7%p.
- 누적 원본 50개 이상에서도 커버리지 30% 미만이라 `source_limited / secondary_campaign_reference`로 자동 판정한다.
- `services/ad_reference/source_mix_metrics.py`가 일반 Meta 쿼리의 Qwen 검수 성과를 집계한다.
- `scripts/collect_meta_source_mix.py`가 미검증 상품·성분 쿼리를 자동 수집·Qwen 검수한다.
- 자동 보완 수집 2회 완료, 대기 계획 0개.
- 보완 공급원 전체: reviewed 48 / clean product visual 24 / clean rate 50%.
- 검증 쿼리:
  - `나이아신아마이드 세럼` 77.8%.
  - `스킨케어 제품` 66.7%.
  - `스킨케어 세럼` 40%.
  - `스킨케어 크림` 38.9%.

### 다음 순서

1. 브랜드 묶음은 캠페인·프로모션 구조 보조 참고로 사용한다.
2. 클린 제품 비주얼은 검증된 상품·성분 쿼리를 병행한다.
3. 세 번째 실제 이벤트 최종 archive 완료.

## 2026-06-14 Handoff - 반복 운영 증거 감사

### 완료

- `scripts/audit_repeated_operations.py`와 테스트를 추가했다.
- 실제 run을 event ID 기준으로 묶어 자동화 구간 완료, 최종 종료 성공, 동일 run 실패 후 복구를 구분한다.
- 공통 project hook이 반복 운영 증거 리포트를 갱신한다.
- Workboard에 반복 운영 완료 수치를 표시한다.

### 현재 판정

- 자동화 구간 완료: 서로 다른 이벤트 5종 / 목표 3종, 충족.
- 최종 archive 성공: 서로 다른 이벤트 2종 / 목표 3종, 미충족.
- 동일 run 실패 후 복구: 1건 / 목표 1건, 충족.
- 전체 반복 실운영 증거 상태: `incomplete`.

### 검증 및 남은 조건

- 프로젝트 테스트 54개, project hook 통과.
- `scripts/run_recovery_rehearsal.py`로 테스트 이벤트 03 단계의 실제 실패와 동일 run 복구를 완료했다.
- 복구 run: `2026-06-14_05-56-34_테스트-자동화-이벤트`, 최종 상태 `reference_ready`, failureCount 1.
- 최신 콘솔 재시작 완료. Workboard `5/3`, `2/3`, `1/1` 렌더링과 JS 오류 0 확인.
- 반복 운영 감사가 다음 최종 종료 후보를 자동 선정한다.
- 현재 1순위 후보: `2026-06-13_05-01-36_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`, `05_admin_selection`.
- 세 번째 이벤트의 사람 선택·QA 승인 이후 archive 완료가 필요하다.

## 2026-06-14 Handoff - Meta 운영 지표와 Workboard

### 완료

- `services/ad_reference/registry_metrics.py`: 기존 검증 브랜드 배치에서 단계별 비율, 브랜드 커버리지, 최상위 브랜드 비중, creative type 분포와 경고를 계산한다.
- `scripts/report_meta_brand_metrics.py`: `.tmp/meta-brand-metrics/latest-meta-brand-metrics.{json,md}`를 생성한다.
- 콘솔 bootstrap/API에 `metaBrandMetrics`, `operationsReadiness`, `/api/meta-brand-metrics`를 추가했다.
- Workboard에서 운영 감사 상태·종료 run·잘못된 입력·승격 규칙·Meta 배치/경고를 확인할 수 있다.
- Meta 광고 수집 화면에서 업종별 최신 배치 지표와 경고를 확인할 수 있다.
- 공통 project hook에 Meta 지표 생성을 연결했다.

### 실제 최신 지표

- cosmetics_skincare: match 60.0% / creative acceptance 6.0% / brand coverage 10.0% / accepted 4.
- jewelry_luxury: match 43.1% / creative acceptance 95.2% / brand coverage 50.0% / accepted 60.
- 화장품 최신 배치에는 `low_creative_acceptance`, `low_brand_coverage` 경고가 있다.
- 주얼리 최신 배치는 현재 경고가 없다.

### 검증 및 다음 순서

- 프로젝트 테스트 48개, 운영 준비도 감사, 자산 무결성 감사, project hook 통과.
- 로컬 콘솔 최신 코드로 재시작 완료. Workboard와 Meta 카드 실제 렌더링, JS 오류 0 확인.
- 반복 운영 감사 결과 자동화 구간 4/3, 최종 종료 2/3, 실패 후 복구 0/1이다.

## 2026-06-14 Handoff - 자동화 운영 준비도 전체 검토

### 완료

- 신규 stage 일반 예외를 `blocked/failed`, `stage_failures`, `stage-errors.log`에 기록한다.
- run 생성 전에 `event-input.json`, `brand-guide.json`을 canonical schema로 검증한다.
- event 입력은 `objective|purpose`를 호환하며 콘솔 신규 이벤트는 둘을 함께 기록한다.
- 콘솔 job 최근 200개를 `.tmp/console-jobs/jobs.json`에 보존하고 재시작 중 running job은 `interrupted`로 복구한다.
- Meta brand provider가 `kiwon_review_state.json`을 읽어 final rejected를 제외하고 final selected를 우선한다.
- 공식 run states에 `reference_research`, `reference_ready`, `review_pending`을 추가했다.
- 최종 `production-package`는 `06_qa_packaging=approved` 이후에만 생성된다.
- learned rules 승격 정책과 runtime consumer를 추가했다.
  - 조건: profile별 반복 2개 세션 이상, 세션당 reviewed 20 이상, 완료율 80% 이상.
  - 현재 승격: `cosmetics_skincare/soften_rejected_to_shortlist`, 5개 세션·244건.
- QA 승인 전 package 1개를 `production-package-legacy-draft`로 migration했다.
- `scripts/audit_asset_integrity.py` 추가, 실제 자산 감사 `pass`.
- 운영 준비도 감사와 자산 무결성 감사를 project hook에 연결했다.
- 신규 감사: `scripts/audit_operational_readiness.py`.
- 상태 정리: `scripts/reconcile_run_states.py` dry-run/apply.
- 과거 stale run 2개를 failed/blocked로, legacy archive run 2개를 archived로 정리했다.
- 전체 프로젝트 테스트 46개와 project hook이 통과했다.

### 현재 감사 결과

- 운영 준비도 감사 `pass`, 자산 무결성 감사 `pass`.
- terminal run 4개, invalid event 0개, learned rule consumer 1개.

### 다음 순서

1. 실제 이벤트 3건 반복 운영 검증.
2. 실패 후 복구 run 1건 증명.
3. 화장품 Meta 개선 배치로 지표 비교.

상세: `knowledge/OPERATIONS_READINESS_REVIEW_2026-06-14.md`

## 2026-06-13 Handoff - Qwen 경쟁사 Meta 130장 분류 완료

### 완료

- Ollama `qwen2.5vl:7b`로 경쟁사 Meta 이미지 130장을 분류했다.
- 확장 배치:
  - `references/meta_ads/brand_registry_runs/2026-06-13_qwen_competitor_cosmetics_expanded`
  - `references/meta_ads/brand_registry_runs/2026-06-13_qwen_competitor_jewelry_expanded`
- 최종 결과: classified 130 / unique SHA 121 / accepted 64 / accepted unique SHA 61 / excluded 66 / 미분류 0.
- 유형 분포: `promotion_text_heavy` 62, `jewelry_product` 34, `model_lifestyle` 17, `brand_campaign` 11, `product_clean` 5, `jewelry_craft` 1.
- 화장품 확장 배치: accepted 4 / excluded 63.
- 주얼리 확장 배치: accepted 60 / excluded 3.

### 코드 변경

- `scripts/collect_meta_brand_registry.py`: 모든 이미지가 제외된 광고도 `accepted-ads.json.excludedItems`에 분류 상세를 보존한다.
- `scripts/reclassify_meta_brand_batch.py`: 기존 배치의 로컬 이미지를 네트워크 재수집 없이 Qwen으로 다시 분류한다.
- `tests/test_collect_meta_brand_registry.py`: 제외 이미지 상세 보존 회귀 테스트를 추가했다.

### 검증 및 다음 작업

- 프로젝트 테스트 27개, pipeline health audit, project hook 통과.
- 다음은 accepted 고유 이미지 61장으로 신규 사람 검수 세션을 만들고 Qwen 오차를 비교한다.
- 화장품 프로모션 문구형 편중과 주얼리 브랜드 편중을 보정해야 한다.

## 2026-06-13 Handoff - 전체 남은 작업 분석

### 현재 결론

- 제어 흐름과 판단 훈련은 운영 가능하다.
- 실제 제작 MVP의 병목은 live 생성 회수, generated 후보 기반 최종 E2E, Meta 재수집 회수율이다.
- 상세 분석: `knowledge/PROJECT_REMAINING_STATUS_2026-06-13.md`.

### 최신 수치

- pipeline health / hook check: pass.
- 테스트: 루트 discover 11개 + 별도 provider/classifier/UI 계약 13개 통과.
- Meta 사람 검수: 100/100, selected 19 / shortlist 52 / rejected 29.
- H&B 브리프 적합 레퍼런스 큐: 117/117 검수 완료.
- Qwen 경쟁사 재수집:
  - cosmetics accepted 1 / raw ads 30.
  - jewelry accepted 5 / raw ads 27.
- 대표 E2E run은 placeholder 15장, archive asset 0개, 현재 05 not_started / 06·07 locked.

### 다음 실행 순서

1. 단일 후보 ComfyUI live smoke test 및 timeout 회수 경로 확정.
2. generated 후보 1개를 선택해 QA pass와 archive approved asset 생성까지 완료.
3. Meta 수집 회수율을 단계별 측정하고 충분한 통과 풀로 신규 검수 세션 생성.
4. warning 승인 메모, 빈 아카이브 상태, 공통 테스트 suite를 보강.

## 2026-06-13 Handoff - Meta 검수 저장 기능 점검 완료

### 완료

- `meta_brand_review/meta_brand_review_001`에서 selected / shortlist / rejected 저장을 실제로 확인했다.
- 저장 직후 API 재조회와 브라우저 새로고침 후 재선택에서 판단이 유지되는 것을 확인했다.
- 새로고침 시 마지막 선택 세션은 유지되지 않고 `reference_learning/all`로 돌아간다. 판단 데이터는 정상 유지된다.
- 최종 검수 결과: 100/100, selected 19 / shortlist 52 / rejected 29, accuracy 0.52.
- 최신 완료 상태로 summary/compare를 다시 생성했다.

### 생성 파일

- `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/kiwon_review_state.json`
- `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/kiwon_review_summary.md`
- `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/correction_summary.md`
- `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/learned_rules.json`
- `design_brain_wiki/training_sessions/meta_brand_review/_comparisons/session-comparison.json`
- `design_brain_wiki/training_sessions/meta_brand_review/_comparisons/session-comparison.md`

### 다음 우선순위

1. Meta 재수집 결과로 새 검수 세션 생성 및 실제 브리프 연결.
2. 필요하면 마지막 선택 검수 세션을 새로고침 후 복원하는 UX 추가.

## 2026-06-13 Handoff - 전체 파이프라인 감사 및 Qwen/Ollama 복구

### 현재 판정

- placeholder 기반 전체 제어 흐름은 동작한다.
- live ComfyUI는 Qwen Image Edit 2511 그룹 생성이 20분 내 끝나지 않아 제작 준비 완료로 볼 수 없다.
- 최신 자동 감사: `.tmp/pipeline-health/latest-pipeline-health.json`
- 최종 자동 감사 상태: `pass`
- 상세 감사: `knowledge/FULL_PIPELINE_AUDIT_2026-06-13.md`

### Qwen/Ollama

- Ollama API `http://127.0.0.1:11434`, 모델 `qwen2.5vl:7b` 정상.
- 실제 Anua 광고를 `promotion_text_heavy`, `excluded`로 판정했다.
- `ollama` 명령은 현재 PowerShell PATH에서 안 잡힐 수 있다.
- `start_reference_ai.bat`와 `scripts/run_event_with_reference_ai.py`는 현재 설치 위치 `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`를 우선 자동 탐지하도록 수정했다.
- Ollama Qwen-VL은 레퍼런스 검수용이고, ComfyUI Qwen Image Edit 2511은 이미지 생성용으로 서로 별개다.

### 다음 작업

1. 단일 후보 live smoke test와 경량 ComfyUI preset을 만든다.
2. Qwen creative gate를 켜고 경쟁사 레지스트리 Meta 100장을 재수집한다.
3. 07 완료인데 재사용 자산 0개인 상태를 별도 상태로 구분한다.

### 재생성 상태 정합성 수정

- upstream 단계를 다시 실행하면 뒤 단계 상태를 `locked`로 돌리고 `stale_stages`에 기록한다.
- 대표 run에서 04 재생성 후 05 `not_started`, 06/07 `locked`를 확인했다.

## 2026-06-13 Handoff - 경쟁사 레지스트리 Meta 재수집 게이트

### 완료

- `services/ad_reference/meta_creative_classifier.py` 추가.
- `scripts/collect_meta_brand_registry.py`가 경쟁사 브랜드별 수집 후 품질 통과 이미지의 광고 성격을 분류한다.
- 수집 단계 제외 성격: `promotion_text_heavy`, `card_news`, `reject_noise`.
- Qwen 미실행·오류 시 `unclassified/review`로 보류하며 자동 선택으로 취급하지 않는다.
- `meta_brand_provider.py`도 같은 제외 성격 집합을 공유한다.
- 표본 재수집 완료:
  - `2026-06-13_competitor_cosmetics_sample`: Medicube, ROUND LAB에서 9장, 모두 성격 검수 보류.
  - `2026-06-13_competitor_jewelry_sample`: Cartier에서 1장, 성격 검수 보류.
- 원인 확인: Ollama 실행 프로그램과 Ollama 모델 저장소가 제거됐고 `.ollama` 키/캐시만 남아 있었다.
- Ollama 0.30.6 및 `qwen2.5vl:7b` 6GB 모델 복구 완료.
- `/api/tags` 응답과 실제 Medicube 이미지 판정을 확인했다. 결과는 `promotion_text_heavy`, `creativeGate=excluded`.

### 검증

- Creative classifier 및 Meta provider 테스트 통과.
- 브랜드 수집기 테스트 통과. 수집 단계 카드뉴스 제외 테스트 포함.
- `scripts/project_hook_check.py` 통과.

### 다음 우선순위

1. 경쟁사 레지스트리 배치를 성격 자동 분류 활성 상태로 실행.
2. 통과 이미지로 신규 100장 검수 세션을 만들고 실제 브리프에 연결.

> 콘솔 UI 작업을 이어갈 때는 먼저 [[CONSOLE_UI_HANDOFF]]를 확인한다.

마지막 업데이트: 2026-06-11

## 2026-06-11 Handoff - Meta 병렬 개선 완료

### 완료

- Meta 100장 Pinterest 혼입 확인:
  - 100장 모두 Meta Ad Library 원본이다.
  - 기존 Pinterest 검수 이미지 274장과 SHA-256 정확 중복 및 dHash 근접 중복은 모두 0장이다.
  - Pinterest처럼 보이는 원인은 카드뉴스 10장과 프로모션 문구형 34장이었다.
- Meta provider 성격 필터 연결:
  - `manual_meta_character_audit.json`을 읽어 `promotion_text_heavy`, `card_news`, `reject_noise`를 기본 제외한다.
  - 화장품 후보는 62장에서 18장으로 줄어든다.
- 주의: 콘솔 API 기준 `meta_brand_review_001`의 사람 검수 저장 기록은 현재 0건이다. 다음 콘솔 검수에서 선택·제외 후 새로고침하여 저장 여부를 확인한다.
- 코드 리뷰 오류 수정:
  - Meta provider가 기존 자산의 SHA, 원본 경로, 현재 경로를 모두 비교해 중복 import를 막는다.
  - 후보 브랜드명이 비어 있으면 브랜드 일치 점수를 부여하지 않는다.
  - Meta 검수 상태 탭과 완료 여부 필터를 동기화하고 초기화 시 둘 다 `all`로 복원한다.
- 수집기 안정화:
  - 동일 초 batch 경로 충돌 시 접미사 경로를 예약한다.
  - 브랜드 시작·완료·실패 직후 manifest를 원자 저장한다.
  - `--batch-id --resume`, `--batch-id --retry-failed`, `failed-brands.json`을 지원한다.
- 100장 성격 검수:
  - `knowledge/META_REVIEW_100_AUDIT.md`
  - `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/manual_meta_character_audit.json`
  - 화장품 할인 문구형·카드뉴스 44장을 clean product·brand campaign 학습 풀 기본 제외 대상으로 정리했다.
- 콘솔 Meta 검수:
  - 브랜드, 업종, direct/partner, standard/review, riskSignals, 검수 완료 여부 필터를 추가했다.
  - Pinterest 판단 훈련 동작을 유지했다.
- 03_reference_research 연결:
  - Meta 검수 세션 후보를 브리프 업종·브랜드·역할 기준으로 검색한다.
  - direct 우선, partner `-10`, review `-12` 감점을 적용하고 `reference-evidence.json`에 기록한다.
  - 테스트 런에서 Meta 8개를 선택·import하고 기존 Pinterest 계열 20개와 Meta Ad Library 23개를 유지했다.
- 확장 후보:
  - `knowledge/META_BRAND_EXPANSION_CANDIDATES.md`에 화장품 20개, 주얼리 20개를 정리했다.

### 검증

- `python -m unittest discover -v`: 5개 통과.
- Meta provider 테스트: 5개 통과.
- Meta UI 계약 테스트: 3개 통과.
- `node --check ui/console/app.js`, 관련 Python `py_compile`, `scripts/project_hook_check.py` 통과.
- 브라우저에서 완료 탭 `reviewed`, 미완료 탭 `unreviewed`, 필터 초기화 `all` 동기화를 확인했다.
- 실제 장시간 Meta 네트워크 수집은 이번 통합 검증에서 실행하지 않았다.

### 다음 운영 순서

1. 새 batch로 2~3개 브랜드를 수집한 뒤 강제 중단하고 `--resume`을 실제 네트워크 환경에서 확인한다.
2. 실패 브랜드가 생기면 같은 `batch-id`로 `--retry-failed`를 실행한다.
3. 콘솔에서 `promotion_text_heavy`, `card_news`, `device` 경계를 빠르게 검수한다.
4. 확장 후보 A 우선순위 브랜드를 업종별 3개씩 시험 수집한다.

## Meta 브랜드 검수 세션

- `meta_brand_review_001`에 Meta 광고 이미지 100장을 구성했다.
- 구성: 화장품·스킨케어 62장, 주얼리·럭셔리 38장, 23개 브랜드.
- 광고주 유형: 공식 계정 `direct` 88장, 협업 계정 `partner` 12장.
- 품질: `standard` 84장, `review` 16장. 파일 손상과 SHA 중복은 없다.
- 편중 제한: 브랜드당 최대 20장, 광고당 최대 5장, 협업 광고 최대 20장.
- 대표 샘플 육안 검수 결과 주얼리는 캠페인·제품·제작 과정이 정상이고, 화장품은 할인 문구형 프로모션 카드가 일부 포함되어 사람 판단이 필요하다.
- 생성 명령: `.venv\Scripts\python.exe scripts\create_meta_brand_review_session.py --session-id meta_brand_review_001 --limit 100 --force`

## 프로젝트 포지션

이 프로젝트는 GPT보다 똑똑한 기획툴이 아니다.

목표는 브랜드/이벤트 입력에서 시작해 레퍼런스 수집, 콘텐츠 기획, 이미지 후보 생성, 사람 선택, QA 패키징, 자산 아카이브까지 이어지는 로컬 제작 콘솔이다.

핵심 사용자는 브랜드 이벤트 이미지를 만드는 디자이너/운영자다.

## 현재 기준 파이프라인

```text
01_event_brief
→ 02_content_planning
→ 03_reference_research
→ 04_visual_candidates
→ 05_admin_selection
→ 06_qa_packaging
→ 07_asset_archive
```

`05_figma_assembly`는 제거된 상태다.

## 구현 상태

| 기준 단계 | 실제 구현/호환 경로 | 상태 |
|---|---|---|
| 01_event_brief | `pipeline/01_event_brief/handlers/generate_brief.py` | 구현 완료 |
| 02_content_planning | `pipeline/02_content_planning/handlers/generate_content_plan.py` | 구현 완료 |
| 03_reference_research | `pipeline/03_reference_research/handlers/run_reference_research.py` | MVP 추가 완료 |
| 04_visual_candidates | `pipeline/03_visual_candidates/handlers/generate_visual_candidates.py` | 구현 완료, 물리 폴더명은 기존 유지 |
| 05_admin_selection | `pipeline/04_admin_selection/handlers/apply_selection.py` | 구현 완료, 물리 폴더명은 기존 유지 |
| 06_qa_packaging | `pipeline/06_qa_packaging/handlers/run_qa_packaging.py` | 구현 완료 |
| 07_asset_archive | `pipeline/07_asset_archive/handlers/run_asset_archive.py` | 구현 완료 |

## 호환 규칙

- 새 실행 기준은 `03_reference_research`, `04_visual_candidates`, `05_admin_selection`.
- 기존 명령 `03_visual_candidates`는 workflow alias로 `04_visual_candidates`에 매핑된다.
- 기존 명령 `04_admin_selection`은 workflow alias로 `05_admin_selection`에 매핑된다.
- 런 산출물 폴더는 당분간 `03_visual_candidates/`, `04_admin_selection/`을 유지한다.

## 로컬 콘솔

```powershell
start_brand_event_console.bat
```

접속:

```text
http://127.0.0.1:5177
```

콘솔 역할:

- 런 목록/상태 확인
- 레퍼런스 검수
- 프롬프트 확인
- ComfyUI 후보 생성
- 이미지 선택/탈락/보류/재생성 요청
- QA/패키지 확인

## ComfyUI 상태

기준 URL:

```text
http://127.0.0.1:8188
```

현재 연결:

- placeholder 생성과 ComfyUI payload 구성은 동작.
- `qwen_candidate_2511` live 생성 검증 완료: 테스트 런 `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`, 그룹 `instagram_cardnews_01__key_visual`에서 후보 3장 생성/회수 성공.
- `generation-quality.json`으로 생성 성공 여부, 파일 정보, ComfyUI prompt id, `reference_direction` 반영 여부를 추적한다.
- cosmetics/jewelry/bullion 외부 workflow registry 연결 완료.

주요 실행:

```powershell
$env:COMFYUI_GENERATION_MODE='live'
python scripts\workflow.py --run runs\<run-id> --stage 04_visual_candidates --mode regenerate --group <group-id>
```

## 03_reference_research 사용

기본 실행은 레퍼런스 검색 계획과 현재 수집 상태 요약만 만든다.

```powershell
python scripts\workflow.py --run runs\<run-id> --stage 03_reference_research
```

자동 검색/선정까지 stage 안에서 실행하려면:

```powershell
$env:REFERENCE_RESEARCH_MODE='auto_search'
python scripts\workflow.py --run runs\<run-id> --stage 03_reference_research
```

자동 검색은 Pinterest/브라우저/세션 상태의 영향을 받으므로 MVP 기본값은 `plan`이다.

## 다음 우선순위

## 2026-05-27 추가 업데이트 — reference research → visual candidates 연결

- `03_reference_research/reference-research.json`에 프롬프트 방향 필드를 추가했다.
- 추가 필드: `moodKeywords`, `compositionKeywords`, `lightingKeywords`, `colorPalette`, `materialTexture`, `avoidKeywords`, `promptHints`, `negativePromptHints`, `selectedReferences`.
- `04_visual_candidates`가 `reference-research.json`을 읽어 `positive_prompt`, `negative_prompt`, `visual-plan.json.reference_direction`, `image-prompts.json.prompts[].reference_direction`에 반영한다.
- 선택 레퍼런스가 없어도 검색 계획/이벤트 의도에서 추출한 mood/composition/color/texture 힌트가 후보 프롬프트에 들어간다.
- 검증 런: `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`에서 03 재실행 후 04 후보 프롬프트에 `reference prompt hints`와 negative hint 반영 확인.

## 2026-05-27 추가 업데이트 — ComfyUI live 생성 검증 및 품질 추적

- `services/comfyui/client.py`가 ComfyUI HTTP 400 응답 본문을 `generation_error`에 남기도록 보강했다.
- ComfyUI client 기본 timeout을 1200초로 늘렸다.
- 제품 이미지가 없는 이벤트에서 `product_input.png`로 떨어지던 fallback을 `qwen_image_edit_1024.png`로 수정했다.
- `qwen_candidate_2511` 기본값을 `8 steps / cfg 1.0 / heun / beta`로 맞췄다.
- live 검증 결과:
  - `instagram_cardnews_01__key_visual_c01.png` generated, 1024x1024
  - `instagram_cardnews_01__key_visual_c02.png` generated, 1024x1024
  - `instagram_cardnews_01__key_visual_c03.png` generated, 1024x1024
- 품질 메모: c02가 가장 안정적. c01은 baked-in 깨진 텍스트가 많고, c03은 제품 카테고리가 와인/패키지 쪽으로 이탈했다.

## 2026-05-28 추가 업데이트 — reference_research 품질 필터 강화

- 금/은/투자/상담 이벤트를 `bullion_investment` profile로 감지한다.
- 검색어는 프리미엄 금 투자/금융 상담/골드바/자산관리 캠페인 중심으로 생성한다.
- `reference-research.json`에 `eventProfile`, `qualityFilter`, 강화된 `avoidKeywords`, `negativePromptHints`를 기록한다.
- Qwen reviewer와 `reference-quality-filter.json` 기준에 `brandFit`, `eventFit`, `seriousnessFit`, `productRelevance`, `riskLevel`을 추가했다.
- selected gate: `brandFit >= 7`, `eventFit >= 7`, `productRelevance >= 7`, `seriousnessFit >= 6`, `riskLevel <= 4`.
- 이미지 프롬프트는 `blank space for Korean headline`, `poster layout with empty text area`, `no readable text`, `no fake typography`를 기본 포함한다.
- 테스트 런 `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`에서 03 재생성 확인:
  - 검색어가 `premium gold investment campaign visual`, `luxury financial consultation poster`, `gold bar premium product photography` 등으로 교체됨.
  - mood는 `premium`, `calm`, `financial-trust`로 정리됨.
  - toy/kawaii/camping/wine/fake text 계열 negative 방향이 포함됨.
- 04 추가 보강: `bullion_investment` profile에서는 positive prompt와 reference prompt hint에서 `mascot/character/cute/camping/picnic/tent/toy/diorama/cartoon/kawaii/playful/wine/bottle/package box`를 제거한다.
- 검증: 같은 테스트 런의 `instagram_cardnews_01__key_visual` 그룹 3개 프롬프트에서 positive 금지어 hit 0, trace prompt hint 금지어 hit 0, negative core blocker 포함 확인.

## 2026-05-28 추가 업데이트 — 04 prompt audit

- live 생성 전 `scripts/audit_visual_prompts.py`로 `03_visual_candidates/image-prompts.json`을 검사한다.
- 출력:
  - `04_visual_candidates/prompt-audit.json`
  - `04_visual_candidates/prompt-audit.md`
- 검사 기준:
  - positive forbidden hit = 0
  - negative prompt에 금지 방향 포함
  - required 방향 최소 5개 이상 포함
  - fake text 방지 문구 포함
  - Korean headline 빈 공간 문구 포함
- 테스트 런 `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`: total 15, passed 15, warning 0, failed 0.

## 2026-05-28 추가 업데이트 — 04 live 소량 생성 테스트

- 실행 범위: `instagram_cardnews_01__key_visual` 3장만 live 생성.
- 결과 파일:
  - `04_visual_candidates/live-small-test-report.json`
  - `04_visual_candidates/live-small-test-report.md`
- 생성 자체는 성공: 3장 모두 `generation_status=generated`, 1024x1024 PNG.
- 품질 판정은 실패:
  - c01: mascot/character, cute 3D style 남음.
  - c02: mascot/character, fake broken poster text, random package/box-like object 남음.
  - c03: mascot/character, fake broken text, toy-like colorful object ring 남음.
- 핵심 원인: prompt는 clean하지만 `product_image`와 `base_image`가 여전히 `qwen_image_edit_1024.png`이며, 이 입력 이미지의 캐릭터/장난감 맥락을 Qwen image-edit이 유지하는 것으로 보인다.
- 다음 수정: `bullion_investment`에서 `qwen_image_edit_1024.png` fallback을 금지하고, neutral bullion/gold-bar 입력 이미지 또는 bullion 전용 workflow/text-to-image 경로로 분기해야 한다.

## 다음 우선순위

1. `bullion_investment`에서 `qwen_image_edit_1024.png` fallback 금지 및 neutral bullion input/workflow 분기
2. audit 통과 프롬프트 기준으로 1~3장 live 재테스트
3. 강화된 03 기준으로 reference auto_search를 다시 돌려 실제 selected/rejected 분포 확인
4. 콘솔 선택 화면에 `generation-quality.json`, `reference-quality-filter.json`, `prompt-audit.json` 품질 상태 노출
5. 콘솔에서 `03_reference_research → 04_visual_candidates → 05_admin_selection` 버튼 흐름 확인
## 2026-05-28 추가 업데이트 - 브랜드/이벤트별 레퍼런스 기준 데이터 구조화

- GOAL: 이미지 생성 중단 -> 레퍼런스 기준 데이터셋 정리 -> fallback 오염 제거 -> 이후 04 테스트 재개.
- 생성된 룰 파일:
  - `assets/rules/brand-persona.json`
  - `assets/rules/event-rules.json`
  - `assets/rules/reference-rules.json`
  - `assets/rules/visual-avoid-rules.json`
  - `assets/rules/tone-rules.md`
- 생성된 데이터셋 폴더:
  - `assets/reference_training/bullion_investment/good/`
  - `assets/reference_training/bullion_investment/bad/`
- bad dataset에는 최근 실패 후보 3장과 태그 `mascot_character`, `toy_3d`, `childish_mood`, `fake_text`, `not_financial`, `not_premium`, `wrong_event_tone`을 기록.
- `core/utils/rulebook.py` 추가: 룰 파일 로딩, event profile 감지, 검색어/게이트/금지어/prompt hint 제공.
- `scripts/reference_pipeline.py`는 bullion 검색어와 selection gate를 룰 파일에서 읽는다.
- `pipeline/03_reference_research/handlers/run_reference_research.py`는 `ruleSources`, `referenceDecisions`, 룰 기반 prompt/negative hint를 출력한다.
- `pipeline/03_visual_candidates/handlers/generate_visual_candidates.py`는 bullion 프로필에서 오염된 `qwen_image_edit_1024.png` fallback을 금지하고 neutral bullion 샘플 이미지를 사용한다.
- 검증:
  - `python -m py_compile ...` 통과
  - `python scripts\workflow.py --run runs\2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트 --stage 03_reference_research --mode regenerate` 통과
  - bad mock reference가 `rejected`로 분류되고 reject reason이 기록됨 확인.

## 다음 우선순위

1. auto_search를 다시 돌려 selected/shortlist/rejected 분포 확인
2. good reference 수동 추가 후 기준 보강
3. reference 기준 통과 후 04 prompt/placeholder audit
4. 마지막에만 1~3장 소량 live ComfyUI 테스트

## 2026-05-30 추가 업데이트 - good reference seed 구축 및 03 품질 검증

- good seed 10장 생성:
  - `assets/reference_training/bullion_investment/good/01_silver_coin_tube_product.png`
  - `assets/reference_training/bullion_investment/good/02_silver_coin_product_angle.jpg`
  - `assets/reference_training/bullion_investment/good/03_silver_coin_obverse.jpg`
  - `assets/reference_training/bullion_investment/good/04_silver_coin_slab_product.jpg`
  - `assets/reference_training/bullion_investment/good/05_silver_krugerrand_obverse.jpg`
  - `assets/reference_training/bullion_investment/good/06_silver_krugerrand_slab.jpg`
  - `assets/reference_training/bullion_investment/good/07_silver_philharmonic_obverse.jpg`
  - `assets/reference_training/bullion_investment/good/08_silver_philharmonic_reverse.jpg`
  - `assets/reference_training/bullion_investment/good/09_bullion_coin_tube_case.png`
  - `assets/reference_training/bullion_investment/good/10_precious_metal_eagle_coin.png`
- `assets/reference_training/bullion_investment/good/metadata.json` 작성 완료.
- `core/utils/reference_training.py` 추가: good/bad seed 기반 `training_alignment` 계산.
- `scripts/reference_pipeline.py`는 `training_alignment.goodScore/badScore`를 selection gate에 반영한다.
- `pipeline/03_reference_research/handlers/run_reference_research.py`는 다음 파일을 추가 출력한다:
  - `03_reference_research/reference-quality-report.json`
  - `03_reference_research/reference-quality-report.md`
- 검증:
  - good/bad local seed를 run reference 후보로 import
  - heuristic selector 실행
  - `03_reference_research --mode regenerate` 실행
  - 결과: status pass, selected 8, rejected 5, selected bad signal 0, fallback clean true
  - bad seed 3장은 모두 rejected
- 아직 ComfyUI live 생성은 재개하지 않음.

## 다음 우선순위

1. good seed에 product-only가 아닌 premium finance poster/layout reference를 추가
2. 03 report에서 selected 평균 good score와 selected bad signal을 계속 확인
3. 통과 후 04 prompt/placeholder audit
4. 마지막에만 live ComfyUI 소량 테스트

## 2026-05-30 추가 업데이트 - good seed 2차 보강

- good seed를 30장 구조로 확장했다.
- 폴더:
  - `assets/reference_training/bullion_investment/good/product_reference/` 10장
  - `assets/reference_training/bullion_investment/good/finance_mood_reference/` 10장
  - `assets/reference_training/bullion_investment/good/poster_layout_reference/` 10장
- `assets/reference_training/bullion_investment/good/metadata.json`에 `category`, `tags`, `whyGood`, `usefulFor` 반영.
- `core/utils/reference_training.py`는 category/usefulFor coverage를 계산한다.
- `scripts/reference_pipeline.py`는 accepted reference를 category round-robin으로 정렬해 product-only 편향을 줄인다.
- `reference-quality-report` 추가 필드:
  - `goodSeedCoverage`
  - `selectedCategoryCoverage`
  - `selectedCoverage`
- 검증 run: `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`
- 최종 검증 결과:
  - status pass
  - selected 12
  - accepted/shortlist/rejected 25/4/4
  - selected bad signal 0
  - average good training score 8.48
  - average bad training score 0.0
  - fallback clean true
  - good seed coverage 10/10/10
  - selected category coverage product 4 / finance mood 4 / poster layout 4
  - selected role coverage product_identity 8 / mood 8 / composition 12 / lighting 8 / headline_space 8
- ComfyUI는 재개하지 않았다.

## 다음 우선순위

1. 04를 live가 아니라 placeholder/prompt 생성으로만 실행
2. prompt audit에서 캐릭터/장난감/캠핑/fake text 차단 확인
3. 사람 검토 후 live ComfyUI 1~3장만 소량 테스트
## 2026-05-30 추가 업데이트 - Senior Designer Brain Wiki 1차 구축

- 새 1차 GOAL: `Senior Designer Brain Wiki` 구축.
- 목적: AI가 브랜드/이벤트/레퍼런스를 시니어 디자이너처럼 판단하도록 디자인 원칙, 브랜드 전략, UX 기준, 그래픽 원론, 업종별 playbook, good/bad 사례, 피드백 언어를 구조화한다.
- 생성 위치: `design_brain_wiki/`
- 생성된 주요 파일:
  - `design_brain_wiki/00_INDEX.md`
  - `design_brain_wiki/00_JUDGE_SCHEMA.md`
  - `design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json`
  - `design_brain_wiki/99_sources/source_map.md`
  - 원칙/전략/판단/채널/업종/사례/취향/피드백 문서 다수
- 문서 형식: 링크 모음이 아니라 `자료 원문/링크 -> 핵심 요약 -> 디자인 판단 질문 -> 평가 항목 -> good/bad 적용 -> AI 피드백 문장 예시`.
- 참고 출처: Design Council Double Diamond, IDEO, NN/g heuristics, Apple HIG, Material Design, IBM Carbon, Pentagram, COLLINS, Wolff Olins, Landor, Interbrand.

### 다음 우선순위

1. `03_reference_research`에서 wiki rubric/source를 로드.
2. selected/shortlist/rejected 이유에 wiki rule id 또는 source file을 남김.
3. `reference-quality-report.md/json`에 senior designer feedback을 추가.
4. ComfyUI는 위 기준 통과 전까지 추가 live 생성 금지.
## 2026-05-31 추가 업데이트 - Wiki Judge 샘플 테스트

- 목적: `Senior Designer Brain Wiki`가 실제로 reference judgement 품질을 올리는지 검증.
- 생성:
  - `design_brain_wiki/tests/reference_judge_sample_set.json`
  - `design_brain_wiki/tests/README.md`
  - `scripts/run_reference_judge_wiki_tests.py`
  - `design_brain_wiki/tests/output/reference-judge-test-report.json`
  - `design_brain_wiki/tests/output/reference-judge-test-report.md`
- 테스트 범위:
  - `bullion_investment`: 6개 후보
  - `cosmetics_skincare`: 6개 후보
  - `jewelry_luxury`: 6개 후보
- 후보 구성: good / bad / ambiguous 혼합.
- 평가 항목:
  - expected decision vs actual decision
  - selected/shortlist/rejected 정확도
  - 피드백 깊이
  - generic phrase 사용 여부
  - 역할/사용 위치/부족 기준/리스크 신호 포함 여부
- 최신 결과:
  - total 18
  - correct 18
  - accuracy 1.0
  - feedback depth rate 1.0
  - status pass

### 다음 우선순위

1. `scripts/run_reference_judge_wiki_tests.py`의 scoring/feedback logic을 `03_reference_research` report generation 쪽으로 흡수.
2. `reference-quality-report.json/md`에 `wikiSources`, `seniorDesignerFeedback`, `feedbackDepth` 필드 추가.
3. 실제 reference 20장 테스트에서 shallow feedback이 나오면 해당 업종 playbook 또는 feedback language만 보강.
## 2026-05-31 추가 업데이트 - Senior Designer Brain Wiki v0.2 확장

- 정정: 위키는 아직 완성본이 아니다. 현재 상태는 `v0.1 골격 + 샘플 테스트 통과 + v0.2 자료 확장 시작`이다.
- 추가 파일:
  - `design_brain_wiki/VERSION_STATUS.md`
  - `design_brain_wiki/06_case_studies/case_banks/README.md`
  - `design_brain_wiki/06_case_studies/case_banks/pentagram_10.md`
  - `design_brain_wiki/06_case_studies/case_banks/collins_10.md`
  - `design_brain_wiki/06_case_studies/case_banks/wolff_olins_10.md`
  - `design_brain_wiki/06_case_studies/case_banks/landor_10.md`
  - `design_brain_wiki/06_case_studies/case_banks/interbrand_10.md`
  - `design_brain_wiki/05_industry_playbooks/deep/bullion_investment_v0_2.md`
  - `design_brain_wiki/05_industry_playbooks/deep/cosmetics_skincare_v0_2.md`
  - `design_brain_wiki/05_industry_playbooks/deep/jewelry_luxury_v0_2.md`
  - `design_brain_wiki/05_industry_playbooks/deep/industry_boundary_matrix.md`
  - `design_brain_wiki/07_my_taste_dataset/v0_2/kiwon_feedback_bank_100.md`
  - `design_brain_wiki/07_my_taste_dataset/v0_2/reference_dataset_growth_plan.md`
  - `design_brain_wiki/07_my_taste_dataset/v0_2/review_session_template.md`
  - `design_brain_wiki/07_my_taste_dataset/v0_2/taste_tags.md`
- 검증:
  - `design_brain_wiki` 파일 수 73개.
  - case bank 항목 50개 확인.
  - deep playbook 3개 모두 `고급스러움과 싸보임의 경계`, `브랜드 위험 요소`, `채널별 사용 기준`, `Senior Feedback 예시` 포함.

### 다음 우선순위

1. 실제 이미지 레퍼런스 100-300장 수집/분류.
2. 기원님 실제 판단 문장 100개 입력.
3. v0.2 case bank와 deep playbook을 `03_reference_research`의 rule source로 연결.
4. 실제 수집 레퍼런스로 v0.3 검증 로그 생성.
## 2026-05-31 추가 업데이트 - bullion_investment training session 001

- 목적: 위키를 파일 저장소가 아니라 실제 판단 훈련 루프로 전환.
- 생성 스크립트: `scripts/create_bullion_training_session.py`
- 세션 위치: `design_brain_wiki/training_sessions/bullion_investment/session_001/`
- 입력:
  - `assets/reference_training/bullion_investment/good/` 27장
  - `assets/reference_training/bullion_investment/bad/` 3장
- 출력:
  - `references/` 30장
  - `ai_judgement.json`
  - `ai_judgement.md`
  - `kiwon_review_template.md`
  - `correction_log.md`
  - `wiki_update_suggestions.md`
  - `README.md`
- AI 1차 판단 결과:
  - selected 7
  - shortlist 20
  - rejected 3
- 판단 방식:
  - 로컬 Qwen/Ollama vision model 미사용.
  - metadata와 `design_brain_wiki` 기준을 사용한 Codex/wiki heuristic 1차 판단.
- 수정 사항:
  - `no fake text`, `no character` 같은 긍정/차단 태그가 위험 신호로 오독되어 일부 good seed가 rejected되는 문제가 있었음.
  - `scripts/create_bullion_training_session.py`에서 `no ...`, `without ...` 태그는 risk detection에서 제외하도록 수정.

### 다음 우선순위

1. 기원님이 `kiwon_review_template.md`에 교정 입력.
2. 교정 결과를 `correction_log.md`에 반영.
3. 과승인/과거절 패턴을 bullion deep playbook과 rubric에 반영.
4. 다음 세션은 실제 외부 수집 reference 30장으로 진행하고 가능하면 Qwen VL 리뷰도 함께 붙인다.
## 2026-05-31 추가 업데이트 - 판단 훈련 로컬 콘솔 UI

- 기존 로컬 콘솔에 `판단 훈련` 탭을 추가했다.
- 서버 변경: `scripts/console_server.py`
  - training session list/detail API 추가.
  - session image serving 추가.
  - 기원님 review 저장 API 추가.
- 프론트 변경:
  - `ui/console/index.html`
  - `ui/console/app.js`
  - `ui/console/styles.css`
- 사용 방법:
  1. `start_brand_event_console.bat`
  2. `http://127.0.0.1:5177`
  3. 왼쪽 `판단 훈련` 탭
  4. `bullion_investment/session_001` 선택
  5. 이미지별로 `맞음 / 틀림 / 애매`, `정답 판단`, `기원님 이유`, `수정할 룰` 입력
  6. `교정 저장`
- 저장 결과:
  - `design_brain_wiki/training_sessions/bullion_investment/session_001/kiwon_review_state.json`
  - `design_brain_wiki/training_sessions/bullion_investment/session_001/kiwon_review_summary.md`
- 현재 콘솔 서버는 `http://127.0.0.1:5177`로 시작됨.
## 2026-05-31 Progress - Senior Designer Brain / Reference Review 방향 정리

### 현재 목표

- 1차 목표는 이미지 생성기가 아니라 `Senior Designer Brain Wiki` 기반의 디자인 판단 에이전트 구축이다.
- 흐름은 `Senior Designer Brain Wiki -> Reference Judge -> Direction Director -> Prompt/Image production` 순서로 본다.
- ComfyUI는 현재 판단 기준이 통과된 뒤에 붙는 downstream 실행 엔진이며, 레퍼런스 판단/교정 루프 전에는 추가 live 생성하지 않는다.

### 지금까지 구축된 데이터

- `design_brain_wiki/` 구조 생성 완료.
  - 디자인 원칙, 브랜드 전략, 레퍼런스 판단, 채널 사용성, 업종별 playbook, 케이스스터디, 취향 데이터셋, 피드백 언어로 분리.
- Wiki judge 기본 스키마 생성.
  - `design_brain_wiki/00_JUDGE_SCHEMA.md`
  - `design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json`
- v0.2 확장 데이터 생성.
  - studio case bank 50개: Pentagram 10 / COLLINS 10 / Wolff Olins 10 / Landor 10 / Interbrand 10.
  - deep playbook 3개: `bullion_investment`, `cosmetics_skincare`, `jewelry_luxury`.
  - Kiwon feedback bank 초안과 reference dataset growth plan 생성.
- Wiki judge 샘플 테스트 생성 및 통과.
  - 위치: `design_brain_wiki/tests/`
  - 범위: bullion/cosmetics/jewelry 각 6개, 총 18개.
  - 결과: accuracy 1.0, feedback depth rate 1.0.
  - 주의: 이건 작은 자체 시험지라서, 실제 시니어 디자이너 판단력 검증으로 보기에는 부족하다.

### bullion_investment reference 기준 데이터

- rule 파일 생성 완료.
  - `assets/rules/brand-persona.json`
  - `assets/rules/event-rules.json`
  - `assets/rules/reference-rules.json`
  - `assets/rules/visual-avoid-rules.json`
  - `assets/rules/tone-rules.md`
- bad dataset 생성.
  - 위치: `assets/reference_training/bullion_investment/bad/`
  - 태그: mascot_character, toy_3d, childish_mood, fake_text, not_financial, not_premium, wrong_event_tone.
- good seed 2차 구조화 완료.
  - `assets/reference_training/bullion_investment/good/product_reference/` 10개.
  - `assets/reference_training/bullion_investment/good/finance_mood_reference/` 10개.
  - `assets/reference_training/bullion_investment/good/poster_layout_reference/` 10개.
  - `metadata.json`에 category, tags, whyGood, usefulFor 기록.
- `03_reference_research` report에 coverage와 selected/rejected 판단 기준 반영.
  - selected bad signal 0.
  - fallback clean true.
  - selected category coverage가 product / finance mood / poster layout로 분산되도록 보강.

### 판단 훈련 UI

- 로컬 콘솔 `http://127.0.0.1:5177`에 `판단 훈련` 탭 추가.
- 서버/API 변경:
  - `scripts/console_server.py`
  - `GET /api/training-sessions`
  - `GET /api/training-sessions/<profile>/<session_id>`
  - `POST /api/training-sessions/<profile>/<session_id>/review`
  - `GET /training-assets/<profile>/<session_id>/<filename>`
- 프론트 변경:
  - `ui/console/index.html`
  - `ui/console/app.js`
  - `ui/console/styles.css`
- 저장 파일:
  - `kiwon_review_state.json`
  - `kiwon_review_summary.md`

### 중요한 정정

- 현재 `design_brain_wiki/training_sessions/bullion_investment/session_001/`은 실제 Pinterest 레퍼런스 검수 세션이 아니다.
- `session_001`은 `assets/reference_training/bullion_investment/good|bad`에 있던 기존 seed 이미지를 복사해서 만든 seed 기준 검증 세션이다.
- 사용자가 지적한 대로, 이 세션을 "핀터레스트에서 가져온 실제 레퍼런스 30장 판단"으로 보면 안 된다.
- 다음 작업에서는 `session_001`을 seed test로 명확히 표시하고, 실제 수집 reference 기반 세션을 별도로 만들어야 한다.

### 다음 우선순위

1. `session_001`을 `seed_test`로 라벨링한다.
2. 기존 run의 `references/candidates` 또는 새 수집 결과에서 실제 Pinterest/search reference 30장을 가져와 `pinterest_session_001`을 만든다.
3. 판단 훈련 UI에서 seed session과 실제 reference session을 구분해 보여준다.
4. `pinterest_session_001`에 대해 AI 1차 판단을 생성한다.
   - selected / shortlist / rejected
   - confidence
   - 판단 이유
   - 참고 가능한 요소
   - 위험 요소
   - 사용한 wiki 기준
   - seniorDesignerFeedback
5. 사용자가 UI에서 agree / disagree / unsure, correctDecision, kiwonReason, ruleToUpdate를 입력한다.
6. 교정 로그를 기반으로 bullion playbook, feedback phrase, reference judge rubric을 보강한다.
## 2026-05-31 Progress - Pinterest 실제 reference 세션 생성 완료

### 해결한 문제

- 사용자가 지적한 대로 기존 `session_001`은 실제 Pinterest 레퍼런스가 아니라 `assets/reference_training/bullion_investment/good|bad` seed 이미지 복사본이었다.
- `session_001`을 `sessionType: seed_test`로 명확히 라벨링했다.
- 실제 Pinterest/search 수집물 기반 세션을 별도 생성했다.

### 코드 변경

- `scripts/reference_pipeline.py`
  - Playwright Pinterest collector가 남기는 `metadata.jsonl`을 읽어 `pin_url`, `image_url`, `downloaded_url`, `sha256`, `title`을 ranked/selected 후보에 보존.
  - 이제 실제 수집 이미지인지 `source_url`과 `pin_url`로 확인 가능.
- `scripts/create_bullion_training_session.py`
  - `--run <run>` 옵션 추가.
  - run의 `references/reference-quality-filter.json`에서 accepted/shortlist/rejected를 읽어 30장 판단 세션 생성.
  - `--require-pinterest` 옵션으로 Pinterest/search 출처가 없으면 실패하게 함.
- `scripts/console_server.py`, `ui/console/app.js`
  - 판단 훈련 목록/상세에 `sessionType`, `sourceRun` 표시.
  - 항목별 `Pinterest pin 열기` 링크 표시.

### 실행/검증

- 기본 `python`에는 Playwright가 없어 auto_search가 실패했다.
- `.venv\Scripts\python.exe`에는 Playwright가 있어 아래 방식으로 성공:

```powershell
$env:REFERENCE_RESEARCH_MODE='auto_search'
$env:REFERENCE_QUERY_LIMIT='3'
$env:REFERENCE_PER_QUERY_LIMIT='12'
$env:REFERENCE_SELECT_COUNT='30'
.venv\Scripts\python.exe scripts\workflow.py --run runs\<2026-05-27 gold run> --stage 03_reference_research --mode regenerate
```

- 생성 세션:
  - `design_brain_wiki/training_sessions/bullion_investment/pinterest_session_001/`
  - total 30
  - selected 4 / shortlist 5 / rejected 21
  - 30/30 items have `sourceIsPinterest: true`
  - 첫 항목 예시 pin: `https://kr.pinterest.com/pin/1829656092852096/`

### 다음 우선순위

1. 콘솔 `판단 훈련`에서 `bullion_investment/pinterest_session_001` 리뷰.
2. rejected가 많은 이유가 실제로 타당한지 기원님 교정으로 확인.
3. selected 후보가 너무 적으면 query_limit/per_query_limit을 늘리거나 curated Pinterest board URL을 source로 추가.
4. 교정 결과를 correction log와 wiki update suggestions에 반영.
## 2026-05-31 Progress - 한국어 검색 기준과 빠른 비교 UI

### 배경

- 사용자가 실제 Pinterest 검색 때 한국 자료 위주로 넣어달라고 했지만, 기존 `assets/rules/reference-rules.json`의 bullion 검색어는 영문 위주였다.
- 그 결과 `pinterest_session_001`은 해외 금융/금 이미지가 많이 섞였다.
- 기존 판단 훈련 UI는 왼쪽 리스트에서 이미지를 하나씩 클릭해야 해서 30장 리뷰가 느렸다.

### 변경

- `assets/rules/reference-rules.json`
  - bullion searchQueries를 한국어 우선으로 변경.
  - 주요 쿼리: `한국 금 투자 상담 카드뉴스 디자인`, `한국 금거래소 이벤트 배너 디자인`, `실물 금 투자 상담 인스타 카드뉴스`, `골드바 투자 프로모션 배너`, `금 시세 상담 카드뉴스 디자인`.
- `scripts/create_bullion_training_session.py`
  - run 기반 세션 생성 시 accepted/shortlist/rejected를 10장씩 균형 샘플링.
  - 순서도 selected/shortlist/rejected가 섞이도록 round-robin 배치.
- `ui/console/index.html`, `ui/console/app.js`, `ui/console/styles.css`
  - 판단 훈련에 `빠른 비교 판정` 패널 추가.
  - 두 장을 동시에 보고 `왼쪽 좋음`, `오른쪽 좋음`, `둘 다 후보`, `둘 다 제외`, `건너뛰기`로 저장/이동.

### 새 세션

- 위치: `design_brain_wiki/training_sessions/bullion_investment/pinterest_kr_session_001/`
- 입력: `.venv` Python으로 `03_reference_research` auto_search 재실행.
- 결과:
  - total 30
  - selected 10 / shortlist 10 / rejected 10
  - 30/30 `sourceIsPinterest: true`
  - 첫 쌍은 `selected`와 `shortlist`가 같이 보이도록 확인.

### 검증

- `node --check ui/console/app.js` 통과.
- `.venv\Scripts\python.exe -m py_compile scripts/create_bullion_training_session.py` 통과.
- 브라우저에서 `http://127.0.0.1:5177` 판단 훈련 화면 확인:
  - 세션 목록에 `pinterest_kr_session_001` 표시.
  - summary가 30 / 10 / 10 / 10으로 표시.
  - 빠른 비교 버튼 5개 표시.

### 다음 우선순위

1. 기원님이 `pinterest_kr_session_001`을 빠른 비교로 리뷰.
2. 외국 자료/한국 감성 부족/금융 신뢰 부족을 빠르게 rejected로 교정.
3. 교정 로그를 기반으로 한국형 금거래소/금투자 카드뉴스 기준을 playbook에 추가.
## 2026-06-03 Progress - pinterest_kr_session_001 correction summary

### 생성 파일

- `design_brain_wiki/training_sessions/bullion_investment/pinterest_kr_session_001/correction_summary.md`

### 분석 결과

- 리뷰 완료: 30/30.
- 전체 일치율: 11/30, 36.7%.
- AI selected 일치율: 2/10, 20.0%.
- AI shortlist 일치율: 0/10, 0.0%.
- AI rejected 일치율: 9/10, 90.0%.
- 최종 기원님 판단 분포:
  - selected 5
  - shortlist 0
  - rejected 25

### 주요 결론

- AI가 `한국어 검색어로 수집됨`, `금/돈/금융 분위기`, `부분 참고 가능`을 selected/shortlist 근거로 과대평가했다.
- `shortlist` 기준은 현재 의미가 약하다. 이번 세션에서 기원님 최종 shortlist는 0개였다.
- `mascot_character`는 기본 감점 신호지만 무조건 hard reject로 두면 안 된다. `bullion_ref_03`은 AI rejected였지만 기원님 selected였다.
- feedback 문장에 `부분 참고`, `기준선을 통과` 같은 추상 표현이 반복된다.

### 다음 우선순위

1. `bullion_investment_v0_2.md`에 한국형 금거래소/금투자 카드뉴스 기준 추가.
2. `REFERENCE_JUDGE_RUBRIC.json`에 role coverage 기준 추가:
   - bullion identity
   - Korean event layout
   - consultation/CTA structure
   - premium finance trust
   - production usability
3. selected gate에서 `partial_reference`를 제한한다.
4. feedback phrase bank에 selected/shortlist/rejected별 구체 문장을 추가한다.
## 2026-06-03 Progress - cosmetics summer H&B sale event started

### 생성 이벤트

- Event folder: `events/summer-hb-beauty-sale-hsgn/`
- Event name: `여름 H&B 뷰티 세일 나이아신아마이드 집중 케어`
- Product: `cosmetic/hsgn_niacinamide`
- Intent: 한국 H&B 스토어 대형 여름 세일 감성. 단, 올리브영/올영 브랜드명, 로고, 행사명, 고유 색상 조합은 모방하지 않음.
- Key offer: 20% 할인, 선착순 미니 클렌저 증정, 2개 이상 무료배송.

### Run

- `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어/`

### 01_event_brief

- 최초 실행 후 skincare risk check에서 blocking 발생.
- 원인: 타깃이 인구통계 중심으로 읽힘.
- 수정: event-input target을 피부 고민, 구매 상황, 정보 탐색 채널 기준으로 재정의.
- 재생성 결과:
  - Category risk: clear.
  - Blocking: false.
  - Quality flags: none.
- 01 승인 완료.

### 02_content_planning

- 실행 완료.
- Deliverables: 5.
- Image needs: 5.
- Quality status: `approval_ready`.
- Current state: `02_content_planning` review_pending.

### 다음 우선순위

1. 02_content_planning 승인.
2. cosmetics_skincare reference search rule을 한국어/H&B 세일/스킨케어 프로모션 중심으로 보강.
3. 03_reference_research auto_search 실행.
4. cosmetics 판단 훈련 세션 생성 후 빠른 비교 리뷰.

## 2026-06-03 Progress - cosmetics Pinterest references 100 selected

### Rule updates

- Added `cosmetics_skincare` profile to event/reference/persona/visual-avoid rules.
- Search is now Korean-first for H&B sale, skincare sale banner, cosmetic card news, niacinamide serum promotion, whitening functional cosmetic card news, and cosmetic gift event references.
- Tightened `bullion_investment` detection to avoid false positives from single-character `금`, `은` and generic `상담`.

### Run

- `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어/`

### Current state

- `02_content_planning`: approved.
- `03_reference_research`: done.
- `run_state`: `reference_ready`.
- `current_stage`: `04_visual_candidates`.

### Reference result

- Mode: `auto_search`.
- Query count: 10.
- References: 100.
- Selected references: 100.
- Selected folder: `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어/references/selected/`.
- Notes: `03_reference_research/notes.md`.
- Console: `http://127.0.0.1:5177`.

### Next priority

1. Review whether the 100 selected references are Korean H&B sale enough.
2. Create a cosmetics judgement training session if the references need Kiwon correction before image generation.
3. Proceed to `04_visual_candidates` only after reference direction is acceptable.

## 2026-06-03 Progress - cosmetics judgement training session created

### Important note

- The console reference button was clicked once with small test values, so the latest reference manifest temporarily became 1 selected reference.
- Restored the run by regenerating `03_reference_research` with:
  - `REFERENCE_QUERY_LIMIT=8`
  - `REFERENCE_PER_QUERY_LIMIT=20`
  - `REFERENCE_SELECT_COUNT=100`

### Verification

- Selected reference files: 100.
- `03_reference_research/notes.md`: `Selected references: 100`.
- Console API `/api/training-sessions` shows the new cosmetics session.

### New script

- `scripts/create_reference_training_session.py`
- Purpose: create profile-based judgement training sessions from run-collected Pinterest/search references.

### New session

- `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_session_001/`
- Total: 100.
- AI first-pass decisions:
  - selected 41
  - shortlist 56
  - rejected 3
- Source run: `runs/2026-06-02_15-40-41_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`

### Next priority

1. In the console, open `판단 훈련`.
2. Select `cosmetics_skincare/pinterest_session_001`.
3. Use quick pair review to record Kiwon corrections.
4. Generate correction summary after all 100 are reviewed.

## 2026-06-03 Progress - cosmetics 100-review training test

### Review result

- Reviewed: 100/100.
- Baseline AI/Kiwon match: 15/100, 15.0%.
- AI selected match: 9/41, 22.0%.
- AI shortlist match: 5/56, 8.9%.
- AI rejected match: 1/3, 33.3%.

### Kiwon final distribution

- selected: 29.
- shortlist: 12.
- rejected: 59.

### Generated files

- `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_session_001/correction_summary.md`
- `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_session_001/learned_replay_test.md`

### Updated knowledge

- `design_brain_wiki/05_industry_playbooks/deep/cosmetics_skincare_v0_2.md`
- `design_brain_wiki/REFERENCE_JUDGE_RUBRIC.json`

### Interpretation

- Same-session memory replay passes because Kiwon decisions are stored.
- New-image generalization is not proven.
- Metadata/search-query scoring cannot separate Kiwon selected vs rejected well enough; future judgement needs stronger visual signals or more detailed Kiwon reason tags.

### Next priority

1. Collect a fresh cosmetics holdout session of 30-50 references.
2. Judge with updated cosmetics playbook/rubric.
3. Compare Kiwon review accuracy; target first milestone is 70-80%.

## 2026-06-03 Progress - query metadata removed from judgement evidence

### Changes

- Simplified cosmetics Pinterest search queries.
- `reference_pipeline.text_relevance_score` now ignores query/file/path evidence and uses Pinterest source metadata only:
  - alt
  - title
  - description
  - grid title
  - SEO title
- `create_reference_training_session.record_text` now excludes:
  - query
  - source_id
  - asset_id
  - path
  - relative_path
  - text_relevance_reason
- Judgement evidence now focuses on:
  - title/alt/description
  - Qwen review result if present
  - Kiwon feedback if present

### Extra bug fixed

- `_is_bullion_investment_context` used broad Korean tokens such as single-character `금`.
- This caused cosmetics text like `기능성` to pollute reference direction with bullion hints.
- Removed broad bullion tokens and made reference direction use the detected event profile.

### Holdout

- New run: `runs/2026-06-02_16-44-06_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- New session: `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_001/`
- Total: 47.
- First-pass decisions after evidence cleanup:
  - selected 0
  - shortlist 23
  - rejected 24

### Interpretation

- Query leakage is fixed.
- The judge is now conservative; this is better than over-selected, but it needs Kiwon holdout review to tune selected thresholds.

## 2026-06-03 Progress - holdout reviewed and low-res gate added

### Holdout result

- Session: `cosmetics_skincare/pinterest_holdout_001`
- Reviewed: 47/47.
- Accuracy after query/path evidence cleanup: 22/47, 46.8%.
- Previous baseline: 15.0%.

### Kiwon final distribution

- selected: 14.
- shortlist: 20.
- rejected: 13.

### AI first-pass distribution

- selected: 0.
- shortlist: 23.
- rejected: 24.

### Interpretation

- Removing query/path evidence improved accuracy substantially.
- The judge is now too conservative and misses selected references.
- Need to reopen selected gate based on Kiwon-selected patterns.

### Image quality issue

- Several low-resolution Pinterest thumbnails entered the selected pool, including 60x60 images.
- Added `reference_quality_defects()` in `scripts/reference_pipeline.py`.
- Future collection rejects width or height under 300px before brand/event judgement.

### Generated file

- `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_001/correction_summary.md`

### Next priority

1. Rerun fresh holdout after low-resolution gate.
2. Tune selected gate so strong product/event banner references can become selected.
3. Add quick review reason tags to collect more useful Kiwon feedback.

## 2026-06-03 Progress - holdout 002 ready

### Fixes

- Added event-layout evidence terms to cosmetics training judge:
  - `광고`, `배너`, `프로모션`, `사은품`, `이벤트 페이지`, `gift`, `banner`.
- Fixed low-resolution gate bug:
  - Dimension values were read through `numeric_score()`, which clamps at 100.
  - Added `numeric_value()` so width/height use real pixel values.

### New holdout run

- `runs/2026-06-02_16-59-22_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`

### Collection result

- Selected references: 36.
- Accepted/shortlist/rejected: 48/0/12.
- Low-res selected: 0.
- Low-res rejected: 11.

### New session

- `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_002/`
- Total: 36.
- AI first pass:
  - selected 2
  - shortlist 21
  - rejected 13

### Next priority

1. Review `cosmetics_skincare/pinterest_holdout_002` in the console.
2. Compare accuracy against holdout 001: 46.8%.
3. Tune selected gate again based on Kiwon decisions.

## 2026-06-03 Progress - holdout 002 reviewed, duplicate source controlled

### Holdout result

- Session: `cosmetics_skincare/pinterest_holdout_002`
- Reviewed: 36/36.
- Accuracy: 19/36, 52.8%.
- Previous holdout: 46.8%.

### Kiwon final distribution

- selected: 2.
- shortlist: 31.
- rejected: 3.

### AI first-pass distribution

- selected: 2.
- shortlist: 21.
- rejected: 13.

### Error pattern

- selected -> shortlist: 1.
- selected -> rejected: 1.
- shortlist -> shortlist: 19.
- shortlist -> rejected: 2.
- rejected -> shortlist: 11.
- rejected -> selected: 2.

### Interpretation

- Low-resolution gate worked: selected low-res stayed at 0 and low-res rejected was 11.
- The judge is still too strict: many AI rejected items should be shortlist.
- Website/homepage/browser capture images with visible URL/header are a real risk and should not be selected.

### Fixes

- Added website/browser screenshot, visible URL bar, address bar, homepage capture terms to cosmetics visual avoid rules.
- Added `--exclude-profile-history` to `scripts/create_reference_training_session.py` so future holdout sessions can skip images already used in prior sessions for the same profile.
- Duplicate audit:
  - same-run selected duplicates in holdout 002: 0 groups.
  - across `pinterest_session_001`, `pinterest_holdout_001`, `pinterest_holdout_002`: 35 duplicate groups, 81 duplicate items.
  - Cause is repeated collection against the same brief and similar Pinterest queries, not an in-run duplicate bug.

### Generated file

- `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_002/correction_summary.md`

### Next priority

1. Create the next cosmetics holdout with `--exclude-profile-history`.
2. Soften rejected -> shortlist gate without reopening low-quality or website capture images.
3. Add homepage capture/url-bar risk as a feedback phrase and rubric warning.

## 2026-06-03 Handoff - next cosmetics generalization test

### Current console

- Brand event console is running at `http://127.0.0.1:5177`.
- Current workstream is `cosmetics_skincare` reference judge training for the summer H&B beauty sale brief.
- Latest reviewed session: `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_002/`.

### What is fixed so far

- Pinterest/search query is no longer used as judgement evidence.
- Path, filename, source id, and asset id are no longer used as judgement evidence.
- Judge evidence now focuses on title/alt/description, Qwen vision result, and Kiwon feedback.
- Cosmetics search queries were simplified to local Korean banner/cardnews terms such as `스킨케어 이벤트 배너`, `화장품 이벤트 배너`, `뷰티 이벤트 배너`.
- `기능성` text no longer triggers `bullion_investment` through the single-character `금` keyword.
- Low-resolution references under 300px width or height are rejected before judgement.
- Homepage/browser screenshot and visible URL bar are now risk/reject signals for cosmetics references.
- Future holdout sessions can exclude prior session images with `--exclude-profile-history`.

### Latest numbers

- Original cosmetics session: 15.0% match.
- Holdout 001 after query/path evidence cleanup: 46.8% match.
- Holdout 002 after low-res gate and event-layout evidence: 52.8% match.
- Holdout 002 final Kiwon distribution:
  - selected 2
  - shortlist 31
  - rejected 3
- Holdout 002 main error:
  - AI is still too strict: rejected -> shortlist 11.

### Duplicate finding

- Same-run duplicates in holdout 002 selected set: 0.
- Cross-session duplicates across `pinterest_session_001`, `pinterest_holdout_001`, `pinterest_holdout_002`: 35 groups / 81 items.
- Interpretation: duplicates come from rerunning the same brief with similar Pinterest queries, not from an internal same-run duplicate bug.

### Next exact move

1. Create a new 30-50 image cosmetics holdout from a fresh reference run.
2. Generate its training session with `--exclude-profile-history`.
3. Review in the console.
4. After review, make a new `correction_summary.md`.
5. Tune only the strict rejected gate first:
   - hard reject: low-res, wrong category, website capture, URL bar, severe artifact.
   - otherwise prefer shortlist over rejected.

### Useful commands

```powershell
$env:REFERENCE_RESEARCH_MODE='auto_search'
python scripts\workflow.py --run runs\<new-run-id> --stage 03_reference_research --mode regenerate

python scripts\create_reference_training_session.py `
  --run runs\<new-run-id> `
  --profile cosmetics_skincare `
  --session pinterest_holdout_003 `
  --limit 50 `
  --require-pinterest `
  --exclude-profile-history
```
## 2026-06-03 Handoff - ComfyUI 제외 파이프라인 고도화

### 완료

- 판단 훈련 UI에 빠른 사유 태그 버튼을 추가했다.
  - 빠른 비교 판정과 상세 교정 폼 모두 `reasonTags`를 저장한다.
  - 태그는 저해상도, 웹페이지 캡처, 로컬감 부족, 상품 약함, 혜택 구조 좋음, 선택 가능, 해외 세일감, 가짜 텍스트, 레이아웃 좋음, 카테고리 오류 기준이다.
- `scripts/console_server.py`가 교정 저장 시 자동으로 아래 파일을 갱신한다.
  - `kiwon_review_summary.md`
  - `correction_summary.md`
  - `learned_rules.json`
- `scripts/summarize_reference_training_session.py`로 기존 `cosmetics_skincare` 세션 3개를 backfill했다.
- `services/visual_reference/qwen_reviewer.py`에 profile 기반 Qwen 비전 프롬프트를 추가했다.
- `scripts/create_reference_training_session.py`에 `--qwen-vision`, `--qwen-limit`, `--qwen-model`, `--qwen-host` 옵션을 추가했다.
  - cosmetics 기준 Qwen 필드: `local_hb_sale_fit`, `benefit_hierarchy`, `product_trust`, `layout_usability`, `website_capture_risk`, `text_artifact_risk`, `foreign_sale_risk`.
- `scripts/audit_visual_prompts.py`가 `cosmetics_skincare` profile을 분기 처리한다.
- 신규 hook/비교/QA 스크립트:
  - `scripts/audit_planning_quality.py`
  - `scripts/compare_reference_sessions.py`
  - `scripts/summarize_reference_training_session.py`
  - `scripts/project_hook_check.py`

### 검증

- `python scripts\project_hook_check.py --run runs\2026-06-02_16-59-22_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어` 통과.
- `python scripts\compare_reference_sessions.py --profile cosmetics_skincare` 실행 완료.
  - 기존 기준: session 001 15.0%, holdout 001 46.8%, holdout 002 52.8%.
- 콘솔 서버 `http://127.0.0.1:5177` 응답 200 확인.
- Chrome headless로 판단 훈련 화면 로드 확인.
  - JS 오류 0.
  - 사유 태그 DOM 20개 확인.

### 다음 정확한 작업

1. 새 reference run을 만들고 `pinterest_holdout_003` 세션 생성:

```powershell
python scripts\create_reference_training_session.py `
  --run runs\<new-run-id> `
  --profile cosmetics_skincare `
  --session-id pinterest_holdout_003 `
  --limit 50 `
  --exclude-profile-history `
  --qwen-vision
```

2. Qwen/Ollama가 꺼져 있거나 느리면 `--qwen-vision` 없이 세션을 만들고, UI 태그 기반 검수부터 진행한다.
3. 검수 후:

```powershell
python scripts\summarize_reference_training_session.py --profile cosmetics_skincare --session-id pinterest_holdout_003
python scripts\compare_reference_sessions.py --profile cosmetics_skincare
python scripts\project_hook_check.py --run runs\<new-run-id>
```
## 2026-06-03 Next Work Handoff - cosmetics holdout 003

### 지금 이어서 할 일

다음 작업은 `cosmetics_skincare` reference judge의 generalization 확인이다.  
ComfyUI 생성은 아직 하지 말고, Qwen/로컬 judge와 기원님 검수 데이터로 레퍼런스 판단 정확도를 먼저 올린다.

### 현재 완료된 기반

- 판단 훈련 UI에 사유 태그 저장이 붙어 있다.
- 교정 저장 시 `correction_summary.md`, `learned_rules.json`, `kiwon_review_summary.md`가 자동 갱신된다.
- 기존 cosmetics 세션은 backfill 완료:
  - `pinterest_session_001`: 15.0%
  - `pinterest_holdout_001`: 46.8%
  - `pinterest_holdout_002`: 52.8%
- `--exclude-profile-history`로 기존 세션 이미지 중복을 피할 수 있다.
- `--qwen-vision`으로 Qwen/Ollama 비전 평가를 세션 생성 단계에 붙일 수 있다.

### 다음 권장 순서

1. 새 reference run을 만든다.
2. `pinterest_holdout_003` 세션을 만든다.
3. 콘솔 판단 훈련에서 빠른 비교 + 사유 태그로 검수한다.
4. summary/backfill을 실행한다.
5. session comparison으로 holdout 001/002/003 정확도를 비교한다.
6. 반복 패턴만 cosmetics playbook/rubric에 반영한다.

### 세션 생성 명령

Qwen/Ollama가 켜져 있으면:

```powershell
python scripts\create_reference_training_session.py `
  --run runs\<new-run-id> `
  --profile cosmetics_skincare `
  --session-id pinterest_holdout_003 `
  --limit 50 `
  --exclude-profile-history `
  --qwen-vision
```

Qwen/Ollama가 꺼져 있거나 느리면:

```powershell
python scripts\create_reference_training_session.py `
  --run runs\<new-run-id> `
  --profile cosmetics_skincare `
  --session-id pinterest_holdout_003 `
  --limit 50 `
  --exclude-profile-history
```

### 검수 후 실행

```powershell
python scripts\summarize_reference_training_session.py --profile cosmetics_skincare --session-id pinterest_holdout_003
python scripts\compare_reference_sessions.py --profile cosmetics_skincare
python scripts\project_hook_check.py --run runs\<new-run-id>
```

### 판단 기준 메모

- hard reject:
  - 저해상도
  - 웹페이지/브라우저 캡처
  - URL/주소창 노출
  - 카테고리 오류
  - 심한 fake text / broken Korean text
- hard reject가 아니고 부분 참고 가치가 있으면 rejected보다 shortlist를 우선한다.
- selected는 제품 신뢰, 한국 H&B 세일감, 혜택 위계, 제작 가능한 레이아웃이 함께 있어야 한다.

## 2026-06-03 Work Result - cosmetics holdout 003 created

### 완료

- 새 reference run 생성:
  - `runs/2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어`
- 01_event_brief, 02_content_planning 생성 및 승인 완료.
- `REFERENCE_RESEARCH_MODE=auto_search`로 03_reference_research 재생성 완료.
- 03 결과:
  - profile: `cosmetics_skincare`
  - selected references: 20
  - accepted/shortlist/rejected: 79/0/14
  - clear reject reason: 14
  - selected bad signal: 0
- Qwen/Ollama는 `http://127.0.0.1:11434`에 연결되지 않아 `--qwen-vision` 없이 진행.
- 새 세션 생성:
  - `design_brain_wiki/training_sessions/cosmetics_skincare/pinterest_holdout_003/`
  - total: 31
  - AI first pass: selected 2 / shortlist 17 / rejected 12
  - reviewed: 0
- 검증:
  - 콘솔 `http://127.0.0.1:5177` 응답 200.
  - `scripts/project_hook_check.py --run runs\2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어` 통과.
  - `scripts/compare_reference_sessions.py --profile cosmetics_skincare` 실행 결과 holdout 003이 reviewed 0으로 비교 목록에 등록됨.

### 다음 정확한 작업

1. 콘솔 판단 훈련에서 `cosmetics_skincare/pinterest_holdout_003`을 검수한다.
2. 검수 기준:
   - hard reject: 저해상도, 웹페이지/브라우저 캡처, URL/주소창 노출, 카테고리 오류, 심한 fake text/broken Korean text.
   - hard reject가 아니고 부분 참고 가치가 있으면 rejected보다 shortlist.
   - selected는 제품 신뢰, 한국 H&B 세일감, 혜택 위계, 제작 가능한 레이아웃이 함께 있어야 함.
3. 검수 후 실행:

```powershell
.venv\Scripts\python.exe scripts\summarize_reference_training_session.py --profile cosmetics_skincare --session-id pinterest_holdout_003
.venv\Scripts\python.exe scripts\compare_reference_sessions.py --profile cosmetics_skincare
.venv\Scripts\python.exe scripts\project_hook_check.py --run runs\2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어
```

4. holdout 003의 반복 오차만 cosmetics playbook/rubric에 반영한다.

## 2026-06-03 Work Result - Reference Judge gate 보정

### 확인

- `cosmetics_skincare/pinterest_holdout_003`은 아직 기원님 검수가 저장되지 않았다.
  - `kiwon_review_state.json` 없음.
  - reviewed 0/31.
- summary/compare는 실행했다.
  - summary: `correction_summary.md`, `learned_rules.json`, `kiwon_review_summary.md` 생성.
  - compare: holdout 003을 `pending_review`로 표시하도록 수정.
- Qwen/Ollama는 현재 연결되지 않는다.
  - `http://127.0.0.1:11434/api/tags` 실패.
  - `ollama` 명령과 프로세스 없음.

### 코드 변경

- `scripts/create_reference_training_session.py`
  - cosmetics rejected gate를 hard reject 중심으로 완화.
  - 저해상도, 웹페이지/브라우저 캡처, 업종 오류, AI artifact, Qwen hard risk만 rejected로 강하게 보냄.
  - weak copy space와 부족한 metadata는 shortlist로 남김.
- `scripts/compare_reference_sessions.py`
  - 미검수 세션 accuracy를 `null`로 두고 markdown에서는 `pending`으로 표시.

### 검증

```powershell
.venv\Scripts\python.exe -m py_compile scripts\create_reference_training_session.py scripts\compare_reference_sessions.py
.venv\Scripts\python.exe scripts\compare_reference_sessions.py --profile cosmetics_skincare
```

- 003 source pool 기준 완화 gate 예상 분포:
  - selected 3
  - shortlist 72
  - rejected 18
  - rejected 주요 사유: low resolution 14, website capture 2, wrong category 1.

### 다음 정확한 작업

1. 기원님이 콘솔에서 `cosmetics_skincare/pinterest_holdout_003`을 검수한다.
2. 검수 후 실행:

```powershell
.venv\Scripts\python.exe scripts\summarize_reference_training_session.py --profile cosmetics_skincare --session-id pinterest_holdout_003
.venv\Scripts\python.exe scripts\compare_reference_sessions.py --profile cosmetics_skincare
```

3. Qwen/Ollama를 켠 뒤 연결 확인:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing
```

4. 연결 확인 후에만 `pinterest_holdout_004`를 `--qwen-vision`으로 생성한다.
## 2026-06-03 Handoff - QA Packaging evidence manifest

### 완료

- `pipeline/06_qa_packaging/handlers/run_qa_packaging.py`에 품질 근거 manifest 수집을 추가했다.
- 06이 아래 파일을 확인한다.
  - `planning-quality/planning-quality-audit.json`
  - `03_reference_research/reference-quality-report.json`
  - `03_visual_candidates/prompt-audit.json`
  - `03_visual_candidates/generation-quality.json`
  - `04_admin_selection/selected-assets.json`
- `qa-report.json`에는 `qualityArtifacts`와 summary count가 들어간다.
- `final-package-manifest.json`의 각 파일 레코드에는 `qualityEvidence.artifacts`와 `qualityEvidence.selection`이 들어간다.
- `qa-packaging.json`에도 `quality_artifacts`가 들어간다.
- 누락/실패한 근거는 QA issue로 기록하고 `suggested_fix_stage`를 품질 근거의 원래 단계로 지정한다.

### 검증

- `python -m py_compile pipeline/06_qa_packaging/handlers/run_qa_packaging.py` 통과.
- `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`에 06 핸들러 직접 실행.
- 같은 run으로 07_asset_archive 핸들러 입력 검증 통과. QA status가 warning이라 archive asset은 0개로 필터링됨.
- `python scripts/project_hook_check.py --run runs/2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트` 통과.

### 다음 작업

1. 콘솔 QA/패키지 화면에 `qualityArtifacts` 상태를 표시한다.
2. 선택 후보 카드에서 `qualityEvidence.selection`, reference report, prompt audit, generation quality 요약을 펼쳐볼 수 있게 만든다.
3. live 이미지 생성 이후에는 selected candidate만 generation fail인지 전체 후보 fail인지 구분하는 세부 gate를 추가한다.

## 2026-06-04 Handoff - QA Evidence console + selected candidate QA

### 완료

- `pipeline/06_qa_packaging/handlers/run_qa_packaging.py`
  - `prompt_audit`, `generation_quality` 상태를 선택된 candidate 기준으로 우선 판정하도록 변경.
  - 선택 후보가 있으면 전체 후보 실패 수보다 선택 후보의 prompt/generation 상태를 우선한다.
  - `qualityEvidence.artifacts[]`에 각 artifact의 summary를 포함한다.
  - 선택 후보 `generation_status=generated`이면 generation evidence pass, `placeholder/prompt_only`이면 warning, `failed/error`이면 fail/error로 처리한다.
- `scripts/console_server.py`
  - `/api/runs/<run-id>` 응답에 `qa_report`, `final_package_manifest`, `qa_packaging`을 추가했다.
- `ui/console/app.js`, `ui/console/styles.css`
  - 최종 패키지 화면에 QA Evidence 패널 추가.
  - `qualityArtifacts` 5종 상태와 요약 표시.
  - 선택 후보 카드에 `qualityEvidence` 칩 표시.

### 검증

- `2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`에서 06 핸들러 직접 실행.
  - 전체 generation failed count는 12지만 선택 후보 1개가 generated라 `generation_quality`가 pass로 판정됨.
  - 남은 issue는 `reference-quality-report` warning과 `prompt-audit.json` missing warning 2개.
- 콘솔 API 확인:
  - `qa_report.qualityArtifacts` 5개 반환.
  - `final_package_manifest` 1개 반환.
  - 첫 manifest record에 `qualityEvidence` 존재.
- 07 핸들러 직접 실행 통과.
  - QA status warning 상태라 archive asset은 0개로 필터링됨.
- `python -m py_compile pipeline/06_qa_packaging/handlers/run_qa_packaging.py scripts/console_server.py` 통과.
- `node --check ui/console/app.js` 통과.
- `python scripts/project_hook_check.py --run runs/2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트` 통과.

### 주의

- Chrome headless 원격 디버깅 포트 방식은 유지되지 않았지만, `?view=package&run=<run-id>` 직접 진입을 추가해 `--dump-dom` 방식으로 패키지 화면 DOM 검증은 완료했다.
- DOM 검증 파일: `.tmp/qa-console-package-dom.html`.
- 확인 문자열: `QA Evidence`, `quality-artifact`, `candidate-evidence`, `생성 QA`, `QA 이슈`.

### 다음 작업

1. 07_asset_archive가 `qualityEvidence`를 asset record에 반영하도록 확장한다.
2. QA warning 자산은 archive reuse score를 낮추거나 `limited_reuse`로 분류하는 정책을 추가한다.
## 2026-06-03 Handoff - Console UI review acceleration

### 완료

- 판단 훈련 세션 목록/선택 옵션에 reviewed, accuracy, AI decision distribution, Kiwon final distribution을 함께 표시한다.
- 판단 훈련 상단 summary에 다음 지표를 추가했다:
  - reviewed / total
  - accuracy
  - AI selected/shortlist/rejected
  - final selected/shortlist/rejected
  - over-selected / over-rejected
  - transition counts
  - reason tag counts
- quick compare card, reference item list, detail preview에 AI decision, Kiwon final decision, transition을 표시한다.
- 주요 오차 자동 하이라이트:
  - `rejected->shortlist`
  - `rejected->selected`
  - `selected->rejected`
- hard reject 태그 강조:
  - `low_resolution`
  - `website_capture`
  - `fake_text_risk`
  - `wrong_category`
- 검수 폼에서 `summary 생성`, `compare 생성` 버튼을 바로 실행할 수 있다.
- 추가 API:
  - `POST /api/training-sessions/<profile>/<session_id>/summary`
  - `POST /api/training-sessions/<profile>/compare`
- `list_training_sessions()`에서 `ai_judgement.json`이 없는 `_comparisons` 보조 폴더는 제외한다.
- `training_session_detail()`은 stale `kiwon_review_state.summary` 대신 현재 reviews 기준으로 summary를 재계산한다.
- 콘솔 서버는 `http://127.0.0.1:5177`로 재시작 완료.

### 검증

- `python -m py_compile scripts/console_server.py scripts/summarize_reference_training_session.py scripts/compare_reference_sessions.py` 통과.
- `node --check ui/console/app.js` 통과.
- `python scripts\project_hook_check.py` 통과.
- 브라우저 스냅샷에서:
  - `Final S 5 / H 0 / R 25`처럼 final distribution 표시 확인.
  - `_comparisons`가 세션 목록에서 제외된 것 확인.
  - `summary 생성` 버튼 표시 확인.
  - JS error 0.

### 다음 작업

1. Console `판단 훈련`에서 `cosmetics_skincare/pinterest_holdout_003` 검수.
2. 검수 완료 후 UI의 `summary 생성`, `compare 생성` 버튼 실행.
3. reason tag 통계와 주요 transition을 보고 cosmetics playbook/rubric에 반복 패턴만 반영.
## 2026-06-04 Handoff - Console UX redesign pass 1

### 완료

- 사용자가 제공한 Figma 스타일 방향을 기반으로 콘솔 UX 방향을 정리했다.
- 새 문서:
  - `knowledge/CONSOLE_UX_REDESIGN.md`
- UI 톤 변경:
  - 기존 dark/blue AI dashboard 느낌 제거.
  - light canvas, black ink, pastel color-block, pill CTA, hairline border 중심으로 변경.
  - Workboard는 lavender/cream color block으로 작업 큐와 운영 상태를 분리.
- 메뉴/페이지 언어 변경:
  - Workboard
  - New Event
  - Pipeline
  - References
  - Review Training
  - Prompt Sheet
  - Image Selection
  - Package
  - Settings
- Dashboard를 Workboard로 재설계:
  - Active runs
  - Ready for action
  - Review sessions
  - Generated images
  - Work that needs a decision
  - Queue health
  - Production history
- Workboard에서 generic progress block은 숨김 처리했다.
  - Pipeline 화면에서만 run progress가 보이도록 정리.

### 수정 파일

- `knowledge/CONSOLE_UX_REDESIGN.md`
- `ui/console/styles.css`
- `ui/console/app.js`
- `knowledge/00_DASHBOARD.md`
- `knowledge/09_HANDOFF.md`

### 검증

- `node --check ui/console/app.js` 통과.
- `python scripts\project_hook_check.py` 통과.
- 브라우저 확인:
  - `Workboard` h1 표시.
  - 사이드바 업무형 라벨 표시.
  - Workboard에 `Work that needs a decision` 표시.
  - Workboard에서 `작업 선택 필요` progress block 미표시.
  - body background `rgb(251, 250, 247)`.
  - JS error 0.

### 다음 작업 제안

1. Reference / Review Training / Image Selection 화면도 Workboard와 같은 visual grammar로 섹션 구조 재배치.
2. 남아 있는 깨진/AI스러운 문구를 업무 언어로 정리.
3. Review Training 화면에 필터 바를 추가해 `unreviewed`, `major error`, `hard reject`, `selected`, `shortlist`, `rejected` 기준으로 바로 볼 수 있게 만들기.
## 2026-06-04 Handoff - Handhold-inspired homepage direction

### 완료

- 사용자가 지정한 `https://handhold.io/` 홈페이지를 레퍼런스로 확인했다.
- Console Workboard 첫 화면을 Handhold 스타일에 맞춰 다시 조정했다.
- 반영한 특징:
  - 상단 horizontal nav 구조.
  - 흰/오프화이트 canvas.
  - 대형 serif headline.
  - 중앙 정렬 hero.
  - black pill primary CTA.
  - 얇은 announcement strip.
  - 파란/노란 blurred ribbon visual.
- Workboard 상단의 중복 `Workboard` title bar는 dashboard에서 숨김 처리했다.
- nav가 한 줄로 유지되도록 조정하고 `Workboard` active item 잘림 문제를 수정했다.

### 검증

- `node --check ui/console/app.js` 통과.
- `python scripts\project_hook_check.py` 통과.
- 브라우저 확인:
  - `body[data-view="dashboard"]`.
  - dashboard topbar hidden.
  - hero text `A dedicated review desk for every campaign` 표시.
  - nav nowrap.
  - hero ribbon 존재.
  - JS error 0.
## 2026-06-07 Handoff - Meta Ad Reference MVP 1차

### 완료

- `Ad Reference` 콘솔 탭을 추가했다.
- Meta Ad Library Playwright 수집기와 CLI를 추가했다.
- 수집 결과는 `references/meta_ads/searches/<검색-id>/collected-ads.json`과 `captures/`에 저장된다.
- 선택형 `--qwen` 태깅을 지원한다.
- 콘솔에서 수집 작업 실행, 수집 횟수/광고 수 확인, 카드 캡처/카피/CTA/태그 확인이 가능하다.
- 실수집에서 페이지 전체가 카드로 잡히는 selector 문제를 발견해, Library ID가 정확히 하나인 카드 크기 요소만 캡처하도록 수정했다.

### 검증

- `.venv\Scripts\python.exe -m py_compile services\ad_reference\meta_collector.py scripts\collect_meta_ads.py scripts\console_server.py`
- `node --check ui\console\app.js`
- `.venv\Scripts\python.exe scripts\project_hook_check.py`
- 실수집: `anua skincare`, KR, 카드 2개.
- 콘솔 `http://127.0.0.1:5177/?view=ad-reference`에서 탭과 카드 렌더링 확인.

### 다음 작업

1. 광고 카드별 selected/shortlist/rejected 저장.
2. 선택 광고를 `reference-evidence.json`으로 변환.
3. OpenCLIP 랭킹 연결.
4. 01/02/03 입력 연결.

## 2026-06-07 Handoff - Meta 원본 이미지 다운로드와 pipeline 연결

### 변경

- `services/ad_reference/meta_collector.py`
  - 광고 카드 내부 실제 이미지 URL 추출 및 다운로드.
  - 프로필 이미지/아이콘 제외.
  - 광고당 최대 10개 이미지 제한.
- `scripts/collect_meta_ads.py`
  - `--run` 옵션 추가.
  - 다운로드 이미지를 run의 selected reference와 manifest로 등록.
- 콘솔
  - 원본 이미지를 카드 미리보기로 표시.
  - `현재 작업 레퍼런스로 연결` 옵션 추가.

### 검증

- `anua skincare`, KR, 광고 2개에서 원본 이미지 20개 다운로드.
- 임시 run import 결과: manifest assets 20, selected files 20.
- `03_reference_research` 직접 실행 결과: reference count 20, selected 20.

## 2026-06-07 Handoff - 기존 브리프 Meta 수집 테스트

- 최신 H&B 나이아신아마이드 브리프 run에 Meta 이미지 21개를 연결했다.
- 쿼리별 결과:
  - 메디큐브: 7개
  - 나이아신아마이드 세럼: 7개
  - 스킨케어 세일: 7개
- 03_reference_research 재실행 후 reference/selected 41개 인식.
- 비교용 contact sheet: `references/meta_ads/meta-brief-test-contact-sheet.jpg`.
- 다음 개선은 Meta import 자산을 즉시 selected로 넣지 않고 Reference Judge를 거쳐 shortlist/selected로 분리하는 것이다.

## 2026-06-07 Handoff - Meta clean product visual filter test

- Ollama/Qwen2.5VL을 실제 실행해 광고 성격 판정을 검증했다.
- 광고 단위 첫 이미지 판정에서 이미지별 판정으로 변경했다.
- 추가 필드: `category_fit`, `visible_cosmetic_container`, `package_box_only`, `card_news_style`, `large_headline_or_dense_copy`, `screen_capture_risk`.
- Qwen은 샤넬 제품 사진을 올바르게 판정했지만 일부 카드뉴스를 clean product visual로 오판했다.
- 따라서 strict gate에 낮은 text density 조건을 유지했다.
- 잘못 연결된 앱 화면과 박스-only 테스트 자산은 run manifest/selected 폴더에서 제거했다.
- 다음 우선순위: Qwen + OpenCLIP + 기존 Reference Judge 결합 후 selected, 그 전에는 filtered 결과를 shortlist로 다루는 것이 안전하다.

## 2026-06-07 Handoff - zip UI 통합

### 변경
- `자동화 프로젝트.zip`에 포함된 LoopStudio 콘솔 UI를 기준으로 `ui/console/index.html`과 `ui/console/styles.css`를 재구성했다.
- 기존 API 및 `ui/console/app.js`가 사용하는 DOM ID는 유지했다.
- 작업 현황, 레퍼런스 검수, 판단 훈련, 이미지 선택 메뉴 전환을 브라우저에서 확인했다.

### 검증
- `node --check ui/console/app.js`
- `python -m py_compile scripts/console_server.py`
- `python scripts/project_hook_check.py`
- `http://127.0.0.1:5177` 응답 200, 브라우저 오류 0
- 모바일 폭 390px 기준 가로 넘침 없음

## 2026-06-07 Handoff - 광고 레퍼런스 요약/상세 모달

- 광고 카드에서 Meta 원문 전체 노출을 없애고 정리된 3줄 요약만 표시한다.
- `자세히 보기` 모달에 수집 원문, 랜딩 링크, 광고 라이브러리 링크를 배치했다.
- 동일 Library ID 중복 광고는 한 번만 표시한다.
- `신규/지속/장기 집행` 배지는 집행 기간 기반 보조 신호이며 실제 광고 성과 지표가 아니다.

## 2026-06-07 Handoff - 신규 zip UI 재적용

- 갱신된 zip에 추가된 `screens-f.jsx`의 활동 로그 방향을 현재 vanilla 콘솔에 이식했다.
- 활동 로그는 현재 bootstrap의 run/job 기록을 합쳐 작업/실행/오류 필터와 요약을 제공한다.
- 오류 run 상세 화면에 복구 안내 패널을 추가했다.
- 검증: `node --check ui/console/app.js`, `python scripts/project_hook_check.py`, 브라우저 메뉴/필터/광고 상세 기능 오류 0.

## 2026-06-07 Handoff - Vercel 배포

- 프로덕션 URL: `https://loopstudio-console.vercel.app`
- `api/index.py`가 기존 Python 콘솔 GET API를 Vercel Function으로 제공한다.
- Vercel Function은 읽기 전용이며 POST 요청은 로컬 콘솔 전용 안내와 함께 503을 반환한다.
- `vercel.json`, `.vercelignore`로 UI와 필요한 데이터만 배포하도록 구성했다.

## 2026-06-08 Handoff - Console UI 컨텍스트 클리어 전 정리

- 콘솔 UI 전용 인수인계 문서를 `knowledge/CONSOLE_UI_HANDOFF.md`에 작성했다.
- 로컬 콘솔을 실제 운영 기준으로 사용하며 Vercel은 조회 전용으로 유지한다.
- 다음 우선순위는 광고 레퍼런스 selected/shortlist/rejected 저장과 Reference Judge 연결이다.
- 콘솔 관련 파일은 Git 기준 미추적 상태이므로 다음 작업자가 삭제하거나 초기화하지 않도록 주의한다.

## 2026-06-08 Handoff - Console UI 용어와 이미지 표시 정리

- 깨진 사이드바/검색 장식 아이콘을 제거했다.
- 혼동되던 메뉴를 역할 기준으로 정리했다.
  - `작업 레퍼런스`: 현재 run 후보 확인과 수집·검수.
  - `Meta 광고 수집`: Meta 광고 라이브러리 신규 수집과 run 연결.
  - `판단 훈련`: AI 판단과 사람 최종 판단 교정.
- 레퍼런스 카드 이미지는 잘리지 않도록 `contain`으로 표시한다.
- 작업 레퍼런스와 Meta 광고 카드 이미지를 클릭하면 원본 보기 모달이 열린다.

## 2026-06-08 Handoff - Pinterest + Meta 혼합 판단 훈련

- `scripts/create_reference_training_session.py`가 `--session-type mixed_reference`를 지원한다.
- 혼합 세션은 run의 Pinterest/search 후보와 Meta 광고 연결 이미지를 합치고 중복 제거 후 출처 균형을 맞춘다.
- 콘솔 API: `POST /api/runs/<run-id>/training-sessions/mixed`.
- Meta 광고 수집 화면의 `Pinterest + Meta 판단 훈련 만들기` 버튼에서 생성한다.
- 생성 완료 후 새로고침하면 판단 훈련 세션 목록에 `mixed_reference`로 표시된다.

## 2026-06-08 Handoff - Reference Learning 1000

- 기준 문서: `knowledge/REFERENCE_LEARNING_1000.md`.
- 전용 수집기: `scripts/collect_reference_learning_1000.py`.
- 마스터 인덱스 생성기: `scripts/build_reference_learning_dataset.py`.
- 검수 배치 생성기: `scripts/create_reference_learning_batches.py`.
- 현재 검수 가능한 고유 이미지 1,219장으로 목표 1,000장을 달성했다.
- 새 미검수 큐 1,021장을 `reference_learning/learning_batch_001`부터 `learning_batch_021`까지 생성했다.
- 정확 중복 804개와 근접 중복 49개는 검수 큐에서 제외한다.
- 콘솔 판단 훈련 상단에 전체 학습 현황과 `다음 미검수 배치 열기` 버튼이 표시된다.
- 중요한 주의: 사용자 검수가 시작된 뒤 `scripts/create_reference_learning_batches.py --force`를 실행하면 해당 배치의 리뷰 상태가 삭제될 수 있으므로 사용하지 않는다.

## 2026-06-08 Handoff - 레퍼런스 품질 기준과 전체 검수

- 콘솔 판단 훈련은 `reference_learning/all` 가상 세션으로 모든 기존 배치를 연결한다.
- UI는 `미완료 / 자동 제외 / 완료`로 분리하며 50장 배치 선택을 요구하지 않는다.
- Meta `/captures/` 페이지 캡처는 `website_capture`, 짧은 변 500px 미만 이미지는 `low_resolution` 자동 제외 대상이다.
- 현재 실제 소재 후보 945장, 자동 제외 사례 274장이다.
- 기존 배치 디렉터리와 `kiwon_review_state.json` 리뷰는 보존한다.
## 2026-06-10 Handoff - 레퍼런스 학습 브리프 재정리

- 문제: Reference Learning 1000이 수량을 먼저 채우며 다른 업종, 로컬 이미지, 샘플, 해외 Meta 광고까지 섞였다.
- 해결:
  - `assets/rules/reference-learning-brief.json`에 현재 H&B 나이아신아마이드 브리프 게이트 추가.
  - `scripts/build_reference_learning_dataset.py`가 업종, 허용 출처, 해외 Meta, 해상도, 비율, 웹 캡처, 명백한 다른 카테고리를 제외하도록 변경.
  - 콘솔 전체 학습 화면은 현재 dataset에서 `eligible=true`인 항목만 노출.
  - 기존 사람 검수 파일은 삭제하지 않음.
- 결과: 기존 검수 가능 1,219개에서 브리프 적합 후보 117개로 축소.
- 정보가 빽빽한 카드뉴스·인포그래픽과 치과 등 Meta 검색 오염도 기본 제외한다.
- 상세 기준: `knowledge/REFERENCE_LEARNING_BRIEF.md`

## 2026-06-10 Handoff - Meta 검증 브랜드 레지스트리

- `assets/rules/meta-brand-registry.json`: cosmetics_skincare 20개, jewelry_luxury 20개.
- `services/ad_reference/brand_registry.py`: 브랜드 목록, 광고주명 별칭 일치 helper.
- `scripts/collect_meta_brand_registry.py`: 브랜드별 Meta 수집, 엄격 광고주 일치, 이미지 품질 검사, 배치 manifest.
- 저장 위치: `references/meta_ads/brand_registry_runs/<batch>/brands/<brand>/`.
- 콘솔 `Meta 광고 수집` 화면에 `검증 브랜드 묶음 수집` 컨트롤 추가.
- 실제 테스트:
  - Medicube: raw 3 / advertiser match 1 / images 7.
  - Cartier: raw 3 / advertiser match 2 / accepted ads 1 / image 1.
- 다음 우선순위: 브랜드 결과를 Qwen/OpenCLIP로 역할 분류한 뒤 브리프가 요구한 역할만 shortlist로 연결.
# 2026-06-13 품질/구조 점검

- `scripts/workflow.py`: QA가 warning 계열이면 승인 메모가 없을 때 승인을 차단한다.
- `07_asset_archive`: 자산 0개 완료를 `done_no_assets` / `archived_no_assets`로 구분한다.
- `scripts/run_project_tests.py`: 분산된 27개 테스트를 한 번에 실행한다.
- `scripts/project_hook_check.py`: 실행 중인 Python 인터프리터를 사용하며 공통 테스트를 포함한다.
- `ui/console/app.js`: 마지막 선언에 가려지던 중복 함수 13개를 제거했다. 브라우저에서 대시보드/판단 훈련 전환과 오류 없음 확인.
- 제품 고정 합성/한글 오버레이 실제 검수 결과는 `knowledge/QUALITY_VALIDATION_2026-06-13.md` 참고.
- OpenCLIP 5-fold holdout은 ROC AUC 0.9328, top-10 precision 0.80으로 효과 확인. 자동 selected가 아니라 shortlist 우선순위에 사용한다.
- 다음 품질 작업: 제품 alpha bounding box 기반 scale, 오버레이 대비/줄바꿈/비율 배지 개선.
# 2026-06-14 제품 합성/한글 오버레이 후속 개선

- `ProductLockedAdComposite`가 alpha 실제 제품 경계를 crop한 뒤 `product_scale`을 적용하도록 실제 ComfyUI 커스텀 노드를 수정했다.
- `korean_poster_overlay_1024` 기본값에서 비율 배지를 제거하고 밝은 배경용 진한 글자와 굵은 제목 폰트를 사용한다.
- 제목 영역을 넓혀 한글 제목의 어색한 줄바꿈을 줄였다.
- 전체 테스트 30개 및 project hook 통과.
- 개선 출력은 `.tmp/comfy-quality-validation/`에 있으며, ComfyUI 커스텀 노드 변경은 서비스 재시작 이후 live 요청에 반영된다.
# 2026-06-14 Handoff - 6월 이벤트 이미지 외 E2E 품질 테스트

## 실행

- 이벤트: `events/june-monsoon-barrier-care`
- run: `runs/2026-06-14_11-39-28_6월-장마철-수분-장벽-리셋-위크`
- 01/02 승인, 03/04 완료, 현재 `05_admin_selection`.
- ComfyUI live는 사용하지 않았고 12개 placeholder 후보만 생성했다.

## 발견 및 개선

- 최초 01/02는 입력 문장 반복과 범용 채널 역할 중심이라 실제 전략 품질이 낮았으나 planning audit가 `pass` 처리했다.
- `generate_brief.py`: 핵심 메시지를 공감/제안/제품/전환/원칙 구조로 변경.
- `generate_content_plan.py`: 채널별 목적과 카드뉴스 장별 `message_intent` 추가.
- `audit_planning_quality.py`: 낮은 전략 가공, 범용 채널 역할, 장별 메시지 누락, 반복 전략 논지 경고 추가.
- `run_reference_research.py`: 브랜드 mood/color/event references가 일반 cosmetics profile보다 우선하도록 변경.
- 회귀 테스트 `tests/test_planning_strategy_quality.py` 4개 통과.

## 현재 판정

- 기획 골격: 최초 C급 수준에서 B급 실무 초안 수준으로 개선.
- planning audit: `pass`.
- reference quality: `warning` — 선택 레퍼런스가 good seed 유사도와 카테고리 커버리지가 약함.
- prompt audit: 12/12 `warning` — 고정 H&B sale 요구와 `broken korean text` negative 누락.
- product_id `cosmetic/cleanderma_ceramide_ampoule`는 제품 라이브러리에 실제 자산이 없어 prompt product source가 비어 있음.
- 공통 project hook은 로직 문제가 아니라 현재 Python 환경의 `playwright` 미설치로 실패.

## 다음 우선순위

1. 레퍼런스 warning gate를 해소하거나 warning 상태에서 04 자동 진행을 막는다.
2. prompt audit 기준을 이벤트별 비주얼 방향에 맞게 바꾼다.
3. 제품 라이브러리 미등록 입력을 01 승인 전에 경고한다.
# 2026-06-14 Handoff - Meta 광고 기획 학습 MVP

## 구현

- `services/ad_strategy/library.py`
  - Meta 광고 카피 정리, 패턴 추상화, 중복 제거, 유사 패턴 검색, 현재 이벤트용 재작성.
- `scripts/build_meta_ad_strategy_library.py`
  - 기존 수집물 전체를 광고 전략 JSON 라이브러리로 변환.
- `design_brain_wiki/ad_strategy/meta-ad-strategy-library.json`
  - 현재 46개 패턴.
- 01 `strategy_inspiration`
  - 유사 패턴 5개와 `adaptedConcepts`를 포함.
- 02 deliverable
  - 채널별 `copy_intent`, `copy_blueprint` 포함.

## 검증

- 테스트 run: `runs/2026-06-14_11-39-28_6월-장마철-수분-장벽-리셋-위크`
- 카드뉴스 훅:
  - `장마철에는 번들거리지만 냉방 공간에서는 속당김과 민감함을 느낄 때, 지금 루틴은 괜찮을까요?`
- 블루프린트:
  - 질문 훅 -> 문제 상황 -> 믿을 이유 -> 루틴 -> 혜택 -> CTA
- planning audit `pass`.
- `tests.test_planning_strategy_quality` 포함 관련 테스트 16개 통과.

## 다음 우선순위

1. 신규 Meta 수집 job 종료 시 `build_meta_ad_strategy_library.py` 자동 실행.
2. 광고 전략 패턴 검수 세션 추가: selected / shortlist / rejected.
3. 사람이 선택한 패턴만 01/02 검색 우선순위에 반영.
# 2026-06-14 Handoff - 실사용급 광고 기획·카피 엔진 1차

## 구현

- 전략/교정 스키마:
  - `core/schemas/ad-strategy-example.schema.json`
  - `core/schemas/copy-correction-record.schema.json`
- 검수 전략 저장소와 교정 기록:
  - `services/ad_strategy/repository.py`
- 전략 브리프, 3개 콘셉트, 완성 카피, planning QA:
  - `services/ad_strategy/planning_engine.py`
- 01 산출물: `strategic-brief.json`
- 02 산출물: `concept-candidates.json`, `concept-review.json`, `selected-concept.json`, `copy-package.json`, `copy-review.json`, `planning-scorecard.json`
- 02 단계 승인은 콘셉트와 최종 카피 승인, 치명 오류 0을 강제한다.
- 콘솔 진행 상세에서 콘셉트 선택과 카피 승인 흐름을 조작할 수 있다.

## 검증

- 실제 run: `runs/2026-06-14_12-39-06_6월-장마철-수분-장벽-리셋-위크`
- 콘셉트 선택 전 02 승인 차단 확인.
- 콘셉트 선택 → 카피 생성 → 카피 승인 → 02 승인 → 03 잠금 해제 확인.
- planning quality audit `pass`.
- 전체 프로젝트 테스트 69개와 project hook 통과.
- Meta 수집기의 Playwright import를 실제 수집 실행 시점으로 늦춰 테스트 환경에서도 전체 검증이 가능하다.
- `scripts/evaluate_local_model_promotion.py`로 외부 대비 80% 이상, 치명 오류 0의 로컬 승격 기준을 평가한다.

## 다음 우선순위

1. 업종별 전략 골드셋 100~150개를 실제 검수한다.
2. 텍스트 전략 검수 화면에 원문·추상 전략 비교와 직접 수정 입력을 확장한다.
3. 외부 모델과 로컬 instruct 모델의 블라인드 벤치마크를 구축한다.
# 2026-06-14 Handoff - 광고 기획 실전 QA 테스트

## 실행 및 발견

- 실전 테스트 run: `runs/2026-06-14_12-46-22_6월-장마철-수분-장벽-리셋-위크`
- 최초 결정론적 카피에서 `은(는)`, `입력된 사실 안에서 설명합니다`, 동일 문장 반복이 나왔지만 scorecard가 `pass`를 반환했다.
- 이는 생성 품질 문제와 QA 거짓 통과 문제를 동시에 보여준다.

## 수정

- `services/ad_strategy/planning_engine.py`
  - 조사 오류와 내부용 문구 제거.
  - 제품명 선택 개선.
  - 카드뉴스 전환 문장과 블로그 섹션 문장 다양화.
  - `awkward_korean`, `repetitive_copy` 자동 경고 추가.
- `scripts/audit_planning_quality.py`
  - scorecard의 일반 품질 경고를 `planning_quality_warning`으로 노출.
- `tests/test_ad_planning_engine.py`
  - 어색한 한국어, 반복 카피, audit 경고 회귀 테스트 추가.

## 검증 및 현재 판정

- 전체 테스트 71개 통과, project hook 통과.
- 재생성 결과 조사 오류와 내부 문구는 제거됐다.
- 반복 문장이 남아 scorecard와 planning audit가 모두 `warning`으로 정확히 판정한다.
- 현재 deterministic baseline은 구조 검증용이며 실사용 카피 승인 수준은 아니다.
# 2026-06-14 Handoff - 화장품 광고 기획 품질 업그레이드

## 구현

- OpenAI 역할 기반 구조화 생성: `services/llm/openai_provider.py`, `services/ad_strategy/generation.py`
- run별 외부 호출 예산: `02_content_planning/provider-budget.json`, 기본 최대 8회
- 외부 모델 실패 시 `provider_unavailable` 치명 오류 및 승인 차단
- 전략 3안 최소 2개 전략 항목 차별성 검사
- 비평 모델 이슈와 결정론적 QA 통합, 평균 4점 미만 경고
- 경고가 남은 02단계 승인 차단
- 전략 검수 저장/API/UI, 카피 직접 수정·8항목 사람 점수·교정 저장
- 20건 고정 평가셋과 `scripts/benchmark_ad_planning.py`

## 검증

- 전체 프로젝트 테스트 75개 통과.
- 고정 평가셋 20건 생성, 현재 사람 검수 0건으로 `incomplete`.
- 파일럿 run `2026-06-14_12-58-52_6월-장마철-수분-장벽-리셋-위크`:
  - `OPENAI_API_KEY` 미설정
  - strategist `missing_api_key`
  - planning scorecard `fail`, `provider_unavailable`
  - 02 승인 차단
- 브라우저에서 전략 검수 카드 6개/버튼 18개, 품질 지표, provider 오류 메시지, 승인 버튼 미노출, JS 오류 0 확인.

## 남은 운영 작업

- 실제 OpenAI 파일럿은 API 키가 없어 실행하지 못했다.
- Meta 전략 46건은 아직 모두 unreviewed다.
- 카피 교정 기록과 사람 평가도 아직 0건이다.
# 2026-06-15 Handoff - 광고 기획 블라인드 벤치마크 및 회귀 테스트 보강

## 구현

- `scripts/benchmark_ad_planning.py`
  - 외부 결과 점진 생성, 케이스별 즉시 저장, 사람 콘셉트 선택 후 카피 생성, 결정론적 기준선과 외부 결과 블라인드 A/B 구성.
  - 사람 평가 저장과 외부 선호도 역산.
  - 외부 생성 수, 호출 수, 지연시간, 예상 비용 집계.
- `scripts/console_server.py`
  - 벤치마크 리포트 bootstrap 제공.
  - `GET /api/planning-benchmark`, `POST /api/planning-benchmark/review`.
- `ui/console/app.js`
  - 전략 검수 8개 루브릭 개별 입력.
  - 출처/추상 전략 비교.
  - 블라인드 A/B 벤치마크 검수와 모델 호출·비용·지연 지표.
  - 블라인드 선호, 최종 승인, 수정 여부를 분리 입력해 무수정 승인율 왜곡 방지.
- `services/ad_strategy/repository.py`
  - 46개 전략 모두 원본 수집 파일에서 광고 원문을 찾아 검수 응답에만 추가.
- `tests/test_ad_planning_upgrade.py`
  - 전략/카피 비평 후 재작성 루프, 4호출 형태, 블라인드 선호도 역산, 비용 집계 검증.

## 검증

- 전체 프로젝트 테스트 82개 통과.
- `scripts/project_hook_check.py` 통과.
- `node --check ui/console/app.js`, Python compile, `git diff --check` 통과.
- 콘솔 bootstrap API: 평가셋 20건, 전략 사례 46건, 외부 생성 0건 확인.
- 콘솔 bootstrap API: 전략 사례 46건 모두 원문 광고 연결 확인.
- 브라우저 자동 검증은 데스크톱 브라우저 런타임 권한 문제로 실행되지 않아 API 계약으로 대체 검증했다.
- 외부 파일럿 1건 시도는 API 키 미설정으로 `provider_unavailable / missing_api_key / callsUsed 0`을 기록했다.

## 남은 목표 증거

- 외부 생성 완료: 0/20
- 사람 블라인드 평가: 0/20
- Meta 전략 검수: selected 0 / shortlist 0 / unreviewed 46
- 따라서 치명 오류 0, 평균 4.0 이상, 무수정 승인율 50%, 외부 선호도 70% 달성은 아직 증명되지 않았다.
# 2026-06-15 Handoff - 광고 기획 치명 오류 QA 및 목표 감사 강화

## 구현

- `services/ad_strategy/quality_gate.py`
  - 미확인 가격·혜택·기간·효능, 경쟁사 원문 복제, 업종 혼용, 채널 불일치 자동 차단.
  - 채널 계약, 글자 수, 메타데이터, 내부 문구, 제품·오퍼·CTA 연결, 채널 재사용 경고.
- `services/ad_strategy/planning_engine.py`
  - 콘셉트와 카피 비평 결과를 모두 반영.
  - 최종 critic `fail`은 치명 오류, 미해결 `revise`는 경고.
- `services/ad_strategy/generation.py`
  - 비평 `targetIds`에 지정된 실패 콘셉트·채널만 재작성.
  - 교정 예시를 업종·브랜드별로 분리 검색.
- `services/llm/openai_provider.py`
  - Structured Output 응답을 로컬 JSON Schema로 재검증.
- `services/ad_strategy/repository.py`
  - selected 전략은 8개 루브릭 평균 4점 이상과 완성된 추상 전략을 요구.
  - 교정 기록 필수 컨텍스트 검증 및 타 브랜드 교정 격리.
- `scripts/audit_ad_planning_goal.py`
  - 20건 외부 생성·사람 평가·치명 오류·평균 점수·무수정 승인율·블라인드 선호도를 요구사항별 감사.

## 검증

- 전체 프로젝트 테스트 97개 통과.
- project hook, Python compile, JS check, diff check 통과.
- 전체 생성·비평·재작성 흐름이 공유 예산 8회에서 중단됨을 검증.
- 고정 평가셋 20건과 이벤트 유형 5종 유지, 결정론적 기준선 치명 오류 0건 확인.
- 외부 결과 0건에서는 치명 오류 0을 목표 성공으로 계산하지 않음.
- 목표 감사: 핵심 조건 1/7, 준비 조건 포함 1/8, `incomplete`.

## 외부 상태

- `OPENAI_API_KEY` 미설정.
- 외부 결과 0/20, 사람 평가 0/20, 치명 오류 평가 완료 0/20.
- 전략 46건은 원문 연결 완료지만 selected 0 / shortlist 0 / unreviewed 46.
## 2026-06-16 Handoff - 광고 기획 리뷰 패킷 및 목표 진행 상태

### 이번 진행

- ComfyUI/이미지 제작 작업은 제외하고 광고 기획·카피 품질 목표만 진행했다.
- `scripts/export_ad_planning_review_packet.py`를 추가했다.
  - 고정 화장품 평가셋 20건의 파일럿 검수 상태를 정리한다.
  - 외부 모델 결과, 콘셉트 선택, 사람 평가 여부를 케이스별로 표시한다.
  - Meta 전략 예시 46건 중 우선 검수할 30건 큐를 만든다.
  - selected 승격에 필요한 누락 필드와 8개 루브릭 키를 같이 표시한다.
- 산출물:
  - `.tmp/model-benchmarks/ad-planning-review-packet.json`
  - `.tmp/model-benchmarks/ad-planning-review-packet.md`

### 현재 증거

- `OPENAI_API_KEY` 미설정.
- 고정 평가셋: 20/20.
- 외부 모델 결과: 0/20.
- 사람 평가: 0/20.
- 파일럿 5건 기준 외부 결과: 0/5.
- 파일럿 5건 기준 사람 평가: 0/5.
- selected + shortlist 전략: 0/30.
- 목표 감사: `incomplete`, 핵심 조건 1/7.
- 리뷰 패킷 상태: `blocked_waiting_for_api_key`.

### 검증

- `.venv\Scripts\python.exe -m unittest tests.test_ad_planning_review_packet` 통과.
- `.venv\Scripts\python.exe scripts\run_project_tests.py` 통과: 100 tests.
- `.venv\Scripts\python.exe scripts\project_hook_check.py` 통과.
- `node --check ui\console\app.js` 통과.
- `git diff --check` 통과.

### 다음 실행 순서

1. API 키 설정 후 `.venv\Scripts\python.exe scripts\benchmark_ad_planning.py --run-external --limit 5` 실행.
2. 콘솔에서 파일럿 5건의 콘셉트 선택을 완료해 카피 생성을 이어간다.
3. `.tmp/model-benchmarks/ad-planning-review-packet.md` 또는 콘솔을 기준으로 전략 30건을 selected/shortlist/rejected로 검수한다.
4. 파일럿 5건의 블라인드 평가와 수정 여부를 저장한다.
5. `.venv\Scripts\python.exe scripts\benchmark_ad_planning.py`와 `.venv\Scripts\python.exe scripts\audit_ad_planning_goal.py`로 목표 상태를 재감사한다.
## 2026-06-16 Handoff - 광고 기획 리뷰 패킷 콘솔 연동

### 완료

- `scripts/console_server.py`
  - `ad_planning_review_packet()` helper 추가.
  - bootstrap 응답에 `planningReviewPacket` 추가.
  - `GET /api/planning-review-packet` 추가.
  - 전략 검수, 벤치마크 콘셉트 선택, 벤치마크 평가 저장 응답에 최신 `reviewPacket` 포함.
- `ui/console/app.js`
  - `state.planningReviewPacket` 추가.
  - 대시보드 상단에 광고 기획 파일럿 리뷰 패킷 패널 추가.
  - API 키 상태, 파일럿 외부 결과, 파일럿 사람 평가, selected/shortlist 전략 수, blocker 표시.
- `tests/test_ad_planning_review_packet.py`
  - 콘솔 helper가 현재 목표 구조인 20건/파일럿 5건 큐를 유지하는지 테스트 추가.

### 현재 상태

- 리뷰 패킷 상태: `blocked_waiting_for_api_key`.
- `OPENAI_API_KEY` 미설정.
- 파일럿 외부 결과 0/5, 사람 평가 0/5.
- selected + shortlist 전략 0/30.
- 목표 감사는 여전히 `incomplete`, 핵심 조건 1/7.

### 검증

- `.venv\Scripts\python.exe scripts\run_project_tests.py`: 101 tests 통과.
- `.venv\Scripts\python.exe scripts\project_hook_check.py`: pass.
- `node --check ui\console\app.js`: pass.
- `.venv\Scripts\python.exe scripts\benchmark_ad_planning.py`: expected incomplete.
- `.venv\Scripts\python.exe scripts\audit_ad_planning_goal.py`: expected incomplete.

### 다음

1. API 키가 있는 터미널에서 `scripts\benchmark_ad_planning.py --run-external --limit 5` 실행.
2. 콘솔 대시보드의 광고 기획 파일럿 리뷰 패킷 패널에서 파일럿 큐 상태 확인.
3. 콘셉트 선택 및 블라인드 평가 저장.
4. 전략 46건 중 최소 30건을 selected/shortlist로 검수.
## 2026-06-16 Handoff - 전략 검수 CSV 시트

### 완료

- `scripts/manage_ad_strategy_review_sheet.py` 추가.
  - 기본 export: `.tmp/model-benchmarks/ad-strategy-review-sheet.csv`
  - 기본 import dry-run: `.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --import-sheet`
  - 실제 반영: `.venv\Scripts\python.exe scripts\manage_ad_strategy_review_sheet.py --import-sheet --apply`
- CSV 점수 컬럼은 전략 필드와 충돌하지 않도록 `score_strategyClarity`, `score_channelFit`처럼 `score_` 접두사를 사용한다.
- `scripts/export_ad_planning_review_packet.py`의 `reviewArtifacts`에 전략 검수 시트 경로를 추가했다.
- 콘솔 광고 기획 파일럿 리뷰 패킷 패널에 전략 검수 시트 경로를 표시한다.
- `tests/test_ad_strategy_review_sheet.py` 추가, 프로젝트 테스트 러너에 등록.

### 현재 상태

- 생성된 시트: `.tmp/model-benchmarks/ad-strategy-review-sheet.csv`
- rows: 30
- dry-run import: skipped 30, errors 0
- 실제 전략 검수 저장은 아직 없음: selected 0 / shortlist 0 / rejected 0 / unreviewed 46

### 검증

- `.venv\Scripts\python.exe scripts\run_project_tests.py`: 105 tests 통과.
- `.venv\Scripts\python.exe scripts\project_hook_check.py`: pass.
- `.venv\Scripts\python.exe scripts\benchmark_ad_planning.py`: expected incomplete.
- `.venv\Scripts\python.exe scripts\audit_ad_planning_goal.py`: expected incomplete.
- `git diff --check`: pass.
## 2026-06-16 Handoff - 광고 기획 파일럿 실행 오케스트레이터

### 완료

- `scripts/run_ad_planning_pilot.py`를 추가했다.
  - API 키가 있으면 화장품 고정 평가셋 중 파일럿 5건의 외부 모델 생성 흐름을 실행한다.
  - API 키가 없으면 외부 모델 생성은 시도하지 않고 벤치마크 리포트, 리뷰 패킷, 전략 검수 CSV, 목표 감사를 갱신한다.
  - 실행 요약은 `.tmp/model-benchmarks/ad-planning-pilot-run.json`에 저장한다.
- `scripts/console_server.py`에 `POST /api/planning-pilot/run`을 추가했다.
- `ui/console/app.js`의 광고 기획 리뷰 패킷 패널에 파일럿 5건 실행/갱신 버튼을 추가했다.
- 콘솔 job은 `.tmp/console-jobs/` 로그로 추적된다.

### 현재 상태

- `OPENAI_API_KEY` 미설정으로 현재 파일럿 상태는 `blocked_waiting_for_api_key`다.
- 외부 모델 생성: 0/5.
- 사람 평가: 0/5.
- selected + shortlist 전략: 0/30.
- 전략 검수 CSV dry-run: 30 rows skipped, errors 0.
- 목표 감사: 핵심 조건 1/7 통과, 전체 1/8 통과.

### 검증

- `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5`: `blocked_waiting_for_api_key`로 정상 종료.
- `.venv\Scripts\python.exe scripts\run_project_tests.py`: 108 tests 통과.
- `.venv\Scripts\python.exe scripts\project_hook_check.py`: pass.
- `node --check ui\console\app.js`: pass.
- `git diff --check`: pass.

### 다음

1. 같은 PowerShell 세션에 `OPENAI_API_KEY`를 설정한다.
2. 콘솔의 파일럿 5건 실행/갱신 버튼 또는 `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5`를 실행한다.
3. 외부 모델 콘셉트가 생기면 콘솔에서 사람 콘셉트 선택, 카피 생성, 사람 평가와 수정문 저장을 진행한다.
4. 5건에서 치명 오류 0건을 확인한 뒤 20건 전체 평가로 확장한다.

## 2026-06-16 Handoff - 광고 전략 CSV 검수 콘솔 job

### 완료

- `POST /api/ad-strategy/review-sheet`를 추가했다.
  - `mode=export`: `.tmp/model-benchmarks/ad-strategy-review-sheet.csv` 30건 export.
  - `mode=import_dry_run`: CSV 검증만 실행.
  - `mode=import_apply`: CSV 검증 후 전략 저장소에 반영.
- 콘솔 리뷰 패킷 패널에 `Strategy CSV export 30`, `Strategy CSV validate`, `Strategy CSV apply` 버튼을 추가했다.
- `tests/test_ad_planning_pilot_runner.py`에 CSV job command contract 테스트를 추가했다.

### 현재 상태

- CSV export: 30 rows, errors 0.
- CSV dry-run import: 30 skipped, errors 0.
- 실제 검수 반영은 아직 없음: selected 0 / shortlist 0 / rejected 0 / unreviewed 46.
- 목표 감사는 `incomplete`, 핵심 조건 1/7 통과.

### 검증

- `node --check ui\console\app.js`: pass.
- `.venv\Scripts\python.exe -m unittest tests.test_ad_planning_pilot_runner`: 6 tests pass.
- `.venv\Scripts\python.exe scripts\run_project_tests.py`: 111 tests pass.
- `git diff --check`: pass.

### 다음

1. CSV를 열어 최소 30건에 decision과 8개 루브릭 점수를 채운다.
2. `Strategy CSV validate`로 errors 0을 확인한다.
3. `Strategy CSV apply`로 저장소에 반영한다.
4. 리뷰 패킷에서 selected/shortlist 30/30에 도달했는지 확인한다.

## 2026-06-16 Handoff - 벤치마크 사람 평가 CSV

### 완료

- `scripts/manage_ad_planning_benchmark_review_sheet.py`를 추가했다.
  - `--limit 5`: 파일럿 5건 블라인드 A/B 평가 CSV export.
  - `--import-sheet`: dry-run 검증.
  - `--import-sheet --apply`: `cosmetics-human-reviews.json`에 사람 평가 저장.
- `scripts/export_ad_planning_review_packet.py`의 `reviewArtifacts`에 `benchmarkReviewSheet` 경로를 추가했다.
- `scripts/run_ad_planning_pilot.py`가 벤치마크 리뷰 CSV도 생성하고 dry-run 오류 수를 요약한다.
- `POST /api/ad-planning/benchmark-review-sheet`를 추가했다.
- 콘솔 리뷰 패킷 패널에 `Benchmark CSV export 5`, `Benchmark CSV validate`, `Benchmark CSV apply` 버튼을 추가했다.
- `tests/test_ad_planning_benchmark_review_sheet.py`를 추가하고 프로젝트 테스트 러너에 등록했다.

### 현재 상태

- CSV: `.tmp/model-benchmarks/ad-planning-benchmark-review-sheet.csv`
- rows: 5
- dry-run: skipped 5, errors 0
- 저장된 사람 평가: 0/5
- 외부 모델 결과: 0/5
- 목표 감사: `incomplete`, 핵심 조건 1/7 통과

### 검증

- `.venv\Scripts\python.exe -m unittest tests.test_ad_planning_benchmark_review_sheet tests.test_ad_planning_pilot_runner tests.test_ad_planning_review_packet`: 16 tests pass.
- `.venv\Scripts\python.exe scripts\run_project_tests.py`: 117 tests pass.
- `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5`: `blocked_waiting_for_api_key`, benchmarkReviewSheet 요약 포함.

### 다음

1. API 키 설정 후 외부 모델 파일럿 5건 생성.
2. 생성 결과 포함 상태로 `Benchmark CSV export 5` 재실행.
3. 사람이 A/B 선호와 8개 루브릭 점수를 입력.
4. `Benchmark CSV validate` 후 `Benchmark CSV apply`.
## 2026-06-17 Handoff - OpenAI API 비사용 전환 및 광고 기획 스킬화

### 결정

- 사용자는 OpenAI API를 사용하지 않기로 확정했다.
- 광고 기획/카피 품질 기준선은 API provider가 아니라 Codex/Claude에서 재사용 가능한 스킬 지침과 사람 검수 루프로 올린다.
- OpenAI provider 코드는 선택/호환 모드로 유지하지만 기본 파일럿, 리뷰 패킷, 콘솔 표시는 `local` provider 기준으로 전환했다.

### 구현

- 새 Codex 스킬:
  - `C:\Users\jinkiwon\.codex\skills\ad-planning-copy-engine\SKILL.md`
  - `references/rubric.md`
  - `references/output-schema.md`
  - `references/claude-skill.md`
  - `scripts/validate_ad_planning_output.py`
- `scripts/benchmark_ad_planning.py`
  - `--run-candidates --provider local|openai` 추가.
  - 기존 `--run-external`은 OpenAI 호환 alias로 유지.
  - 기본 `run_external_cases()` provider를 `local`로 변경.
  - summary에 `candidateGenerated` 추가.
- `scripts/run_ad_planning_pilot.py`
  - 기본 provider를 `local`로 변경.
  - API 키 없이 후보 5건 생성을 실행.
- `scripts/export_ad_planning_review_packet.py`
  - `OPENAI_API_KEY_MISSING` blocker 제거.
  - `PILOT_CANDIDATE_RESULTS_INCOMPLETE`, `pilotCandidateReady`, `provider` 추가.
- `scripts/audit_ad_planning_goal.py`
  - `external_results_complete`를 `candidate_results_complete`로 변경.
- 콘솔 UI:
  - API 키 표시를 Provider/local 및 파일럿 후보 결과 표시로 변경.

### 최신 실행 결과

- `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5`
  - status: `candidate_generation_attempted`
  - provider: `local`
  - candidateGenerated: 5/20
  - pilotCandidateReady: 5/5
  - blockers: `STRATEGY_REVIEW_BELOW_30`, `PILOT_HUMAN_REVIEWS_INCOMPLETE`
- 스킬 검증:
  - `quick_validate.py C:\Users\jinkiwon\.codex\skills\ad-planning-copy-engine`: pass

### 남은 일

1. local 후보의 현재 한국어 품질은 깨진 문자열이 포함되어 있어 실사용급이 아니다. 스킬 기반 JSON 출력으로 후보 품질을 교체/보강해야 한다.
2. 전략 CSV 30건을 사람 검수로 채운다.
3. 후보 5건에서 콘셉트 선택, 카피 생성, 사람 평가/수정 기록을 완료한다.
4. 목표 감사는 아직 incomplete다.
## 2026-06-17 Handoff - local 광고 기획 템플릿 품질 보강

### 완료

- `services/ad_strategy/planning_engine.py`를 정상 한국어 템플릿으로 재작성했다.
  - 콘셉트 3안: 문제 재정의, 선택 근거, 나다운 순간 축으로 분리.
  - 카피 패키지: 카드뉴스, 인스타 피드, 블로그 썸네일/본문, 단문 채널 기본 문장을 정상화.
  - QA 메시지와 루브릭 기본 점수도 사람이 읽을 수 있는 한국어로 정리.
- 깨진 문자열/과도한 질문형/반복 문장은 계속 경고로 잡는다.
- local 파일럿 5건을 다시 실행했다.

### 현재 증거

- `.venv\Scripts\python.exe scripts\run_ad_planning_pilot.py --limit 5`
  - status: `candidate_generation_attempted`
  - provider: `local`
  - candidateGenerated: 5/20
  - pilotCandidateReady: 5/5
  - human reviews: 0/5
- 첫 케이스 예시:
  - `concept_01`: `일상의 불편을 다시 정의하는 캠페인`
  - target insight: `새 루틴을 부담 없이 시작하려는 고객. 이 고객은 문제를 참고 넘기기보다 부담 없는 해결 기준을 원합니다.`
  - core promise: `수분 앰플을 복잡한 고민을 줄이는 현실적인 루틴 제안으로 보여줍니다.`

### 검증

- `.venv\Scripts\python.exe scripts\run_project_tests.py`: 117 passed
- `.venv\Scripts\python.exe scripts\project_hook_check.py`: pass
- `.venv\Scripts\python.exe scripts\audit_ad_planning_goal.py`: expected incomplete

### 남은 blocker

- `STRATEGY_REVIEW_BELOW_30`: 전략 CSV 30건 검수 필요.
- `PILOT_HUMAN_REVIEWS_INCOMPLETE`: 파일럿 5건 콘셉트 선택/카피 평가 필요.

## 2026-06-17 Handoff - 광고 기획 콘솔 UI 전면 개편

### 완료

- `ui/console/app.js`의 메인 광고 기획 패널을 사용자용 `광고 기획 검수 데스크`로 교체했다.
- A/B 블라인드 비교 렌더러를 메인 흐름에서 제거하고, 기존 A/B 카드 함수도 제거했다.
- 파일럿 이벤트는 제품, 목적, 다음 작업, 콘셉트 3안, 채널별 카피 패키지, 평가 폼으로 표시한다.
- 카피 패키지에서 `JSON.stringify` 출력과 JSON 편집 textarea를 제거했다.
- QA issue는 채널 ID나 critic 용어 대신 사람이 읽는 한국어 메시지로 표시한다.
- 전략 검수/CSV/운영 지표는 `고급 정보 / 데이터 검수` details 영역으로 이동했다.
- `scripts/benchmark_ad_planning.py`와 benchmark CSV import에서 `blindPreferred`를 선택 입력으로 완화했다.

### 검증

- `node --check ui\console\app.js`: pass
- `.venv\Scripts\python.exe -m unittest tests.test_ad_planning_upgrade tests.test_ad_planning_benchmark_review_sheet`: 22 tests pass
- `git diff --check`: whitespace error 없음
- Browser DOM 확인:
  - `광고 기획 검수 데스크` 표시됨
  - planning case 5개, concept card 15개, copy card 12개
  - `Provider`, `Blockers`, A/B, `meta_strategy_*`, JSON 노출 0개
  - dashboard overflow 0개

### 남은 일

1. 실제 파일럿 5건에서 콘셉트 선택과 검수 저장을 진행한다.
2. 수정 요청 메모와 사람 평가를 correction data로 축적한다.
3. 전략 CSV 30건 검수를 완료해 `STRATEGY_REVIEW_BELOW_30` blocker를 제거한다.
# 2026-06-18 Handoff - 마케팅 신호 추천 검수 큐

## 완료

- `scripts/console_server.py`
  - `with_signal_recommendation()`, `signal_recommendation_score()`, `evidence_priority()` 추가.
  - `marketing_signal_packet()`이 원본 신호에 `reviewRecommendation`을 덧붙여 반환한다.
  - 미검수 큐는 추천 점수 높은 순서로 정렬된다.
- `ui/console/app.js`
  - 신호 카드에 `우선 검토 / 검토 후보 / 보조 후보` 라벨과 점수를 표시한다.
  - `추천 이유` 문장을 카드에 표시한다.
- `ui/console/styles.css`
  - 추천 배지 스택과 추천 이유 박스 스타일 추가.
- `scripts/audit_console_ui_playwright.py`
  - `.signal-recommendation` 노출 검사를 추가했다.
- `tests/test_marketing_intelligence_console.py`
  - 추천 점수 기반 큐 정렬 테스트 추가.

## 현재 확인

- 현재 마케팅 신호: 100개.
- selected: 0개.
- reviewQueue: 24개.
- 첫 번째 추천 후보: `우선 검토 10/10`.
- InsightBrief 상태: `needs_signal_review`.

## 검증

- `node --check ui/console/app.js`: 통과.
- `python -m unittest tests.test_marketing_intelligence_console`: 통과.
- `python -m unittest tests.test_console_ui_playwright_audit tests.test_marketing_intelligence_console`: 통과.
- `python scripts/run_project_tests.py`: 134 tests 통과.
- `python scripts/audit_console_ui_playwright.py --url http://127.0.0.1:5177/ --timeout-ms 20000`: `pass`.

## 다음

1. 우선 검토 카드부터 3개 이상 선택한다.
2. `InsightBrief 만들기` 버튼으로 기획 근거 패킷을 ready로 만든다.
3. 파일럿 5건에 ready 근거 패킷을 붙여 재생성한다.

# 2026-06-18 Handoff - 마케팅 신호 수집/CSV job 콘솔 연결

## 완료

- `scripts/console_server.py`
  - `run_marketing_signal_job()` 추가.
  - `POST /api/marketing-signals/job` 추가.
  - 모드: `random_seed`, `export`, `import_dry_run`, `import_apply`.
- `ui/console/app.js`
  - 마케팅 신호 검수 패널에 작업 버튼 4개 추가.
  - `runMarketingSignalJob()`으로 콘솔 job 시작 후 최근 작업 목록에 반영.
- `tests/test_marketing_intelligence_console.py`
  - 랜덤 수집 job command contract 테스트 추가.
  - CSV import dry-run/apply 테스트 추가.
  - 알 수 없는 mode 차단 테스트 추가.
- `scripts/audit_console_ui_playwright.py`
  - 마케팅 신호 작업 버튼 4개 이상 노출 검사를 추가.

## 현재 데이터 상태

- 실제 수집 실행 결과:
  - 기존 신호 50개
  - 추가 50개
  - 총 100개
  - 검수 CSV 100행
- 저장소: `design_brain_wiki/marketing_signals/signals.json`
- 검수 CSV: `.tmp/marketing-signals/marketing-signal-review-sheet.csv`
- selected 0 / shortlist 0 / rejected 0 / unreviewed 100.

## 검증

- `node --check ui/console/app.js`: 통과.
- `python -m unittest tests.test_marketing_intelligence_console`: 통과.
- `python -m unittest tests.test_console_ui_playwright_audit tests.test_marketing_intelligence_console`: 통과.
- `python scripts/run_project_tests.py`: 133 tests 통과.
- `python scripts/audit_console_ui_playwright.py --url http://127.0.0.1:5177/ --timeout-ms 20000`: `pass`.

## 다음

1. 콘솔에서 100개 신호 중 최소 3개를 `선택`한다.
2. `InsightBrief 만들기`를 실행해 ready 근거 패킷을 만든다.
3. ready 근거 패킷으로 파일럿 5건을 재실행한다.

# 2026-06-18 Handoff - Playwright 콘솔 UI 감사 추가

## 결정

- Playwright는 1차로 광고 데이터 수집 엔진이 아니라 콘솔 UI 품질 감사 도구로 사용한다.
- 목적은 사용자가 보는 메인 화면에서 개발자 상태값, raw JSON, A/B 잔재, 텍스트 넘침이 다시 나타나는 것을 자동 차단하는 것이다.

## 구현

- `scripts/audit_console_ui_playwright.py` 추가.
  - 기본 URL: `http://127.0.0.1:5177/`
  - 기본 화면: 1280x1100
  - 브라우저 실행 순서: Playwright 번들 Chromium → 설치된 Chrome → Edge
  - 리포트: `.tmp/console-ui-audit/latest-console-ui-playwright.json` 및 `.md`
- `tests/test_console_ui_playwright_audit.py` 추가.
- `scripts/run_project_tests.py`에 판정 로직 테스트를 등록했다.
- `scripts/project_hook_check.py`에는 새 감사 스크립트 py_compile만 등록했다. 실제 Playwright 실행은 콘솔 서버가 필요하므로 hook에서 강제하지 않는다.

## 검증

- `python -m unittest tests.test_console_ui_playwright_audit`: 통과.
- `node --check ui/console/app.js`: 통과.
- `python scripts/audit_console_ui_playwright.py --url http://127.0.0.1:5177/ --timeout-ms 20000`: `pass`.

## 다음

1. 마케팅 신호 검수 버튼/CSV 작업을 콘솔 job으로 보강한다.
2. selected 신호 3개 이상 검수 후 InsightBrief를 ready로 만든다.
3. UI를 수정할 때마다 Playwright 감사를 한 번씩 돌린다.
## 2026-06-20 Handoff - HSGN 근거 기반 광고 기획 품질 1차 업그레이드

### 완료

- `scripts/seed_hsgn_marketing_signals.py` 추가.
  - HSGN 여름 톤 케어 이벤트용 검수 신호 13개를 `selected` 상태로 저장한다.
  - 실행 결과 `design_brain_wiki/marketing_signals/insight-brief.json`이 `eventId=hsgn-summer-tone-care-2026`, `status=ready`, `selectedSignalCount=13`로 생성됐다.
- `services/ad_strategy/planning_engine.py`를 깨진 템플릿 없는 한국어 기획 엔진으로 교체했다.
  - 콘셉트 3안은 문제 재정의 / 선택 근거 / 자기관리 순간 축으로 분리된다.
  - 카피 본문에는 내부 기획 문구를 노출하지 않고, 근거는 `planningEvidence`와 `strategyBasis`에 남긴다.
  - 채널별 헤드라인을 분리해 동일 문장 반복과 채널 재사용 경고를 제거했다.
- `services/ad_strategy/quality_gate.py`를 정상 한국어 QA 게이트로 교체했다.
  - 허위 혜택/효능/기간/가격, 업종 혼용, 원문 복제, 필수 필드, 글자 수, CTA, 제품/오퍼 연결을 검사한다.
- HSGN run `runs/2026-06-20_01-26-50_hsgn-여름-톤-케어-집중-이벤트` 02단계를 재생성했다.
  - 선택 콘셉트: `concept_02`
  - scorecard: `pass`
  - criticalErrorCount: 0
  - averageScore: 4.0
  - issues: 0

### 검증

- `.venv\Scripts\python.exe -m py_compile services\ad_strategy\planning_engine.py services\ad_strategy\quality_gate.py scripts\seed_hsgn_marketing_signals.py`
- `.venv\Scripts\python.exe -m unittest tests.test_ad_planning_engine tests.test_ad_planning_upgrade tests.test_ad_planning_quality_gate tests.test_marketing_insight_brief`
- 테스트 결과: 37개 통과.

### 남은 작업

1. HSGN 카피를 콘솔에서 사람이 최종 승인하거나 수정 요청을 저장한다.
2. 현재 Playwright 연결은 콘솔 UI 감사용으로 검증됐고, 외부 트렌드/상품/브랜드 신호 자동 수집기는 아직 별도 구현해야 한다.
3. 이벤트별 InsightBrief 격리를 계속 유지해야 한다. 전역 `general` ready 패킷이 다른 이벤트에 섞이면 품질 평가가 오염된다.
4. 화장품 파일럿 5건에 같은 구조를 확장해 치명 오류 0건과 평균 4.0 이상을 반복 검증한다.
## 2026-06-20 Handoff - 공개 웹 관찰 신호 수집기 1차 구현

### 완료

- `services/marketing_intelligence/public_signal_collector.py` 추가.
  - `brand_site`, `public_web`, `google_trends`, `naver_datalab`, `oliveyoung_rank`, `weather`, `calendar`, `meta_ad`, `review` 관찰을 `MarketingSignal`로 변환한다.
  - 경쟁 광고/공개 페이지 원문은 `signalText`에만 보관하고, 생성 근거는 추상화된 `normalizedInsight`를 쓰도록 설계했다.
  - 기본 결정은 `unreviewed`이며, 사람이 selected로 승격하기 전에는 InsightBrief에 들어가지 않는다.
- `scripts/collect_marketing_signals.py` 확장.
  - `--public-snapshot`: JSON snapshot에서 공개 관찰 신호 import.
  - `--capture-url`: Playwright로 공개 페이지 본문 snapshot 생성.
  - `--source-kind`: 관찰 출처 종류 지정.
  - `--auto-select-public`: 테스트/내부 검증용 자동 selected 옵션.
- `scripts/console_server.py`의 `run_marketing_signal_job`에 `public_snapshot` 모드 추가.
- HSGN 샘플 snapshot `assets/rules/hsgn-public-marketing-snapshot.json` 추가.
- 실제 실행으로 공개 관찰 신호 5개를 `design_brain_wiki/marketing_signals/signals.json`에 추가했다.
  - sourceTypes: `brand_site`, `google_trends`, `meta_ad`, `review`, `weather`
  - decisions: unreviewed 5

### 검증

- `.venv\Scripts\python.exe -m py_compile services\marketing_intelligence\public_signal_collector.py scripts\collect_marketing_signals.py scripts\console_server.py`
- `.venv\Scripts\python.exe -m unittest tests.test_public_marketing_signal_collector tests.test_marketing_intelligence_console tests.test_marketing_intelligence_signals tests.test_marketing_insight_brief`
- `.venv\Scripts\python.exe -m unittest tests.test_ad_planning_engine tests.test_ad_planning_upgrade tests.test_ad_planning_quality_gate tests.test_public_marketing_signal_collector tests.test_marketing_intelligence_console tests.test_marketing_intelligence_signals tests.test_marketing_insight_brief`
- 최종 묶음 테스트: 52개 통과.

### 현재 상태

- 공개 관찰 신호는 아직 생성 근거가 아니라 검수 대기 데이터다.
- HSGN `InsightBrief`는 기존 selected 13개 상태를 유지한다.
- HSGN 02 scorecard는 `pass`, criticalErrorCount 0, averageScore 4.0, issues 0을 유지한다.

### 다음 작업

1. 콘솔에서 공개 관찰 신호 5개를 검수한다.
2. selected 공개 신호를 포함한 HSGN InsightBrief를 다시 만들고 카피 변화를 비교한다.
3. Playwright `--capture-url`을 콘솔 UI job으로 노출해 실제 공개 URL snapshot 수집을 시작한다.
