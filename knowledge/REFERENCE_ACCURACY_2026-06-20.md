# 레퍼런스 판단 정확도 진단 (2026-06-20)

## 한 줄 결론

레퍼런스 판단 정확도를 처음으로 재현 가능하게 측정했다. 떠돌던 "52.8%"는 단일 세션 수치였고,
전체 검수 244건 기준 실제 정확도는 **3-class 43.4% / 2-class(keep·drop) 62.7%**(learned rules 적용)다.
6/14 learned rules는 정확도를 실제로 올린다(+9~13%p, 데이터로 처음 확인). 반면 **Qwen 비전을 그냥
켜면 정확도가 오히려 떨어진다** — 가정과 반대 결과.

## 측정 도구

`scripts/replay_reference_accuracy.py` (신규)

- 검수 완료 training session에 대해 사람 검수/라이브 모델 없이 현재 판단 코드의 정확도를 재측정.
- ground truth: `kiwon_review_state.json` (agree→당시 AI결정, disagree→correctDecision, unsure/미검수→제외)
- baseline(룰 이전) vs learned(promoted rules 적용) vs vision(`--qwen-vision`) 비교, 혼동행렬 출력.
- 사용:
  - 메타데이터: `python scripts/replay_reference_accuracy.py --profile cosmetics_skincare`
  - 비전 A/B: `python scripts/replay_reference_accuracy.py --qwen-vision --sessions <id...>`

## 베이스라인 (cosmetics_skincare, 244건)

| 지표 | baseline | learned rules |
|---|---|---|
| 3-class | 34.0% | 43.4% |
| 2-class (keep/drop) | 49.6% | 62.7% |

세션별: pinterest_session_001 15%/40% (최악, 100건, 초기 과선택 로직), mixed_reference_001 36.7%/46.7%,
holdout_001 66%/87.2%, holdout_002 83.3%/88.9%, holdout_003 61.3%/80.6%.

## 핵심 병목: 거절 탐지 실패 (과선택 편향)

메타데이터 혼동행렬(learned, 244건): 기원님이 **거절한 101건 중 84건을 AI가 살림**(shortlist 56 + selected 28),
정상 거절 17건뿐. 과선택 92 vs 과제외 46 → AI가 2배 후하게 평가. 원인은 화장품 fallback이 전부 `shortlist`이고,
검수 세션의 `qwen_review`가 0건(메타데이터만으로 판단)이라 거절 근거 신호가 없기 때문.

## 비전 A/B 결과 (반증)

mixed_reference_001 + holdout_001 총 77건을 Qwen 비전으로 재판단:

| 세션 | 메타데이터 2-class | 비전 2-class |
|---|---|---|
| mixed_reference_001 | 46.7% | 53.3% (개선) |
| pinterest_holdout_001 | 87.2% | 68.1% (악화) |
| 전체 | 71.4% | 62.3% (악화) |

비전은 메타데이터의 과선택을 **과제외로 뒤바꿀 뿐** 캘리브레이션이 안 됨(holdout_001에서 keep 31건 중 11건을
거절로 떨굼). 따라서 **`--qwen-vision`을 신규 세션에 무조건 켜면 안 된다.** `review_image` 출력 스키마는
auto_decision 기대 필드와 정확히 정렬돼 있음(local_hb_sale_fit/benefit_hierarchy/product_trust/decision 등).

## 하이브리드 실험 결과 (반증 2)

캘리브레이션 하이브리드(메타 keep 기본 + 비전 hard-risk >= 임계값일 때만 거절 downgrade)를
같은 77건에 대해 임계값 75~101로 스윕:

| threshold | 메타 2-class | 비전 2-class | 하이브리드 2-class |
|---|---|---|---|
| 75~90 | 71.4% | 63.6% | 66.2% |
| 95~101 | 71.4% | 63.6% | 71.4% (downgrade 거의 안 함) |

**어떤 임계값에서도 하이브리드가 메타데이터를 못 넘는다.** 비전의 hard-risk 점수가 기원님 거절 기준과
정렬이 안 돼서, downgrade가 net으로 틀린다(임계값을 올리면 메타와 같아질 뿐). 결론: **현재 Qwen
프롬프트/모델로는 비전이 어떤 통합 방식(pure/hybrid)으로도 메타데이터+learned rules를 못 이긴다.**

## 검증된 결정

1. learned rules는 정확도를 올리므로 유지한다. (현재 최선: 244건 3-class 43.4% / 2-class 62.7%)
2. **비전 통합은 지금 쫓을 레버가 아니다.** pure도 hybrid도 메타데이터보다 나쁘다. 비전을 살리려면
   먼저 Qwen 프롬프트/모델을 기원님 거절 기준에 맞게 캘리브레이션해야 한다(별도 R&D).
3. 정확도를 더 올리는 현실적 경로는 **learned rules 성장**(사람 검수 reason-tag 데이터 축적)이며,
   이는 사람 검수가 필요하다(🙋).
4. 측정 인프라(`replay_reference_accuracy.py`)는 비전 결과를 세션별 `.vision_cache.json`에 캐시하므로,
   향후 프롬프트/룰 변형은 비전 재호출 없이 A/B할 수 있다.

관련: [[BACKLOG]], [[09_HANDOFF]]
