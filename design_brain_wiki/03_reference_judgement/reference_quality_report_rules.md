# Reference Quality Report Rules

## 자료 원문/링크

- Senior Designer Brain Wiki local schema: ../00_JUDGE_SCHEMA.md
- Current project rule files: ../../assets/rules/

## 핵심 요약

`reference-quality-report`는 선택 결과만 보여주면 안 된다. 왜 selected인지, 왜 rejected인지, good/bad seed와 얼마나 가까운지, fallback이 깨끗한지까지 보여줘야 한다.

## 디자인 판단 질문

- selected 안에 bad signal이 0인가?
- selected가 product/mood/layout 역할을 균형 있게 포함하는가?
- rejected 이유가 사람이 검토 가능한 문장인가?
- fallback이 캐릭터/귀여운 3D 방향으로 오염되지 않았는가?

## 평가 항목

- `selectedBadSignalCount`
- `fallbackClean`
- `goodSeedCoverage`
- `selectedCoverage`
- `rejectionReasonClarity`

## good/bad 적용

- good: report를 읽으면 다음 행동이 명확하다.
- bad: selected 리스트만 있고 판단 근거가 없다.

## AI 피드백 문장 예시

- selected 세트는 bad signal이 없지만 poster layout coverage가 낮아 카피 여백 기준 레퍼런스를 추가해야 합니다.

