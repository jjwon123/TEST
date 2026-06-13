# 캠페인 제작 프로젝트 — 섹션별 파이프라인 기초 설계서

## 문서 목적

이 문서는 기존 6단계 캠페인 제작 파이프라인을 유지하되, 각 단계를 독립 실행 가능한 세부 파이프라인으로 확장하기 위한 기초 설계서입니다.

이 프로젝트는 “한 번 클릭해서 최종 산출물까지 자동 생성하는 도구”가 아니라, 캠페인 제작 과정에서 필요한 판단, 구조화, 초안 생성, 검수, 패키징을 단계별로 지원하는 제작 파이프라인입니다.

---

## 전체 구조 요약

```text
0. Project Control Pipeline
   └─ 이번 실행 범위와 상태 관리

1. Campaign Brief Pipeline
   └─ 이벤트 정보를 작업 가능한 브리프로 변환

2. Message & Copy Pipeline
   └─ 채널별로 쓸 수 있는 카피 시스템 생성

3. Channel Output Planning Pipeline
   └─ 이번에 무엇을 만들지 결정

4. Visual Direction Pipeline
   └─ 디자인 방향과 레이아웃 전략 정의

5. Figma Production Pipeline
   └─ 작업 가능한 디자인 초안 생성

6. QA & Packaging Pipeline
   └─ 검수하고 최종 사용 파일로 정리
```

---

# 0. Project Control Pipeline

## 목적

전체 실행 단위를 관리하고, 이번 작업에서 어디까지 진행할지 정의합니다.  
각 단계가 독립적으로 실행될 수 있도록 실행 범위, 저장 위치, 기준 파일, 상태값을 관리하는 컨트롤 타워 역할을 합니다.

## 입력값

- 프로젝트명
- 캠페인명 또는 이벤트명
- 실행 날짜
- 실행 모드
  - brief only
  - copy only
  - output planning only
  - visual direction only
  - figma draft only
  - qa only
  - full flow
- 사용할 디자인 시스템
- 사용할 스킬 목록
- 이전 runs 참조 여부
- 최종 저장 위치

## 처리 흐름

```text
0-1. 실행 요청 수집
0-2. 실행 모드 판단
0-3. run_id 생성
0-4. runs 폴더 생성
0-5. 기준 파일 로드
0-6. 이전 실행 결과 참조 여부 판단
0-7. 이번 실행 범위 확정
0-8. 다음 단계로 전달할 run-config 생성
```

## 세부 모듈

### 0-1. Run Request Intake

사용자가 이번에 원하는 작업 범위를 수집합니다.

예:

```text
이번엔 브리프까지만 정리
이번엔 카피까지
이번엔 Figma 초안만
이번엔 QA만
```

### 0-2. Execution Mode Resolver

요청을 실행 모드로 변환합니다.

예:

```json
{
  "mode": "copy_only",
  "start_step": 2,
  "end_step": 2
}
```

### 0-3. Run ID Generator

실행 단위를 추적하기 위한 ID를 생성합니다.

예:

```text
runs/2026-04-27_time-deal-fast-shipping/
```

### 0-4. Project State Loader

현재 프로젝트 상태를 불러옵니다.

확인 대상:

- design-system.md
- 기존 campaign-brief.md
- 이전 copy-bank.md
- output-checklist.json
- visual-direction.md
- figma-frame-schema.json
- qa-report.md

## 산출물

```text
run-config.json
run-log.md
project-state.md
step-status.json
```

## 검수 기준

- 이번 실행 범위가 명확한가
- 실행하지 않을 단계도 명확히 제외되었는가
- 필요한 기준 파일이 존재하는가
- 이전 실행 결과를 참조할지 여부가 정리되었는가
- 다음 단계에 넘길 최소 데이터가 준비되었는가

## 실패 케이스

- 실행 범위가 모호함
- 이전 결과와 현재 요청이 충돌함
- 필수 기준 파일이 없음
- run_id가 중복됨
- 특정 단계만 실행하려는데 이전 단계 산출물이 없음

## 사람이 판단할 부분

