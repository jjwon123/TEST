# Wiki Update Suggestions - Bullion Investment Session 001

## Bullion playbook 보강점

- product_reference는 제품 정체성 기준으로는 good이어도, 카피 여백과 상담 이벤트 구조가 없으면 shortlist로 둔다.
- poster_layout_reference는 headline area와 CTA 위계가 있으면 selected 후보로 볼 수 있다.
- finance_mood_reference는 제품 없이도 무드 기준으로는 좋지만, 단독 selected가 되려면 상담/자산관리 맥락과 카피 구조가 필요하다.

## Feedback phrase 보강점

- `제품 정체성은 좋지만 메인 비주얼이 아니라 제품 보조 레퍼런스입니다.`
- `금융 신뢰 무드는 맞지만 실제 이벤트 구조가 약해 shortlist가 안전합니다.`
- `카피 여백과 CTA 위계가 있어 제작 기준으로 selected 가능성이 있습니다.`
- `캐릭터/장난감/fake text 신호는 금융 투자 브랜드에서 미학과 무관하게 rejected입니다.`

## Reference Judge rubric 수정점

- selected gate에 `referenceRoleCoverage`를 추가한다.
- product/mood/layout 중 2개 이상 충족하면 selected 후보, 1개만 충족하면 기본 shortlist.
- bad signal은 점수와 무관하게 hard reject.
- `confidence`는 점수뿐 아니라 역할 coverage와 risk signal 수로 계산한다.
