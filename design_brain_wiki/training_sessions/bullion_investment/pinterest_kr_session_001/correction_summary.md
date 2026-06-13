# Correction Summary - pinterest_kr_session_001

- Session: `bullion_investment/pinterest_kr_session_001`
- Source type: `pinterest_search_reference`
- Reviewed: 30 / 30
- Review date source: `kiwon_review_state.json`, updated at `2026-05-31T07:59:40+00:00`

## AI 판단과 기원님 판단 일치율

| Metric | Count | Rate |
|---|---:|---:|
| Overall match | 11 / 30 | 36.7% |
| AI selected match | 2 / 10 | 20.0% |
| AI shortlist match | 0 / 10 | 0.0% |
| AI rejected match | 9 / 10 | 90.0% |

## Decision Shift

| AI decision -> Kiwon decision | Count |
|---|---:|
| selected -> selected | 2 |
| selected -> rejected | 8 |
| shortlist -> selected | 2 |
| shortlist -> rejected | 8 |
| rejected -> selected | 1 |
| rejected -> rejected | 9 |

Kiwon final distribution:

| Final decision | Count |
|---|---:|
| selected | 5 |
| shortlist | 0 |
| rejected | 25 |

Interpretation: this session shows strong over-acceptance. The AI treated Korean Pinterest search relevance and partial finance/gold cues as enough for selected/shortlist, while Kiwon mostly rejected images that were not directly usable as a premium Korean gold-investment event reference.

## Selected 오판 목록

AI가 selected로 올렸지만 기원님이 rejected로 내린 항목이다.

| ID | AI -> Kiwon | File | AI reason | Kiwon reason |
|---|---|---|---|---|
| `bullion_ref_01` | selected -> rejected | `01_0005_the-korean-version-of-money-is-being-displayed-o_1d94d1651b.jpg` | 부분 참고가 확인되고 기준선을 통과 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_04` | selected -> rejected | `04_0002_an-advertisement-for-the-korean-language-textboo_7593f034d4.jpg` | 부분 참고가 확인되고 기준선을 통과 | 빠른 비교에서 상대적으로 부적합 |
| `bullion_ref_13` | selected -> rejected | `13_0016_an-advertisement-with-money-coming-out-of-it-and_cc9dfcacf8.jpg` | 부분 참고가 확인되고 기준선을 통과 | 빠른 비교에서 상대적으로 부적합 |
| `bullion_ref_16` | selected -> rejected | `16_0008_정보성-카드뉴스-안내-배너-인스타그램-콘텐츠-카드뉴스-표지-카드-뉴스-카드뉴스-템플릿_ba2e08a8e9.jpg` | 부분 참고가 확인되고 기준선을 통과 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_19` | selected -> rejected | `19_0018_an-advertisement-for-the-korean-language-website_f52c34f845.jpg` | 부분 참고가 확인되고 기준선을 통과 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_22` | selected -> rejected | `22_0005_an-image-of-a-white-background-with-black-and-ye_783a391ecb.jpg` | 부분 참고가 확인되고 기준선을 통과 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_25` | selected -> rejected | `25_0007_an-image-of-a-website-page-with-information_70b5dab8c7.jpg` | 부분 참고가 확인되고 기준선을 통과 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_28` | selected -> rejected | `28_0002_event-오늘도-변기-위에서-고군분투-중인-당신께-전합니다--작은-습관-하나가-속-편_0115ac7566.jpg` | 부분 참고가 확인되고 기준선을 통과 | 빠른 비교에서 둘 다 제외 |

Pattern: AI selected 기준이 너무 약하다. `부분 참고`, `한국어 검색어`, `금/돈/정보성 카드뉴스 느낌`만으로 selected를 허용했다.

## Rejected 오판 목록

AI가 rejected로 내렸지만 기원님이 selected로 올린 항목이다.

| ID | AI -> Kiwon | File | AI reason | Kiwon reason |
|---|---|---|---|---|
| `bullion_ref_03` | rejected -> selected | `03_0012_an-image-of-a-cartoon-character-with-money-comin_cc6595b7cc.jpg` | mascot_character 위험 요소 | 빠른 비교에서 더 적합한 레퍼런스로 선택 |

Pattern: 현재 hard reject가 너무 단순하다. 캐릭터/일러스트 신호가 있어도, 사용자가 보기에는 카드뉴스 구조, 메시지 전달력, 한국형 금융 콘텐츠 맥락이 상대 비교에서 더 쓸 만할 수 있다. `mascot_character`는 무조건 hard reject가 아니라 표현 톤과 사용 목적에 따라 감점/shortlist 처리할 예외가 필요하다.

## Shortlist 오판 목록

AI shortlist 10개 중 기원님이 shortlist로 유지한 항목은 0개다.

### Shortlist -> selected

| ID | File | AI reason | Kiwon reason |
|---|---|---|---|
| `bullion_ref_05` | `05_0014_an-advertisement-for-the-korean-bank_c670900232.jpg` | brandFit<7.0 | 빠른 비교에서 더 적합한 레퍼런스로 선택 |
| `bullion_ref_14` | `14_0003_a-person-holding-a-gold-ticket-with-the-words-ev_e21257aa41.jpg` | brandFit<7.0 | 빠른 비교에서 더 적합한 레퍼런스로 선택 |

### Shortlist -> rejected

| ID | File | AI reason | Kiwon reason |
|---|---|---|---|
| `bullion_ref_02` | `02_0003_the-website-for-an-investment-firm-in-south-kore_abcb79f2e9.jpg` | brandFit<7.0 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_08` | `08_0013_pin_d742d015d6.jpg` | brandFit<7.0 | 빠른 비교에서 상대적으로 부적합 |
| `bullion_ref_11` | `11_0016_four-postcards-with-two-men-shaking-hands-in-fro_1d93cee6db.jpg` | brandFit<7.0 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_17` | `17_0007_pin_d405029a6c.jpg` | brandFit<7.0 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_20` | `20_0008_pin_7e5683569a.jpg` | brandFit<7.0 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_23` | `23_0009_an-image-of-a-gold-coin-with-the-word-ssg-money_9f8ceef01b.jpg` | brandFit<7.0 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_26` | `26_0012_an-image-of-a-gold-coin-with-the-word-ssg-money_9f8ceef01b.jpg` | brandFit<7.0 | 빠른 비교에서 둘 다 제외 |
| `bullion_ref_29` | `29_0015_a-website-page-with-an-image-of-money-coming-out_1d12900ee8.jpg` | brandFit<7.0 | 빠른 비교에서 둘 다 제외 |

