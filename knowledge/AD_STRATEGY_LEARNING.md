# 광고 기획 학습 라이브러리

## 목적

Meta 광고 이미지 레퍼런스와 별개로 광고 카피의 설득 구조를 학습한다.
경쟁사 문장을 그대로 재사용하지 않고 훅 유형, 설득 순서, 혜택 방식, CTA, 문체 특징만 추상 패턴으로 저장한다.

## 데이터 흐름

```text
references/meta_ads/searches/*/collected-ads.json
  -> scripts/build_meta_ad_strategy_library.py
  -> design_brain_wiki/ad_strategy/meta-ad-strategy-library.json
  -> 01_event_brief.strategy_inspiration
  -> 02_content_planning.copy_intent / copy_blueprint
```

## 생성 명령

```powershell
python scripts\build_meta_ad_strategy_library.py
```

새 Meta 광고를 수집한 뒤 이 명령을 다시 실행하면 라이브러리가 갱신된다.

## 저장 필드

- `hookType`: 질문형, 문제 공감형, 혜택 선제시형, 수치형 등
- `persuasionSequence`: hook, problem, reason to believe, routine, offer, CTA 순서
- `offerMechanics`: 증정, 할인, 번들, 한정, 환불 등
- `ctaType`: 구매, 더 알아보기, 신청 등
- `toneTraits`: 구체적, 대화형, 신뢰형, 한정성 등
- `copyBlueprint`: 새 이벤트에 적용할 추상 설계
- `source`: 브랜드, Library ID, 원문 해시, 출처 파일

## 저작권·브랜드 안전 원칙

- 경쟁사 광고 원문은 학습 라이브러리 출력에 저장하지 않는다.
- 생성 결과에 경쟁사 문장을 그대로 복사하지 않는다.
- 출처는 감사와 중복 제거를 위해 브랜드, Library ID, 원문 해시만 남긴다.
- 새 이벤트의 타깃, 제품, 혜택, 브랜드 톤으로 다시 작성한다.

## 현재 상태

- 2026-06-14 기준 기존 Meta 수집물에서 46개 추상 전략 패턴 생성.
- 6월 장마철 이벤트에 유사 패턴 5개를 연결.
- 카드뉴스, 인스타 피드, 블로그 썸네일, 블로그 인라인별 `copy_intent`와 `copy_blueprint` 생성 확인.

## 2026-06-18 확장 방향: 전략 패턴에서 마케팅 신호로

Meta 광고 전략 패턴만으로는 실제 마케터 수준의 훅을 만들기 어렵다.
앞으로 광고 기획 학습은 `MarketingSignal` 기반으로 확장한다.

- 경쟁사 광고 구조는 하나의 신호일 뿐이며, 최종 판단 근거가 되어서는 안 된다.
- 올리브영 랭킹, 리뷰 불만, 검색 트렌드, 계절/날씨, SNS 문장 유행, 채널별 반응 문법을 함께 저장한다.
- 카피 생성 전 `InsightBrief`가 타깃 인사이트, 구매 망설임, 시즌 훅, 제품 선택 기준, 오퍼 이유를 정리한다.
- 자세한 계획은 `knowledge/MARKETING_INTELLIGENCE_DATA_FLOW.md`를 기준으로 한다.

# 2026-06-14 검수 전략 저장소와 교정 학습

- 검수 전략 저장소: `design_brain_wiki/ad_strategy/reviewed-strategy-examples.json`
- 교정 기록: `design_brain_wiki/ad_strategy/copy-corrections.json`
- 기존 `meta-ad-strategy-library.json`의 패턴은 최초 import 시 모두 `unreviewed`다.
- 생성 검색에는 업종이 일치하고 `review.decision=selected`인 사례만 사용한다.
- 기본 기획 사유 태그:
  - `generic`, `weak_insight`, `awkward_korean`, `brand_mismatch`
  - `unsupported_claim`, `copied_expression`, `weak_cta`, `channel_mismatch`
  - `good_hook`, `good_structure`, `strong_product_link`
- 파인튜닝은 업종별 검수 사례와 직접 수정 카피가 충분히 쌓인 뒤 진행한다.