- 이번 작업을 어디까지 진행할지
- 이전 결과를 재사용할지 새로 만들지
- 전체 실행인지 일부 단계 실행인지
- 캠페인 단위인지 단일 채널 작업인지

## 다음 단계로 넘길 데이터

```json
{
  "run_id": "2026-04-27_time-deal-fast-shipping",
  "campaign_name": "빠른 배송 금은 상품 타임딜",
  "execution_mode": "brief_to_copy",
  "design_system_path": "design-system.md",
  "output_root": "runs/2026-04-27_time-deal-fast-shipping/"
}
```

---

# 1. Campaign Brief Pipeline

## 목적

흩어진 이벤트 정보를 디자인, 카피, 채널 제작에 사용할 수 있는 구조화된 브리프로 변환합니다.

## 입력값

- 이벤트명
- 이벤트 목적
- 상품명
- 판매 방식
- 판매 기간
- 혜택
- 가격 조건
- 수량 조건
- 배송 조건
- 고객 주의사항
- 운영상 제한사항
- 참고 이미지 또는 기존 문구

## 처리 흐름

```text
1-1. Raw Input Intake
1-2. Information Extraction
1-3. Information Normalization
1-4. Missing Info Check
1-5. Campaign Type Classification
1-6. Core Message Definition
1-7. Customer Risk Check
1-8. Final Brief Export
```

## 세부 모듈

### 1-1. Raw Input Intake

사용자가 제공한 원문을 그대로 저장합니다.  
이 단계에서는 정리하지 않고 원본성을 유지합니다.

산출 예:

```text
raw-input.md
```

### 1-2. Information Extraction

원문에서 핵심 정보를 추출합니다.

추출 항목:

- 상품
- 혜택
- 가격
- 기간
- 수량
- 배송
- 채널
- 주의사항
- 운영 조건

### 1-3. Information Normalization

추출한 정보를 일정한 형식으로 정리합니다.

예:

```json
{
  "campaign_type": "time_deal",
  "main_benefit": "고정가 한정 판매",
  "delivery_message": "빠른 배송 가능 상품 중심",
  "stock_condition": "한정 수량"
}
```

### 1-4. Missing Info Check

부족한 정보를 체크합니다.

예:

```text
- 판매 시작일 미입력
- 종료 기준 미입력
- 수량 제한 기준 미입력
- 적용 상품 리스트 미확정
```

### 1-5. Campaign Type Classification

캠페인 유형을 분류합니다.

기본 유형:

- 타임딜
- 신상품 입고
- 빠른 배송 상품
- 시즌 기획전
- 콜라보 이벤트
- 쿠폰 이벤트
- 당첨자 발표
- 배송 공지
- 일반 공지
- 상세페이지 보강

### 1-6. Core Message Definition

이번 캠페인에서 가장 중요한 메시지를 한 문장으로 정의합니다.

예:

```text
시장가 변동과 무관하게 빠른 배송 가능한 금·은 상품을 고정가로 한정 판매한다.
```

### 1-7. Customer Risk Check

고객 오해와 CS 가능성을 체크합니다.

체크 항목:

- 가격 고정 조건이 명확한가
- 모든 상품이 빠른 배송인지 일부만 해당하는지 명확한가
- 수량 소진 기준이 명확한가
- 배송일 보장이 과장되지 않았는가
- 쿠폰/할인 중복 적용 여부가 명확한가

### 1-8. Final Brief Export

다음 단계에서 바로 쓸 수 있는 브리프를 생성합니다.

## 산출물

```text
raw-input.md
campaign-brief.md
campaign-brief.json
missing-info-report.md
risk-check.md
core-message.md
```

## 검수 기준

- 이벤트 목적이 한 문장으로 정리되었는가
- 고객에게 반드시 보여야 할 정보가 빠지지 않았는가
- 상품, 혜택, 조건, 기간이 분리되어 있는가
- 과장될 수 있는 표현이 사전에 표시되었는가
- 다음 단계에서 카피로 전환 가능한 구조인가

## 실패 케이스

