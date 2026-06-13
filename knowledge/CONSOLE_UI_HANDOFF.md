# Console UI 인수인계

마지막 확인: 2026-06-08

## 접속 주소

- 전체 기능 로컬 콘솔: `http://127.0.0.1:5177`
- 조회 전용 Vercel 콘솔: `https://loopstudio-console.vercel.app`
- 로컬 시작: `start_brand_event_console.bat`

## 현재 결론

- 실제 운영은 당분간 로컬 콘솔을 사용한다.
- 로컬에서는 레퍼런스 수집·선택, 판단 저장, Meta 광고 수집, ComfyUI 생성, 패키지 생성, 폴더 열기 등 기존 POST 기능을 사용할 수 있다.
- Vercel은 화면 공유와 조회 확인용이다. Python API라서 기능이 제한되는 것이 아니라, Vercel에서 로컬 PC 파일시스템과 ComfyUI에 접근할 수 없고 배포 파일시스템이 읽기 전용이기 때문에 POST 기능을 막아 둔 상태다.

## 주요 파일

| 파일 | 역할 |
|---|---|
| `ui/console/index.html` | 전체 콘솔 화면 구조와 기능용 DOM ID |
| `ui/console/styles.css` | LoopStudio UI 스타일과 반응형 처리 |
| `ui/console/app.js` | 화면 렌더링, API 호출, 메뉴 이동, 검수·선택 기능 |
| `scripts/console_server.py` | 로컬 Python API, 파일 조회·저장, 작업 실행 |
| `api/index.py` | Vercel 읽기 전용 Python API 어댑터 |
| `vercel.json` | Vercel Function, rewrite, 배포 파일 설정 |
| `.vercelignore` | Vercel 업로드 제외 파일 |

## 적용된 UI

- 최신 기준 소스: `자동화 프로젝트.zip`
- 마지막으로 푼 비교 소스: `.tmp/ui-redesign-source-2324`
- 좌측 그룹 내비게이션, 상단 작업 바, 지표와 run 카드 중심의 LoopStudio 구조를 적용했다.
- 최신 zip에서 추가된 활동 로그 방향을 현재 vanilla JS 콘솔에 이식했다.
- zip 내부 React JSX를 그대로 실행하는 구조가 아니다. 현재 API와 기능을 보존하기 위해 `ui/console/`의 vanilla HTML/CSS/JS에 필요한 부분만 이식했다.

## 현재 메뉴

- 작업 현황
- 이벤트 생성
- 진행 상세
- 레퍼런스 검수
- 광고 레퍼런스
- 판단 훈련
- 프롬프트
- 이미지 선택
- 최종 패키지
- 활동 로그
- 설정

## 최근 UI 기능

### 광고 레퍼런스

- 긴 Meta 원문 대신 광고주, 3줄 요약, CTA, 원본 이미지 수를 카드에 표시한다.
- 동일 Library ID 광고는 화면에서 중복 제거한다.
- `자세히 보기` 모달에서 전체 수집 원문, 랜딩, 광고 라이브러리 링크를 확인한다.
- Meta 일반 광고의 CTR·ROAS·매출은 공개되지 않는다.
- `신규/지속/장기 집행` 배지는 광고 시작일 기반 보조 신호이며 실제 성과 판정이 아니다.

### 활동 로그

- 현재 bootstrap에서 받은 run과 job 기록을 합쳐 표시한다.
- 전체, 작업, 실행, 오류 필터를 제공한다.
- 실제 사용자 감사 로그 DB는 아직 없다. 현재는 운영 현황 요약 화면에 가깝다.

### 오류 run

- 오류가 있는 run 상세에 복구 안내 패널을 표시한다.
- 완료 단계 유지 안내, 관련 job 로그, 작업 폴더 접근을 제공한다.

## 로컬과 Vercel 기능 경계

| 기능 | 로컬 | Vercel |
|---|---:|---:|
| 대시보드/run 조회 | 가능 | 가능 |
| 레퍼런스·광고 조회 | 가능 | 가능 |
| 활동 로그 조회 | 가능 | 가능 |
| 레퍼런스 선택·판단 저장 | 가능 | 불가 |
| 이벤트 생성·단계 실행 | 가능 | 불가 |
| Meta 광고 수집 | 가능 | 불가 |
| ComfyUI 생성·재생성 | 가능 | 불가 |
| 패키지 생성 | 가능 | 불가 |
| 로컬 폴더 열기 | 가능 | 불가 |

Vercel POST 요청은 `api/index.py`에서 503과 로컬 전용 안내를 반환한다.

## Vercel 배포 상태

- 프로젝트: `loopstudio-console`
- 프로덕션 URL: `https://loopstudio-console.vercel.app`
- 마지막 정상 배포 ID: `dpl_BqDPqUTpAE31gBx7rXAA9ubk4Kzc`
- 배포본 API `/api/bootstrap` 응답 200 확인.
- 작업 현황 26 run, 활동 로그, 광고 레퍼런스와 상세 모달 렌더링 확인.
- 배포 데이터는 저장소 전체가 아니라 필요한 조회 데이터만 포함한다.

## 중요한 주의사항

