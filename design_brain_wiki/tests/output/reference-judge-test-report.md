# Reference Judge Wiki Test Report

- Status: pass
- Total: 18
- Accuracy: 1.0
- Feedback depth rate: 1.0
- Test set: `design_brain_wiki\tests\reference_judge_sample_set.json`
- Rubric: `design_brain_wiki\REFERENCE_JUDGE_RUBRIC.json`

## bullion_investment

- Context: 금 투자 상담 이벤트, 인스타그램 카드뉴스와 상담 신청 배너
- Accuracy: 1.0
- Feedback depth rate: 1.0
- Wiki sources:
  - `design_brain_wiki/05_industry_playbooks/bullion_investment.md`
  - `design_brain_wiki/03_reference_judgement/selected_criteria.md`
  - `design_brain_wiki/04_channel_usability/cardnews.md`
  - `design_brain_wiki/08_feedback_language/senior_designer_critique_phrases.md`

| Candidate | Expected | Actual | Feedback depth | Senior designer feedback |
|---|---:|---:|---:|---|
| `bullion_good_01` | selected | selected | pass | 이 레퍼런스는 blank_headline_area, calm_trust, dark_navy 신호가 분명해서 금융 투자 브랜드의 신뢰와 프리미엄 상담 톤에 맞습니다. 제품 정체성, 무드/신뢰, 레이아웃/카피 여백 기준이 함께 살아 있고 copySpace 6점, layoutUsability 8점이라 금 투자 상담 카드뉴스 메인 또는 상담 신청 배너로 확장하기 좋습니다. |
| `bullion_good_02` | selected | selected | pass | 이 레퍼런스는 copy_space, cta_space, gold_coin 신호가 분명해서 금융 투자 브랜드의 신뢰와 프리미엄 상담 톤에 맞습니다. 제품 정체성, 무드/신뢰, 레이아웃/카피 여백 기준이 함께 살아 있고 copySpace 9점, layoutUsability 9점이라 금 투자 상담 카드뉴스 메인 또는 상담 신청 배너로 확장하기 좋습니다. |
| `bullion_amb_01` | shortlist | shortlist | pass | 이 레퍼런스는 무드/신뢰, 레이아웃/카피 여백 관점에서는 참고 가치가 있지만 업종 신뢰감이 약합니다 때문에 selected로 올리기에는 부족합니다. 제품 질감, 금융 무드, 포스터 레이아웃 중 일부 보조 기준으로만 쓰고, 메인 방향으로 쓰려면 카피 여백과 업종 신뢰 신호를 보강해야 합니다. |
| `bullion_amb_02` | shortlist | shortlist | pass | 이 레퍼런스는 제품 정체성 관점에서는 참고 가치가 있지만 카피 여백이 부족합니다 때문에 selected로 올리기에는 부족합니다. 제품 질감, 금융 무드, 포스터 레이아웃 중 일부 보조 기준으로만 쓰고, 메인 방향으로 쓰려면 카피 여백과 업종 신뢰 신호를 보강해야 합니다. |
| `bullion_bad_01` | rejected | rejected | pass | 이 레퍼런스는 camping, cute, fake_text, mascot 신호가 강해 금융 투자 브랜드의 신뢰와 프리미엄 상담 톤을 통과하지 못합니다. 특히 cheapSignalRisk 10점, typographyRisk 8점이라 다음 검색/생성에서는 해당 방향을 rejected seed로 차단해야 합니다. |
| `bullion_bad_02` | rejected | rejected | pass | 이 레퍼런스는 casino, fake_text, hype, jackpot 신호가 강해 금융 투자 브랜드의 신뢰와 프리미엄 상담 톤을 통과하지 못합니다. 특히 cheapSignalRisk 10점, typographyRisk 8점이라 다음 검색/생성에서는 해당 방향을 rejected seed로 차단해야 합니다. |

## cosmetics_skincare

- Context: 스킨케어 신제품/상담형 카드뉴스와 랜딩 페이지
- Accuracy: 1.0
- Feedback depth rate: 1.0
- Wiki sources:
  - `design_brain_wiki/05_industry_playbooks/cosmetics_skincare.md`
  - `design_brain_wiki/01_design_principles/typography.md`
  - `design_brain_wiki/04_channel_usability/landing_page.md`
  - `design_brain_wiki/08_feedback_language/direction_feedback.md`

