# Industry Boundary Matrix v0.2

목적: 업종별로 같은 시각 신호가 good인지 bad인지 다르게 판단하기 위한 경계표다.

| 시각 신호 | bullion_investment | cosmetics_skincare | jewelry_luxury |
|---|---|---|---|
| 금색 | 안전자산/금속 소재로만 good | 포인트 컬러 정도만 허용 | 제품 소재일 때 good |
| 캐릭터 | 거의 항상 rejected | 브랜드가 playful이면 제한적 허용 | 거의 rejected |
| 물방울 | 금융과 무관, rejected 가능 | 제형/수분감이면 shortlist/good | 대체로 불필요 |
| sparkle | 과하면 casino risk | 거의 불필요 | 통제되면 good, 과하면 cheap |
| dark background | premium finance에 good | 더마/클린 톤에는 무거울 수 있음 | luxury에 good |
| fake text | 항상 rejected | 항상 rejected | 항상 rejected |
| tight macro | 제품 디테일 shortlist | texture shortlist | 소재 detail shortlist |
| 할인 badge | 신뢰 리스크 | 저가 프로모션이면 위험 | luxury value 훼손 |
| abstract background | finance mood shortlist | 보조 배경 shortlist | luxury mood shortlist |
| product-only | identity에는 good, campaign에는 부족 | hero에는 good, story에는 부족 | material proof에는 good, campaign에는 부족 |

## 판단 원칙

- 같은 이미지 신호라도 업종에 따라 의미가 달라진다.
- `selected`는 업종 신호, 브랜드 신호, 채널 실무성이 함께 맞아야 한다.
- 부분적으로 좋은 이미지는 `shortlist`로 남기고 역할을 명시한다.
- 업종 신뢰를 깨는 신호는 미학적으로 좋아도 `rejected`한다.

