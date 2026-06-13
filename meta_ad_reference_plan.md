# Meta Ad Reference 보강 계획서

## 1. 한 줄 요약

기존 Pinterest 레퍼런스 수집 방식을 유지하되, 수집 소스를 `Meta Ad Library`로 바꿔서 광고 이미지/영상 카드, 카피, CTA, 랜딩 URL을 수집하고, 이를 우리 이벤트 콘텐츠 자동화 파이프라인의 앞단 참고자료로 연결한다.

---

## 2. 목표

### 기존 문제

현재 프로젝트는 이벤트 입력 → 브리프 → 콘텐츠 기획 → 이미지 후보 생성 → 선택 → QA → 아카이브 흐름은 갖춰져 있다.
하지만 이미지 생성 전에 참고할 업계 광고 레퍼런스가 약하면, 03_visual_candidates의 프롬프트 품질이 흔들릴 수 있다.

### 보강 목표

Meta 광고 레퍼런스를 수집해 다음 정보를 자동 정리한다.

- 광고 이미지 또는 영상 썸네일
- 브랜드명
- 광고 카피
- CTA
- 랜딩 URL
- 게재 플랫폼
- 게재 시작일
- 광고 유형
- 시각 태그
- 카피 유형
- 레이아웃 힌트

이 데이터를 `reference-evidence.json`으로 만들어 01/02/03 단계에 넣는다.

---

## 3. 참고할 사이트 기능

벤치마크 대상은 Snipit 계열 구조다.
단, 그대로 SaaS를 만드는 것이 아니라 내부 기능만 가져온다.

### 참고할 기능

- 이미지 검색
- 영상 검색
- 경쟁사 모니터링
- 레퍼런스 보드
- 이미지 설명 기반 검색
- 카피 기반 검색
- AI 추천
- 실험실/캔버스형 탐색
- Instagram/Meta 광고 보드 저장 구조

### 우리 프로젝트에 필요한 버전

| Snipit식 기능 | 우리 프로젝트 적용 |
|---|---|
| 이미지 검색 | 광고 카드 이미지 검색 |
| 영상 검색 | 영상 썸네일/광고 카드 저장 |
| 경쟁사 모니터링 | 브랜드별 Meta Ad Library 검색어 저장 |
| 레퍼런스 보드 | 내부 reference board |
| 이미지 설명 검색 | AI 태그 기반 검색 |
| 카피 검색 | 광고 카피/CTA 검색 |
| AI 추천 | 이벤트와 맞는 광고 레퍼런스 추천 |
| 캔버스 | 보류. MVP 제외 |

---

## 4. 만들 프로그램 기준

### 핵심 프로그램

1. Python
   - 기존 프로젝트 스크립트와 연결하기 좋음
   - JSON 저장/가공/파이프라인 연결에 적합

2. Playwright
   - Meta Ad Library 페이지를 브라우저로 열고 조작
   - 검색어 입력, 스크롤, 광고 카드 캡처 가능
   - API 없이 웹 화면 기반 수집 가능

3. 기존 로컬 콘솔
   - `start_brand_event_console.bat`
   - 현재 프로젝트 UI에 레퍼런스 수집 버튼 추가

4. Qwen-VL
   - 광고 카드 이미지 분석
   - 제품컷/모델컷/할인형/프리미엄/성분 강조 등 태깅

5. OpenCLIP
   - 레퍼런스 이미지 유사도/랭킹
   - 사용자가 고른 좋은 레퍼런스 기준으로 점수화 가능

6. Local JSON DB
   - 처음부터 DB 서버를 붙이지 않음
   - `references/meta_ads/` 폴더에 JSON과 이미지 저장

### 나중에 고려할 것

- SQLite
- 브라우저 확장 프로그램
- 자동 스케줄러
- Google Ads Transparency / TikTok Creative Center provider 추가

---

## 5. 전체 구조

```text
Meta Ad Library
→ Playwright로 검색/스크롤/캡처
→ 광고 카드 이미지 저장
→ 광고 텍스트/CTA/URL 추출
→ Qwen-VL 태깅
→ OpenCLIP 랭킹
→ shortlist 생성
→ reference-evidence.json 생성
→ 01_event_brief
→ 02_content_planning
→ 03_visual_candidates
```

---

## 6. 폴더 구조

```text
references/
  meta_ads/
    brands.json
    searches/
      cosmetics.json
      jewelry.json
      bullion.json
    captures/
      raw_cards/
    images/
    videos/
    items/
      meta_ad_001.json
    shortlist/
      selected-meta-refs.json
    indexes/
      meta-reference-index.json

runs/<run-id>/
  00_ad_reference_collection/
    reference-evidence.json
    collected-ads.json
    shortlist.json
    notes.md
```

---

## 7. 데이터 구조

### meta_ad_item.json

```json
{
  "id": "meta_ad_001",
  "source": "meta_ad_library",
  "brand": "anua",
  "category": "cosmetics",
  "searchKeyword": "anua",
  "adLibraryUrl": "https://www.facebook.com/ads/library/...",
  "landingUrl": "https://...",
  "mediaType": "image",
  "capturePath": "references/meta_ads/captures/raw_cards/meta_ad_001.png",
  "copy": "광고 문구",
  "cta": "Shop now",
  "platforms": ["instagram", "facebook"],
  "deliveryStartDate": "2026-06-01",
  "visualTags": [
    "product_cut",
    "white_background",
    "clean_layout",
    "ingredient_focus"
  ],
  "copyTags": [
    "benefit_first",
    "discount_offer",
    "ingredient_proof"
  ],
  "layoutHint": "center product with left headline space",
  "useFor": ["brief", "content_plan", "visual_prompt"],
  "score": 0.84,
  "needsReview": false
}
```