Pattern: `brandFit<7.0` 하나로 shortlist를 만든 기준은 의미가 약하다. Kiwon 판단에서는 shortlist라는 중간값이 거의 쓰이지 않았고, 상대 비교 후 selected 또는 rejected로 명확히 갈렸다.

## 자주 틀린 이유

1. Search relevance를 design relevance로 착각했다.
   - 한국어 Pinterest 쿼리에서 나온 이미지라는 사실이 selected 근거로 과대 반영됐다.
   - `한국`, `금`, `투자`, `카드뉴스` 검색어와 실제 이미지 품질/업종 적합성을 분리해야 한다.

2. `부분 참고`를 selected 근거로 사용했다.
   - AI selected 사유가 반복적으로 "부분 참고가 확인되고 기준선을 통과"였다.
   - selected는 부분 참고가 아니라 제작 기준으로 바로 쓸 수 있는 구조, 톤, 정보 위계가 있어야 한다.

3. 한국형 카드뉴스/배너 품질 기준이 없다.
   - 정보성 템플릿, 웹페이지 캡처, 일반 금융 광고, 의료/교육/기타 업종 카드뉴스가 금 투자 상담 레퍼런스로 올라왔다.
   - 한국어가 있거나 카드뉴스처럼 보여도 업종/행사 목적이 다르면 rejected가 맞다.

4. Bullion product identity 기준이 약하다.
   - 돈, 은행, 투자, 금색 그래픽은 bullion reference가 아니다.
   - 금거래소/골드바/금화/실물 금/금 시세/상담 CTA가 명확해야 한다.

5. Hard reject와 exception 기준이 거칠다.
   - `mascot_character` 하나로 rejected한 `bullion_ref_03`은 기원님이 selected로 올렸다.
   - 캐릭터가 있어도 한국형 카드뉴스 구조와 정보 전달력이 상대적으로 좋으면 selected/shortlist 가능성이 있다.

6. Feedback 문장이 너무 추상적이다.
   - "부분 참고", "기준선을 통과" 같은 문장이 실제 판단 근거를 설명하지 못한다.
   - rejected feedback 중 일부는 위험 신호가 비어 있는데도 "신호가 강하다"고 출력됐다.

## bullion_investment playbook 수정 제안

### Selected 기준 강화

selected는 아래 조건 중 최소 2개 이상을 만족해야 한다.

- 실물 금/골드바/금화/금거래소/금 시세/금 투자 상담 중 하나가 명확하다.
- 한국 카드뉴스/배너/블로그 썸네일로 전환 가능한 정보 위계가 있다.
- 헤드라인/본문/CTA 또는 상담 신청 흐름이 보인다.
- 프리미엄 금융 신뢰감이 있고, 장난감/의료/교육/일반 쇼핑 이벤트로 오해되지 않는다.
- 제작에 바로 참고할 수 있는 레이아웃, 여백, 색, 제품/정보 배치가 있다.

### Rejected 기준 강화

아래는 기본 rejected로 둔다.

- 금/투자 검색어로 나왔지만 실제 이미지는 의료, 교육, 일반 이벤트, 웹페이지 캡처, 범용 템플릿인 경우.
- 돈/동전/금색만 있고 금 투자 상담 또는 금거래소 맥락이 없는 경우.
- 한국어 텍스트가 있어도 업종이 다르거나 메시지 위계가 이벤트 제작에 쓸 수 없는 경우.
- 제품/상담/정보 구조가 없고 단순 배경, 추상 그래픽, 일반 금융 무드에 그치는 경우.