- 이벤트 목적이 불명확함
- 상품과 혜택이 섞여 있음
- 일부 상품 조건을 전체 조건처럼 해석함
- 판매 조건과 배송 조건이 구분되지 않음
- 고객이 오해할 수 있는 표현이 남아 있음

## 사람이 판단할 부분

- 이번 캠페인의 핵심 목적
- 빠른 배송, 가격, 한정 수량 중 무엇을 가장 강조할지
- 제외해야 할 채널이나 산출물이 있는지
- 고객에게 민감할 수 있는 조건을 어디까지 노출할지

## 다음 단계로 넘길 데이터

```json
{
  "campaign_type": "time_deal",
  "core_message": "빠른 배송 가능한 금·은 상품을 고정가로 한정 판매",
  "main_products": [],
  "main_benefit": "고정가 한정 판매",
  "risk_notes": [
    "모든 상품이 빠른 배송 대상인지 일부 상품인지 명확히 표기 필요"
  ]
}
```

---

# 2. Message & Copy Pipeline

## 목적

브리프를 기반으로 채널별로 사용할 수 있는 메시지 체계와 카피 초안을 생성합니다.  
단순히 문장을 예쁘게 쓰는 것이 아니라, 메시지 위계와 운영 안정성을 함께 설계합니다.

## 입력값

- campaign-brief.md
- campaign-brief.json
- core-message.md
- risk-check.md
- 브랜드 톤앤매너
- 채널별 제한 조건

## 처리 흐름

```text
2-1. Message Hierarchy
2-2. Copy Angle Generation
2-3. Channel Tone Mapping
2-4. CTA Generation
2-5. Notice Copy Generation
2-6. CS Safe Copy
2-7. Copy QA
2-8. Copy Bank Export
```

## 세부 모듈

### 2-1. Message Hierarchy

메시지 우선순위를 정합니다.

구조:

```text
1순위 메시지: 고객이 가장 먼저 알아야 할 내용
2순위 메시지: 혜택 또는 조건
3순위 메시지: 상품/기간/수량
보조 메시지: 주의사항, 배송, 운영 조건
```

### 2-2. Copy Angle Generation

여러 각도의 카피를 생성합니다.

각도 예:

- 가격 강조형
- 수량 강조형
- 빠른 배송 강조형
- 신뢰 강조형
- 프리미엄 강조형
- 시즌성 강조형
- 공지형
- 긴급형

### 2-3. Channel Tone Mapping

채널별 톤을 조정합니다.

예:

```text
인스타그램: 짧고 시각 중심
홈페이지 팝업: 즉시 이해 가능한 안내형
카카오 알림톡: 명확하고 운영 안정적인 문장
네이버 블로그: 설명형, 검색 친화적
상세페이지 상단: 구매 판단 보조형
```

### 2-4. CTA Generation

행동 유도 문구를 생성합니다.

예:

```text
한정 수량 확인하기
고정가 상품 보러가기
빠른 배송 상품 확인하기
쿠폰 받기
자세히 보기
```

### 2-5. Notice Copy Generation

운영 문구와 공지 문구를 생성합니다.

포함 항목:

- 판매 기간
- 수량 소진 안내
- 배송 조건
- 가격 변동 관련 안내
- 쿠폰/할인 제한
- 고객 유의사항

### 2-6. CS Safe Copy

오해를 줄이는 문장으로 정리합니다.

예:

```text
빠른 배송 상품은 일부 대상 상품에 한해 적용됩니다.
한정 수량 소진 시 별도 공지 없이 종료될 수 있습니다.
고정가는 해당 이벤트 기간 내 지정 상품에만 적용됩니다.
```

### 2-7. Copy QA

카피를 검수합니다.

검수 항목:

- 과장 표현
- 가격 오해
- 배송 보장 표현
- 불필요한 수식어
- 중복 문장
- 채널 부적합 문장
- 핵심 정보 누락

### 2-8. Copy Bank Export

사용 가능한 카피 묶음을 저장합니다.

## 산출물

```text
message-system.md
copy-bank.md
channel-copy.json
cta-list.md
notice-copy.md
cs-safe-copy.md
copy-qa-report.md
```

