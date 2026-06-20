# 마케팅 인텔리전스 데이터 플로우

## 목적

현재 광고 기획 엔진은 이벤트 브리프와 일부 Meta 광고 전략 패턴만으로 카피를 만든다.
이 방식은 문장은 만들 수 있지만, 실제 퍼포먼스 마케터가 기획할 때 사용하는 시장 맥락, 고객 반응, 계절성, 채널 유행, 경쟁 제품 흐름이 부족하다.

목표는 이미지 제작 전 단계에서 후임 기획자가 시니어 마케터에게 넘길 수 있는 수준의 근거 패킷을 만드는 것이다.

```text
이벤트 입력
→ 시장/고객/트렌드/계절/경쟁/채널 데이터 수집
→ 신호 정규화와 신뢰도 평가
→ 타깃 인사이트 후보 생성
→ 캠페인 전략 3안
→ 채널별 카피 패키지
→ 사람 평가와 수정
→ 다음 생성에 반영
```

## 핵심 판단

- 좋은 광고 카피는 문장 생성 문제가 아니라 근거 선택 문제다.
- 훅이 약한 이유는 모델 문장력이 아니라, 타깃이 지금 무엇에 반응하는지에 대한 신호가 부족하기 때문이다.
- Meta 광고 사례만으로는 부족하다. 경쟁사 광고, 제품 랭킹, 검색 트렌드, SNS 반응, 계절/날씨, 리뷰 언어, 커뮤니티 불만, 브랜드 자산을 함께 읽어야 한다.
- 한 번에 완성하려 하지 않고, 매일 질문을 받아 데이터 플로우를 확장하는 장기 과제로 운영한다.

## 1차 목표

화장품 이벤트 5건에서 다음을 달성한다.

- 각 이벤트마다 최소 50개 이상의 근거 신호를 저장한다.
- 콘셉트 3안마다 서로 다른 고객 인사이트와 시장 근거를 연결한다.
- 최종 카피마다 왜 이 문장을 썼는지 근거를 3개 이상 표시한다.
- 사람 평가에서 `타깃 공감도`, `훅 강도`, `제품 연결력` 평균 4.0/5 이상을 목표로 한다.
- 근거 없는 주장, 확인 안 된 혜택, 과장 효능은 0건으로 유지한다.

## 장기 목표

화장품 광고 기획을 위한 `MarketingSignal` 1,000개 이상을 누적한다.

- 시장 신호: 인기 제품, 카테고리 상승/하락, 가격대, 주요 성분, 시즌 제품군
- 고객 신호: 리뷰 불만, 구매 이유, 망설임, 반복 표현, 피부 고민
- 트렌드 신호: Google/Naver 검색 흐름, SNS 해시태그, Meta 광고 소재 흐름
- 환경 신호: 계절, 날씨, 미세먼지, 습도, 자외선, 명절/휴가/개학 등 캘린더
- 경쟁 신호: 경쟁사 오퍼, 메시지, 랜딩 구조, 광고 후킹 방식
- 채널 신호: Instagram, Threads, blog, banner별 반응 문법
- 브랜드 신호: 브랜드 톤, 금지 표현, 과거 승인 카피, 거절 사유

## 데이터 소스 후보

### 제품/시장

- 올리브영 랭킹, 카테고리 인기 제품, 리뷰 키워드
- 쿠팡/네이버쇼핑 랭킹과 가격대
- 브랜드 자사몰 베스트셀러와 리뷰
- 성분 트렌드: 나이아신아마이드, 세라마이드, 레티놀, PDRN, 판테놀 등

### 검색/트렌드

- Google Trends
- Naver DataLab
- 네이버 쇼핑/검색 자동완성
- 계절 키워드: 장마, 폭염, 자외선, 환절기, 개학, 휴가, 명절

### SNS/광고

- Meta 광고 라이브러리
- Instagram 공개 해시태그/게시물 언어
- Threads/Twitter 짧은 문장 유행
- 크리에이터/인플루언서 리뷰 표현

### 고객 반응

- 제품 리뷰의 긍정/부정 문장
- 댓글의 질문, 불만, 망설임
- 구매 전후 비교 표현
- 자주 반복되는 피부 고민과 사용 상황

