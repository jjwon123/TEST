# Collection Queue

추후 확장할 자료 큐다. 수집 기준은 "많은 링크"가 아니라 "판단 기준으로 변환 가능한가"다.

## 우선 수집

- 금융/투자 브랜드의 premium trust 표현 방식.
- 럭셔리 제품 사진에서 재질, 조명, 여백을 쓰는 방식.
- 카드뉴스/인스타 광고에서 headline space가 살아있는 레이아웃.
- 디자인 시스템이 campaign template로 확장되는 사례.
- 나쁜 AI 이미지 사례: fake text, toy 3D, wrong industry tone, overdecorated luxury.

## 각 자료 저장 포맷

```text
source:
summary:
judgement_questions:
evaluation_fields:
good_application:
bad_application:
feedback_examples:
```

## 금지

- 링크만 저장.
- 예쁜 이미지 감상평만 저장.
- 출처 없이 "느낌상 좋음"으로 저장.
- 브랜드/이벤트/채널 맥락 없이 이미지 단독으로 selected 처리.