## 검수 기준

- 핵심 메시지가 모든 채널에서 일관되는가
- 채널별 문장 길이와 톤이 적절한가
- 고객 오해 가능성이 있는 문구가 제거되었는가
- CTA가 명확한가
- 운영 문구가 빠지지 않았는가

## 실패 케이스

- 모든 채널에 같은 문장을 사용함
- 인스타그램 카피가 너무 설명적임
- 알림톡 문구가 과하게 광고성임
- 배송 보장처럼 보이는 표현 사용
- 빠른 배송 조건이 불명확함
- 고객 주의사항이 누락됨

## 사람이 판단할 부분

- 어떤 카피 각도를 메인으로 사용할지
- 얼마나 강한 프로모션 톤을 사용할지
- 브랜드 신뢰감과 판매 자극 중 어느 쪽을 우선할지
- CS 방어 문구를 어느 정도 노출할지

## 다음 단계로 넘길 데이터

```json
{
  "main_copy": "빠른 배송 금·은 상품, 고정가 한정 판매",
  "sub_copy": "시장가 변동과 무관하게 지정 상품을 한정 수량으로 제공합니다.",
  "cta": "고정가 상품 확인하기",
  "channel_copy": {
    "instagram": [],
    "kakao": [],
    "homepage_popup": [],
    "naver_blog": []
  }
}
```

---

# 3. Channel Output Planning Pipeline

## 목적

이번 캠페인에서 실제로 어떤 산출물을 만들지 결정합니다.  
모든 채널을 무조건 생성하지 않고, 캠페인 목적과 운영 효율에 맞게 필수/선택/제외 산출물을 구분합니다.

## 입력값

- campaign-brief.json
- message-system.md
- channel-copy.json
- 캠페인 유형
- 운영 채널 목록
- 제작 가능 리소스
- 마감 일정

## 처리 흐름

```text
3-1. Channel Requirement Mapping
3-2. Output Set Recommendation
3-3. Format Specification
3-4. Content Allocation
3-5. Production Priority
3-6. Human Selection Point
3-7. Output Checklist Export
```

## 세부 모듈

### 3-1. Channel Requirement Mapping

캠페인 유형별 적합 채널을 판단합니다.

예:

```text
타임딜: 홈페이지 팝업, 인스타 피드, 카카오 메시지
배송공지: 공지 이미지, 알림톡, 홈페이지 공지
콜라보 이벤트: 카드뉴스, 피드, 블로그, 팝업
신상품 입고: 피드, 상세 상단 이미지, 블로그 썸네일
```

### 3-2. Output Set Recommendation

산출물을 필수/선택/제외로 나눕니다.

구조:

```text
필수: 반드시 제작해야 하는 산출물
선택: 상황에 따라 제작할 산출물
제외: 이번 캠페인에는 비효율적인 산출물
```

### 3-3. Format Specification

각 산출물의 규격을 정의합니다.

예:

```text
인스타 피드: 1080x1350
카드뉴스: 1080x1350, 3~5장
홈페이지 팝업: 1200x800
블로그 썸네일: 1200x630
공지 이미지: 1200x1200
```

### 3-4. Content Allocation

각 이미지 또는 채널에 어떤 메시지를 배치할지 정합니다.

예:

```text
피드 1장: 메인 카피 + 대표 상품 + CTA
카드뉴스 1장: 이벤트 메인
카드뉴스 2장: 상품/혜택
카드뉴스 3장: 조건/주의사항
팝업: 메인 혜택 + CTA + 기간
```

### 3-5. Production Priority

제작 우선순위를 정합니다.

예:

```text
1순위: 홈페이지 팝업
2순위: 인스타 피드
3순위: 카카오 메시지
4순위: 스토리
5순위: 블로그 이미지
```

### 3-6. Human Selection Point

사람이 실제 제작할 산출물을 확정합니다.

확정 항목:

- 이번에 만들 것
- 이번에 제외할 것
- 나중에 만들 것
- Figma로 넘길 것
- 텍스트만 필요한 것

