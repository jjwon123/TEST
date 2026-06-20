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

1. 경쟁 이미지 수집 (소스별 아래 참고)
2. `scripts/ingest_image_folder_session.py`로 **임의 폴더 → 콘솔 라벨 가능 세션** 변환
3. 콘솔 판단 훈련에서 사람 라벨링(🙋) — 학습 연료
4. `train_taste_model.py` 재학습, AUC 재측정
5. `rank_images_by_taste.py`로 신규 수집을 자동 순위·필터 → 좋은 것만 남김

## 소스별 수집 (어느 게 나은가)

기원님 목적엔 **품질·타깃·안정성** 기준으로 우선순위가 있다:

1. **Meta Ad Library (1순위)** — 실제 집행 경쟁 광고. 검증된 최고 성적(AUC 0.93)이 Meta에서 나옴.
   시스템 Edge로 로그인 없이 동작. `python scripts/collect_meta_ads.py --query "..." --country KR --limit 8 --scrolls 3 --headless`
   → 출력 `references/meta_ads/searches/<stamp>_<query>/`. 검증: 2026-06-20 "스킨케어 세럼" 23장 수집 성공.
2. **Chrome 확장 (`pinterest-board-collector`, 2순위)** — gallery-dl 원본 해상도가 최고 품질.
   특정 좋은 보드를 수동으로 긁을 때. 다운로드 폴더를 ingest로 연결.
3. **Playwright Pinterest 검색 (취향학습엔 비추천)** — 썸네일 저화질(low_resolution 게이트 존재) + DOM 취약.
   런 파이프라인 경량 레퍼런스 용도로만.

## (가)/(나) 공통 연결 흐름

```powershell
# 1) 수집 (Meta 예시)
.venv\Scripts\python.exe scripts\collect_meta_ads.py --query "스킨케어 세럼" --country KR --limit 8 --scrolls 3 --headless
# 2) 폴더 -> 콘솔 라벨 가능 세션
.venv\Scripts\python.exe scripts\ingest_image_folder_session.py <수집폴더> --session-id meta_serum_001
# 2-1) (선택) 학습된 모델로 AI 1차 추천 미리 붙이기 -> 사람은 맞다/틀리다만
.venv\Scripts\python.exe scripts\pretag_session_with_taste.py --session-id meta_serum_001
# 3) 콘솔(http://127.0.0.1:5177) 판단 훈련에서 good/bad 교정  [사람]
# 4) 재학습
.venv\Scripts\python.exe scripts\train_taste_model.py
```

확장(나)도 동일: 확장 다운로드 폴더를 2)의 <수집폴더>로 주면 끝.

## 명령

```powershell
.venv\Scripts\python.exe scripts\train_taste_model.py                 # 전체 세션 학습
.venv\Scripts\python.exe scripts\train_taste_model.py --include-shortlist
.venv\Scripts\python.exe scripts\rank_images_by_taste.py <이미지폴더> --top-k 30
```

산출물: `.tmp/taste-model/taste-classifier.joblib`, `taste-model-report.{json,md}` (모두 재생성 가능).
관련: [[BACKLOG]], [[REFERENCE_ACCURACY_2026-06-20]]
