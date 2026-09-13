# 결정사항 기록

이 문서는 프로젝트의 중요한 결정을 날짜와 이유와 함께 남기는 곳이다. 나중에 AI가 작업할 때 가장 많이 참고해야 하는 문서 중 하나다.

## 2026-07-18 - 이벤트 주 의도와 집행 가능 일정을 승인 전에 확정한다

- 이벤트 유형은 명시값을 최우선으로 하고, 없으면 이벤트명·목적의 주 의도를
  부가 오퍼보다 먼저 판정한다.
- 시즌 캠페인에 증정 혜택이 포함돼도 혜택이 주 목적이 아니면 `seasonal`이다.
- 종료일이 현재보다 과거인 입력은 자동 승인하거나 임의 연장하지 않고
  `needs_input`으로 차단한다.
- 이유: 잘못된 유형은 전략과 근거 큐를 오염시키고, 만료 일정의 승인은 실제
  집행 불가능한 산출물을 다음 단계로 넘긴다.
- 상태 계약: 미해결 입력은 `01_event_brief=needs_input`,
  `run_state=brief_input_required`로 명시하고 승인 API에서도 차단한다.

## 2026-07-18 - 전체 경로 실증은 운영 자산과 분리한 격리 런에서 수행한다

- 자동 스모크의 사람 승인 표시는 `smoke_test`로 명시하고 임시 루트에만 기록한다.
- 생성 스텁의 파일 경로 검증에는 기존 로컬 PNG를 임시 런으로 복사해 사용한다.
- 아카이브 정책·스키마·인덱스·승인 자산도 `.tmp` 루트로 돌려 전역 자산을
  변경하지 않는다.
- 운영 사람 검수와 스모크 승인은 서로 대체하지 않는다.

## 2026-07-18 - 승인된 비차단 QA 경고는 경고 상태를 보존해 아카이브한다

- 6단계에서 사람이 구체 메모와 함께 승인한 `warn`은 7단계 진행을 허용한다.
- 자산의 `qa_status`는 `warn`으로 남겨 완전 통과 자산과 구분한다.
- 승인 기록이 없거나 `error`, `blocker`, `fail`이면 아카이브하지 않는다.
- 이유: 승인 가능 게이트와 아카이브 정책이 서로 모순되면 정상적인 사람 예외
  처리도 항상 `done_no_assets`로 끝난다.

## 2026-07-01 - 빠른 검수는 추천만 자동화하고 최종 저장은 사람이 승인한다

- 결정: 이벤트별 후보의 추천 판정과 사유 초안은 자동 계산할 수 있지만
  selected/shortlist 저장은 명시적 사람 확인 이후에만 수행한다.
- 이유: 15개를 반복 입력하는 부담은 줄이되 검수 데이터의 사람 승인 의미는
  유지해야 한다.
- 저장은 원자적으로 처리해 배치 중 하나가 실패하면 전체를 반영하지 않는다.

## 2026-07-01 - 외부 카테고리 연구를 가상 제품 효능 proof로 쓰지 않는다

- 결정: 탄력·장벽·보습 카테고리 연구가 있어도 현재 이벤트 제품의 성분과
  제형이 확인되지 않으면 제품 효능 proof로 selected할 수 없다.
- 이유: 같은 카테고리의 체계적 문헌고찰은 고객 저항과 주장 한계를 설명할 수
  있지만 미확인 제품의 효능을 입증하지 않는다.
- 적용: `launch-serum`은 후보 3개가 있어도 공식 제품 자료가 없으므로
  `ready`로 승격하지 않는다.
- 출처 다양성: 저장 분류가 같은 `public_web`이어도 서로 다른 host이면 독립
  출처로 계산한다.

## 2026-07-01 - 근거 준비는 개수뿐 아니라 역할과 출처 다양성을 강제한다

- 결정: 이벤트당 selected 신호 3개만으로 준비 완료 처리하지 않는다.
- 필수 조건:
  - 이벤트 유형별 필수 근거 역할을 각각 최소 1개 포함.
  - 서로 다른 출처 종류를 최소 2개 포함.
  - 품질 차단 위험 플래그가 없어야 함.
- 이유: 같은 종류의 광고 문구나 동일 출처 관찰 3개는 고객 반응, 제품 진실,
  시기 명분을 함께 설명하지 못한다.
- 운영: 대표 5건을 우선 처리하되 동일 규칙을 20건 전체에 적용한다.
- 자동화 제한: 큐는 수집·검수 우선순위만 제안하며 selected와 사람 평가는
  자동 생성하지 않는다.

## 2026-06-30 - 마케팅 근거는 이벤트 ID 정확 일치만 허용한다

- 결정: 구체 이벤트 생성에서 다른 이벤트 또는 `general` InsightBrief를
  fallback으로 사용하지 않는다.
- 허용 범위: 신호의 `sourceRef.eventId`가 현재 이벤트와 정확히 같거나,
  사람이 명시한 전용 `topic`이 일치하는 경우.
- 이유: 신호 ID 존재만으로 통과시키면 겨울 보습과 여름 톤케어처럼 서로 다른
  이벤트가 같은 고객 인사이트와 시즌 근거를 사용해 설득력이 무너진다.
- 기존 결과: 20건 모두 HSGN 여름 톤케어 신호를 사용했으므로 전용 근거
  기준 `0/20`으로 재분류한다.
- 정책: 근거 불일치 결과는 읽을 수는 있지만 편집·최종 승인할 수 없다.

## 2026-06-30 - 사유 없는 검수는 학습 데이터로 저장하지 않는다

- 결정: 전략과 카피 검수에는 최소 1개의 허용 사유 태그와 구체 검수 메모가
  반드시 있어야 한다.
- 적용 범위: 콘솔 직접 검수, 이벤트 run 검수, 20건 벤치마크, 전략 CSV import.
- 이유: 판정값과 점수만 있는 데이터는 수정 방향과 선호 원인을 설명하지 못해
  검색 예시, 교정 규칙, 향후 파인튜닝 데이터로 쓰기 어렵다.
- 저장 실패는 산출물 변경 전에 처리해 부분 저장을 허용하지 않는다.
- 진행률은 브라우저 localStorage가 아니라 실제 저장소 수치에서 계산한다.

## 2026-06-28 - 로컬 생성은 같은 이벤트 exact-match 교정만 직접 재사용한다

- 결정: 로컬 결정론적 생성기는 승인된 `CopyCorrectionRecord` 중 같은 이벤트·같은 채널의 원문 필드가 현재 생성문과 정확히 일치할 때만 수정문을 적용한다.
- 이유: 다른 이벤트의 승인 문장을 통째로 복사하면 제품·혜택·시즌 사실이 잘못 전이될 수 있다.
- 브랜드 정책: 업종과 브랜드를 함께 분리하며, 브랜드 없는 생성은 타 브랜드 교정을 가져오지 않는다.
- 외부 모델 정책: 승인 교정을 구조화 예시로 제공하되 최종 QA를 거친다.
- 추적: 적용된 교정 ID는 `correctionExampleIds`와 `correctionSearch.appliedIds`에 기록한다.

## 2026-06-28 - 벤치마크 수정문도 CopyCorrectionRecord로 저장한다

- 결정: 고정 평가셋 20건에서 사람이 수정하거나 승인한 채널별 카피도 일반 이벤트와 같은 `CopyCorrectionRecord` 저장소에 기록한다.
- 원문 보존: 최초 생성 카피는 `generatedCopy`, 사람이 검수한 최종문은 `copy`로 분리한다.
- 브랜드 격리: 평가셋에는 실제 브랜드명이 없으므로 `brandName: benchmark_cosmetics`로 저장해 실제 브랜드 교정 예시와 섞이지 않게 한다.
- 중복 정책: 동일 correction ID를 다시 저장하면 새 레코드를 추가하지 않고 최신 승인 상태와 QA 결과로 갱신한다.
- 승인 정책: 사람 평균 4.0 미만 또는 QA issue가 남은 결과는 최종 승인할 수 없다.

## 2026-06-20 - 전략 추천 초안은 자동 selected로 저장하지 않는다

- 결정: 레거시 Meta 전략 46건에 자동 추천 점수와 추천 판정을 붙이지만, 이 값은 실제 `selected / shortlist / rejected` 검수 결과로 저장하지 않는다.
- 방식: 콘솔과 CSV는 추천값을 입력칸에 채워 사람이 빠르게 검수하도록 돕는다. 최종 승격은 사람이 `선택 / 참고 / 거절`을 명시적으로 저장했을 때만 반영한다.
- 이유: 목표는 “검수된 전략 사례”를 생성 예시로 쓰는 것이다. 자동 추천을 곧바로 selected로 저장하면 전략 검수 30건 기준은 빨리 채울 수 있지만, 품질 기준과 학습 데이터 신뢰도가 깨진다.
- 영향: `STRATEGY_REVIEW_BELOW_30` blocker는 추천 초안만으로 해제되지 않는다. 사람이 30건을 selected 또는 shortlist로 저장해야 품질 목표 다음 단계가 열린다.

## 2026-06-20 - 취향(좋은 마케팅) 학습은 OpenCLIP 임베딩+분류기로 한다

