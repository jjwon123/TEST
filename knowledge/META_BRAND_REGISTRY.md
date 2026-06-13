# Meta 브랜드 레지스트리

마지막 업데이트: 2026-06-11

## Meta 검수 100장 결과

- 원본 풀: 132장
- 최종 검수 세션: 100장
- 프로필: 화장품·스킨케어 62장, 주얼리·럭셔리 38장
- 광고주 유형: `direct` 88장, `partner` 12장
- 브랜드 수: 23개
- 품질: `standard` 84장, `review` 16장
- 무결성: 정상 이미지 100장, SHA 중복 0장
- 세션: `design_brain_wiki/training_sessions/meta_brand_review/meta_brand_review_001`

검수 세션은 브랜드당 최대 20장, 한 광고당 최대 5장, 협업 광고 최대 20장으로 제한한다. 화장품의 할인 문구형 프로모션 카드는 자동 채택하지 않고 사람 검수에서 제외 기준을 학습한다.

## 목적

범용 키워드 검색보다 검증된 브랜드 광고주를 먼저 수집해 Meta 광고 검색 오염을 줄인다.

```text
업종별 메이저 브랜드 레지스트리
→ 브랜드명으로 Meta 검색
→ 광고주명 별칭 엄격 일치
→ 이미지 기본 품질 검사
→ 브랜드별 accepted-ads.json
→ 이후 브리프 역할 필터와 Reference Judge
```

## 현재 레지스트리

- `cosmetics_skincare`: 20개
- `jewelry_luxury`: 20개
- 기준 파일: `assets/rules/meta-brand-registry.json`

각 브랜드는 아래 정보를 가진다.

- 영문 브랜드명
- Meta 검색어
- 광고주명 일치용 한글·영문 별칭
- 기본 시장
- 참고 역할: product, promotion, ingredient, luxury, campaign, craft 등

## 수집 원칙

- 처음부터 20개 전체를 돌리지 않고 업종별 1~3개부터 소량 테스트한다.
- 광고주명이 브랜드 별칭과 일치한 광고만 accepted 후보로 남긴다.
- 브랜드 광고라도 제품 성격이 브리프와 다를 수 있으므로 바로 run selected에 연결하지 않는다.
- 짧은 변 500px 이상은 `standard`, 450~499px는 `review` 품질로 저장한다.
- 450px 미만, 극단 비율, 파일 손상은 제외한다.
- 결과가 계속 0개이거나 오염이 심한 브랜드는 비활성화하고 별칭 또는 국가를 보정한다.

## 실행

```powershell
# 화장품 상위 3개 브랜드 소량 수집
.venv\Scripts\python.exe scripts\collect_meta_brand_registry.py `
  --profile cosmetics_skincare --brand-limit 3 --ads-per-brand 3

# 특정 주얼리 브랜드 수집
.venv\Scripts\python.exe scripts\collect_meta_brand_registry.py `
  --profile jewelry_luxury --brand-id cartier --ads-per-brand 3
```

콘솔 `Meta 광고 수집 → 검증 브랜드 묶음 수집`에서도 실행할 수 있다.

## 테스트 결과

### Medicube

- Meta 검색 광고: 3
- 광고주명 일치 광고: 1
- 허용 이미지: 7
- 관찰: 공식 광고지만 뷰티 디바이스 소재가 포함됨. 이후 브리프 역할 필터 필요.

### Cartier

- Meta 검색 광고: 3
- 광고주명 일치 광고: 2
- 허용 광고: 1
- 허용 이미지: 1
- 관찰: 리셀러 광고는 제외됨. 공식 세로형 소재는 480px라 `review` 품질로 허용.

## 브랜드 선정 근거

- L'Oréal 글로벌 브랜드 포트폴리오
- Amorepacific 글로벌 브랜드 운영 사례
- Richemont Maisons
- LVMH Watches & Jewelry Maisons

레지스트리는 완성 목록이 아니다. 소량 수집 결과가 안정적인 브랜드부터 유지하고 계속 추가한다.