### 3-7. Output Checklist Export

최종 제작 목록을 생성합니다.

## 산출물

```text
output-plan.md
output-checklist.json
channel-format-spec.md
content-allocation.md
production-priority.md
human-selection.md
```

## 검수 기준

- 캠페인 목적에 맞는 산출물만 선택되었는가
- 불필요한 채널 제작이 제거되었는가
- 각 산출물의 규격이 명확한가
- 각 산출물에 들어갈 메시지가 배정되었는가
- 제작 우선순위가 정리되었는가

## 실패 케이스

- 모든 채널을 무조건 생성함
- 카드뉴스가 필요 없는 이벤트에 카드뉴스 생성
- 카카오 메시지만 필요한 공지에 이미지 과다 제작
- 채널별 사이즈 미정
- 같은 메시지가 모든 산출물에 반복됨

## 사람이 판단할 부분

- 이번 캠페인에서 실제로 제작할 채널
- 리소스 대비 효율이 낮은 산출물 제외 여부
- 카드뉴스 장수
- 블로그 콘텐츠 필요 여부
- 홈페이지 팝업 노출 여부

## 다음 단계로 넘길 데이터

```json
{
  "required_outputs": [
    {
      "channel": "homepage",
      "type": "popup",
      "size": "1200x800",
      "priority": 1
    },
    {
      "channel": "instagram",
      "type": "feed",
      "size": "1080x1350",
      "priority": 2
    }
  ],
  "optional_outputs": [],
  "excluded_outputs": [
    "naver_blog_section_image"
  ]
}
```

---

# 4. Visual Direction Pipeline

## 목적

Figma 제작 전에 캠페인의 시각 방향, 레이아웃 전략, 그래픽 규칙을 정의합니다.  
이 단계는 디자인 초안의 품질을 결정하는 핵심 단계입니다.

## 입력값

- campaign-brief.md
- message-system.md
- output-plan.md
- design-system.md
- 브랜드 기준
- 참고 이미지 또는 레퍼런스
- 상품 이미지
- 채널별 규격

## 처리 흐름

```text
4-1. Design System Load
4-2. Campaign Mood Definition
4-3. Visual Keyword Mapping
4-4. Layout Strategy
4-5. Graphic Motif Definition
4-6. Reference Direction
4-7. Visual Rule Sheet Export
```

## 세부 모듈

### 4-1. Design System Load

기존 디자인 시스템을 불러옵니다.

확인 항목:

- 색상
- 폰트
- 간격
- 라운드 값
- 버튼 스타일
- 타이포 위계
- 이미지 사용 규칙
- 브랜드 금지 표현

### 4-2. Campaign Mood Definition

이번 캠페인의 분위기를 정의합니다.

예:

```text
프리미엄
신뢰감
긴급함
고정가 안정감
빠른 배송
한정 수량
선물감
시즌성
```

### 4-3. Visual Keyword Mapping

시각 키워드를 정리합니다.

예:

```text
black
gold
silver
clean layout
dense typography
high contrast
product-centered
financial trust
```

### 4-4. Layout Strategy

레이아웃 타입을 선택합니다.

기본 타입:

- 상품 중심형
- 혜택 중심형
- 타이포 중심형
- 공지형
- 프리미엄 비주얼형
- 리스트형
- 비교형
- 단계 안내형

### 4-5. Graphic Motif Definition

그래픽 모티프를 정의합니다.

예:

```text
금속 질감
코인 엣지
가격표
프레임
선형 구획
스탬프
라벨
카드형 정보 블록
```

### 4-6. Reference Direction

참고 방향을 정리하되 복제하지 않도록 제한합니다.

정리 방식:

```text
참고할 요소:
- 여백감
- 타이포 비율
- 정보 구획 방식
- 색 대비

참고하지 않을 요소:
- 로고 형태
- 특정 그래픽 구조
- 동일한 배치
- 고유한 장식 요소
```

### 4-7. Visual Rule Sheet Export

이번 캠페인에서 지킬 시각 규칙을 생성합니다.

## 산출물