### reference-evidence.json

```json
{
  "eventId": "hsgn-vitamin-c-sale",
  "source": "meta_ad_library",
  "category": "cosmetics",
  "selectedReferences": [
    {
      "id": "meta_ad_001",
      "brand": "anua",
      "visualPattern": "white product-centered layout",
      "copyPattern": "benefit headline + ingredient proof + CTA",
      "layoutHint": "center product with left headline space",
      "useFor": ["brief", "content_plan", "visual_prompt"]
    }
  ],
  "insights": {
    "commonVisualPattern": "clean product-centered layout",
    "commonCopyPattern": "short benefit headline with ingredient support",
    "recommendedDirection": "제품 중심, 카피 여백 확보, 성분/혜택 뱃지 사용",
    "avoid": [
      "overcrowded text",
      "cheap discount flyer mood",
      "direct copy of competitor creative"
    ]
  }
}
```

---

## 8. 파이프라인 연결 위치

현재 구조를 크게 바꾸지 않는다.
앞에 보조 입력만 추가한다.

```text
event-input.json
brand-guide.json
reference-evidence.json
        ↓
01_event_brief
        ↓
02_content_planning
        ↓
03_visual_candidates
        ↓
04_admin_selection
        ↓
06_qa_packaging
        ↓
07_asset_archive
```

### 01_event_brief 보강

- 업계 광고 흐름 요약
- 이벤트 메시지 방향 보강
- 경쟁사와 겹치면 피해야 할 표현 표시

### 02_content_planning 보강

- 채널별 카피 구조 참고
- CTA 방식 참고
- 상세페이지/피드/스토리별 메시지 구분

### 03_visual_candidates 보강

- 레이아웃 힌트 반영
- 조명/배경/제품 배치 힌트 반영
- 카피 여백 기준 강화

---

## 9. MVP 범위

### 1차 MVP

- Meta Ad Library 검색 URL 생성
- Playwright로 페이지 열기
- 광고 카드 20~50개 캡처
- 카드별 기본 텍스트 추출
- 이미지 저장
- JSON 저장
- Qwen-VL 태깅
- 사람이 shortlist 선택
- reference-evidence.json 생성

### 제외

- 완전 자동 대량 크롤링
- API 연결
- 로그인 우회
- 광고 영상 원본 다운로드
- 성과 데이터 추정
- SaaS형 결제/팀 기능
- 자동 트렌드 리포트

---

## 10. UI 구성

현재 로컬 콘솔에 탭 하나 추가한다.

### 탭 이름

```text
Ad Reference
```

### 화면 구성

```text
[브랜드/검색어 입력]
[카테고리 선택: cosmetics / jewelry / bullion / fashion]
[국가 선택]
[수집 개수]
[Meta 광고 수집 실행]

수집 결과 카드 리스트
- 광고 카드 이미지
- 브랜드명
- 카피
- CTA
- 랜딩 URL
- AI 태그
- 선택 / 제외 / 보류

[Shortlist 저장]
[현재 이벤트에 연결]
```

---

## 11. 개발 순서

### Step 1. 수집기 뼈대

- `services/ad_reference/meta_collector.py`
- Playwright 실행
- 검색 URL 생성
- 페이지 캡처 저장

### Step 2. 광고 카드 분리

- 광고 카드 단위 locator 탐색
- 카드별 스크린샷 저장
- 텍스트/링크 추출

### Step 3. JSON 저장

- `meta_ad_item.json` 생성
- `meta-reference-index.json` 업데이트

### Step 4. AI 태깅

- Qwen-VL로 광고 카드 분석
- visualTags/copyTags/layoutHint 생성

### Step 5. 콘솔 UI 연결

- Ad Reference 탭 추가
- 수집 실행 버튼
- 카드 선택/제외/보류 기능

### Step 6. 파이프라인 연결

- shortlist를 `reference-evidence.json`으로 변환
- 01/02/03 핸들러에서 선택적으로 읽기

---

## 12. 리스크

### 기술 리스크

- Meta 페이지 구조 변경
- 광고 카드 DOM selector 변경
- 무한 스크롤 로딩 실패
- 일부 광고 이미지/영상 접근 제한
- 국가/검색 조건별 결과 차이

### 운영 리스크

- 경쟁사 광고를 그대로 복제하면 법적/브랜드 리스크 발생
- 레퍼런스가 많아질수록 품질 낮은 자료가 쌓일 수 있음
- 자동 태깅이 틀릴 수 있으므로 사람 검토 필요

### 대응

- 원본 복제가 아니라 구조/무드/카피 패턴만 추출
- 수집량 제한
- 출처 URL 보관
- `needsReview` 필드 유지
- 사람이 shortlist 확정

---

## 13. 최종 판단

이 기능은 프로젝트를 키우는 기능이 아니라, 기존 파이프라인 앞단 품질을 올리는 기능이다.

가장 중요한 포인트는 다음이다.

```text
Pinterest 이미지 수집
→ Meta 광고 카드 수집
```

그리고 최종 목적은 다음이다.

```text
광고 레퍼런스 저장
→ AI 태깅
→ 좋은 레퍼런스 선택
→ 이벤트 브리프/기획/이미지 프롬프트 보강
```

즉, 우리 프로젝트의 차별점은 “이미지 생성”이 아니라 “광고 레퍼런스 기반 이벤트 비주얼 기획 자동화”로 잡는다.
