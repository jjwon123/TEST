# Reference Judge Wiki Tests

목적: `design_brain_wiki`가 실제로 AI의 레퍼런스 판단력을 올리는지 검증한다.

이 테스트는 실제 이미지 생성 테스트가 아니다. good/bad/ambiguous 성격이 섞인 레퍼런스 후보 설명을 넣고, 위키 기준으로 `selected / shortlist / rejected` 판단과 시니어 디자이너 피드백 문장이 나오는지 확인한다.

## 테스트 대상

1. `bullion_investment`
2. `cosmetics_skincare`
3. `jewelry_luxury`

## 실행

```powershell
python scripts\run_reference_judge_wiki_tests.py
```

## 출력

```text
design_brain_wiki/tests/output/reference-judge-test-report.json
design_brain_wiki/tests/output/reference-judge-test-report.md
```

## 통과 기준

- decision accuracy가 충분히 높아야 한다.
- 피드백이 "고급스럽습니다/잘 맞습니다"처럼 얕으면 실패한다.
- 피드백에는 역할, 사용 위치, 부족한 기준, 리스크 신호가 들어가야 한다.
- `selected`는 실제 제작 방향 기준이어야 하고, 일부만 좋은 이미지는 `shortlist`로 남아야 한다.

