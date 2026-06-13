# My Taste Dataset

기원님이 직접 고른 good/bad/shortlist 판단을 쌓는 폴더다. 이 데이터는 "정답 이미지 저장소"가 아니라 시니어 디자이너 에이전트의 취향과 판단 근거를 학습시키는 기준 데이터다.

## 저장 원칙

- 이미지 파일만 넣지 말고 반드시 이유를 남긴다.
- "좋음/나쁨" 대신 어떤 역할에 좋은지, 어떤 기준을 위반했는지 기록한다.
- 브랜드별로 분리한다.
- 애매한 이미지는 버리지 말고 shortlist로 저장해 판단 경계를 만든다.

## 기본 구조

```text
good/
bad/
shortlist/
feedback_notes.md
metadata.json
```

## 메타데이터 필드

```json
{
  "filename": "",
  "brandProfile": "",
  "decision": "good | bad | shortlist",
  "category": "",
  "tags": [],
  "why": "",
  "usefulFor": [],
  "riskSignals": [],
  "feedbackExample": ""
}
```