- 결정: 경쟁 마케팅 이미지에서 "좋은 마케팅/브랜딩"을 체화하는 엔진은 OpenCLIP 임베딩 + 분류기(linear probe)로 한다. 사람 라벨로 학습→신규 이미지 순위/필터.
- 이유: 데이터로 검증됨. 이미지 임베딩 학습은 단일 Meta 세션 ROC AUC 0.93, 통합 240장 0.82. 반면 텍스트 메타데이터/Qwen 프롬프트 판단은 50%대로 약했다.
- 도구: `taste_labels.py`, `train_taste_model.py`, `rank_images_by_taste.py`, `ingest_image_folder_session.py`, `pretag_session_with_taste.py`. 상세 `knowledge/TASTE_MODEL_2026-06-20.md`.
- 범위: "취향 모델"은 좋은 이미지 인식/순위/필터까지. 그 스타일로 생성하는 건 ComfyUI(별개).

## 2026-06-20 - Qwen 비전은 레퍼런스 취향 판단 레버로 쓰지 않는다(보류)

- 결정: 레퍼런스 selected/rejected 판단에 Qwen 비전을 (pure/hybrid 모두) 통합하지 않는다.
- 이유: `replay_reference_accuracy.py` A/B에서 어떤 임계값에서도 메타데이터+learned rules(2-class 62.7%)를 못 넘었다. 비전 hard-risk가 사람 거절 기준과 정렬되지 않아 과제외로 역전.
- 대안: learned rules 성장(사람 검수) 또는 Qwen 프롬프트 캘리브레이션(별도 R&D). 상세 `knowledge/REFERENCE_ACCURACY_2026-06-20.md`.

## 2026-06-20 - 경쟁 이미지 수집 우선순위: Meta > Chrome 확장 > Playwright 검색

- 결정: 취향 모델 학습 데이터는 Meta Ad Library(1순위), Chrome 확장 gallery-dl 원본(2순위) 순으로 모은다. Playwright Pinterest 검색은 취향학습용으론 쓰지 않는다.
- 이유: 검증 최고 성적이 Meta였고(로그인 불필요, 시스템 Edge), 확장은 원본 해상도가 최고 품질. Playwright 검색은 썸네일 저화질(low_resolution 게이트 존재) + DOM 취약.
- 연결: 어떤 소스든 `ingest_image_folder_session.py`로 콘솔 라벨 세션화 → 학습.

## 2026-06-14 - 검증된 Meta source mix는 화장품 03단계의 제품 비주얼 보완 공급원으로 사용

- 결정: 검증된 제품·성분 검색어에서 Qwen이 `clean_product_visual`로 판정한 결과를 화장품 `03_reference_research`에 자동 공급한다.
- 이유: 브랜드 중심 Meta 수집은 캠페인 구조 참고에는 유용하지만 clean product visual 단독 공급원으로는 부족하다.
- 안전 조건: 검토 5건 이상, clean product rate 20% 이상, SHA 중복 제거, 검색어당 2개, 광고당 1개, 기본 총 6개.
- 범위: 후보 참고자료 공급만 자동화하며 사람의 최종 이미지 선택을 대체하지 않는다.
- 운영 설정: `META_SOURCE_MIX_REFERENCE_MODE=off`로 독립 비활성화할 수 있다.

## 기록 형식

```text
날짜:
결정:
이유:
영향:
관련 파일:
상태:
```

## 결정 목록

### 2026-06-14: Meta 검증 브랜드 수집은 적응형 5×5 배치를 기본으로 한다

결정:

- 기본 수집은 레지스트리 앞순서가 아니라 검수 완료 누적 증거 기반 적응형 순서를 사용한다.
- 한 배치는 통과 앵커 1개와 커버리지 확대 후보를 조합하고, 직전 배치 브랜드는 뒤로 보낸다.
- 기본 검증 크기는 브랜드 5개 × 광고 5개이며, `media_type=all`을 유지한다.

이유:

- 3×3 배치는 개선 판단 표본이 부족했고, 같은 브랜드 반복은 커버리지를 늘리지 못했다.
- 정지 이미지 전용 실제 테스트는 광고 0건으로 회수율을 낮췄다.
- 적응형 누적 실검증에서 creative acceptance와 브랜드 커버리지가 기준 대비 각각 +17.6%p, +6.7%p 개선됐다.
- 누적 원본 광고 77개에서도 브랜드 커버리지가 16.7%라 클린 제품 비주얼의 단독 공급원으로는 부족하다.

영향:

- 다음 수집은 실패가 누적된 브랜드를 자동 감점하고, 아직 통과하지 못했지만 가능성이 있는 브랜드를 순환 탐색한다.
- 검증 브랜드 수집은 캠페인·프로모션 구조 참고용으로 두고, 클린 제품 비주얼은 검증된 상품·성분 쿼리를 병행한다.
- 상품·성분 쿼리 자동 수집/Qwen 검수 결과 전체 clean product visual 회수율 50%를 확인했다.

관련 파일:

- `services/ad_reference/collection_strategy.py`
- `services/ad_reference/registry_metrics.py`
- `scripts/collect_meta_brand_registry.py`
- `ui/console/app.js`

상태: 적용 완료

### 2026-06-14: 반복 운영 완료는 서로 다른 이벤트 3건과 동일 run 복구 증거로 판정한다

결정:

- 자동화 구간 반복 성공과 최종 archive 성공을 분리해서 측정한다.
- 실제 운영 완료에는 서로 다른 이벤트 3건의 최종 성공과 실패 이력이 있는 동일 run 1건의 복구 증거가 필요하다.

이유:

- 같은 이벤트의 반복 run이나 중간 단계 완료만으로는 전체 운영과 복구 능력을 증명할 수 없다.

영향:

- 현재 자동화 구간 5종과 동일 run 복구 1건은 충족했지만 최종 성공이 2종이므로 실제 운영 완료 상태는 아니다.

관련 파일:

- `scripts/audit_repeated_operations.py`
- `.tmp/repeated-operations/latest-repeated-operations.json`
- `ui/console/app.js`

상태: 적용 완료

### 2026-06-14: Meta 수집 목표를 요청 수가 아니라 운영 회수율과 다양성으로 판단한다

결정:

- Meta 검증 브랜드 배치는 광고주 일치율, 성격 검수 통과율, 브랜드 커버리지, 최상위 브랜드 비중, creative type 분포로 평가한다.
- 경고 기준은 광고주 일치율 30% 미만, 성격 검수 통과율 10% 미만, 브랜드 커버리지 30% 미만, 통과 이미지 10장 이상에서 최상위 브랜드 비중 40% 초과다.

이유:

- 브랜드 수나 광고 요청 수가 많아도 실제 쓸 수 있는 이미지가 적거나 한 브랜드에 편중되면 운영 성과로 볼 수 없다.

영향:

- 화장품 수집은 현재 낮은 성격 검수 통과율과 브랜드 커버리지를 개선해야 하며, 주얼리 수집은 현재 기준을 통과한다.

관련 파일:

- `services/ad_reference/registry_metrics.py`
- `scripts/report_meta_brand_metrics.py`
- `ui/console/app.js`

상태: 적용 완료

### 2026-06-11: Meta 검수 세트는 공식 광고와 협업 광고를 분리하고 편중을 제한한다

결정:

- 광고주명이 브랜드 별칭으로 시작하면 `direct`, 다른 계정의 협업 문구에 브랜드가 포함되면 `partner`로 저장한다.
- Meta 검수 세트는 브랜드당 최대 20장, 한 광고당 최대 5장, 협업 광고 최대 20장으로 제한한다.

이유:

- 단순 브랜드 포함 검색은 협업 광고를 공식 광고로 오판하고, 한 브랜드 또는 한 캐러셀이 검수 세트를 독점할 수 있다.

영향:

- Meta 검수 세트는 브랜드 다양성과 광고 단위 다양성을 유지하며, 협업 광고를 별도 위험 신호로 검수할 수 있다.

관련 파일:

- `services/ad_reference/brand_registry.py`
- `scripts/collect_meta_brand_registry.py`
- `scripts/create_meta_brand_review_session.py`

상태: 적용 완료

### 2026-05-18: Obsidian을 프로젝트 기억 저장소로 둔다

결정:

- Obsidian은 실행 도구가 아니라 기획, 기준, 지식, 결정사항을 저장하는 프로젝트 기억 저장소로 둔다.

이유:

- 이벤트 자동화는 코드보다 기준과 판단 흐름이 더 쉽게 흩어진다.
- 브랜드 톤, 프롬프트 규칙, 이미지 평가 기준, 실패 사례, 회의 기록을 한곳에서 찾을 수 있어야 한다.

영향:

- `knowledge/` 폴더를 만들고 Obsidian에서 읽을 기준 문서를 둔다.
- Codex/OpenCode/LM Studio는 이 문서를 참고해 작업한다.

관련 파일:

- `knowledge/00_INDEX.md`
- `knowledge/01_PROJECT_GOAL.md`
- `knowledge/02_WORKFLOW.md`

상태:

- 적용

### 2026-05-18: 기준 문서를 먼저 만들고 플러그인은 나중에 붙인다

결정:

