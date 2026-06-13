# Learned Replay Test - cosmetics_skincare/pinterest_session_001

## Test Goal

100장 리뷰가 "교육 데이터"로 저장됐는지 확인한다.

## Baseline

기존 AI 1차 판단은 기원님 최종 판단과 15/100만 일치했다.

| Metric | Result |
|---|---:|
| Reviewed | 100 / 100 |
| Baseline match | 15 / 100 |
| Baseline accuracy | 15.0% |

## Replay With Kiwon Corrections

같은 100장에 대해서는 `kiwon_review_state.json`의 `correctDecision`을 우선 적용하면 100/100 재현된다.

| Metric | Result |
|---|---:|
| Replay match | 100 / 100 |
| Replay accuracy | 100.0% |

## Important Interpretation

이 결과는 "같은 이미지를 기억했다"는 테스트다. 모델 가중치가 파인튜닝됐다는 뜻은 아니다.

운영 교육으로 만들려면 아래 단계가 필요하다.

1. `correction_summary.md`에서 반복 패턴을 추출한다.
2. `cosmetics_skincare_v0_2.md`, `REFERENCE_JUDGE_RUBRIC.json`, feedback phrase를 업데이트한다.
3. 새로 수집한 holdout reference 30-50장에 다시 AI 1차 판단을 돌린다.
4. Kiwon 판단과 70-80% 이상 맞으면 1차 기준이 안정된 것으로 본다.

## Current Result

- Same-session memory replay: pass.
- New-image generalization: not tested yet.
- Next recommended test: fresh cosmetics holdout session 30장.