### 외부 환경

- 날씨: 온도, 습도, 강수, 자외선, 미세먼지
- 캘린더: 시즌, 연휴, 급여일, 쇼핑 시즌, 입학/졸업, 휴가철
- 사회적 맥락: 절약 소비, 작은 사치, 선물 수요, 루틴 단순화

## 공통 스키마

### MarketingSignal

```json
{
  "id": "signal-id",
  "industry": "cosmetics_skincare",
  "sourceType": "oliveyoung_rank | google_trends | naver_datalab | meta_ad | review | weather | calendar | internal",
  "sourceRef": {},
  "collectedAt": "2026-06-18T00:00:00+09:00",
  "topic": "summer_barrier_care",
  "signalText": "",
  "normalizedInsight": "",
  "targetSegment": "",
  "funnelStage": "awareness | consideration | conversion | retention",
  "evidenceType": "trend | pain | desire | objection | proof | offer | channel_pattern | timing",
  "strength": 1,
  "freshness": 1,
  "confidence": 1,
  "riskFlags": [],
  "usableFor": ["concept", "copy", "offer", "channel", "qa"]
}
```

### InsightBrief

```json
{
  "eventId": "",
  "createdAt": "",
  "targetHypotheses": [],
  "customerPains": [],
  "customerDesires": [],
  "purchaseObjections": [],
  "trendHooks": [],
  "seasonalHooks": [],
  "productProofs": [],
  "offerAngles": [],
  "channelPatterns": [],
  "doNotClaim": [],
  "evidenceSignalIds": []
}
```

## 생성 전 근거 패킷

새 이벤트는 카피 생성 전에 `00_marketing_intelligence` 단계를 통과해야 한다.

출력:

- `marketing-signals.json`
- `insight-brief.json`
- `target-hypotheses.json`
- `trend-and-season-report.json`
- `competitor-message-map.json`
- `review-language-map.json`
- `evidence-scorecard.json`

카피 생성기는 이 패킷에서 승인된 신호만 사용한다.

## 02 콘텐츠 기획 반영 방식

콘셉트 3안은 단순히 말투만 다르게 만들지 않는다.
각 안은 최소 3개 이상의 서로 다른 근거 신호를 사용해야 한다.

- A안: 고객 불편/문제 재정의 기반
- B안: 제품 선택 기준/근거 기반
- C안: 시즌·상황·감정 맥락 기반

각 콘셉트에는 다음을 필수 기록한다.

- 사용한 `MarketingSignal` ID
- 타깃 가설
- 고객이 반응할 이유
- 제품이 이 인사이트와 연결되는 이유
- 오퍼가 행동을 밀어주는 이유
- 해당 채널에서 먹힐 가능성
- 위험한 주장 또는 확인 필요 사항

## QA 기준

다음은 자동 차단한다.

- 외부 데이터에 없는 인기 순위, 가격, 효능, 후기 수 생성
- 날씨/트렌드 데이터를 임의로 꾸며낸 주장
- 경쟁사 문구 직접 복제
- 신호 ID 없이 만들어진 핵심 훅
- 타깃 인사이트와 제품 역할이 연결되지 않은 카피

다음은 경고로 표시하고 수정 전 승인하지 않는다.

- 근거가 너무 일반적임
- 고객 데이터가 아니라 기획자 추측에 가까움
- 현재 시즌과 맞지 않음
- 채널 유행 문법과 맞지 않음
- 오퍼가 행동 유도에 약함

## 구현 순서

### Phase 1: 내부 데이터 기반

1. 기존 Meta 광고 전략 46건을 모두 검수한다.
2. 화장품 파일럿 5건의 사람 평가와 수정문을 채운다.
3. 내부 승인/거절 카피를 `MarketingSignal`로 변환한다.
4. 리뷰 언어와 고객 불만을 수동 CSV로 50개 입력한다.
5. 콘셉트 생성 전에 `InsightBrief`를 만들도록 한다.

### Phase 2: 공개 트렌드/환경 데이터