```text
visual-direction.md
campaign-art-direction.md
layout-strategy.md
visual-keywords.json
graphic-motif.md
figma-style-brief.md
visual-rule-sheet.md
```

## 검수 기준

- 캠페인 목적과 시각 방향이 연결되어 있는가
- 디자인 시스템과 충돌하지 않는가
- 레이아웃 타입이 채널 목적에 맞는가
- 참고 이미지 복제 위험이 없는가
- Figma 제작자가 바로 이해할 수 있는가

## 실패 케이스

- 비주얼 방향이 너무 추상적임
- 레퍼런스를 그대로 따라가는 구조
- 카피와 비주얼 톤이 맞지 않음
- 타임딜인데 너무 룩북처럼 표현됨
- 공지인데 과도하게 장식적임
- 상품 판매에 필요한 정보 위계가 약함

## 사람이 판단할 부분

- 이번 캠페인의 시각 강도
- 프리미엄과 프로모션 중 어느 쪽을 우선할지
- 상품 이미지 중심인지 타이포 중심인지
- 그래픽 모티프를 어느 정도 사용할지
- 레퍼런스에서 무엇만 참고할지

## 다음 단계로 넘길 데이터

```json
{
  "mood": ["premium", "trust", "fast_delivery"],
  "layout_type": "product_centered",
  "visual_keywords": ["black", "gold", "clean", "high_contrast"],
  "graphic_motif": ["metal_label", "coin_edge", "price_block"],
  "figma_notes": "상품 중심의 단단한 레이아웃. 정보 위계를 명확히 하고 과한 장식은 배제."
}
```

---

# 5. Figma Production Pipeline

## 목적

앞 단계에서 정의한 브리프, 카피, 산출물 계획, 비주얼 방향을 기반으로 Figma에서 작업 가능한 디자인 초안을 생성합니다.  
목표는 완성본이 아니라 디자이너가 빠르게 마감할 수 있는 70% 수준의 구조화된 초안입니다.

## 입력값

- output-checklist.json
- channel-format-spec.md
- content-allocation.md
- visual-direction.md
- figma-style-brief.md
- design-system.md
- channel-copy.json
- 상품 이미지 또는 대체 박스
- 로고/브랜드 에셋

## 처리 흐름

```text
5-1. Frame Schema Generation
5-2. Component Mapping
5-3. Layout Block Construction
5-4. Design Token Application
5-5. Auto Layout Rule Application
5-6. Draft Frame Generation
5-7. Human Edit Zone Marking
5-8. Export Preparation
```

## 세부 모듈

### 5-1. Frame Schema Generation

생성할 프레임 구조를 정의합니다.

예:

```json
{
  "frame_name": "instagram_feed_01",
  "size": "1080x1350",
  "blocks": [
    "headline",
    "product_image",
    "benefit_badge",
    "sub_copy",
    "cta",
    "notice"
  ]
}
```

### 5-2. Component Mapping

각 콘텐츠를 디자인 컴포넌트에 연결합니다.

컴포넌트 예:

- headline
- subheadline
- product image
- price block
- benefit badge
- CTA button
- notice text
- brand logo
- background
- divider
- label

### 5-3. Layout Block Construction

콘텐츠 블록을 배치합니다.

기본 구조:

```text
상단: 메인 카피
중앙: 상품 또는 핵심 비주얼
하단: 혜택/CTA/주의사항
```

또는:

```text
좌측: 텍스트 정보
우측: 상품 이미지
하단: CTA 및 조건
```

### 5-4. Design Token Application

디자인 시스템 기준을 적용합니다.

적용 항목:

- 색상
- 폰트
- 크기
- 행간
- 자간
- 여백
- 라운드
- 선 두께
- 그림자 여부

### 5-5. Auto Layout Rule Application

수정하기 쉬운 구조로 만듭니다.

기준:

- 텍스트 길이 변경 가능
- 상품 수 변경 가능
- CTA 숨김 가능
- 주의사항 영역 확장 가능
- 모바일/피드 가독성 유지

### 5-6. Draft Frame Generation