- Obsidian 플러그인 세팅보다 기준 문서 구조를 먼저 만든다.

이유:

- Dataview, Tasks, Templater 같은 플러그인은 문서가 쌓인 뒤에 효과가 크다.
- 초기에는 구조가 복잡해지는 것보다 프로젝트 기준을 빠르게 고정하는 것이 중요하다.

영향:

- 우선 9개 핵심 문서만 만든다.
- 플러그인 추천은 이후 운영이 반복될 때 다시 정리한다.

상태:

- 적용

### 2026-05-18: 작업 후 기준 변화는 Obsidian 지식에 자동 반영한다

결정:

- Codex/OpenCode 작업 결과가 프로젝트 기준, 반복 운영 방식, 실패 해결법, 모델 테스트, 워크플로 구조에 영향을 주면 `knowledge/` 문서에 함께 반영한다.

이유:

- 실행 결과는 `runs/`에 남지만, 다음 작업에서 바로 참고해야 하는 판단 기준은 Obsidian에서 보여야 한다.
- 모든 로그를 문서화하면 지식베이스가 지저분해지므로 중요한 기준 변화만 기록한다.

영향:

- `00_DASHBOARD.md`를 추가해 빠른 링크와 기록 위치 판단 기준을 둔다.
- 단순 실행 로그, 임시 파일, 일회성 산출물은 `knowledge/`에 넣지 않는다.

관련 파일:

- `knowledge/00_DASHBOARD.md`
- `knowledge/00_INDEX.md`

상태:

- 적용

### 2026-05-18: `byextremeai/static-ads`는 완제품으로 쓰지 않는다

결정:

- `byextremeai/static-ads`는 완제품으로 복제하지 않고 패턴만 참고한다.

이유:

- 이 프로젝트의 도메인은 이벤트 콘텐츠 자동화이며, 고정 광고 템플릿 생성과 다르다.
- 단계 분리, 승인 게이트, JSON 중간 산출물, 개별 재생성, 버전 관리만 가져오는 편이 맞다.

영향:

- 프로젝트 도메인은 `event-content-pipeline`으로 재설계한다.
- 실행 헬퍼는 `scripts/workflow.py`가 담당하고, AI 생성 로직은 단계 실행 또는 하위 모듈로 분리한다.

관련 파일:

- `AGENTS.md`
- `PIPELINE.md`
- `scripts/workflow.py`

상태:

- 적용

---

### 2026-05-18: 05_figma_assembly 단계 제거

결정:

- `05_figma_assembly`를 파이프라인에서 제거한다.
- `04_admin_selection` 완료 후 `06_qa_packaging`으로 직행한다.

이유:

- ComfyUI와 자동화를 통합하는 방향으로 전환. Figma 조립은 수동 개입 병목.
- 이미지 생성(ComfyUI) → 선택(04) → QA(06)로 흐름이 단순해짐.

영향:

- `scripts/workflow.py` STAGES에서 05 제거, 04 → 06 직결
- `CLAUDE.md`, `AGENTS.md`, `knowledge/` 전반 반영
- `pipeline/05_figma_assembly/` 폴더는 디스크에 보존 (archive 참고용)

상태:

- 적용
## 2026-05-25 — 04_admin_selection 최소 구현

- 결정: 04_admin_selection은 ComfyUI 실생성 여부와 무관하게 `03_visual_candidates/image-prompts.json` 및 후보 매니페스트를 읽어 사람이 고른 후보를 `selected-assets.json`으로 확정한다.
- 결정: 04는 별도 승인 게이트가 아니라 사람 선택 자체를 완료 조건으로 보고, 완료 후 `06_qa_packaging`을 바로 unlock한다.
- 범위 제외: ComfyUI 실생성, Figma 조립, 제품 합성, 영상 생성은 이번 단계에 포함하지 않는다.
- 06 연결 준비: Figma 산출물이 없을 때도 `04_admin_selection/selected-assets.json`을 입력으로 최소 QA 리포트와 패키지 매니페스트를 만들 수 있게 한다.

## 2026-05-27 — MVP 단계명 재정리와 레퍼런스 리서치 stage 추가

- 결정: 프로젝트 포지션을 "GPT보다 똑똑한 기획툴"이 아니라 "브랜드 이벤트 이미지 제작용 로컬 제작 콘솔"로 고정한다.
- 결정: 기준 파이프라인을 `01_event_brief → 02_content_planning → 03_reference_research → 04_visual_candidates → 05_admin_selection → 06_qa_packaging → 07_asset_archive`로 정리한다.
- 이유: 실제 사용 흐름에서 레퍼런스 수집이 콘텐츠 기획과 이미지 후보 생성 사이의 독립 작업으로 중요하며, 기존 `03_visual_candidates` 안에 암묵적으로 붙어 있으면 콘솔 사용자가 작업 상태를 이해하기 어렵다.
- 구현: `03_reference_research` handler를 추가해 기본 실행은 레퍼런스 검색 계획/요약을 만들고, `REFERENCE_RESEARCH_MODE=auto_search`일 때 기존 자동 검색/선정 파이프라인을 실행하게 한다.
- 호환: 기존 런과 코드 경로를 깨지 않기 위해 물리 산출물 폴더 `03_visual_candidates`, `04_admin_selection`은 유지한다.
- 호환: `scripts/workflow.py`에서 기존 stage id `03_visual_candidates`, `04_admin_selection`은 새 기준 stage `04_visual_candidates`, `05_admin_selection`으로 alias 처리한다.

## 2026-05-27 — reference_research 산출물을 visual prompt에 직접 연결

- 결정: `03_reference_research/reference-research.json`을 단순 진행 요약이 아니라 04 후보 생성 프롬프트의 방향성 입력으로 사용한다.
- 이유: 레퍼런스 수집 단계가 실제 이미지 후보 품질에 영향을 주려면 선택 이미지 경로뿐 아니라 mood, composition, lighting, color, texture, avoid 방향이 구조화되어 04 단계에 전달되어야 한다.
- 구현: `reference-research.json`에 `moodKeywords`, `compositionKeywords`, `lightingKeywords`, `colorPalette`, `materialTexture`, `avoidKeywords`, `promptHints`, `negativePromptHints`, `selectedReferences`를 항상 생성한다.
- 구현: `04_visual_candidates`는 이 값을 읽어 positive prompt에는 `reference prompt hints`, negative prompt에는 `avoidKeywords`와 `negativePromptHints`를 반영한다.
- 추적: `visual-plan.json.reference_direction`과 `image-prompts.json.prompts[].reference_direction`에 원본 방향성을 남긴다.

## 2026-05-25 — 외부 브랜드 workflow를 단일 원본으로 사용

- 결정: `D:\CD\jewelry_ad_project\02_workflows`를 cosmetics/jewelry/bullion ComfyUI workflow의 단일 원본으로 사용한다.
- 결정: 프로젝트 내부 `services/comfyui/workflows`로 복사하지 않고 레지스트리에서 canonical path를 참조한다.
- 결정: 캔버스 workflow JSON은 사람이 관리하는 원본으로 유지하고, 자동 큐 실행에는 프롬프트/샘플러 값을 읽어 API prompt adapter에 주입한다.
- 이유: ComfyUI 워크플로 관리 위치를 하나로 유지하고, 자동화 프로젝트는 이벤트/제품 카테고리별 매핑과 실행 데이터 생성에 집중한다.

## 2026-05-27 — live 생성 결과 품질 추적 파일을 stage 산출물로 둔다

- 결정: `04_visual_candidates` 실행 시 `03_visual_candidates/generation-quality.json`을 항상 생성한다.
- 이유: live/placeholder 여부, ComfyUI 제출 결과, 파일 존재/해상도/용량, `reference_direction` 반영 여부를 후보 선택 전에 한곳에서 확인해야 한다.
- 구현: 후보별 `generation_mode`, `generation_status`, `generation_error`, `image`, `reference_direction_checks`, `comfyui_submission`을 기록한다.
- 영향: 콘솔은 이후 이 파일을 읽어 "생성 성공/실패", "레퍼런스 방향 반영", "텍스트/카테고리 품질 이슈"를 선택 화면에 노출할 수 있다.

## 2026-05-27 — `qwen_candidate_2511` 기본 실행값을 Lightning 권장값으로 맞춘다

- 결정: local preset `qwen_candidate_2511`의 stage 기본값은 `8 steps / cfg 1.0 / heun / beta`로 둔다.
- 이유: 프리셋 자체가 Lightning LoRA 기반인데 일반 후보 생성 기본값 `28 steps / cfg 6.5 / dpmpp_2m`를 쓰면 live 검증 시간이 과도하게 길고 큐 stuck처럼 보인다.
- 영향: 기본 live 후보 생성 속도가 안정화된다. 더 높은 품질 실험은 별도 preset 또는 명시적 workflow 설정으로 분리한다.

## 2026-05-28 — 금/은/투자 이벤트용 reference quality gate 강화

