# Direction Feedback

## 목적

direction feedback은 selected/rejected 개별 판단을 넘어 다음 디자인 방향을 제안한다.

## 문장 구조

```text
현재 방향은 [강점]은 있지만 [부족한 축]이 약합니다.
다음 단계에서는 [보강할 reference category]를 추가하고 [피해야 할 방향]을 차단해야 합니다.
```

## 예시

- 현재 selected 세트는 제품 정체성은 강하지만 포스터 레이아웃 기준이 약합니다. 다음 단계에서는 headline space가 분명한 campaign layout reference를 보강해야 합니다.
- 무드가 고급스럽긴 하지만 금융 상담의 신뢰보다 장식성이 강합니다. 다음 검색에서는 private banking, wealth management, calm consultation 방향을 강화해야 합니다.
- bad signal은 없지만 모든 이미지가 제품컷 중심입니다. 카드뉴스 메인과 배너 변환을 위해 blank text area가 있는 레퍼런스를 추가해야 합니다.

## 평가 항목 연결

- `selectedCoverage`
- `goodSeedCoverage`
- `missingCriteria`
- `nextQueryHints`