### Shortlist 기준 재정의

shortlist는 "애매한 것"이 아니라 명확한 보조 용도로만 둔다.

- product-only: 제품 정체성은 좋지만 카드뉴스/CTA 구조가 없는 경우.
- layout-only: 카드뉴스 구조는 좋지만 금/실물 투자 정체성이 약한 경우.
- mood-only: 프리미엄 금융 무드는 좋지만 제품/정보 위계가 없는 경우.

이번 세션에서는 기원님 최종 shortlist가 0개였으므로, shortlist를 남발하지 않도록 한다.

### Character/illustration 예외

- mascot/character는 기본 감점이지만 무조건 hard reject는 아니다.
- 한국형 정보성 카드뉴스 구조, 금융/투자 메시지 전달력, CTA 위계가 더 강하면 shortlist 또는 selected 예외를 허용한다.
- 단, 귀여움 자체가 핵심이거나 장난감/게임/캐주얼 이벤트로 읽히면 rejected 유지.

## Reference Judge Rubric 수정 제안

1. selected gate를 점수 평균이 아니라 role coverage로 바꾼다.
   - `bullion_identity`
   - `korean_event_layout`
   - `consultation_or_cta_structure`
   - `premium_finance_trust`
   - `production_usability`

2. `searchQueryFit`를 별도 필드로 낮은 가중치만 준다.
   - 검색어와 맞는 것은 후보 수집 신호이지 selected 근거가 아니다.

3. `partial_reference`는 selected 금지 신호로 본다.
   - AI reason이 "부분 참고"이면 기본 shortlist 이하.
   - selected는 "바로 제작 기준으로 쓸 수 있음"이어야 한다.

4. `wrong_industry_cardnews` detector를 추가한다.
   - medical, education, generic event, banking-only, website screenshot, shopping coupon 등.

5. shortlist gate를 더 엄격하게 정의한다.
   - missing axis가 1개일 때만 shortlist.
   - missing axis가 2개 이상이면 rejected.

6. hard reject를 exception-aware로 바꾼다.
   - `mascot_character`는 hard reject가 아니라 `toneRisk`로 시작.
   - `childish/toy/game-like`와 결합하면 hard reject.
   - 정보 구조와 금융 맥락이 강하면 감점 후 재평가.

7. confidence 산식을 교정한다.
   - AI가 selected로 틀린 항목 대부분이 confidence 0.79~0.84였다.
   - role coverage가 약하거나 reason이 generic이면 confidence를 0.65 이하로 제한한다.

## Feedback Phrase 보강 제안

### Selected

- 이 레퍼런스는 금 투자 상담 이벤트에 필요한 제품/정보/CTA 위계가 함께 보여 제작 기준으로 바로 참고할 수 있습니다.
- 한국형 카드뉴스 흐름과 금 투자 메시지가 동시에 살아 있어 메인 레퍼런스로 둘 수 있습니다.
- 골드바/금 시세/상담 신청 맥락이 분명하고, 헤드라인을 얹을 여백과 정보 구조가 있어 selected로 봅니다.

### Shortlist

- 레이아웃은 좋지만 금 투자 상담 맥락이 약해 구조 보조 레퍼런스로만 둡니다.
- 제품 정체성은 보이지만 상담 이벤트의 카피/CTA 위계가 부족해 selected보다는 shortlist가 맞습니다.
- 금융 무드는 참고 가능하지만 실물 금/금거래소 신호가 약해 단독 메인 레퍼런스로는 부족합니다.

### Rejected

- 한국어 카드뉴스처럼 보이지만 업종과 메시지가 금 투자 상담과 맞지 않아 제외합니다.
- 돈/금색 요소만 있고 실물 금 투자나 상담 신청 구조가 없어 bullion reference로 쓰기 어렵습니다.
- 검색어로는 걸렸지만 실제 이미지는 범용 템플릿/다른 업종 콘텐츠라 위키 학습 기준에서 제외해야 합니다.
- 정보량은 있어도 제품 정체성, 금융 신뢰감, 이벤트 CTA 중 핵심 축이 빠져 rejected가 맞습니다.

### Feedback Quality Rule

- 금지 문장: `부분 참고가 확인됩니다`, `기준선을 통과했습니다`, `신호가 강합니다`처럼 근거 없는 일반문.
- 필수 문장 구조: `[쓸 수 있는 축] + [부족한 축] + [최종 판단] + [다음 검색/제작에 반영할 기준]`.

## 다음 액션

1. `REFERENCE_JUDGE_RUBRIC.json`에 role coverage와 searchQueryFit 분리 반영.
2. `bullion_investment_v0_2.md`에 한국형 금거래소 카드뉴스 selected/rejected 기준 추가.
3. feedback language에 selected/shortlist/rejected phrase를 위 문장으로 보강.
4. 다음 Pinterest 한국어 세션부터 AI selected의 reason이 `부분 참고`이면 자동으로 shortlist 이하로 내린다.
5. 빠른 비교 UI에서 기본 사유 외에 버튼별 세부 사유 태그를 남길 수 있도록 개선한다.
