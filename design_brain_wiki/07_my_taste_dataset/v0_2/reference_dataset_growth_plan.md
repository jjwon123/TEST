# Reference Dataset Growth Plan v0.2

목표: good/bad/shortlist 레퍼런스 300장 이상을 기원님 판단 이유와 함께 축적한다.

## 수량 목표

| profile | good | shortlist | bad | total |
|---|---:|---:|---:|---:|
| bullion_investment | 40 | 30 | 30 | 100 |
| cosmetics_skincare | 40 | 30 | 30 | 100 |
| jewelry_luxury | 40 | 30 | 30 | 100 |

총 300장.

## 저장 위치

```text
assets/reference_training/<profile>/good/
assets/reference_training/<profile>/shortlist/
assets/reference_training/<profile>/bad/
```

현재 `reference_training.py`는 good/bad 중심이므로 shortlist는 v0.3에서 scoring에 정식 반영한다.

## 파일당 필수 메타데이터

```json
{
  "filename": "",
  "decision": "good | shortlist | bad",
  "category": "",
  "tags": [],
  "why": "",
  "usefulFor": [],
  "riskSignals": [],
  "kiwonFeedback": "",
  "agentRuleUpdate": ""
}
```

## 수집 세션 운영

1. 한 세션에 한 업종만 본다.
2. 30장 단위로 good/shortlist/bad를 나눈다.
3. selected 비율이 너무 높으면 기준이 느슨한 것이다.
4. bad가 너무 적으면 금지 기준이 아직 부족한 것이다.
5. shortlist가 많아야 판단 경계가 정교해진다.

## v0.3 연결 기준

- profile별 최소 100장 누적.
- 기원님 피드백 문장 최소 30개 이상.
- actual reference 20장 테스트에서 feedback depth 0.8 이상.
- selected 과승인률 10% 이하.