1. 날씨와 계절 캘린더 신호를 자동 수집한다.
2. Google Trends/Naver DataLab 수동 입력 또는 반자동 수집을 붙인다.
3. 올리브영/쇼핑 랭킹은 먼저 CSV 업로드 방식으로 시작한다.
4. 각 신호에 freshness, confidence, risk를 부여한다.
5. 이벤트별 최소 근거 신호 50개를 요구한다.

### Phase 3: 광고/채널 반응 데이터

1. Meta 광고 라이브러리에서 메시지 구조와 오퍼 흐름을 추상화한다.
2. Instagram/Threads 짧은 문장 패턴을 채널 신호로 저장한다.
3. 블로그 검색 상위 콘텐츠의 제목/도입 구조를 추상화한다.
4. 경쟁사 원문은 복사 금지하고 전략 구조만 저장한다.

### Phase 4: 성과 피드백

1. 사람이 선택한 콘셉트와 거절한 콘셉트를 모두 저장한다.
2. 최종 승인 카피와 수정 전 카피의 차이를 학습한다.
3. 실제 광고 성과가 있으면 CTR, CVR, 저장, 댓글, 문의를 연결한다.
4. 성과가 좋은 신호 조합을 다음 기획의 우선 근거로 승격한다.

## 매일 받을 질문

이 과제는 하루에 한 번씩 다음 질문을 기준으로 확장한다.

```text
오늘 화장품 광고 기획 엔진에 어떤 시장/고객/트렌드 신호를 하나 더 넣을 것인가?
그 신호는 어떤 이벤트와 어떤 카피 판단을 더 똑똑하게 만드는가?
그 신호는 검증 가능한가, 아니면 추측인가?
```

## 다음 작업

1. `MarketingSignal` 스키마와 저장소를 만든다.
2. `00_marketing_intelligence` 단계를 워크플로우 앞단에 추가할지, 우선 01/02 내부 산출물로 둘지 결정한다.
3. 올리브영 랭킹/리뷰 키워드 CSV 업로드 포맷을 만든다.
4. 날씨/계절 캘린더 신호를 자동 생성한다.
5. 화장품 파일럿 5건에서 이벤트당 근거 신호 50개 기준으로 재평가한다.

## 2026-06-18 1차 자동화 목표: 무작위 후보 수집 후 검수

사용자 결정:

- 처음부터 완벽한 외부 데이터 수집을 만들기보다, 일단 넓게 무작위 후보 신호를 모은다.
- 모은 뒤 사람이 `selected / shortlist / rejected`로 검수한다.
- 검수 전 랜덤 신호는 사실 근거가 아니라 가설이므로 카피 생성에 직접 사용하지 않는다.

구현 상태:

- `core/schemas/marketing-signal.schema.json` 추가.
- `services/marketing_intelligence/repository.py` 추가.
- `scripts/collect_marketing_signals.py` 추가.
- 저장소: `design_brain_wiki/marketing_signals/signals.json`.
- 검수 CSV: `.tmp/marketing-signals/marketing-signal-review-sheet.csv`.
- 2026-06-18 기준 `seed_random` 화장품 신호 50개 생성 완료.

실행 명령:

```powershell
python scripts\collect_marketing_signals.py --random-seed --count 50 --topic daily_random_seed --export-review
```

검수 CSV를 수정한 뒤 반영:

```powershell
python scripts\collect_marketing_signals.py --import-review --apply
```

검수 기준:

- `selected`: 실제 기획 근거로 바로 쓸 수 있는 신호.
- `shortlist`: 방향은 좋지만 외부 근거 확인이 필요한 신호.
- `rejected`: 너무 일반적이거나 브랜드/제품/시즌과 연결이 약한 신호.

다음 구현:

1. selected 신호만 `InsightBrief` 후보에 들어가게 연결한다.
2. 올리브영 랭킹/리뷰 키워드 CSV 업로드 수집기를 붙인다.
3. Playwright 기반 공개 페이지 수집기는 약관·로그인·캡차 리스크 없는 범위에서 별도 단계로 붙인다.

## 2026-06-18 2차 자동화: 콘솔 검수 화면

구현 상태:

- 콘솔 bootstrap에 `marketingSignals` 패킷을 추가했다.
- API `GET /api/marketing-signals`와 `POST /api/marketing-signals/review`를 추가했다.
- 대시보드에 `마케팅 신호 검수` 섹션을 추가했다.
- 화면에서 랜덤 가설 신호를 카드로 보고 `선택 / 보류 / 거절`을 저장할 수 있다.
- 화면에는 `seed_random`, `needs_external_validation`, `daily_random_seed` 같은 내부 코드를 노출하지 않고 한국어 라벨로 표시한다.

검증:

- 브라우저에서 신호 카드 12개 노출, 전체 신호 50개, 검수 대기 50개 확인.
- 텍스트 넘침 0건.
- 내부 코드 노출 0건.
- 전체 프로젝트 테스트 122개 통과.

다음 구현:

1. 사람이 선택한 `selected` 신호만 `InsightBrief`에 연결한다.
2. 선택 신호 3개 이상 없으면 강한 훅 생성을 막는 QA를 추가한다.
3. 올리브영/리뷰 CSV 업로드로 `seed_random`이 아닌 실제 출처 신호를 추가한다.

## 2026-06-18 3차 자동화: selected 신호 기반 InsightBrief 게이트

구현 상태:

- `core/schemas/insight-brief.schema.json` 추가.
- `services/marketing_intelligence/insight_brief.py` 추가.
- `scripts/build_marketing_insight_brief.py` 추가.
- 콘솔 API `POST /api/marketing-signals/insight-brief` 추가.
- 콘솔 `마케팅 신호 검수` 섹션에 `기획 근거 패킷` 상태 박스를 추가했다.
- selected 신호가 최소 3개 이상일 때만 `InsightBrief`가 `ready`가 된다.
- 현재 selected 신호가 0개이므로 `design_brain_wiki/marketing_signals/insight-brief.json`은 `needs_signal_review` 상태다.

검증:

- 현재 API 상태: 전체 신호 50개, selected 0개, InsightBrief `needs_signal_review`.
- 브라우저 상태: `선택 신호 0/3개`, `InsightBrief 만들기` 버튼 disabled.
- 내부 코드 노출 0건, 텍스트 넘침 0건.
- 전체 프로젝트 테스트 125개 통과.

다음 구현:

1. 콘솔에서 최소 3개 이상을 실제 selected로 검수한다.
2. selected 신호가 3개 이상일 때 `InsightBrief 만들기` 버튼으로 ready 패킷을 생성한다.
3. ready `InsightBrief`를 콘셉트 생성과 카피 근거에 주입한다.
4. selected 신호가 부족하면 기획 훅 생성 또는 02단계 승인을 막는 QA를 추가한다.

## 2026-06-18 4차 자동화: InsightBrief 기획 엔진 연결

구현 상태:

- ready `InsightBrief`가 있으면 `build_concept_candidates`가 콘셉트별 `marketingEvidence`, `marketingSignalIds`를 기록한다.
- ready `InsightBrief`가 있으면 `build_copy_package`가 채널별 `planningEvidence.marketingSignals`, `marketingSignalIds`, `marketingEvidenceStatus`를 기록한다.
- 카피 `strategyBasis`에 검수된 마케팅 신호 개수를 근거 문장으로 반영한다.
- selected 신호가 3개 미만이면 `score_planning`이 `marketing_signal_review_required` 경고를 남긴다.
- 현재 운영 데이터는 selected 신호 0개라 경고 상태가 정상이다.

검증:

- ready InsightBrief mock 테스트에서 콘셉트/카피에 `signal-a`, `signal-b`, `signal-c`가 연결됨을 확인했다.
- selected 부족 테스트에서 `marketing_signal_review_required` 경고 확인.
- 전체 프로젝트 테스트 127개 통과.

다음 구현:

1. 콘솔에서 실제 selected 신호 3개 이상을 만든다.
2. 실제 ready `InsightBrief`를 생성한 뒤 파일럿 5건을 다시 실행한다.
3. `marketingEvidenceStatus != ready`일 때 02단계 승인 차단 강도를 warning에서 blocker로 올릴지 판단한다.
4. 올리브영/리뷰 CSV 업로드로 랜덤 가설이 아닌 실제 출처 신호를 추가한다.
# 2026-06-18 진행 기록 - 추천 검수 큐