- 결정: `03_reference_research`에서 금/은/투자/상담 이벤트를 `bullion_investment` profile로 감지하고, 일반 이벤트보다 엄격한 레퍼런스 필터를 적용한다.
- 이유: live 생성 결과가 귀여운 3D 캠핑, 캐릭터, 와인/패키지 오인식으로 흐른 원인은 ComfyUI보다 앞단 레퍼런스 방향성이 약했기 때문이다.
- 구현: 검색어를 `premium gold investment campaign visual`, `luxury financial consultation poster`, `gold bar premium product photography`, `bullion investment advertising` 등으로 교체한다.
- 구현: reference 평가에 `brandFit`, `eventFit`, `visualQuality`, `compositionUsefulness`, `promptUsefulness`, `seriousnessFit`, `productRelevance`, `riskLevel`을 남긴다.
- 구현: selected 기준은 `brandFit >= 7`, `eventFit >= 7`, `productRelevance >= 7`, `seriousnessFit >= 6`, `riskLevel <= 4`로 둔다.
- 구현: kids/toy/kawaii/camping/theme park/picnic/wine/random package/fake text 계열은 자동 reject 또는 shortlist로 내린다.
- 영향: 다음 gold/bullion 후보 생성은 "귀여운 이벤트 이미지"가 아니라 "프리미엄 금 투자 상담 비주얼"을 기준으로 시작한다.

## 2026-05-28 — `bullion_investment` positive prompt 하드 정화

- 결정: `04_visual_candidates`는 `reference-research.json.eventProfile.category == bullion_investment`일 때 positive prompt와 reference prompt hint에서 캐릭터/캠핑/장난감/와인/패키지 계열 토큰을 제거한다.
- 이유: "not cute", "no mascot"처럼 부정문으로 positive에 남긴 단어도 이미지 모델에는 해당 시각 개념을 활성화할 수 있다.
- 구현: `mascot`, `character`, `cute`, `camping`, `picnic`, `tent`, `toy`, `diorama`, `cartoon`, `kawaii`, `playful`, `wine`, `bottle`, `package box`는 positive에서 제거하고 negative에만 강하게 둔다.
- 영향: gold/bullion 후보 프롬프트는 프리미엄 금융/금 제품/상담 비주얼만 positive 방향으로 전달한다.
## 2026-05-28 - 이미지 생성 중단, 레퍼런스 기준 데이터 우선

- 결정: ComfyUI/LoRA 튜닝보다 먼저 브랜드/이벤트별 레퍼런스 판단 기준을 구조화한다.
- 이유: 최근 bullion_investment live 테스트 실패 원인은 모델 자체보다 캐릭터/장난감/귀여운 3D 방향의 fallback/레퍼런스 오염과 기준 데이터 부족에 가깝다.
- 적용: `assets/rules/brand-persona.json`, `event-rules.json`, `reference-rules.json`, `visual-avoid-rules.json`, `tone-rules.md`를 생성하고 `bullion_investment` 기준을 고정했다.
- 운영 원칙: 이미지 생성은 reference 기준, fallback 오염 제거, selected/rejected 사유 기록이 안정된 뒤 재개한다.

## 2026-05-30 - bad만으로는 부족하므로 good seed를 기준에 포함

- 결정: `bullion_investment` reference 판단에 good/bad seed dataset을 모두 사용한다.
- 이유: bad dataset은 피해야 할 방향을 알려주지만, good dataset이 있어야 선택해야 할 방향이 생긴다.
- 적용: `assets/reference_training/bullion_investment/good/`에 로컬 금/은/precious-metal 계열 seed 10장을 저장하고 `metadata.json`을 작성했다.
- 게이트: 03 품질 리포트가 pass이고 selected bad signal이 0일 때만 04 프롬프트/이미지 후보 단계로 넘어간다.

## 2026-05-30 - good seed는 product/mood/layout으로 분리

- 결정: `bullion_investment` good seed를 `product_reference`, `finance_mood_reference`, `poster_layout_reference`로 분리한다.
- 이유: product reference만 늘리면 selector가 금화/골드바 제품컷만 좋은 reference로 학습할 수 있다.
- 적용: good seed를 30장 구조로 확장하고, selected reference도 category coverage를 검사한다.
- 선택 원칙: selected는 product identity, finance trust mood, poster/headline layout이 모두 들어가야 한다.
## 2026-05-30 - 1차 GOAL을 Senior Designer Brain Wiki로 재정의

- 결정: 프로젝트의 1차 목표를 이미지 생성 자동화가 아니라 `Senior Designer Brain Wiki` 구축으로 둔다.
- 이유: 최근 ComfyUI 실패의 핵심 원인은 모델 파인튜닝 부족보다 브랜드/이벤트/레퍼런스 판단 기준 부족과 fallback 오염이었다. 먼저 AI가 좋은/나쁜 레퍼런스를 설명 가능한 기준으로 판단하게 만들어야 한다.
- 적용: `design_brain_wiki/` 폴더를 생성하고 디자인 원칙, 브랜드 전략, 레퍼런스 판단, 채널 사용성, 업종별 playbook, 공식 사례 연구, 기원님 taste dataset, feedback language를 MD/JSON으로 구조화했다.
- 판단 기준: 자료는 링크 모음으로 저장하지 않고 `자료 원문/링크 -> 핵심 요약 -> 디자인 판단 질문 -> 평가 항목 -> good/bad 적용 -> AI 피드백 문장 예시` 형식으로 변환한다.
- 후속: Reference Judge는 `assets/rules`, `assets/reference_training`, `design_brain_wiki`를 함께 읽어 selected/shortlist/rejected와 이유를 산출해야 한다.
## 2026-05-31 - Senior Designer Brain Wiki는 샘플 Judge 테스트를 통과해야 03에 연결

- 결정: `design_brain_wiki`를 바로 운영 파이프라인에 넣기 전에, 업종별 샘플 reference judge 테스트를 먼저 통과시킨다.
- 이유: 파일을 많이 만든 것만으로는 AI 판단력이 좋아졌는지 알 수 없다. selected/shortlist/rejected 판단과 피드백 문장 수준을 샘플 세트로 검증해야 한다.
- 적용: `design_brain_wiki/tests/reference_judge_sample_set.json`에 `bullion_investment`, `cosmetics_skincare`, `jewelry_luxury` 각각 good/bad/ambiguous 후보를 섞은 테스트 세트를 만들었다.
- 적용: `scripts/run_reference_judge_wiki_tests.py`는 위키 rubric을 읽고 후보별 decision, score, role, senior designer feedback, feedback depth를 평가한다.
- 통과 기준: decision accuracy와 feedback depth rate가 모두 1.0에 도달해야 한다.
- 현재 결과: 총 18개 후보, accuracy 1.0, feedback depth rate 1.0, status pass.
## 2026-05-31 - Wiki는 완성이 아니라 v0.2 확장 단계로 재정의

- 결정: 현재 `design_brain_wiki`는 완성본이 아니라 `v0.1 골격 + 1차 테스트 세트`로 본다.
- 이유: 샘플 18개 테스트 통과는 자체 제작한 작은 시험지를 통과한 수준이다. 실제 시니어 디자이너 에이전트가 되려면 더 많은 공식 사례, 업종별 경계 기준, 기원님 판단 데이터, 실제 레퍼런스 검증 로그가 필요하다.
- 적용: `design_brain_wiki/VERSION_STATUS.md`를 추가해 v0.1/v0.2/v0.3/v1.0 상태를 분리했다.
- 적용: v0.2 확장으로 studio case bank 50개, 핵심 업종 deep playbook 3개, 기원님 피드백 100개/레퍼런스 300장 축적 계획을 추가했다.
- 원칙: 앞으로 "완료"라고 부르지 않고, 버전별로 `골격`, `자료 확장`, `실전 검증`, `운영 Judge`를 구분한다.
## 2026-05-31 - bullion_investment 판단 훈련은 기원님 교정 루프를 기준으로 한다

- 결정: `bullion_investment` 위키 품질 검증은 파일 수가 아니라 30장 단위 판단 세션과 기원님 교정 로그로 진행한다.
- 적용: `design_brain_wiki/training_sessions/bullion_investment/session_001/` 생성.
- 산출물: AI 1차 판단, 기원님 리뷰 템플릿, 교정 로그, wiki update suggestion을 한 세트로 둔다.
- 원칙: AI의 selected/shortlist/rejected는 정답이 아니라 기원님이 교정할 초안이다.
- 다음 기준: 기원님 교정 후 과승인, 과거절, 추상 피드백, 업종 playbook 누락을 위키에 반영한다.
## 2026-05-31 - seed test와 실제 Pinterest reference session을 분리한다

- 결정: `session_001` 같은 seed 기반 세션과 `pinterest_session_001` 같은 실제 수집 레퍼런스 세션을 명시적으로 구분한다.
- 이유: seed 이미지는 기준 검증에는 유용하지만, 실제 Pinterest/search 레퍼런스 판단력 검증과 위키 교정에는 부족하다.
- 적용: training session JSON에 `sessionType`을 기록한다.
- 적용: 실제 레퍼런스 세션 생성은 run의 `references/reference-quality-filter.json`을 입력으로 사용하고, 필요하면 `--require-pinterest`로 Pinterest 출처를 강제한다.
- 운영 원칙: 위키 보강의 주 근거는 실제 수집 세션과 기원님 교정 로그로 삼고, seed 세션은 smoke test로만 본다.
## 2026-05-31 - 한국 이벤트 레퍼런스는 한국어 Pinterest 검색어를 우선한다

