# 통합 백로그 (패스하고 넘어간 항목 추적)

> 목적: 그동안 방향을 잡으며 "일단 패스"한 항목을 한 곳에 모아 놓치지 않고 추적한다.
> 규칙: 새로 패스/보류하는 항목이 생기면 여기에 즉시 추가한다. 끝낸 항목은 `[x]`로 체크하고 완료일/근거를 남긴다.
> ComfyUI 워크플로 제작은 별도 폴더에서 진행하므로 이 백로그에서 제외한다.

마지막 갱신: 2026-06-20

범례: `[ ]` 미완 · `[~]` 진행중 · `[x]` 완료 · 🤖 = 자동/코드로 가능 · 🙋 = 기원님 사람 검수 필요

---

## A. 레퍼런스 판단 정확도 (최우선 — 본질 과제)

- [x] 🤖 재현 가능한 정확도 측정 하니스 구축 — `scripts/replay_reference_accuracy.py` (2026-06-20)
- [x] 🤖 진짜 베이스라인 확정 — 244건 기준 3-class 43.4% / 2-class 62.7%(learned rules). learned rules가 정확도 올림을 데이터로 확인 (상세: [[REFERENCE_ACCURACY_2026-06-20]])
- [x] 🤖 병목 특정 — 거절 탐지 실패(과선택 2배 편향). 메타데이터만으론 거절 못 가림(qwen_review 0건)
- [x] 🤖 비전 가설 검증 — Qwen 비전 블랭킷 적용은 오히려 정확도 하락(과제외로 역전). 가정 반증
- [x] 🤖 캘리브레이션 하이브리드 + 비전 캐시 A/B — 실험 완료. 어떤 임계값에서도 메타데이터를 못 넘음(반증). 비전 통합 보류 결론 (2026-06-20)
- [ ] 🙋 화장품 신규 holdout 30~50장 수집 후 갱신된 기준으로 재판정, 정확도 비교
- [ ] 🤖 새 holdout 생성 시 `--exclude-profile-history`로 이전 세션 중복 제외 (session_001/holdout_001/002)

## B. 마케팅 인텔리전스 / 광고 기획 (6/17~6/18)

- [ ] 🙋 마케팅 신호 50개를 `선택/보류/거절`로 실제 검수 (현재 selected 0)
- [ ] 🙋 selected 신호 3개+ 만든 뒤 `InsightBrief 만들기` 실행
- [ ] 🤖 ready InsightBrief로 파일럿 5건 재실행, 훅/타깃/제품 연결 점수 비교 (🙋 selected 신호 3개+ 검수 선행 필요)
- [x] 🤖 올리브영 랭킹·리뷰 키워드 CSV import 포맷 — `scripts/import_oliveyoung_ranking.py` + `services/marketing_intelligence/oliveyoung_csv.py` (2026-06-20)
- [x] 🤖 날씨·계절 캘린더 신호 자동 생성 — `scripts/generate_calendar_signals.py` + `services/marketing_intelligence/calendar_signals.py` (2026-06-20)
- [ ] 🙋 광고 카피 설득력: selected 전략 사례 30건+ 검수 후 재평가
- [ ] 🙋 좋은/나쁜 광고 사례 사람 평가 데이터 보강

## C. Meta 수집 품질 (6/13~6/14)

- [ ] 🙋 accepted 고유 이미지 61장으로 신규 검수 세션 생성, 사람 vs Qwen 판정 비교
- [x] 🤖 화장품 Meta `promotion_text_heavy` 편중 낮출 브랜드·쿼리 전략 — 기존 구현 확인: collection_strategy `deprioritize_promotion_heavy` 후순위 + source_mix `query_type` 우선
- [x] 🤖 accepted 이미지 브랜드별 편중 제한 — 기존 구현 확인: meta_brand_provider `max_per_brand=2`, registry_metrics `high_brand_concentration`(>40%) 경고
- [ ] 🤖 검증된 상품·성분 쿼리를 신규 이벤트 레퍼런스 수집에 병행 (meta_source_mix_provider가 이미 검증 쿼리만 공급 — 운영 반복 측정만 남음)
- [x] 🤖 source-mix 공급 품질 저하 시 자동 경고/비활성화 회귀 gate — `source_mix_regression_gate()` 추가, provider가 disable 시 공급 중단, 테스트 4개 (2026-06-20)
- [ ] 🤖🙋 신규 화장품 이벤트 3건에서 source-mix 공급 수/중복률/QA 경고율 반복 측정 (사람 검수 동반)

## D. 운영 완성도 (6/14)

- [ ] 🙋 세 번째 서로 다른 실제 이벤트를 최종 archive까지 완료 (현재 2/3종). 사람 선택·승인 필요
- [ ] 🤖 완료 후 반복 운영 감사 `pass` 확인

## E. 콘솔 UX (6/13)

- [ ] 🤖 (필요시) 새로고침 후 마지막 선택 검수 세션 복원 UX

## G. 취향 모델 — 경쟁 마케팅 이미지 학습 (기원님 핵심 목적)

- [x] 🤖 CLIP 취향 학습 파이프라인 — `taste_labels.py` + `scripts/train_taste_model.py`. 7세션 240장 통합, ROC AUC 0.82, top-10 lift 2.18x (2026-06-20). 상세: [[TASTE_MODEL_2026-06-20]]
- [x] 🤖 학습 모델로 신규 이미지 자동 순위 — `scripts/rank_images_by_taste.py`
- [x] 🤖 (가) Meta 소량 수집 검증 — `collect_meta_ads.py` "스킨케어 세럼" 23장 수집→취향 점수 확인 (2026-06-20)
- [x] 🤖 임의 폴더→콘솔 라벨 세션 인제스터 — `scripts/ingest_image_folder_session.py` (Meta·확장 공통). 루프 닫힘
- [x] 🤖 데이터 전략 실행 — 노이즈 키워드 수집 대신 브랜드 advertiser-match. 깨끗한 세션 `meta_brand_clean_001`(27장, AI추천 selected 21/shortlist 2). 노이즈 세션 excludeFromTraining (2026-06-20)
- [ ] 🙋 [마지막] `meta_brand_clean_001`(깨끗, 74장 / AI추천 selected 62·shortlist 4) 콘솔에서 라벨 → 재학습 (추천 66장 우선)
- [x] 🤖 번들 chromium 설치(`playwright install`) — chromium-1217 설치·실행 확인 (2026-06-20)
- [x] 🙋 Pinterest 로그인 세션 생성 — `pinterest_login.py`로 생성 완료, 쿠키 11개 usable (2026-06-20)
- [ ] 🙋 [마지막] 콘솔에서 경쟁사 이미지 추가 라벨링 → 재학습으로 AUC 향상 (사람 검수)

## F. 코드/감사 정합성 (이번 세션 발견)

- [x] 🤖 pipeline-health `looks_mojibake()` 오탐 수정 — 정상 한글 물음표를 mojibake로 판정하던 버그. U+FFFD 카운트로 교체 (2026-06-20, 커밋 bc79d86)
- [x] 🤖 6/13 이후 신기능 연결 점검 — 콘솔 API 9개+로 연결 확인(파이프라인 단계 아닌 검수 데스크, 의도된 설계) (2026-06-20)
- [x] 🤖 테스트 러너 정합성 — 메인 기준 25개 모듈 전부 존재, _FailedTest는 worktree 미동기화 탓 (2026-06-20)
