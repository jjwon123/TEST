# 실제 품질 및 OpenCLIP 검증

검증일: 2026-06-13

## 제품 고정 합성

- 대상: `product_locked_ad_background_v1`
- 입력: ComfyUI `cosmetic_product_foreground_v3.png`
- 출력 크기: 1024x1280
- 결과: 기능 통과, 광고 품질 보완 필요
- 확인: 제품 형태, 라벨, 패키지 텍스처가 생성형 재도색 없이 유지됐다.
- 문제: 기본 `product_scale: 0.58`에서도 투명 입력의 실제 제품 영역이 작아 결과상 제품 존재감이 지나치게 약하다.
- 조치: 실제 제품 alpha bounding box 기준 자동 스케일 또는 제품별 scale preset이 필요하다.

## 한글 텍스트 오버레이

- 대상: `korean_poster_overlay_1024`
- 입력: 위 제품 고정 합성 결과
- 결과: 한글 렌더링 기능 통과, 광고 납품 품질 실패
- 확인: Unicode 한글 제목, 부제, 푸터가 깨짐 없이 렌더링됐다.
- 문제: 밝은 배경 대비 부족, 어색한 제목 줄바꿈, 불필요한 `4:5` 배지, 약한 제품/카피 위계.
- 조치: 배경 명도 기반 색상 선택, text shadow/stroke, 제목 폭/크기 조정, 비율 배지 제거가 필요하다.

검수 산출물은 `.tmp/comfy-quality-validation/`에 저장했다.

## OpenCLIP Holdout 효과

- 데이터: `meta_brand_review_001` 사람 최종 판단 중 `selected` 19건, `rejected` 29건
- 방식: OpenCLIP 이미지 임베딩 + 로지스틱 회귀, stratified 5-fold holdout
- ROC AUC: `0.9328`
- Average precision: `0.8840`
- 전체 selected 기준선: `0.3958`
- 상위 10개 selected 정밀도: `0.8000`
- 상위 10개 lift: `2.0211x`
- 결론: 실제 개선 효과가 있다. 단독 자동 selected가 아니라 Qwen/규칙 기반 gate 뒤 shortlist 우선순위에 사용한다.

재실행:

```powershell
.venv\Scripts\python.exe scripts\validate_openclip_effect.py
```

상세 보고서는 `.tmp/openclip-effect/openclip-effect-report.md`에 생성된다.

## 2026-06-14 후속 개선 검수

- 제품 고정 합성: alpha 실제 경계를 기준으로 투명 여백을 잘라낸 뒤 확대하도록 수정했다.
- 결과: 기존 작은 제품 문제를 해결했고, 제품 라벨과 형태 보존을 유지했다.
- 한글 오버레이: 자동 `4:5` 배지를 제거하고, 밝은 배경용 진한 색상과 굵은 제목 폰트, 넓은 제목 영역을 적용했다.
- 결과: 제목 한 줄 유지, 본문/푸터 대비, 제품과 카피 위계가 개선됐다.
- 회귀 테스트: ComfyUI preset 테스트 3개를 추가했으며 전체 프로젝트 테스트 30개와 project hook이 통과했다.
- 검수 산출물:
  - `.tmp/comfy-quality-validation/product_locked_improved_20260614.png`
  - `.tmp/comfy-quality-validation/korean_overlay_improved_v2_20260614.png`
- 실제 ComfyUI 커스텀 노드 파일에도 alpha crop 수정이 반영됐다. 현재 실행 중인 ComfyUI 프로세스에는 다음 재시작부터 적용된다.
