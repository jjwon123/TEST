# Bad Dataset Rules

## 자료 원문/링크

- Local bad seeds: ../../assets/reference_training/

## 핵심 요약

bad는 금지어 리스트보다 강력한 판단 데이터다. 어떤 신호가 브랜드를 망치는지 이미지 단위로 남기면 AI가 "피해야 할 방향"을 더 명확히 배운다.

## 디자인 판단 질문

- 왜 나쁜가: 업종 오해, 저렴함, 가짜 텍스트, 캐릭터화, 카피 불가?
- 이 문제가 프롬프트 금지어로 막을 수 있는가?
- 이 문제가 fallback 또는 입력 이미지 오염에서 왔는가?
- 비슷한 신호를 앞으로 어떻게 탐지할 것인가?

## 평가 항목

- `badSignals`
- `cheapSignalRisk`
- `typographyRisk`
- `wrongEventTone`
- `fallbackContamination`

## good/bad 적용

- bad 저장 시 image tag를 구체화한다: `mascot_character`, `toy_3d`, `fake_text`, `not_financial`, `not_premium`.

## AI 피드백 문장 예시

- 이 이미지는 제품보다 캐릭터와 장난감 질감이 먼저 보여 금융 투자 브랜드의 신뢰를 해칩니다.

