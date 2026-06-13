# Judge Schema

이 문서는 Senior Designer Brain Wiki를 Reference Judge와 연결하기 위한 공통 평가 필드다.

## Decision

```json
{
  "decision": "selected | shortlist | rejected",
  "confidence": 0,
  "referenceRole": ["product_identity", "mood", "composition", "lighting", "headline_space"],
  "scores": {
    "brandFit": 0,
    "eventFit": 0,
    "industryTrust": 0,
    "brandSystemFit": 0,
    "scalability": 0,
    "distinctiveness": 0,
    "premiumSignal": 0,
    "cheapSignalRisk": 0,
    "layoutUsability": 0,
    "copySpace": 0,
    "visualHierarchy": 0,
    "typographyRisk": 0,
    "colorDiscipline": 0,
    "channelFit": 0
  },
  "goodSignals": [],
  "badSignals": [],
  "reason": "",
  "seniorDesignerFeedback": ""
}
```

## 점수 해석

- `0-3`: 해당 기준을 거의 충족하지 못함.
- `4-6`: 일부 가능성은 있으나 실무 적용 전에 보완 필요.
- `7-8`: 기준에 부합하며 shortlist 이상 가능.
- `9-10`: selected 후보로 강하게 추천 가능.

`cheapSignalRisk`와 `typographyRisk`는 역방향 리스크 점수다. 높을수록 위험하다.

## selected 기준

- `brandFit >= 8`
- `eventFit >= 8`
- `industryTrust >= 7`
- `layoutUsability >= 7`
- `cheapSignalRisk <= 3`
- `typographyRisk <= 3`
- bad seed 유사 신호 0 또는 명확히 낮음

## shortlist 기준

- 방향은 맞지만 특정 역할만 수행한다.
- 제품 정체성은 좋은데 카피 여백이 부족하다.
- 무드는 좋은데 업종 신뢰감이 약하다.
- 구도는 좋지만 브랜드 고급감이 약하다.

## rejected 기준

- 브랜드/업종과 다른 카테고리처럼 보인다.
- 캐릭터, 장난감, 유아적 3D, 캠핑/피크닉, 가짜 텍스트가 핵심 인상이다.
- 카피 영역이 없고 실제 채널 산출물로 쓰기 어렵다.
- 분위기는 좋아도 브랜드 시스템으로 반복 확장하기 어렵다.

