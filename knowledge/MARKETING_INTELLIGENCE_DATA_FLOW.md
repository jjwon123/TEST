# 마케팅 인텔리전스 데이터 플로우

## 2026-07-01 대표 파일럿 실제 후보 데이터

- 후보 snapshot:
  `assets/rules/cosmetics-pilot-public-evidence-snapshot.json`
- 후보 수: 대표 5개 이벤트 x 3개 = 15개.
- 현재 모두 unreviewed.
- 출처 메타데이터:
  `sourceName`, `url`, `title`, `publishedAt`, `observedAt`, `methodology`,
  `section`, `query`.
- 독립 출처는 host 기준으로 계산한다.
- 출처 감사:
  `.tmp/model-benchmarks/cosmetics-pilot-source-audit.json`
- 카테고리 연구는 고객 문제, 저항, 시장 흐름 설명에는 쓸 수 있지만
  미확인 제품의 효능 proof에는 사용할 수 없다.

## 2026-07-01 이벤트 근거 작업 큐

근거 데이터는 양보다 이벤트 적합성과 역할 조합을 먼저 검사한다.

```text
이벤트 계획
-> 필수 근거 역할 정의
-> 출처별 공개 관찰 수집
-> eventId/topic 범위 격리
-> 사람 검수
-> 역할·출처 다양성 게이트
-> InsightBrief 승격
```

현재 필수 조합:

| 이벤트 유형 | 필수 근거 |
|---|---|
| 시즌 | 고객 문제, 시기 명분, 검색·시장 흐름 |
| 프로모션 | 고객 욕구, 구매 저항, 혜택 근거 |
| 출시 | 고객 문제, 구매 저항, 제품 근거 |
| 교육 | 고객 문제, 제품 근거, 채널 반응 구조 |
| 브랜딩 | 고객 욕구, 구매 저항, 채널 반응 구조 |

- 모든 이벤트는 selected 3개 이상, 출처 종류 2개 이상이 필요하다.
- Playwright 공개 URL 캡처는 `sourceRef.eventId`와 전용 `topic`을 함께
  저장한다.
- 큐 파일:
  `.tmp/model-benchmarks/cosmetics-evidence-queue.json`
- 이벤트 선택 전에는 전체 랜덤 가설을 검수 목록에 보여주지 않는다.
- 자동 수집 결과는 항상 unreviewed이며 사람이 선택하기 전 생성 근거가 아니다.

## 2026-06-30 이벤트 범위 규칙

- `MarketingSignal`은 가능하면 `sourceRef.eventId`를 가진다.
- 여러 이벤트에 공통으로 쓸 수 있는 관찰은 명시적인 `topic`으로 묶고,
  InsightBrief 생성 시 그 topic을 직접 지정한다.
- 구체 이벤트에서 eventId와 topic을 모두 생략한 전체 selected 조회는 금지한다.
- `general` InsightBrief는 탐색·대시보드용이며 구체 광고 생성 fallback이 아니다.
- 이벤트별 승인 근거 파일은
  `design_brain_wiki/marketing_signals/insight-briefs/`에 저장한다.
- 품질 수치는 신호 개수뿐 아니라 이벤트 ID 일치 여부를 포함한다.

## 2026-06-20 업데이트: 파일럿 감사와 근거 연결 기준

화장품 파일럿 5건 감사는 이제 단순히 화면에 글이 보이는지만 보지 않는다. 다음 세 가지가 동시에 맞아야 통과한다.

```text
마케팅 신호/InsightBrief 연결
-> 콘셉트 3안의 marketingSignalIds 연결
-> 채널별 카피의 planningEvidence.marketingSignalIds 연결
-> scorecard 치명 오류 0
```

- `scripts/audit_cosmetics_pilot_goal.py`는 텍스트 깨짐, JSON/HTML/프로그래밍 구조 노출, 내부 scorecard 치명 오류를 함께 본다.
- `scripts/benchmark_ad_planning.py`는 오래된 결과 캐시에 치명 오류가 있으면 자동 재생성한다.
- 콘셉트 비평은 콘셉트 단계에서 카피/채널 미생성을 실패로 보지 않는다. 카피/채널 검사는 카피 패키지 생성 이후 scorecard에서 판단한다.
- 현재 5건 파일럿은 `criticalErrorCount 0`, 평균 사람 평가 `4.0`, 무수정 승인율 `1.0`으로 통과했다.

다음 데이터 플로우 목표는 파일럿 5건이 아니라 화장품 평가셋 20건에 같은 기준을 적용하는 것이다. 특히 외부 광고, 계절, 제품 랭킹, SNS/검색 트렌드 신호를 더 모아 콘셉트별 근거가 실제 마케터 기획안처럼 설득되게 만들어야 한다.

## 2026-06-20 업데이트: 공개 URL 캡처 경로

마케팅 신호 수집은 이제 CSV/import뿐 아니라 콘솔에서 공개 URL을 직접 넣어 시작할 수 있다.

```text
공개 URL 입력
-> Playwright/공개 페이지 텍스트 캡처
-> 원문을 직접 쓰지 않고 추상 마케팅 신호로 변환
-> unreviewed 신호 저장
-> 검수 CSV export
-> 사람이 selected / shortlist / rejected 판정
-> selected 신호만 InsightBrief와 02_content_planning 생성 근거로 사용
```

콘솔 job 모드:

