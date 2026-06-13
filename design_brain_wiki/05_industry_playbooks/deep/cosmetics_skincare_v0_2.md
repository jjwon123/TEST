# Cosmetics Skincare Deep Playbook v0.2

목적: 스킨케어/화장품 레퍼런스에서 깨끗함, 효능 신뢰, 제형감, 제품 정체성, 광고 리스크를 구분한다.

## 좋은 레퍼런스 기준

### Product And Texture

- 제품 패키지, 제형, 성분 cue 중 최소 하나가 명확하다.
- serum, cream, ampoule, texture가 실제 촬영처럼 credible하다.
- 피부/성분/효능이 과장되지 않고 설득력 있게 보인다.

### Clean Trust

- white, soft neutral, clinical warm tone을 쓴다.
- 더마/클리닉 톤이어도 차갑거나 의료 광고처럼 과장되지 않는다.
- 브랜드가 premium인지 daily인지 dermocosmetic인지 구분된다.

### Campaign Usability

- headline, benefit copy, ingredient proof, CTA를 넣을 구조가 있다.
- 카드뉴스/랜딩에서 product hero와 detail section으로 확장 가능하다.

## 나쁜 레퍼런스 기준

- before-after, medical claim, fake dermatology proof가 강하다.
- 물방울/꽃/스파 무드만 있고 제품/효능 신뢰가 없다.
- neon discount, crowded sale typography, fake text가 있다.
- 피부 표현이 비현실적이라 claim risk가 생긴다.

## 고급스러움과 싸보임의 경계

| 구분 | 고급스러움 | 싸보임 |
|---|---|---|
| 제형 | 실제 질감, 조용한 광택 | 과한 slime/splash |
| 피부 | 자연스럽고 깨끗함 | 비현실적 before-after |
| 패키지 | 정돈된 제품 focus | 박스가 난잡하게 쌓임 |
| 컬러 | clean neutral, controlled pastel | neon sale, 과한 gradient |
| 카피 | benefit proof가 들어갈 여백 | fake label, unreadable text |

## 브랜드 위험 요소

- 화장품인데 의료기기/시술 광고처럼 보이는 것.
- 효능 신뢰 없이 감성 스파 이미지로만 흐르는 것.
- 저가 할인 배너처럼 보이는 것.
- 성분/제형/제품 정체성 없이 예쁜 배경만 있는 것.

## 채널별 사용 기준

### Instagram Cardnews

- 첫 장은 제품명/핵심 효능/제형감이 같이 보여야 한다.
- 성분 설명 장은 texture/ingredient reference를 쓴다.

### Landing Page

- hero는 product + clean trust.
- detail section은 ingredient, texture, proof, usage flow가 필요하다.

### Banner

- 제품과 혜택 카피가 즉시 읽혀야 한다.
- 물방울이나 꽃 장식은 제품을 방해하면 rejected.

## Senior Feedback 예시

- 제형감은 좋지만 제품 패키지와 효능 신뢰가 약해 메인 비주얼보다 texture shortlist가 맞습니다.
- 깨끗한 무드는 있지만 스킨케어 브랜드의 설득 근거가 부족해 selected로는 약합니다.
- before-after와 fake label이 들어가 광고 신뢰와 법적 리스크가 커 rejected가 맞습니다.
- 고급스러운 클린 톤은 있으나 benefit copy를 넣을 공간이 부족해 랜딩 hero로는 보완이 필요합니다.

## Scoring Add-ons

- `productTextureCredibility`
- `efficacyTrust`
- `claimRisk`
- `clinicalWarmth`
- `ingredientProofFit`
- `discountCheapRisk`

## Kiwon Review Update - 2026-06-03 Pinterest Session 001

100장 실제 Pinterest/search 리뷰 결과, 기존 AI judge는 selected/shortlist를 과하게 넓게 잡았다.

- Baseline match: 15/100.
- Kiwon final distribution: selected 29 / shortlist 12 / rejected 59.
- AI selected 41개 중 26개가 rejected로 내려갔다.
- AI shortlist 56개 중 32개가 rejected, 19개가 selected로 이동했다.

### Updated Selected Gate

selected는 단순히 화장품/세일/카피 여백이 보이는 이미지가 아니다. 아래 조건 중 최소 3개 이상이 분명해야 한다.

- 한국 H&B/드럭스토어 세일 감성으로 읽힌다.
- 제품 카테고리, 제형, 성분, 효능 신뢰 중 하나 이상이 명확하다.
- 할인/증정/혜택 위계가 실제 카드뉴스 또는 배너로 전환 가능하다.
- 헤드라인, 혜택 배지, CTA를 얹을 구조가 있다.
- 저가 전단, 해외 영문 sale, generic cosmetic mockup으로 오해되지 않는다.

### Updated Rejected Gate

아래 신호는 기본 rejected로 둔다.

- 화장품 검색어로 수집됐지만 실제 제품/혜택/한국형 이벤트 구조가 약하다.
- 제품은 있지만 이번 이벤트의 H&B 세일/여름 스킨케어/나이아신아마이드 맥락이 약하다.
- 해외 sale 감성 또는 generic cosmetic mockup 느낌이 강하다.
- AI artifact, 깨진 텍스트, nano-banana류 제목/이미지 흔적이 있다.
- 제품보다 배경, 사람, 수영장, 과일, 분위기 장식이 중심이다.

### Updated Shortlist Gate

shortlist는 "애매함"이 아니라 보조 역할이 명확한 이미지에만 쓴다.

- product-only: 제품/제형감은 좋지만 세일 구조가 약하다.
- layout-only: 혜택/카드뉴스 구조는 좋지만 제품 신뢰가 약하다.
- mood-only: 여름/클린 무드는 좋지만 메인 제작 기준으로는 부족하다.

### Copy Space Exception

`copySpace`가 약해도 무조건 rejected로 내리지 않는다. 제품 신뢰와 혜택 구조가 강하면 selected 또는 shortlist 예외가 가능하다. 반대로 copySpace가 좋아도 제품 신뢰, H&B 세일 위계, 로컬 감성이 약하면 selected가 될 수 없다.