Figma에 초안 프레임을 생성합니다.

목표:

```text
완성 이미지가 아니라 구조화된 디자인 초안
```

### 5-7. Human Edit Zone Marking

사람이 수정해야 하는 영역을 표시합니다.

예:

```text
상품 이미지 교체 필요
가격 정보 최종 확인 필요
메인 카피 선택 필요
주의사항 길이 조정 필요
배경 비주얼 보강 가능
```

### 5-8. Export Preparation

export 가능한 상태로 정리합니다.

확인 항목:

- 프레임명
- 사이즈
- 숨김 레이어
- 임시 텍스트
- 이미지 누락
- 가이드 레이어
- export 대상 여부

## 산출물

```text
figma-frame-schema.json
figma-production-brief.md
component-map.json
layout-blocks.json
human-edit-notes.md
export-ready-checklist.md
```

## 검수 기준

- 각 프레임의 목적이 명확한가
- 콘텐츠가 올바른 컴포넌트에 매핑되었는가
- 디자인 시스템이 적용되었는가
- 사람이 수정해야 할 영역이 표시되었는가
- export 전에 정리해야 할 항목이 남아 있는가

## 실패 케이스

- 자동 생성 결과를 완성본으로 착각함
- 텍스트가 컴포넌트 밖으로 넘침
- 상품 이미지 영역이 실제 이미지 비율과 맞지 않음
- CTA와 주의사항이 누락됨
- 레이아웃이 채널 목적과 맞지 않음
- 디자인 시스템과 다른 폰트/색상 사용

## 사람이 판단할 부분

- 최종 레이아웃 선택
- 상품 이미지 교체
- 카피 최종 선택
- 가격/혜택 정보 확인
- 시각적 완성도 보강
- 불필요한 프레임 삭제

## 다음 단계로 넘길 데이터

```json
{
  "figma_file_status": "draft_created",
  "frames": [
    {
      "name": "instagram_feed_01",
      "status": "needs_human_edit",
      "edit_notes": ["상품 이미지 교체", "CTA 문구 확인"]
    }
  ],
  "ready_for_qa": false
}
```

---

# 6. QA & Packaging Pipeline

## 목적

제작된 카피, 디자인, 채널 산출물을 검수하고 최종 사용 가능한 형태로 정리합니다.  
이 단계는 “디자인이 예쁜가”만 보는 것이 아니라, 실제 운영 가능한 상태인지 확인하는 단계입니다.

## 입력값

- campaign-brief.md
- channel-copy.json
- output-checklist.json
- visual-direction.md
- Figma 프레임
- export 파일
- human-edit-notes.md
- export-ready-checklist.md

## 처리 흐름

```text
6-1. Content QA
6-2. Design QA
6-3. Channel QA
6-4. Operational QA
6-5. Export QA
6-6. Package Creation
6-7. Final Report Export
```

## 세부 모듈

### 6-1. Content QA

문구와 정보 정확성을 검수합니다.

검수 항목:

- 오탈자
- 가격 오류
- 기간 오류
- 수량 조건 오류
- 상품명 오류
- 배송 조건 오류
- CTA 오류
- 주의사항 누락

### 6-2. Design QA

디자인 완성도를 검수합니다.

검수 항목:

- 가독성
- 정보 위계
- 여백
- 정렬
- 폰트 크기
- 행간
- 색 대비
- 디자인 시스템 준수
- 모바일 화면 가독성

### 6-3. Channel QA

채널별 적합성을 검수합니다.

예:

```text
인스타그램: 첫 화면에서 핵심 메시지가 보이는가
홈페이지 팝업: 닫기/CTA 영역과 충돌하지 않는가
카카오 메시지: 광고성/안내성 문구가 적절한가
블로그: 검색/설명형 구조에 맞는가
상세페이지: 구매 판단에 필요한 정보가 있는가
```

### 6-4. Operational QA

운영 리스크를 검수합니다.

체크 항목:

- 고객 오해 가능성
- CS 발생 가능성
- 과장 표현
- 배송 보장 표현
- 수량 소진 안내
- 쿠폰 중복 적용 안내
- 법적/정책적 민감 표현