- 결정: `bullion_investment` 검색 쿼리는 한국어 카드뉴스/배너/금거래소/상담 이벤트 표현을 우선 사용한다.
- 이유: 영문 `premium gold investment` 계열 검색어는 해외 금융/투자 그래픽으로 쏠려 한국 카드뉴스와 블로그 배너 감성이 약하다.
- 적용: `assets/rules/reference-rules.json`의 searchQueries를 한국어 우선으로 교체하고, 영문은 보조 쿼리로 뒤쪽에 둔다.
- 운영 원칙: 한국 로컬 이벤트는 한국어 검색어로 먼저 수집하고, 해외 레퍼런스는 제품컷/무드 보조 자료로만 사용한다.

## 2026-05-31 - 판단 훈련은 두 장 빠른 비교 방식을 기본 UX로 둔다

- 결정: 판단 훈련 UI에 두 장 비교 후 즉시 저장/다음 이동하는 빠른 판정 흐름을 추가한다.
- 이유: 리스트에서 이미지 하나씩 클릭하는 방식은 30장 이상 리뷰할 때 느리고, 사용자가 좋은/나쁜 기준을 즉각적으로 교정하기 어렵다.
- 적용: `왼쪽 좋음`, `오른쪽 좋음`, `둘 다 후보`, `둘 다 제외`, `건너뛰기` 액션을 추가했다.
- 운영 원칙: 개별 상세 입력은 유지하되, 1차 교정은 빠른 비교로 처리한다.

## 2026-06-03 - cosmetics_skincare도 한국어 Pinterest 검색 프로필을 별도로 둔다

- 결정: 화장품/H&B/스킨케어 세일 이벤트는 `cosmetics_skincare` 프로필로 감지하고, 한국어 Pinterest/search 쿼리를 우선 사용한다.
- 이유: 일반 이벤트 검색이나 해외 뷰티 레퍼런스는 올영세일 같은 한국 H&B 세일의 카드뉴스/배너/혜택 강조 감성을 충분히 반영하지 못한다.
- 적용: `assets/rules/event-rules.json`, `reference-rules.json`, `brand-persona.json`, `visual-avoid-rules.json`에 화장품 기준을 추가했다.
- 운영 원칙: 한국 로컬 H&B 이벤트는 한국어 검색어로 1차 수집하고, 해외 레퍼런스는 제품 무드나 질감 보조 자료로만 사용한다.

## 2026-06-03 - 업종 감지는 짧고 모호한 키워드를 피한다

- 결정: `bullion_investment` 감지에서 단일 글자 `금`, `은` 및 일반 `상담` 같은 모호한 키워드를 제거한다.
- 이유: 화장품 기능성 문구의 `미백`, 일반 고객 상담 표현 등이 금 투자 이벤트로 오탐될 수 있다.
- 적용: `금 투자`, `금 시세`, `실물 금`, `투자 상담`처럼 업종 의도가 분명한 키워드 중심으로 감지한다.
- 운영 원칙: 새 업종 프로필을 추가할 때도 한 글자 키워드나 여러 업종에서 흔한 단어는 단독 감지 기준으로 쓰지 않는다.

## 2026-06-03 - 판단 훈련 세션 생성은 업종 공통 스크립트로 확장한다

- 결정: `bullion_investment` 전용 세션 생성 스크립트와 별도로, run-collected reference를 업종별 판단 훈련 세션으로 만드는 범용 스크립트를 둔다.
- 이유: 화장품, 주얼리 등도 같은 빠른 비교 교정 루프를 사용해야 하며, 세션 생성이 특정 업종명에 묶이면 반복 확장이 어렵다.
- 적용: `scripts/create_reference_training_session.py`를 추가하고 `cosmetics_skincare/pinterest_session_001`을 생성했다.
- 운영 원칙: 레퍼런스 검수는 계속 판단 훈련 데이터가 되므로, 실제 수집된 이미지를 가능한 한 모두 세션에 넣는다. 빠른 검증은 30장 샘플로 시작할 수 있지만, 운영 세션은 전체 수집분을 교정 대상으로 둔다.

## 2026-06-03 - 검색어는 source metadata이지 판단 evidence가 아니다

- 결정: reference judge는 `query`, `source_id`, `path`, `filename`, `text_relevance_reason`을 selected/shortlist/rejected 판단 evidence로 쓰지 않는다.
- 이유: 검색어와 파일명은 이미 수집 의도를 포함하므로, 판단에 넣으면 "검색어가 맞다"를 "이미지가 좋다"로 오해한다.
- 적용: 수집 단계의 text relevance는 Pinterest title/alt/description 등 source metadata만 보며, 훈련 세션 judge도 title/alt/Qwen/기원님 피드백 중심으로 evidence를 구성한다.
- 운영 원칙: query는 출처 추적과 검색 품질 분석에만 쓰고, 좋은 레퍼런스 판단은 이미지에서 온 설명/비전 결과/사람 피드백을 기준으로 한다.

## 2026-06-03 - 홈페이지 캡쳐와 상단 URL 노출 이미지는 화장품 selected 금지 신호로 둔다

- 결정: `cosmetics_skincare` 레퍼런스에서 홈페이지 캡쳐, 브라우저 화면, 상단 URL/주소창 노출 이미지는 selected로 쓰지 않는다.
- 이유: 이런 이미지는 디자인 레퍼런스라기보다 웹페이지 스크린샷에 가깝고, 원본 링크/브랜드/레이아웃을 그대로 가져올 위험이 크다.
- 적용: `assets/rules/visual-avoid-rules.json`에 website/browser screenshot, visible URL bar, address bar, homepage capture 계열 reject/avoid/negative hint를 추가했다.
- 운영 원칙: 이벤트 배너/카드뉴스로 참고 가능한 부분이 있어도 URL 바나 브라우저 헤더가 보이면 최소 shortlist 이하로 두고, 생성 프롬프트에는 홈페이지 캡쳐 느낌을 넘기지 않는다.

## 2026-06-03 - holdout 테스트는 이전 세션 이미지를 제외하고 일반화 성능을 본다

- 결정: 같은 업종 holdout을 반복할 때는 이전 판단 세션에 들어간 이미지 해시를 제외할 수 있게 한다.
- 이유: 같은 브리프와 비슷한 Pinterest 쿼리를 1/2/3차로 반복하면 새 판단 테스트처럼 보여도 실제로는 같은 이미지가 다시 섞인다.
- 적용: `scripts/create_reference_training_session.py`에 `--exclude-profile-history` 옵션을 추가했다.
- 운영 원칙: 같은 세션 안의 중복과 이전 세션 재등장을 분리해서 본다. 학습/리뷰 누적에는 재등장이 허용될 수 있지만, generalization holdout은 이전 세션 이미지를 제외한다.
## 2026-06-03 - Reference Judge 고도화는 검수 사유 태그와 learned rules를 1차 데이터 계약으로 사용

- 결정: 기원님 검수 결과를 단순 selected/shortlist/rejected로만 저장하지 않고 `reasonTags`를 함께 저장한다.
- 이유: 메타데이터와 검색어만으로는 취향/품질 판단을 일반화하기 어렵고, 반복 오판 패턴을 rule/playbook으로 환원하려면 구조화된 사유가 필요하다.
- 적용:
  - 콘솔 판단 훈련 UI에 사유 태그 버튼 추가.
  - 저장 시 `correction_summary.md`, `learned_rules.json` 자동 갱신.
  - 다음 holdout 비교는 `compare_reference_sessions.py`로 정확도/전이 패턴을 비교한다.

## 2026-06-03 - Qwen 비전 평가는 ComfyUI와 분리된 Reference Judge 보강 옵션으로 둔다

- 결정: `create_reference_training_session.py --qwen-vision` 옵션으로 Qwen/Ollama 비전 평가를 선택적으로 붙인다.
- 이유: ComfyUI 이미지 생성과 무관하게 레퍼런스 판단 정확도만 높일 수 있고, Qwen이 꺼져 있을 때도 기존 heuristic/session 생성은 계속 가능해야 한다.
- 적용:
  - cosmetics profile에서 `local_hb_sale_fit`, `benefit_hierarchy`, `product_trust`, `layout_usability`, `website_capture_risk`, `text_artifact_risk`를 판단 evidence로 사용한다.
  - hard reject 신호가 강하면 selected로 올리지 않는다.

## 2026-06-03 - cosmetics rejected gate는 hard reject 중심으로 완화한다

- 결정: `cosmetics_skincare` 판단 세션에서 rejected는 저해상도, 웹페이지/브라우저 캡처, 업종 오류, AI artifact, Qwen hard risk 같은 안정적 결함에만 강하게 적용한다.
- 이유: holdout 002에서 AI rejected 13건 중 11건이 기원님 기준 shortlist로 올라갔다. selected 오판을 줄이면서도 부분 참고 가치가 있는 이미지를 버리지 않으려면 rejected보다 shortlist를 우선해야 한다.
- 적용: `scripts/create_reference_training_session.py`에서 cosmetics의 weak copy space나 불충분한 metadata만으로 rejected를 만들지 않도록 수정했다.
- 운영 원칙: selected gate는 계속 엄격하게 유지하고, hard reject가 아닌 애매한 이미지는 사람 검수용 shortlist로 남긴다.
## 2026-06-03 - QA packaging evidence manifest

