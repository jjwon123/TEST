# 프롬프트 작성 규칙

이 문서는 이벤트 콘텐츠 자동화에서 텍스트 생성 프롬프트와 이미지 생성 프롬프트를 작성할 때 지켜야 할 기준이다.

## 공통 원칙

- 이벤트 정보, 브랜드 기준, 채널 목적을 함께 반영한다.
- 한 번에 예쁘게 보이는 문장보다 재사용 가능한 구조를 우선한다.
- 생성 결과가 사람이 검토하고 수정하기 쉬워야 한다.
- 출력 파일은 JSON과 Markdown을 함께 둔다.
- AI가 확신할 수 없는 정보는 만들어내지 말고 `needs_review`로 표시한다.

## 텍스트 프롬프트 기준

텍스트 산출물은 다음을 명확히 해야 한다.

- 대상 고객
- 이벤트 핵심 혜택
- 채널별 역할
- CTA
- 금지 표현
- 필요한 수정/승인 포인트

좋은 출력은 다음 형식을 가진다.

- 구조화된 JSON
- 사람이 읽는 Markdown 요약
- 결정 이유
- 리스크 또는 검토 필요 항목

## 이미지 프롬프트 기준

이미지 프롬프트는 다음 요소를 포함한다.

- 주 피사체
- 이벤트 분위기
- 브랜드 톤
- 채널 규격
- 한국어 카피가 들어갈 여백
- 조명, 질감, 촬영 스타일
- 피해야 할 요소
- 모델별 파라미터 또는 후처리 힌트

## 기본 이미지 무드

- trustworthy
- calm
- premium
- clear information design
- high quality commercial advertising image
- realistic lighting
- refined commercial composition

## 기본 구성 규칙

- 한국어 헤드라인을 위한 깨끗한 여백을 남긴다.
- 배경을 복잡하게 만들지 않는다.
- 작은 SNS 크기에서도 주 피사체가 식별되어야 한다.
- 제품 유지가 필요한 경우 제품 형태, 라벨, 컬러 왜곡을 강하게 금지한다.
- 후보마다 구도와 무드를 다르게 만든다.

## 피해야 할 이미지 방향

- 과도한 명품 클리셰
- 공격적인 투자 이미지
- 도박 또는 투기 느낌
- 비현실적인 제품 변형
- 카피를 얹기 어려운 복잡한 배경
- 의미 없는 장식 위주의 이미지

## 텍스트 처리 규칙

- 이미지 생성 프롬프트는 본문 카피를 직접 렌더링하지 않는다.
- 이미지에는 한국어 헤드라인을 얹을 빈 영역만 요구한다.
- 기본 포함 문구:
  - `blank space for Korean headline`
  - `poster layout with empty text area`
  - `no readable text`
  - `no fake typography`
- 최종 텍스트, CTA, 법적 문구는 이후 디자인/오버레이 단계에서 올린다.

## 금/은/투자/상담 이벤트 규칙

- 레퍼런스와 이미지 방향은 프리미엄 금융, 금 제품, 자산관리, 상담 이벤트 시각 언어를 우선한다.
- `bullion_investment` profile에서는 positive prompt와 reference prompt hint에서 아래 단어를 제거한다.
  - mascot, character, cute, camping, picnic, tent, toy, diorama, cartoon, kawaii, playful, wine, bottle, package box
- 위 단어들은 negative prompt에만 강한 차단어로 넣는다.
- 피해야 할 방향:
  - kids toy style
  - cute mascot centered
  - cartoon camping
  - theme park
  - picnic toy scene
  - wine bottle
  - random package box
  - childlike 3d illustration
  - excessive kawaii mood
  - fake text poster
- 이미지 프롬프트는 귀여움보다 신뢰감, 명확함, 제품/카테고리 관련성, 빈 텍스트 영역을 우선한다.

## 프롬프트 산출물 위치

```text
03_image_candidates/output/image-prompts.json
03_image_candidates/output/midjourney-prompts.txt
runs/[run-dir]/03_visual_candidates/image-prompts.json
```

## 프롬프트 개선 기록

실패한 프롬프트, 수정한 프롬프트, 모델별 차이는 [[05_MODEL_TEST]]와 [[06_TROUBLESHOOTING]]에 남긴다.
