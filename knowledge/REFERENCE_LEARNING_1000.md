# Reference Learning 1000

마지막 업데이트: 2026-06-08

> 2026-06-10 변경: 수량 1,000장 목표를 중단하고 현재 뷰티 브리프 적합성 게이트를 우선한다. 최신 기준과 결과는 `REFERENCE_LEARNING_BRIEF.md`를 따른다.

## 목표

Pinterest/search, Meta 광고 라이브러리, 기존 훈련 시드와 샘플 이미지를 모아 중복 없는 레퍼런스 판단 데이터셋을 만든다.

단순히 파일 1,000개를 저장하는 것이 아니라 아래 조건을 만족하는 고유 이미지 1,000장 이상을 목표로 한다.

- SHA-256 기준 정확 중복 제거
- dHash와 종횡비 기준 근접 중복 표시 및 검수 큐 제외
- 출처, 업종 profile, 기존 AI 판단, 사람 최종 판단 추적
- 이미 검수한 이미지는 새 검수 큐에서 제외
- 미검수 이미지는 50장 단위의 다양성 혼합 배치로 고정

## 품질 분류 기준

콘솔에서는 기존 배치 파일을 내부 저장 단위로만 사용하고, 사람에게는 `reference_learning/all` 전체 세션으로 표시한다.

- `creative_candidate`: 실제 제작 레퍼런스로 검수할 후보
- `rejection_example`: 명확한 품질 문제로 자동 제외한 학습 사례
- Meta 광고 라이브러리의 `/captures/` 페이지 전체 캡처는 `website_capture`로 자동 제외
- 이미지 짧은 변이 500px 미만이면 `low_resolution`으로 자동 제외
- 사람이 저장한 완료 판단은 자동 기준보다 우선하며 삭제하거나 초기화하지 않는다.
- 판단 훈련 화면은 `미완료 / 자동 제외 / 완료`로 구분한다.

## 2026-06-08 현재 결과

- 발견한 원본 파일: 2,072
- 정확 중복 제거 후 고유 이미지: 1,268
- 정확 중복 제거: 804
- 근접 중복 표시 및 검수 큐 제외: 49
- 최종 검수 가능한 고유 이미지: 1,219
- 기존 검수 완료 이미지: 198
- 새 검수 큐: 1,021
- 검수 배치: 21개
- 목표까지 남은 이미지: 0
- 실제 소재 후보: 945
- 자동 제외 사례: 274
- 자동 제외 중 Meta 페이지 캡처: 54

출처 분포:

- Pinterest/search: 883
- Meta 광고 라이브러리: 226
- 샘플 이미지: 54
- 훈련 시드: 29
- 기타: 27

업종 분포:

- cosmetics_skincare: 580
- bullion_investment: 247
- jewelry_luxury: 94
- general: 298

## 파일 구조

```text
design_brain_wiki/reference_learning_1000/
  dataset-index.json     전체 고유 이미지 인덱스와 중복/검수 정보
  summary.json           현재 핵심 수치
  SUMMARY.md             사람이 읽는 요약
  review-batches.json    50장 단위 검수 큐

design_brain_wiki/training_sessions/reference_learning/
  learning_batch_001/
  ...
  learning_batch_021/
```

## 검수 방법

1. 로컬 콘솔 `http://127.0.0.1:5177`에서 `판단 훈련`을 연다.
2. 상단 `1,000장 레퍼런스 학습` 패널에서 전체 수치와 진행률을 확인한다.
3. `미완료 계속 검수`를 누른다.
4. 빠른 비교 판정에서 두 장씩 selected / shortlist / rejected를 저장한다.
5. 명확한 오류는 이유 태그를 함께 기록한다.
6. 저장된 항목은 미완료 목록에서 빠지고 완료 목록으로 이동한다.

판단 기준:

- `selected`: 실제 제작 방향으로 바로 사용할 가치가 높다.
- `shortlist`: 일부 요소는 참고 가능하지만 단독 기준으로 부족하다.
- `rejected`: 저해상도, 웹 캡처, 카테고리 오류, 가짜 텍스트 등으로 제외한다.

## 실행 명령

새 Pinterest/search 후보 수집:

```powershell
.venv\Scripts\python.exe scripts\collect_reference_learning_1000.py --per-query 30
```

마스터 인덱스 재계산:

```powershell
.venv\Scripts\python.exe scripts\build_reference_learning_dataset.py --target 1000 --batch-size 50
```

검수 배치 생성:

```powershell
.venv\Scripts\python.exe scripts\create_reference_learning_batches.py
```

주의:

- 이미 사람 검수가 시작된 뒤에는 `create_reference_learning_batches.py --force`를 사용하지 않는다.
- 새 이미지 추가 후 인덱스를 재계산해도 기존 검수 세션은 보존한다.
- 새 배치가 필요할 때는 기존 배치를 유지한 상태로 추가 생성하는 정책이 필요하다.
- 현재 초기 AI 판단이 없는 이미지는 안전하게 shortlist로 시작한다. 사람 교정 결과가 실제 학습 기준이다.