- 결정: 06_qa_packaging은 최종 패키지에 필요한 품질 근거 파일을 `qualityArtifacts`로 수집하고, 각 최종 파일 레코드에 `qualityEvidence`를 붙인다.
- 포함 파일: `planning-quality/planning-quality-audit.json`, `03_reference_research/reference-quality-report.json`, `03_visual_candidates/prompt-audit.json`, `03_visual_candidates/generation-quality.json`, `04_admin_selection/selected-assets.json`.
- 이유: 나중에 이미지 생성까지 연결됐을 때 선택된 후보가 어떤 레퍼런스, 프롬프트, 생성 품질, 사람 선택 근거를 통과했는지 QA manifest에서 한 번에 추적하기 위해서다.
- 누락/실패 처리: `selected-assets.json` 누락은 blocker로 보고, 나머지 품질 근거 누락이나 warning/fail 상태는 QA issue로 기록해 수정 단계로 라우팅한다.

## 2026-06-04 - Selected candidate evidence first

- 결정: QA evidence 판정은 전체 후보 통계보다 사람이 선택한 candidate 상태를 우선한다.
- 이유: 전체 후보 15개 중 12개가 실패했더라도 최종 선택 후보 1개가 정상 generated라면 최종 패키지 위험은 다르게 봐야 한다.
- 적용: `generation-quality.json`과 `prompt-audit.json`은 selected candidate item이 있으면 그 item의 상태로 pass/warning/fail을 우선 판정한다.
- 콘솔: `/api/runs/<run-id>`가 06 산출물인 `qa_report`, `final_package_manifest`, `qa_packaging`을 반환하고, 최종 패키지 화면에서 evidence 상태를 보여준다.
## 2026-06-07 - Meta Ad Library provider MVP 추가

- Pinterest reference provider를 제거하지 않고 `meta_ad_library` provider를 병행한다.
- 1차 범위는 `Ad Reference` 콘솔 탭, Playwright 카드 캡처, 광고 카피/CTA/링크/캡처 JSON 저장, 선택형 Qwen 태깅까지로 제한한다.
- OpenCLIP 랭킹, 사람 shortlist 저장, `reference-evidence.json` 변환, 01/02/03 자동 주입은 다음 단계로 분리한다.
- 경쟁사 광고 원본을 복제하지 않고 구조, 카피 패턴, 레이아웃 힌트만 참고한다.

## 2026-06-07 - Meta 광고는 카드 캡처가 아닌 원본 이미지 다운로드로 사용

- Meta 광고 카드 캡처는 수집 증거와 디버깅 용도로만 유지한다.
- 실제 레퍼런스 자산은 광고 카드 내부 CDN 이미지 URL에서 다운로드한다.
- 캐러셀 광고는 광고당 최대 10장까지 다운로드한다.
- 콘솔 수집 시 `현재 작업 레퍼런스로 연결`이 켜져 있으면 다운로드 이미지를 해당 run의 `references/selected/`와 `reference-manifest.json`에 `meta_ad_library` 출처로 등록한다.
- 등록된 이미지는 기존 `03_reference_research`와 이후 비주얼 프롬프트 단계가 Pinterest 레퍼런스와 동일하게 읽는다.

## 2026-06-07 - Meta 검색 쿼리는 Pinterest 검색 쿼리와 분리

- Pinterest는 `배너 디자인`, `카드뉴스 디자인` 같은 디자인 결과물 묘사형 검색을 사용한다.
- Meta Ad Library는 실제 광고주/광고 카피 검색이므로 `경쟁 브랜드`, `상품·성분`, `카테고리+혜택` 조합을 사용한다.
- 기본 Meta 검색 구성은 경쟁 브랜드 1~2개, 상품/성분 1개, 카테고리+혜택 1~2개로 한다.
- Meta 검색 결과는 실제 광고이지만 자동으로 좋은 레퍼런스는 아니므로 기존 Reference Judge 검수를 필수로 유지한다.

## 2026-06-07 - Meta 검색과 광고 성격 필터를 분리

- 검색어는 `누구/무엇의 광고를 찾는지`를 결정한다.
- 광고 성격 프로필은 `어떤 용도로 쓸 소재를 연결할지`를 결정한다.
- 기본 프로필은 `클린 제품 비주얼`이며 Qwen 판정 없이는 자동 selected로 연결하지 않는다.
- 단일 이미지 광고도 텍스트가 많은 가격 전단일 수 있으므로 `클린 제품 비주얼`과 분리한다.
- 경쟁 브랜드 공식/직접 광고주만 필요할 때 선택적으로 광고주명 일치 필터를 사용한다.

## 2026-06-08 - 레퍼런스 후보와 자동 제외 사례를 분리

- 실제 제작 레퍼런스 후보와 명확한 탈락 사례를 같은 목록에서 섞어 검수하지 않는다.
- Meta 광고 라이브러리 페이지 전체 캡처는 실제 광고 소재가 아니므로 `website_capture` 자동 제외 사례로 분류한다.
- 이미지 짧은 변 500px 미만은 제작 레퍼런스 품질 기준에 부족하므로 `low_resolution` 자동 제외 사례로 분류한다.
- 50장 배치는 저장 구조로만 유지하고, 사람 검수 UI는 전체 미완료 항목을 제한 없이 이어서 보여준다.
- 완료한 항목은 미완료 목록에서 즉시 제거하고 완료 탭에서만 확인한다.
# 2026-06-10 - 레퍼런스 학습은 수량보다 브리프 적합성을 우선

- `Reference Learning 1000`의 1,000장 수량 목표를 운영 기준에서 제외한다.
- 현재 활성 브리프와 업종, 시장, 출처, 이미지 무결성 기준을 통과한 이미지만 판단 훈련 화면에 노출한다.
- 프로젝트 생성 이미지, 로컬 inbox, 샘플, 다른 업종 훈련 시드는 기본 후보에서 제외한다.
- Meta Ad Library의 KR 검색 결과라도 해외 언어 중심 광고는 제외한다.
- 기존 사람 검수 기록은 보존한다.

## 2026-06-10 - Meta 수집은 업종별 검증 브랜드 레지스트리를 우선

- 화장품·스킨케어 20개와 주얼리·럭셔리 20개 브랜드를 초기 레지스트리로 둔다.
- 범용 키워드보다 브랜드 검색과 광고주명 엄격 일치를 우선한다.
- 브랜드 단위 수집 결과는 운영 run selected에 바로 넣지 않고 별도 보관한다.
- 업종별 1~3개 소량 수집으로 안정성을 확인한 뒤 브랜드를 계속 추가한다.
- 브랜드 광고 안에서도 제품·프로모션·디바이스·럭셔리 캠페인 역할이 다르므로 후속 브리프 역할 필터를 유지한다.

## 2026-06-13 - placeholder E2E와 live 제작 준비를 구분한다

- 생성 실패 후보는 selected로 저장하지 않는다.
- QA fail 또는 error/blocker issue가 있으면 06 승인을 차단하고 수정 단계로 라우팅한다.
- 선택된 ComfyUI workflow ID는 registry에 실제 존재해야 한다.
- placeholder 기반 01~07 통과는 제어 흐름 검증으로만 취급하며 live 생성 준비 완료의 근거로 쓰지 않는다.
- 07 완료라도 재사용 자산이 0개면 정상 제작 완료와 구분한다.
# 2026-06-14 - 자동화 운영 완성도 기준 분리

- 사람 직접 검수와 ComfyUI 제작 품질을 제외한 `자동화 운영 MVP` 기준을 별도로 관리한다.
- 자동화 운영 MVP는 입력 검증, 실패 복구, job 이력, 상태 계약, 판단 피드백 소비, QA package gate, archive/index 무결성으로 판정한다.
- 사람 검수 결과는 저장만 하는 것으로 완료로 보지 않고 다음 레퍼런스 공급자가 실제 소비해야 한다.
- 콘솔 background job은 재시작 후에도 이력과 로그를 조회할 수 있어야 한다.
- 상세 기준: `knowledge/OPERATIONS_READINESS_REVIEW_2026-06-14.md`.

# 2026-06-14 - learned rules 안전 승격 정책

- 개별 `learned_rules.json`은 생성 즉시 runtime에 적용하지 않는다.
- 같은 profile의 2개 이상 완료 세션에서 반복되고, 각 세션 reviewed 20 이상·완료율 80% 이상인 규칙만 승격한다.
- `reference_learning`, `meta_brand_review`처럼 범용 또는 별도 공급 경로 profile은 자동 승격에서 제외한다.
- hard reject 신호는 soften 규칙보다 우선한다.
- 현재 승격 규칙은 `cosmetics_skincare/soften_rejected_to_shortlist` 하나다.
# 2026-06-14 - 이벤트별 브랜드 비주얼을 카테고리 기본 프로필보다 우선

