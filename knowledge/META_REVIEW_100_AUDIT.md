# Meta 광고 성격 검수 100장 감사 보고서

## 범위와 방법

- 대상: `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/references/` 100장
- 방식: 번호가 표시된 25장 단위 콘택트시트 4개를 전수 검토하고, 경계 사례와 대표 사례를 원본 크기로 추가 확인했다.
- 단일 주분류를 부여했다. 여러 성격이 겹칠 때는 `reject_noise → card_news → promotion_text_heavy → device → jewelry_craft → jewelry_product → model_lifestyle → brand_campaign → product_clean` 우선순위를 적용했다.
- 기존 `ai_judgement.json`은 수정하지 않았다.
- 상세 전수 결과: `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001/manual_meta_character_audit.json`

## 분류 통계

| 분류 | 수량 | 비율 | 판단 요약 |
|---|---:|---:|---|
| `promotion_text_heavy` | 34 | 34% | 가격, 할인, 증정, 랭킹, 한정 혜택, 구매 CTA가 시각 계층을 지배 |
| `model_lifestyle` | 19 | 19% | 인물, 착용, 라이프스타일 장면이 주피사체 |
| `jewelry_product` | 16 | 16% | 주얼리 정물, 매크로, 디스플레이 |
| `card_news` | 10 | 10% | 비교, 원리, 근거, 설명 패널을 읽어야 하는 정보 슬라이드 |
| `brand_campaign` | 7 | 7% | 직접 판매보다 브랜드 세계관과 캠페인 콘셉트가 중심 |
| `device` | 7 | 7% | 설명 카드보다 뷰티 디바이스 자체가 중심 |
| `product_clean` | 5 | 5% | 화장품 제품이 중심이고 가격/정보 구조가 지배하지 않음 |
| `jewelry_craft` | 2 | 2% | 세팅과 제작 공정 중심 |
| `reject_noise` | 0 | 0% | 파손, 무관, 사용 불가 노이즈 없음 |

화장품·스킨케어 62장 중 `promotion_text_heavy`가 34장, `card_news`가 10장이다. 합계 44장, 즉 화장품 표본의 약 71%가 깨끗한 제품/브랜드 키비주얼 학습 풀에서는 제외되어야 한다. 반면 주얼리 표본은 제품 정물, 모델 착용, 브랜드 캠페인, 공예 과정으로 비교적 명확하게 분리된다.

## 핵심 결론

### 화장품 할인 문구형 제외 기준

다음 중 하나가 상위 2개 시각 초점에 해당하면 `product_clean`이나 `brand_campaign`에서 제외하고 `promotion_text_heavy`로 분류한다.

- 가격 또는 가격대: `1만원대`, `12,250원`, `24,500원`
- 할인율 또는 할인 강조: `53%`, `29% OFF`, `최대 41% 할인`
- 묶음과 증정: `1+1`, `1+1+1`, `10매+2매 증정`, 무료 증정
- 판매 순위와 기간 압박: `1위`, `한정 특가`, `오늘만`, `썸머세일`
- 하단 구매 바, 판매처 배지, CTA가 제품 이미지보다 강하게 작동하는 구성

제품이 크게 보여도 큰 숫자, 가격, 할인 배지, 증정 구조가 먼저 읽히면 프로모션이다. 반대로 판매처 배지 하나만 있고 제품 정물과 소재 표현이 압도적으로 우세하면 자동 제외하지 않는다.

### 카드뉴스 제외 기준

다음 구조가 주된 읽기 방식이면 `card_news`로 제외한다.

- `POINT 1`, `#1 원리`처럼 번호와 단계가 있는 설명
- 좌우 비교, 기존/신형 비교, 팀별 비교
- 전후 사진, 수치, 차트, 시험 성적서, 인증서
- 기능 원리, 사용법, 효능 근거를 여러 패널로 설명
- 문장과 증거 블록을 순서대로 읽어야 의미가 완성되는 구성

단일 헤드라인과 제품 사진만 있는 이미지는 카드뉴스가 아니다. 설명 패널과 근거 블록이 주구조일 때 카드뉴스다. 뷰티 디바이스도 히어로 비주얼은 `device`, 기능 비교·근거 슬라이드는 `card_news`로 분리한다.

## 대표 원본 확인

- `010_medicube_1601d79a11.jpg`: 큰 비교 헤드라인이 있지만 디바이스 출시 키비주얼 성격이 강해 `device`.
- `014_sulwhasoo_e1014e0739.jpg`: 제품 판매보다 협업 전시와 브랜드 세계관이 중심이라 `brand_campaign`.
- `017_cartier_3986d0b682.jpg`: 팬더 콘셉트와 행사 아이덴티티가 중심인 `brand_campaign`.
- `023_van-cleef_d9a718be30.jpg`: 보석 세팅 공정을 근접 촬영한 명확한 `jewelry_craft`.
- `046_medicube_ed899af229.jpg`: `POINT 1`과 좌우 연결 비교를 읽어야 하므로 `card_news`.
- `059_torriden_a7f1c303d2.jpg`: PR팀/소셜팀 비교 구조라 `card_news`.
- `077_medicube_2bb8708af0.jpg`: 효능 주장, 전후 근거, 수치 패널이 결합된 `card_news`.
- `098_medicube_2d1e8f290e.jpg`: 번호가 있는 원리 설명과 비교 열이 명확한 `card_news`.

## 운영 권고

- 깨끗한 브랜드/제품 키비주얼 학습 풀에서는 `promotion_text_heavy`와 `card_news`를 기본 제외한다.
- 두 분류는 폐기하지 말고 각각 `commerce_promotion`과 `educational_carousel` 전용 풀로 분리하는 편이 좋다.
- `product_clean` 자동 선별은 “제품이 보이는가”보다 “가격·혜택·설명 패널이 상위 시각 초점을 점유하는가”를 먼저 검사해야 한다.
- `reject_noise`는 이번 표본에서 0장이므로, 현재 세션의 주요 품질 문제는 파일 파손이 아니라 레퍼런스 역할 혼합이다.

## Pinterest 혼입 확인

- Meta 검수 100장 모두 `sourceType=meta_ad_library`, `sourceIsPinterest=false`이며 원본 경로는 `references/meta_ads/brand_registry_runs`다.
- 모든 `sourceUrl`은 Facebook Meta Ad Library 검색 URL이다.
- 기존 Pinterest 검수 이미지 274장과 SHA-256 정확 중복 및 dHash 근접 중복을 대조한 결과 모두 0장이다.
- Pinterest 이미지가 실제로 혼입된 것이 아니라, Meta 광고의 카드뉴스·프로모션 문구형 디자인이 Pinterest 수집 이미지와 비슷하게 보인 경우다.
- `03_reference_research`의 Meta provider는 `manual_meta_character_audit.json`을 읽어 `promotion_text_heavy`, `card_news`, `reject_noise`를 기본 제외한다.
