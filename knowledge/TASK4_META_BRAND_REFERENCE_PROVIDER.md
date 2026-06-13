# Task 4 - Meta Brand Review Provider

Date: 2026-06-11

## Scope

`meta_brand_review_001`의 검수 이미지를 `03_reference_research`에서 브리프 기반 후보 provider로 사용한다.

- 입력 기준: 이벤트 브리프 업종, 브랜드, 필요한 reference role
- 공급원 병합: 기존 Pinterest/reference manifest를 유지하고 Meta brand review 선택분을 추가
- 우선순위: direct advertiser 우선
- 감점: partner advertiser `-10`, `registryQuality=review` `-12`
- 기본 제외: `manual_meta_character_audit.json`의 `promotion_text_heavy`, `card_news`, `reject_noise`
- 기록: `03_reference_research/reference-evidence.json`

## Implementation

- `services/ad_reference/meta_brand_provider.py`
  - Meta 검수 세션을 읽고 업종/브랜드/역할 적합도를 계산한다.
  - direct를 우선 정렬하고 브랜드/광고별 편중을 제한한다.
  - 선택 이미지를 run의 `references/selected/`로 복사한다.
  - 후보별 score breakdown과 선택/import 상태를 evidence로 만든다.
- `pipeline/03_reference_research/handlers/run_reference_research.py`
  - 기존 Pinterest manifest를 provider 입력으로 유지한다.
  - Meta 선택 결과를 manifest에 병합한다.
  - `reference-evidence.json`을 stage output으로 기록한다.

환경 변수:

```powershell
$env:META_BRAND_REFERENCE_MODE='auto' # off/disabled/none으로 비활성화
$env:META_BRAND_REFERENCE_LIMIT='8'
```

## Verification

단위 테스트:

```powershell
.venv\Scripts\python.exe -m unittest pipeline.03_reference_research.tests.test_meta_brand_provider -v
```

결과: 3 tests passed.

테스트 런:

```text
runs/2026-06-03_02-26-24_여름-h-b-뷰티-세일-나이아신아마이드-집중-케어
```

03 재실행 결과:

- Meta 업종 적합 후보: 62
- Meta 선택/import: 8/8
- 선택 광고주 유형: direct 8, partner 0
- 선택 품질: standard 8, review 0
- 기존 공급원 유지: Pinterest 계열 20, 기존 Meta Ad Library 23
- 최종 Meta brand review 자산: 8
- evidence: `03_reference_research/reference-evidence.json`
