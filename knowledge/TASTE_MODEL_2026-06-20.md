# 취향 모델 (경쟁 마케팅 이미지 학습) 2026-06-20

## 목적

경쟁 브랜드 마케팅 이미지를 수집·분석·학습해 "좋은 마케팅/브랜딩"을 체화하는 것.
실현 방식은 **OpenCLIP 임베딩 + 분류기**(linear probe / transfer learning)다. 진짜 가중치
파인튜닝이나 생성(ComfyUI)이 아니라, 검수 라벨로 "좋은 이미지를 알아보고 순위 매기는
취향 모델"을 학습한다.

## 파이프라인

| 단계 | 도구 | 비고 |
|---|---|---|
| 수집 | `collect_meta_brand_registry.py` (Meta, 시스템 Edge) / Pinterest(로그인 세션 필요) | 브라우저는 시스템 Edge/Chrome 사용 |
| 분석 | `services/visual_reference/qwen_reviewer.py` | creative type 태깅용. 취향 판단엔 부적합(검증됨) |
| 라벨 | `services/visual_reference/taste_labels.py` | 검수 세션의 selected/rejected → good/bad |
| 학습·평가 | `scripts/train_taste_model.py` | 임베딩→교차검증 AUC→전체 학습→모델 저장 |
| 활용 | `scripts/rank_images_by_taste.py` | 저장 모델로 신규 이미지 취향 점수 순위 |

## 검증 결과

- 단일 세션(meta_brand_review_001, 48장): ROC AUC **0.93**, top-10 lift 2.02x.
- 통합 7세션(240장, Pinterest+Meta 혼합): ROC AUC **0.82**, top-10 정밀도 0.70(baseline 0.32 → **2.18x**), status pass.
- 통합셋이 더 낮은 건 Pinterest 노이즈가 섞인 더 어려운 분포라 정상. 여전히 명확히 유용.
- 대조: 메타데이터/Qwen 프롬프트 판단은 50%대로 약함. **이미지 임베딩 학습이 취향 체화의 정답 경로.** ([[REFERENCE_ACCURACY_2026-06-20]])

## 선순환 (데이터 늘릴수록 강해짐)

1. Meta 경쟁사 광고 대량 수집
2. 콘솔 판단 훈련에서 사람 라벨링(🙋) — 학습 연료
3. `train_taste_model.py` 재학습, AUC 재측정
4. `rank_images_by_taste.py`로 신규 수집을 자동 순위·필터 → 좋은 것만 남김

## 명령

```powershell
.venv\Scripts\python.exe scripts\train_taste_model.py                 # 전체 세션 학습
.venv\Scripts\python.exe scripts\train_taste_model.py --include-shortlist
.venv\Scripts\python.exe scripts\rank_images_by_taste.py <이미지폴더> --top-k 30
```

산출물: `.tmp/taste-model/taste-classifier.joblib`, `taste-model-report.{json,md}` (모두 재생성 가능).
관련: [[BACKLOG]], [[REFERENCE_ACCURACY_2026-06-20]]