- 무작위로 모은 신호를 사람이 검수하기 쉽도록 추천 검수 큐를 추가했다.
- 추천 기준:
  - 신호 강도
  - 최신성
  - 신뢰도
  - 타깃 감정/저항과 직접 연결되는지
  - 콘셉트와 카피 양쪽에 쓸 수 있는지
- `seed_random` 신호는 여전히 사실 근거가 아니며, selected 전까지 생성 근거로 직접 사용하지 않는다.
- 추천 큐의 목적은 자동 승인이 아니라 사람이 먼저 볼 순서를 정하는 것이다.

# 2026-06-18 진행 기록 - 콘솔 수집/CSV job 연결

- 마케팅 신호 수집/검수 흐름을 콘솔 job으로 연결했다.
- 콘솔에서 가능한 작업:
  - 랜덤 신호 50개 추가 수집
  - 검수 CSV 내보내기
  - CSV 검증
  - CSV 반영
- 실제 실행으로 랜덤 가설 신호를 100개까지 늘렸다.
- 모든 신호는 아직 `unreviewed`이며, 생성 근거로 쓰려면 사람이 `selected`로 승격해야 한다.
- `selected` 신호 3개 이상이 되기 전에는 InsightBrief가 ready가 되지 않는다.
## 2026-06-20 5차 자동화: HSGN 이벤트별 근거 패킷 적용

- HSGN 여름 톤 케어 이벤트에 대해 수동 검수된 `MarketingSignal` 13개를 추가했다.
- 신호는 고객 불편, 구매 저항, 데일리 루틴 욕구, 6월 시즌 맥락, 제품 근거, 오퍼, 채널 패턴으로 나누어 저장했다.
- `scripts/seed_hsgn_marketing_signals.py`는 신호 저장 후 `InsightBrief`를 `eventId=hsgn-summer-tone-care-2026`으로 생성한다.
- 02 기획 엔진은 이벤트 ID가 맞는 ready `InsightBrief`만 사용한다.
- 근거 신호 원문은 `planningEvidence`와 `strategyBasis`에 남기고, 최종 카피 본문에는 내부 작성용 문구가 섞이지 않도록 사용자용 문장으로 변환한다.
- HSGN 검증 결과: `planning-scorecard.json` status `pass`, criticalErrorCount 0, averageScore 4.0, issues 0.

### 다음 확장

1. Playwright 기반 공개 웹 신호 수집기를 추가한다.
2. 수집 원문은 그대로 생성 예시로 쓰지 않고 `normalizedInsight`로 추상화한다.
3. 화장품 파일럿 5건에 이벤트별 InsightBrief를 만들고 HSGN과 같은 품질 기준을 반복 검증한다.
## 2026-06-20 6차 자동화: 공개 웹 관찰 신호 수집기

- 공개 데이터 수집은 원문을 카피 예시로 쓰지 않고 `MarketingSignal.normalizedInsight`로 추상화해 저장한다.
- `public_signal_collector.py`는 브랜드 페이지, 공개 웹, Google/Naver 트렌드 snapshot, H&B 인기 맥락, 날씨, 캘린더, Meta 광고 관찰, 리뷰 관찰을 지원한다.
- 기본 저장 상태는 `unreviewed`다. 사람이 `selected`로 승격하기 전에는 InsightBrief에 들어가지 않는다.
- 경쟁 광고 관찰은 `do_not_copy_original_expression` risk flag를 붙이고 훅 방식/설득 순서/CTA 구조만 추상화한다.
- `collect_marketing_signals.py --public-snapshot <json>`으로 오프라인 snapshot을 import할 수 있다.
- `collect_marketing_signals.py --capture-url <url> --source-kind <kind>`로 Playwright 공개 페이지 snapshot을 만들 수 있다.
- HSGN 샘플 snapshot 5건을 추가했고, 실제 저장소에는 모두 `unreviewed`로 들어갔다.

### 다음 확장

1. Playwright URL capture를 콘솔 버튼으로 연결한다.
2. 수집된 공개 신호를 검수 카드에서 sourceKind, riskFlags, normalizedInsight 중심으로 보여준다.
3. selected 공개 신호가 늘어난 뒤 이벤트별 InsightBrief를 재생성하고 카피 품질 변화를 측정한다.