- `public_snapshot`: 이미 정리된 공개 관찰 snapshot JSON을 가져온다.
- `public_capture`: URL 하나를 캡처해 `.tmp/marketing-signals/public-capture-latest.json` snapshot으로 만들고 검수 대기 신호에 추가한다.
- `public_capture`는 `urls` 배열과 `--capture-url` 반복 입력을 지원한다. CLI에서는 `--capture-urls-file`로 여러 URL을 한 번에 넣을 수 있다.

주의:

- 공개 URL 원문은 생성 카피에 직접 복사하지 않는다.
- 기본 decision은 `unreviewed`이며 사람이 검수하기 전에는 생성 예시로 쓰지 않는다.
- URL 캡처 결과에 깨진 텍스트, HTML/JSON 조각, 경쟁사 문구 직접 복제가 보이면 `rejected` 또는 QA 차단 규칙으로 승격한다.
- HSGN 파일럿은 `hsgn_summer_tone_care` topic으로 공개 신호를 모은 뒤 selected 신호만 InsightBrief에 연결한다.

### 공개 캡처 QA

공개 페이지 캡처 결과는 다음 위험 플래그를 붙인다.

- `raw_html_detected`: HTML 태그나 script/style 조각이 남아 있음.
- `raw_json_detected`: JSON 키/배열 구조가 원문에 남아 있음.
- `broken_text_suspected`: 깨진 인코딩 또는 사람이 읽기 어려운 텍스트 의심.
- `thin_public_observation`: 관찰 텍스트가 너무 짧아 기획 근거로 쓰기 어려움.
- `capture_quality_blocked`: 위 문제 중 치명적인 항목이 있어 InsightBrief 근거 사용 차단.

`capture_quality_blocked` 신호는 자동 selected 승격을 허용하지 않는다. 사람이 selected로 바꿔도 InsightBrief는 해당 신호를 제외한다. 먼저 원문을 정리하거나 사람이 직접 추상화한 `normalizedInsight`를 만든 뒤 다시 검수해야 한다.

검수 저장 정책:

- 콘솔에서 `선택`을 눌러도 `capture_quality_blocked` 신호는 `shortlist`로 저장된다.
- CSV import에서 decision을 `selected`로 넣어도 같은 정책이 적용된다.
- 자동 보류된 신호에는 `capture_quality_blocked` reason tag와 보류 사유 메모가 붙는다.
- 대시보드의 `사용 가능` 수는 selected 중 실제 InsightBrief 근거로 쓸 수 있는 신호만 계산한다.
- InsightBrief 생성 버튼도 `사용 가능` 수가 최소 기준을 넘을 때만 열린다. selected 총량이 충분해도 품질 차단 신호가 섞여 있으면 다음 단계로 넘어가지 않는다.

정제 흐름:

- 품질 차단 신호는 버리는 것이 아니라 사람이 `관찰 요약`, `타깃 정의`, `기획 인사이트`를 고쳐 다시 저장할 수 있다.
- 정제 저장 후 HTML/JSON/깨진 텍스트/얇은 관찰 문제가 사라지면 차단 flag를 제거하고 `human_cleaned_public_signal`을 붙인다.
- 그 뒤 검수자가 selected로 다시 승격하면 `selectedUsable`에 포함되고 InsightBrief 근거로 사용할 수 있다.

루프 감사:

- `scripts/audit_marketing_planning_loop.py`는 검수된 신호가 실제 02 기획 산출물에 연결됐는지 확인한다.
- 통과 조건:
  - `selectedUsable`이 최소 기준 이상
  - InsightBrief가 `ready`
  - planning scorecard가 `pass`, 치명 오류 0, 평균 4.0 이상
  - 콘셉트 3안이 marketingSignalIds를 가진다
  - 채널별 카피 산출물이 planningEvidence.marketingSignalIds를 가진다
- HSGN 파일럿 run은 현재 이 감사에서 `pass`다.
- 콘솔의 `근거 연결 감사` 버튼은 같은 감사를 job으로 실행한다. 결과는 job 로그와 `.tmp/model-benchmarks/marketing-planning-loop-audit.json`에서 확인한다.
- 콘솔은 최신 감사 리포트를 광고 기획 검수 패널에 요약 표시한다. 검수자는 터미널 없이 `사용 가능 신호`, `평균 점수`, `치명 오류`, `콘셉트/카피 근거 연결`을 확인할 수 있다.

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
## 2026-06-20 업데이트: 파일럿 목표 감사와 텍스트 품질 게이트

- 마케팅 신호가 연결되어도 표시 텍스트가 깨지면 파일럿 목표는 통과하지 않는다.
- `scripts/audit_cosmetics_pilot_goal.py`는 파일럿 5건에서 다음을 함께 본다.
  - 콘셉트 3안 준비
  - 채널별 카피 준비
  - 사람 평가 저장
  - 깨진 한글/raw JSON/HTML/프로그래밍 구조 노출
  - 콘셉트 3안 분리
- 콘셉트와 카피의 근거 신호 연결
- 현재 리포트는 `.tmp/model-benchmarks/cosmetics-pilot-goal-audit.json`이며, 콘솔의 `파일럿 목표 감사` 카드가 이 값을 보여준다.
- 현재 파일럿 5건은 후보·카피·사람평가·치명 오류 기준을 통과했다.
- 다음 데이터 플로우 우선순위는 화장품 20건으로 확대하고, 외부 광고/트렌드/계절/고객 반응 신호를 더 쌓아 콘셉트 설득력을 높이는 것이다.
