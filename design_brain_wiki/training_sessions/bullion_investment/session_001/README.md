# Bullion Investment Training Session 001

이 세션은 Senior Designer Brain Wiki를 실제 판단 훈련으로 바꾸기 위한 첫 bullion reference review 세트다.

## Files

- `references/`: 리뷰 대상 30장
- `ai_judgement.json`: AI 1차 판단 구조화 데이터
- `ai_judgement.md`: 사람이 읽는 AI 판단표
- `kiwon_review_template.md`: 기원님 교정 입력용
- `correction_log.md`: 틀린 패턴 기록용
- `wiki_update_suggestions.md`: 위키/rubric 보강 제안

## Important

Session type: `seed_test`
Source run: `-`

이번 판단은 로컬 Qwen/Ollama 비전 모델을 호출하지 않았다. Pinterest/search 수집물 또는 seed metadata와 design_brain_wiki 기준을 사용한 1차 판단이다.

Summary: {'total': 30, 'decisionCounts': {'selected': 7, 'shortlist': 20, 'rejected': 3}, 'categoryCounts': {'product_reference': 10, 'finance_mood_reference': 10, 'poster_layout_reference': 7, 'bad_reference': 3}, 'needsKiwonReview': 30}