- 카테고리 프로필은 입력이 부족할 때의 fallback으로만 사용한다.
- 이벤트 references 또는 브랜드 visual mood/color가 제공되면 해당 방향을 prompt hints와 color palette의 우선 기준으로 사용한다.
- 이유: 모든 화장품 이벤트를 H&B 세일·오렌지 포인트 방향으로 수렴시키는 문제를 방지하고 브랜드별 차이를 보존하기 위함이다.
# 2026-06-14 - 경쟁사 광고는 원문이 아니라 설득 구조를 학습

- Meta 광고 카피 원문을 새 이벤트 결과에 직접 복사하지 않는다.
- 학습 단위는 훅 유형, 설득 순서, 혜택 방식, CTA, 문체 특징, 추상 copy blueprint다.
- 원문은 라이브러리에 보존하지 않고 브랜드, Library ID, 원문 해시, 출처 파일만 보존한다.
- 검색된 패턴은 반드시 현재 이벤트의 타깃, 제품, 혜택, 브랜드 톤으로 재작성한 뒤 사용한다.
- 이유: 기획 품질은 높이되 경쟁사 모방과 문구 복제를 방지하기 위함이다.
# 2026-06-14 실사용급 광고 기획·카피 엔진 승인 계약

- 01단계는 기존 `brief.json`과 함께 사실·미확정 주장·타깃 저항·채널 역할을 담은 `strategic-brief.json`을 생성한다.
- 02단계는 전략 축이 다른 콘셉트 3안을 생성하고, 사람이 하나를 선택한 뒤에만 채널별 `copy-package.json`을 생성한다.
- `02_content_planning` 단계 승인은 `concept-review.json`과 `copy-review.json`이 모두 승인되고 planning scorecard의 치명 오류가 0일 때만 허용한다.
- 기존 Meta 전략 패턴은 모두 `unreviewed`로 격리하며, 사람에게 `selected` 판정을 받은 전략 사례만 생성 검색에 사용한다.
- 교정 데이터는 원문·수정문·사유 태그·QA 결과를 함께 저장한다.
- 초기에는 자동 승인을 허용하지 않으며 로컬 모델 승격 전에도 동일한 승인 계약을 유지한다.
# 2026-06-14 광고 기획 외부 품질 기준선 결정

- 화장품 광고 기획의 초기 품질 기준선은 OpenAI Responses API 기반 외부 모델로 운영한다.
- 기본 모델은 `gpt-5.5`, 이벤트당 최대 8회 호출한다.
- 결정론적 baseline은 비교 및 장애 진단 용도이며 승인 가능한 fallback으로 사용하지 않는다.
- 외부 모델 장애, 치명 오류, 일반 품질 경고, 평균 4점 미만 중 하나라도 남으면 02단계 승인을 차단한다.
- 자동 승인은 허용하지 않고 콘셉트 선택과 최종 카피 사람 승인을 모두 유지한다.
# 2026-06-15 결정 - 광고 기획 벤치마크는 외부 결과와 사람 검수가 모두 있어야 합격

- 결정론적 기준선의 QA 결과만으로 치명 오류 0을 주장하지 않는다.
- 외부 모델 결과가 생성되지 않은 케이스는 `externalGenerated`에 포함하지 않는다.
- 블라인드 비교 응답에는 실제 출처를 노출하지 않고, 케이스 ID의 고정 해시로 A/B 출처를 역산한다.
- 외부 생성 완료 20건과 사람 평가 20건이 모두 충족되어야 종합 상태를 `pass`로 변경한다.
- API 실패나 키 미설정은 호출 수를 소비하지 않고 `provider_unavailable`로 기록하며 자동 승인하지 않는다.
- A/B 선호 버튼은 승인이나 무수정 승인을 암시하지 않는다. 승인 여부와 사람 수정 여부는 별도 필드로 명시해야 한다.
- 8개 루브릭이 모두 기록되지 않은 벤치마크 평가는 저장하지 않는다.
# 2026-06-15 결정 - 외부 미실행 상태의 치명 오류 0은 성공이 아니다

- 치명 오류 0건은 외부 평가 결과 20건 모두가 QA를 통과했을 때만 달성으로 판정한다.
- 콘셉트와 카피 critic 중 하나라도 `fail`이면 치명 오류다.
- critic의 `revise`가 최종 결과에 남으면 품질 경고로 승인 차단한다.
- 모델 재작성은 지정된 실패 항목만 반영하고 검수 통과 항목은 보존한다.
- 경쟁사 원문은 검수와 유사도 검사에만 사용하며 생성 예시로 직접 전달하지 않는다.
- 교정 데이터는 브랜드별로 격리하고, 불완전한 교정 기록은 저장하지 않는다.
- 전략 `selected`는 평균 4점 이상이며 핵심 추상 전략이 채워진 경우만 허용한다.
# 2026-06-16 결정 - 광고 기획 파일럿은 리뷰 패킷을 공식 진행 단위로 관리

- 화장품 광고 기획·카피 품질 목표는 20건 전체 확장 전에 파일럿 5건을 먼저 검증한다.
- 파일럿 진행 상태는 `.tmp/model-benchmarks/ad-planning-review-packet.{json,md}`로 확인한다.
- 리뷰 패킷은 외부 모델 결과, 콘셉트 선택, 사람 평가, 전략 selected/shortlist 준비도를 함께 보여준다.
- API 키가 없을 때 결정론적 baseline을 승인 가능한 대체 결과로 쓰지 않는다.
- ComfyUI/이미지 제작은 이 목표의 완료 조건에서 제외하고, 이미지 제작 직전의 광고 기획·카피 패키지만 다룬다.
## 2026-06-17 - 광고 기획 품질 기준선은 API 필수가 아니다

- OpenAI API는 기본 요건에서 제외한다.
- 광고 기획 품질 향상은 `local provider`, Codex/Claude 스킬, 사람 검수, 수정 데이터 저장 루프로 진행한다.
- OpenAI provider 코드는 선택 모드/호환 모드로 남기지만, API 키 부재는 더 이상 기본 파일럿 blocker가 아니다.
- 새 스킬 `ad-planning-copy-engine`을 광고 기획/카피 생성 전용 절차 지식으로 사용한다.

## 2026-06-17 - 광고 기획 콘솔은 사용자 검수 데스크를 기본 화면으로 한다

- 콘솔 메인 화면은 개발자 상태판이 아니라 기획자가 읽는 `광고 기획 검수 데스크`로 표시한다.
- `Provider`, `Blockers`, 내부 case status, `meta_strategy_*`, 원문 strategy token은 메인 화면에서 숨긴다.
- A/B 블라인드 비교 UI는 제거하고 `이벤트 확인 → 콘셉트 3안 선택 → 채널별 카피 검수 → 승인/수정 요청` 흐름으로 고정한다.
- 전략 학습, CSV, 운영 지표는 `고급 정보 / 데이터 검수` 접힘 영역에 둔다.
- 기존 벤치마크 A/B CSV 필드는 내부 호환용으로 남기되, 새 콘솔 검수 저장에는 `blindPreferred`를 요구하지 않는다.
# 2026-06-18 - 광고 기획 품질은 마케팅 인텔리전스 데이터 플로우로 확장

- 결정: 광고 카피 품질 개선을 단순 프롬프트/문장 개선으로 보지 않고, 시장·고객·트렌드 근거 데이터 플로우 구축 과제로 전환한다.
- 이유: 실제 마케터 수준의 훅은 제품 정보만으로 나오지 않고 타깃 반응, 리뷰 언어, 인기 제품, 검색 트렌드, 계절/날씨, SNS/Meta 흐름, 경쟁 오퍼를 함께 읽어야 한다.
- 실행: `knowledge/MARKETING_INTELLIGENCE_DATA_FLOW.md`를 기준 문서로 추가했다.
- 1차 목표: 화장품 파일럿 5건에서 이벤트당 근거 신호 50개 이상, 콘셉트별 근거 신호 3개 이상 연결.
- 장기 목표: 화장품 광고 기획용 `MarketingSignal` 1,000개 이상 누적.
- 운영 방식: 하루에 한 번씩 새로운 시장/고객/트렌드 신호를 추가하고, 그 신호가 어떤 카피 판단을 더 좋게 만드는지 검증한다.
# 결정 기록 (2026-06-18, Playwright 사용 범위)

- Playwright를 광고 기획 콘솔의 회귀 감사 도구로 채택한다.
- 1차 용도는 외부 트렌드 수집이 아니라 사용자가 보는 콘솔 화면의 품질 보증이다.
- 자동 감사 항목은 개발자 용어 노출, raw JSON 노출, A/B 비교 잔존, 깨진 한글, 1280px 가로 넘침이다.
- 실제 브라우저 실행은 콘솔 서버가 필요한 선택 검사로 두고, 기본 프로젝트 테스트에는 판정 로직만 포함한다.
## 2026-06-20 — 광고 기획 근거 패킷은 이벤트별로 격리한다

결정:

- `InsightBrief`는 단순히 업종이 같다는 이유만으로 모든 이벤트에 주입하지 않는다.
- `eventId`가 현재 이벤트와 일치하거나 명시적으로 `general` 기준 패킷으로 허용된 경우에만 사용한다.
- HSGN 품질 업그레이드에서는 `hsgn-summer-tone-care-2026` 전용 selected `MarketingSignal` 13개를 사용했다.