1. Git 상태에서 콘솔 관련 파일이 현재 미추적(`??`)으로 보인다. 다음 작업 전 반드시 `git status`를 확인하고 파일을 삭제하거나 초기화하지 않는다.
2. `ui/console/app.js`에는 이전 UI 실험 과정에서 같은 이름의 함수가 여러 번 선언된 부분이 있다. JavaScript에서는 뒤쪽 선언이 최종 적용된다. 수정 전 `rg -n "function renderDashboard|function setView|function applyUxLanguage" ui/console/app.js`로 최종 선언 위치를 확인한다.
3. 새 zip UI를 다시 적용할 때 `index.html`을 통째로 교체하면 기능용 DOM ID가 빠져 기존 기능이 깨질 수 있다.
4. Vercel Function에서 `write_manifest()`를 호출하면 읽기 전용 파일시스템 오류가 난다. Vercel에서는 `build_manifest()`만 사용하도록 현재 분기되어 있다.
5. Vercel에 전체 `runs/`, 이미지, 훈련 데이터를 올리면 업로드가 너무 커져 실패할 수 있다. `.vercelignore`와 `vercel.json` 범위를 유지한다.

## 다음 우선순위

1. 광고 레퍼런스 카드에 selected / shortlist / rejected 선택과 저장 기능 추가.
2. 선택 광고를 `reference-evidence.json`으로 변환해 Reference Judge 흐름에 연결.
3. 레퍼런스 검수 화면도 광고 카드처럼 정보 밀도를 줄이고 상세 모달 구조로 통일.
4. `app.js`의 중복 함수 선언을 기능 회귀 없이 정리.
5. 필요해질 때만 외부 DB와 로컬 worker 연결을 설계해 Vercel 쓰기 기능을 확장.

## 검증 명령

```powershell
node --check ui/console/app.js
python -m py_compile scripts/console_server.py api/index.py
python scripts/project_hook_check.py
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5177
Invoke-WebRequest -UseBasicParsing https://loopstudio-console.vercel.app/api/bootstrap
```

## 2026-06-08 UI 용어·이미지 표시 정리

- 사이드바와 검색창의 깨진 장식 아이콘/기호를 제거했다.
- `레퍼런스 검수`는 `작업 레퍼런스`로 변경했다. 현재 run에 연결된 후보를 확인하고 수집·검수하는 화면이다.
- `광고 레퍼런스`는 `Meta 광고 수집`으로 변경했다. Meta 광고 라이브러리에서 새 소재를 수집해 작업 레퍼런스로 연결하는 화면이다.
- `작업 레퍼런스`와 `Meta 광고 수집`은 제작 그룹으로 이동하고, 검수·훈련 그룹에는 `판단 훈련`만 남겼다.
- 레퍼런스 카드 이미지는 `object-fit: contain`으로 변경해 원본 비율 전체가 보이도록 했다.
- 작업 레퍼런스와 Meta 광고 카드 이미지를 클릭하면 원본 보기 모달이 열린다.

## 2026-06-08 Pinterest + Meta 혼합 판단 훈련

- Meta 광고 수집 화면에 `Pinterest + Meta 판단 훈련 만들기` 버튼을 추가했다.
- 현재 run의 Pinterest/search 후보와 연결된 Meta 광고 이미지를 중복 제거해 하나의 `mixed_reference` 세션으로 만든다.
- 두 출처가 모두 있으면 최대한 반반으로 섞어서 빠른 비교 판정에 제공한다.
- 판단 훈련 요약에 Pinterest/search와 Meta 출처 분포를 표시한다.
- 각 훈련 항목 상세에서 `Pinterest/search` 또는 `Meta Ad Library` 출처를 표시한다.

## 2026-06-08 판단 훈련 레이아웃 겹침 수정

- 빠른 비교 카드는 이미지 영역과 판단 정보 영역을 수직으로 완전히 분리했다.
- 비교 이미지는 `object-fit: contain`으로 원본 비율 전체가 보이며, 카드 텍스트가 이미지 위에 올라오지 않는다.
- 상세 검수 영역은 목록 + 이미지 2열로 배치하고, 교정 폼은 아래 전체 폭을 사용한다.
- 좁은 화면에서는 비교 카드와 판단 흐름을 한 열로 쌓아 텍스트 침범을 방지한다.

## 2026-06-08 레퍼런스 기준 및 전체 검수 UI

- 50장 배치는 내부 저장 단위로만 유지하고, 콘솔에는 `reference_learning/all` 전체 세션 하나로 연결한다.
- 판단 훈련은 `미완료 / 자동 제외 / 완료` 탭으로 분리했다. 기본값은 미완료이며 저장한 항목은 즉시 완료로 이동한다.
- Meta 광고 라이브러리 페이지 캡처는 `website_capture`, 짧은 변 500px 미만은 `low_resolution`으로 자동 제외한다.
- 전체 고유 이미지 기준 실제 소재 후보는 945장, 자동 제외 사례는 274장이다.
- 기존 사람 리뷰는 보존되며 자동 기준으로 초기화하지 않는다.

## 2026-06-11 Meta 브랜드 검수 UI

- 판단 훈련의 `meta_brand_review/meta_brand_review_001` 세션에만 Meta 브랜드 전용 필터를 표시한다.
- 필터: 브랜드, 업종(`cosmetics_skincare`/`jewelry_luxury`), 광고주 유형(`direct`/`partner`), 품질(`standard`/`review`), 위험 신호, 검수 완료 여부.
- Meta 세션 상태 탭에는 `전체`를 추가해 완료 여부 필터와 조합할 수 있다.
- 목록, 빠른 비교 카드, 상세 미리보기에 브랜드명, 업종, 광고주 유형, 품질, 위험 신호를 표시한다.
- Pinterest 및 다른 판단 훈련 세션에서는 Meta 전용 필터와 배지를 숨기고 기존 UI를 유지한다.
- UI 계약 테스트: `python -m unittest ui.console.test_meta_brand_review_ui -v`.
- 브라우저 확인: `Medicube` 필터 18장, `review_low_resolution` 필터 16장, Pinterest holdout 003 완료 탭 31장, JS error 0.