| Candidate | Expected | Actual | Feedback depth | Senior designer feedback |
|---|---:|---:|---:|---|
| `skincare_good_01` | selected | selected | pass | 이 레퍼런스는 blank_headline_area, clean, clinical_warm 신호가 분명해서 화장품 효능 신뢰와 깨끗한 제품 설득력에 맞습니다. 제품 정체성, 무드/신뢰, 레이아웃/카피 여백 기준이 함께 살아 있고 copySpace 6점, layoutUsability 7점이라 스킨케어 신제품 카드뉴스 메인 또는 랜딩 히어로로 확장하기 좋습니다. |
| `skincare_good_02` | selected | selected | pass | 이 레퍼런스는 benefit_copy_space, clean, dermocosmetic 신호가 분명해서 화장품 효능 신뢰와 깨끗한 제품 설득력에 맞습니다. 제품 정체성, 무드/신뢰, 레이아웃/카피 여백 기준이 함께 살아 있고 copySpace 9점, layoutUsability 9점이라 스킨케어 신제품 카드뉴스 메인 또는 랜딩 히어로로 확장하기 좋습니다. |
| `skincare_amb_01` | shortlist | shortlist | pass | 이 레퍼런스는 부분 참고 관점에서는 참고 가치가 있지만 카피 여백이 부족합니다 때문에 selected로 올리기에는 부족합니다. 제형감, 성분 무드, 보조 배경 기준으로만 쓰고, 메인 방향으로 쓰려면 카피 여백과 업종 신뢰 신호를 보강해야 합니다. |
| `skincare_amb_02` | shortlist | shortlist | pass | 이 레퍼런스는 제품 정체성, 무드/신뢰 관점에서는 참고 가치가 있지만 카피 여백이 부족합니다 때문에 selected로 올리기에는 부족합니다. 제형감, 성분 무드, 보조 배경 기준으로만 쓰고, 메인 방향으로 쓰려면 카피 여백과 업종 신뢰 신호를 보강해야 합니다. |
| `skincare_bad_01` | rejected | rejected | pass | 이 레퍼런스는 before_after, claim_risk, fake_text, medical_claim 신호가 강해 화장품 효능 신뢰와 깨끗한 제품 설득력을 통과하지 못합니다. 특히 cheapSignalRisk 10점, typographyRisk 8점이라 다음 검색/생성에서는 해당 방향을 rejected seed로 차단해야 합니다. |
| `skincare_bad_02` | rejected | rejected | pass | 이 레퍼런스는 cheap_discount, crowded_layout, fake_text, low_premium 신호가 강해 화장품 효능 신뢰와 깨끗한 제품 설득력을 통과하지 못합니다. 특히 cheapSignalRisk 10점, typographyRisk 8점이라 다음 검색/생성에서는 해당 방향을 rejected seed로 차단해야 합니다. |

## jewelry_luxury

- Context: 주얼리 럭셔리 컬렉션 캠페인, 인스타그램/배너/랜딩 히어로
- Accuracy: 1.0
- Feedback depth rate: 1.0
- Wiki sources:
  - `design_brain_wiki/05_industry_playbooks/jewelry_luxury.md`
  - `design_brain_wiki/02_brand_strategy/premium_vs_cheap.md`
  - `design_brain_wiki/01_design_principles/whitespace_composition.md`
  - `design_brain_wiki/04_channel_usability/banner.md`

| Candidate | Expected | Actual | Feedback depth | Senior designer feedback |
|---|---:|---:|---:|---|
| `jewelry_good_01` | selected | selected | pass | 이 레퍼런스는 controlled_shadow, diamond, material_quality 신호가 분명해서 주얼리 럭셔리의 소재 신뢰와 절제된 프리미엄 톤에 맞습니다. 제품 정체성, 무드/신뢰, 레이아웃/카피 여백 기준이 함께 살아 있고 copySpace 6점, layoutUsability 7점이라 럭셔리 컬렉션 캠페인 메인 비주얼 또는 배너 히어로로 확장하기 좋습니다. |
| `jewelry_good_02` | selected | selected | pass | 이 레퍼런스는 copy_space, gold_necklace, material_quality 신호가 분명해서 주얼리 럭셔리의 소재 신뢰와 절제된 프리미엄 톤에 맞습니다. 제품 정체성, 무드/신뢰, 레이아웃/카피 여백 기준이 함께 살아 있고 copySpace 6점, layoutUsability 8점이라 럭셔리 컬렉션 캠페인 메인 비주얼 또는 배너 히어로로 확장하기 좋습니다. |
| `jewelry_amb_01` | shortlist | shortlist | pass | 이 레퍼런스는 제품 정체성 관점에서는 참고 가치가 있지만 카피 여백이 부족합니다 때문에 selected로 올리기에는 부족합니다. 소재 디테일, 조명, 착용 무드 보조 기준으로만 쓰고, 메인 방향으로 쓰려면 카피 여백과 업종 신뢰 신호를 보강해야 합니다. |
| `jewelry_amb_02` | shortlist | shortlist | pass | 이 레퍼런스는 제품 정체성, 무드/신뢰 관점에서는 참고 가치가 있지만 카피 여백이 부족합니다 때문에 selected로 올리기에는 부족합니다. 소재 디테일, 조명, 착용 무드 보조 기준으로만 쓰고, 메인 방향으로 쓰려면 카피 여백과 업종 신뢰 신호를 보강해야 합니다. |
| `jewelry_bad_01` | rejected | rejected | pass | 이 레퍼런스는 cheap_gift_box, excessive_sparkle, fantasy_render, low_credibility 신호가 강해 주얼리 럭셔리의 소재 신뢰와 절제된 프리미엄 톤을 통과하지 못합니다. 특히 cheapSignalRisk 10점, typographyRisk 0점이라 다음 검색/생성에서는 해당 방향을 rejected seed로 차단해야 합니다. |
| `jewelry_bad_02` | rejected | rejected | pass | 이 레퍼런스는 cheap_signal, crowded_layout, discount_badge, fake_text 신호가 강해 주얼리 럭셔리의 소재 신뢰와 절제된 프리미엄 톤을 통과하지 못합니다. 특히 cheapSignalRisk 10점, typographyRisk 8점이라 다음 검색/생성에서는 해당 방향을 rejected seed로 차단해야 합니다. |

## Next Actions

- 샘플 테스트는 통과. 다음 단계는 이 evaluator를 03_reference_research report에 연결.