이유:

- 전역 ready 패킷이 다른 이벤트에 섞이면 샘플 벤치마크와 실제 카피에 엉뚱한 근거가 들어간다.
- 근거 신호는 카피 품질을 올리는 재료지만, 이벤트 맥락이 맞지 않으면 오히려 허위 주장이나 어색한 문장을 만든다.

영향:

- `services/ad_strategy/planning_engine.py`는 현재 이벤트 ID를 기준으로 ready `InsightBrief` 사용 여부를 판단한다.
- HSGN 02 기획 결과는 scorecard `pass`, critical error 0, averageScore 4.0을 달성했다.
## 2026-06-20 결정 - 파일럿 목표에서 깨진 텍스트는 치명 오류

- 사용자용 광고 기획 화면이나 파일럿 평가셋에 깨진 한글, raw JSON, HTML, 프로그래밍 구조가 노출되면 품질 점수와 무관하게 치명 오류로 본다.
- 파일럿 5건 목표는 `scripts/audit_cosmetics_pilot_goal.py` 결과가 `pass`일 때만 달성으로 인정한다.
- 후보/카피/사람평가가 채워졌더라도 표시 텍스트가 깨졌거나 근거 신호 연결이 비어 있으면 20건 확장으로 넘어가지 않는다.
## 2026-07-01 - 제품별 공식 근거 없이는 효능 proof를 만들지 않는다

- 유사한 제품 라이브러리 항목, 카테고리 논문, 경쟁사 제품 자료는 해당 이벤트 제품의 효능 근거로 사용하지 않는다.
- 공식 브랜드 페이지 또는 검증된 내부 문서에서 확인한 사실만 제품 proof 후보가 될 수 있다.
- 후보는 항상 `unreviewed`로 저장하며 자동 선택하지 않는다.
- 확인 사실에 없는 수치·기간·효능을 기획 해석에 추가하면 저장 단계에서 차단한다.
- 주장 제한을 필수 입력으로 받아 카피 생성 시 허용 범위를 명시한다.
## 2026-07-02 - 연결 테스트는 사람 승인으로 집계하지 않는다

- `connection_test`, `connection_check_default` 기록은 최종 사람 평가가 아니다.
- 해당 기록은 사람 평가 수, 평균 점수, 무수정 승인율, 완료 상태에서 제외한다.
- 새 마케팅 근거가 들어오면 과거 선택과 카피는 유효하지 않으므로 다시 콘셉트 선택을 받는다.
- 근거가 부족해진 경우 기존 카피를 남겨두지 않고 즉시 무효화한다.
- 시스템 추천안은 선택을 돕는 설명일 뿐 사람 선택을 대체하지 않는다.

## 2026-07-05 - 파일럿 대상은 근거 계획을 단일 기준으로 삼는다

- 화장품 대표 파일럿은 벤치마크 데이터의 배열 순서가 아니라
  `cosmetics-benchmark-evidence-plan.json`의 우선순위로 선택한다.
- 감사, 생성, 검수 패킷, 검수 CSV는 같은 공통 선택기를 사용한다.
- 이벤트 전용 근거가 `ready`가 아니면 콘셉트 3안이 존재해도 준비 완료로
  계산하지 않는다.
- 근거 상태와 이벤트 ID가 모두 일치해야만 사람이 콘셉트를 선택할 수 있다.
- 이유: 일반 초안을 준비 완료로 표시하면 근거 없는 카피를 다시 승인 흐름에
  올리는 거짓 양성이 생긴다.

## 2026-07-05 - 명시 이벤트 유형과 근거 역할 추적을 우선한다

- 이벤트 입력에 `seasonal`, `promotion`, `launch`, `education`,
  `branding`, `retention`이 명시되면 키워드 추정으로 덮어쓰지 않는다.
- 혜택 문구에 `증정`이 있다는 이유만으로 시즌 캠페인을 프로모션으로
  바꾸지 않는다.
- 콘셉트에는 전체 근거 ID만 붙이지 않고 전략을 만든 핵심 근거와 보조
  근거를 분리한다.
- 근거 ID 수를 부풀려 품질 기준을 통과시키지 않는다.
- 이벤트 유형 불일치와 근거 추적 손상은 사람 선택 전에 차단한다.

## 2026-07-05 - 자동 비평 5점 금지와 revise 선택 차단

- 결정론적 로컬 비평은 근거가 확인된 항목에 최대 4점만 부여한다.
- 5점은 실제 사람이 경쟁력과 완성도를 판단한 경우에만 기록한다.
- 형식 충족만으로 타깃 공감, 제품 연결, 차별성, 행동 유도력을 4점 처리하지
  않는다.
- 하나라도 4점 미만이거나 품질 경고가 남으면 `revise`다.
- `revise`와 `fail` 결과는 사람이 콘셉트를 선택할 수 없다.
- 연결 확인용 선택·평가는 목표 지표뿐 아니라 메인 검수 큐의 완료 상태에서도
  제외한다.

## 2026-07-05 - 로컬 카피도 근거 기반 공용 비평을 의무화한다

- API 키가 없는 로컬 생성 결과도 고정 `pass` 또는 고정 4점을 주지 않는다.
- 실제 생성, 벤치마크, 콘솔 검수는 같은 결정론적 비평 기준을 사용한다.
- 카피 평균이 4점 미만이거나 일반 품질 경고가 남으면 사람 승인 전
  `revise` 상태를 유지한다.
- 글자 수는 JSON/Python 표현 길이가 아니라 사람이 읽는 문자열 길이로
  계산한다.
- 반복, 조사 오류, 근거 누락은 단순 표시 문제가 아니라 생성 품질 문제로
  간주해 해당 루브릭 점수를 낮춘다.

## 2026-07-12 - 02단계 승인은 통합 산출물 계약을 통과해야 한다

- 파일별 `approved/pass` 값만으로 02단계를 승인하지 않는다.
- 분리 산출물을 통합한 뒤 콘셉트·사람 선택·카피·QA·교정 기록의 상호
  일관성을 검사한다.
- 사람 선택 콘셉트와 카피 기준 콘셉트가 다르거나, 요청하지 않은 채널이
  포함되거나, 품질 경고가 남으면 승인 불가다.
- 검증 도구는 외부 API 없이 로컬에서 결정론적으로 실행한다.

## 2026-07-12 - 영어 운영 상태는 기획 카드 밖에서도 금지한다

- 메인 사용자 화면의 상단 파이프라인, 최근 작업, 다음 행동도 한국어 표시
  계약에 포함한다.
- 내부 단계 ID와 파일명은 유지하되 화면 렌더링 단계에서 사람용 문장으로
  변환한다.
- `Brief`, `Continue Plan`처럼 짧은 영어 상태라도 사용자 화면에 보이면 UI
  감사 실패로 처리한다.

## 2026-07-12 - 메인 검수 데스크는 한 번에 한 행동만 강조한다

- 사람 검수 화면에서 감사 지표와 전체 진행률은 핵심 행동보다 우선하지
  않는다.
- 검수 큐의 가장 높은 우선순위 한 건만 `지금 할 일 1개`로 표시한다.
- 전체 수치와 기술적 감사 결과는 삭제하지 않고 기본 접힘 상세 영역에 둔다.
- 숨겨진 다른 뷰의 동일 패널은 사용자에게 보이는 행동 개수로 세지 않는다.

## 2026-07-18 - 콘솔 홈은 성숙한 미션 보드로 운영한다

- 제품 제작 단계는 `브리프 → 콘셉트 → 카피 → 이미지 방향 → 이미지 선택 →
  QA·보관`의 6개 사용자 챕터로 표시한다. 내부 7단계 파이프라인 계약은 바꾸지
  않는다.
- 홈의 첫 화면에는 가장 우선순위가 높은 사람 결정 한 건만 크게 표시한다.
- 게이미피케이션은 완료·현재·잠금 상태와 다음 단계 해제 안내까지만 사용한다.
  XP, 랭크, 코인, 연속 기록, 보상 색은 사용하지 않는다.
- 콘셉트 비교와 선택 근거는 한 화면 좌우 구조로 제공하고, 선택 완료 후 같은
  자리에서 카피 검수로 이어진다.
- 배치 도구, 전체 지표, 상세 감사는 삭제하지 않고 기본 접힘 영역에 둔다.

## 2026-07-18 - Nexon 디자인 시스템을 LoopStudio에 맞게 제한 적용한다

- 기준 원본은 `.tmp/oh-my-design/design-md/nexon/DESIGN.md`이며 프로젝트 적용
  계약은 루트 `DESIGN.md`에 기록한다.
- 브랜드 녹색 `#00de5a`는 한 화면의 주요 CTA와 현재 단계 표시에만 쓴다.
- 완료 상태는 검정·회색으로 표시하며 추천안은 금색이 아닌 중립 텍스트로
  표시한다.
- CTA는 0px, 카드·컨트롤은 4px, 대형 컨테이너는 8px 라운드를 사용한다.
- 기존 기능의 파스텔 카드·pill 상태는 고급 접힘 영역에서만 남고, 홈의 핵심
  작업 화면에는 적용하지 않는다.