### 6-5. Export QA

export 결과를 검수합니다.

체크 항목:

- 파일 존재 여부
- 사이즈
- 형식
- 용량
- 채널별 분류
- export 대상 누락
- 불필요한 임시 파일 포함 여부

### 6-6. Package Creation

최종 사용 파일을 정리합니다.

예:

```text
final/
├─ instagram/
├─ homepage/
├─ kakao/
├─ naver_blog/
├─ copy/
└─ report/
```

### 6-7. Final Report Export

최종 리포트를 생성합니다.

포함 항목:

- 실행 요약
- 생성 산출물
- 통과 항목
- 수정 필요 항목
- 보류 항목
- 다음 액션

## 산출물

```text
qa-report.md
content-qa-report.md
design-qa-report.md
channel-qa-report.md
operational-qa-report.md
export-qa-report.md
final-package-report.md
next-action.md
```

## 검수 기준

- 고객에게 잘못 전달될 정보가 없는가
- 디자인 시스템을 지켰는가
- 채널별 목적에 맞는가
- 실제 업로드 가능한 파일인가
- 운영자가 바로 사용할 수 있는 구조인가
- 수정이 필요한 항목이 명확히 표시되었는가

## 실패 케이스

- 시각적으로는 괜찮지만 정보가 틀림
- 카피는 맞지만 채널 규격이 틀림
- 디자인은 완성됐지만 고객 오해 가능성이 있음
- export는 됐지만 실제 업로드용으로 정리되지 않음
- QA pass 기준이 너무 느슨함
- 수정 필요 항목이 리포트에 남지 않음

## 사람이 판단할 부분

- 최종 사용 승인
- 수정 후 재검수 여부
- 일부 산출물 제외 여부
- 업로드 일정
- 고객 공지 범위
- 이벤트 시작 가능 여부

## 최종 데이터

```json
{
  "qa_status": "needs_revision",
  "passed": [
    "content_qa",
    "design_qa"
  ],
  "failed": [
    "export_qa"
  ],
  "next_actions": [
    "누락된 홈페이지 팝업 export 확인",
    "카카오 문구 최종 승인 필요"
  ]
}
```

---

# 단계별 실행 방식

## 전체 실행

```text
0 → 1 → 2 → 3 → 4 → 5 → 6
```

## 부분 실행 예시

### 브리프까지만

```text
0 → 1
```

### 카피까지만

```text
0 → 1 → 2
```

### 제작 산출물 계획까지만

```text
0 → 1 → 2 → 3
```

### 디자인 방향까지만

```text
0 → 1 → 2 → 3 → 4
```

### Figma 초안만

```text
0 → 5
```

단, 이 경우 1~4단계 산출물이 이미 존재해야 합니다.

### QA만

```text
0 → 6
```

단, 제작 산출물과 export 파일이 존재해야 합니다.

---

# 공통 문서 포맷

각 단계별 상세 문서는 아래 구조를 따릅니다.

```text
# 단계명

## 목적
## 입력값
## 처리 흐름
## 세부 모듈
## 산출물
## 검수 기준
## 실패 케이스
## 사람이 판단할 부분
## 다음 단계로 넘길 데이터
```

---

# 현재 단계에서의 결론

이 프로젝트는 기존 6단계 파이프라인을 유지하되, 각 단계를 하나의 독립적인 세부 파이프라인으로 확장하는 방향이 맞습니다.

핵심은 다음과 같습니다.

```text
1. 전체 6단계는 상위 구조로 유지한다.
2. 각 단계는 독립 실행 가능한 작은 시스템으로 만든다.
3. 각 단계마다 입력값, 처리 로직, 산출물, 검수 기준을 둔다.
4. 원클릭 완성보다 단계별 판단과 초안 생성을 목표로 한다.
5. 사람이 판단해야 할 지점과 자동화가 담당할 지점을 명확히 나눈다.
```

최종 정의:

```text
6단계 자동 제작기 X
6개의 독립 실행 가능한 제작 파이프라인 O
```
