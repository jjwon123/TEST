# ComfyUI 운영 메모

이 문서는 ComfyUI를 이벤트 콘텐츠 자동화의 이미지 제작 공장으로 연결하기 위한 기준과 실험 기록을 담는다.

## 역할

ComfyUI는 다음 작업을 담당한다.

- 제품 이미지 기반 광고 배경 생성
- 채널별 이미지 후보 제작
- 특정 이미지의 구도/배경/무드 변형
- 제품 유지가 필요한 이미지 편집
- 승인된 워크플로의 반복 실행

## 프로젝트 안의 위치

관련 코드와 워크플로는 다음 위치를 우선 확인한다.

```text
services/comfyui/
services/comfyui/workflows/
```

이미지 후보는 단계 폴더 또는 run 폴더에 저장한다.

```text
03_image_candidates/candidates/raw/
runs/[run-dir]/03_visual_candidates/
```

## 기본 운영 원칙

- ComfyUI는 이미지 제작 엔진이고, 기획 판단은 브리프와 콘텐츠 플랜을 따른다.
- 제품 유지가 필요한 경우 제품 원본을 기준 자산으로 별도 관리한다.
- 생성 결과는 후보로 보고, 4단계에서 사람이 선택한다.
- 워크플로 이름과 입력/출력 파일을 기록해 재현 가능하게 만든다.

## 제품 유지 이미지에서 확인할 것

- 제품 형태가 바뀌지 않았는가
- 라벨, 캡, 용기 색상, 재질이 유지되는가
- 배경과 제품의 조명 방향이 어색하지 않은가
- 한국어 카피를 얹을 공간이 있는가
- 채널 규격에 맞게 잘릴 위험이 없는가

## 워크플로 기록 템플릿

```text
날짜:
워크플로 파일:
목적:
입력 이미지:
주요 노드:
프롬프트:
네거티브 프롬프트:
결과:
문제:
재사용 가능성:
관련 run:
```

## 다음에 정리할 항목

- 제품 고정 광고 배경 생성 워크플로
- 채널별 해상도 프리셋
- 후보 이미지 파일명 규칙
- 실패 이미지 보관/폐기 기준
- Figma 조립으로 넘길 이미지 export 기준
## 2026-05-25 — 브랜드별 외부 워크플로 연결

- canonical workflow root: `D:\CD\jewelry_ad_project\02_workflows`
- 이 폴더는 ComfyUI 캔버스 workflow JSON의 원본이며 프로젝트 내부로 복사하지 않는다.
- 프로젝트 레지스트리에서 다음 workflow id를 직접 참조한다.
  - `cosmetics/cosmetic_product_hero`
  - `cosmetics/cosmetic_lifestyle_scene`
  - `cosmetics/cosmetic_texture_visual`
  - `cosmetics/cosmetic_promo_banner`
  - `jewelry/jewelry_product_hero`
  - `jewelry/jewelry_on_model`
  - `jewelry/jewelry_luxury_scene`
  - `bullion/bullion_product_hero`
  - `bullion/bullion_trust_visual`
  - `bullion/bullion_promo_banner`
- 자동 큐 실행용 API prompt는 캔버스 workflow의 핵심 프롬프트/샘플러 값을 읽어 Qwen 2511 adapter에 주입한다.
- 카테고리 매핑:
  - cosmetic/cosmetics/skincare → cosmetics workflows
  - jewelry/diamond → jewelry workflows
  - bullion/gold/silver → bullion workflows
- 최신 스모크 테스트에서 hsgn cosmetic 이벤트의 03 후보가 `cosmetics/cosmetic_product_hero`, `cosmetics/cosmetic_lifestyle_scene`으로 매핑됨을 확인.

## 2026-05-27 — live 생성 검증: 봄맞이 금 투자 상담 이벤트

- 테스트 런: `runs/2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`
- 테스트 그룹: `instagram_cardnews_01__key_visual`
- 실행 명령:
  ```powershell
  $env:COMFYUI_GENERATION_MODE='live'
  python scripts\workflow.py --run runs\2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트 --stage 04_visual_candidates --mode regenerate --group instagram_cardnews_01__key_visual
  ```
- 결과: 후보 3장 live 생성 성공, run preview로 회수 완료.
- 생성 파일:
  - `03_visual_candidates/previews/instagram_cardnews_01__key_visual_c01.png` — 1024x1024, 1,227,829 bytes
  - `03_visual_candidates/previews/instagram_cardnews_01__key_visual_c02.png` — 1024x1024, 1,231,017 bytes
  - `03_visual_candidates/previews/instagram_cardnews_01__key_visual_c03.png` — 1024x1024, 965,288 bytes
- `generation-quality.json`에서 `generated_count=3`, 선택 그룹의 `generation_status=generated`, `generation_mode=live`, `comfyui_prompt_id` 기록 확인.
- `reference_direction` 반영 확인:
  - positive prompt에 `reference prompt hints: mood: fresh, financial-trust ...` 포함
  - negative prompt에 `generic stock-photo feeling`, `cluttered layout`, `unreadable or baked-in text`, `wrong product category cues` 포함
- 육안 품질 메모:
  - c02: 레이아웃과 신선한 분위기는 가장 안정적. 텍스트 안전 영역도 비교적 좋음.
  - c01: 금색/봄 무드는 강하지만 깨진 텍스트가 이미지 안에 많이 생성됨.
  - c03: 깨진 제품/브랜드 텍스트와 와인형 오브젝트로 카테고리 이탈이 큼.
- 다음 개선: baked-in text 억제, 제품 카테고리 고정, 사람 선택 전에 품질 플래그를 콘솔에 노출.

## 2026-05-28 — live 소량 재테스트: prompt clean 이후

- 테스트 런: `runs/2026-05-27_13-51-31_봄맞이-금-투자-상담-이벤트`
- 테스트 그룹: `instagram_cardnews_01__key_visual`
- 사전 조건: prompt audit 15/15 pass, positive forbidden hit 0.
- 생성 결과:
  - `instagram_cardnews_01__key_visual_c01.png` — generated, 1024x1024, 892,982 bytes
  - `instagram_cardnews_01__key_visual_c02.png` — generated, 1024x1024, 804,201 bytes
  - `instagram_cardnews_01__key_visual_c03.png` — generated, 1024x1024, 1,107,069 bytes
- 품질 판정: fail.
- 남은 문제:
  - mascot/character가 3장 모두 남음.
  - c02/c03에는 fake/broken text가 남음.
  - c02/c03에는 random package/toy-like visual이 남음.
- 원인 추정: `qwen_candidate_2511`은 image-edit workflow라 입력 이미지 영향을 크게 받는다. 현재 이 이벤트의 `product_image`와 `base_image`가 `qwen_image_edit_1024.png`로 들어가며, 해당 입력의 캐릭터/장난감 맥락이 결과에 유지된다.
- 다음 조치: bullion/gold profile에서는 이 fallback을 쓰지 않고 neutral bullion/gold-bar input 또는 bullion 전용 workflow로 분기.
## 2026-05-28 - bullion_investment fallback 오염 차단

- `bullion_investment` 프로필에서는 `qwen_image_edit_1024.png` fallback을 금지한다.
- product/library 이미지가 없고 기본 fallback이 필요한 경우 `0_자동화 샘플 이미지/금_은 누끼/eagle.png` 등 neutral bullion/gold 계열 입력 이미지를 우선 사용한다.
- 다음 live 생성은 reference 기준 재검증 후 진행한다. 지금은 추가 ComfyUI 생성보다 룰 기반 reference selection 안정화가 우선이다.
## 2026-05-30 - Senior Designer Brain Wiki 구축 전까지 ComfyUI는 downstream 실행 단계로 유지

- 결정: `Senior Designer Brain Wiki`와 Reference Judge 기준이 더 쌓이기 전까지 ComfyUI 튜닝/대량 생성은 우선순위에서 제외한다.
- 이유: 최근 실패는 ComfyUI 자체보다 reference/fallback/판단 기준 오염에서 비롯되었다. 판단 기준 없이 생성만 반복하면 캐릭터, toy 3D, fake text 문제가 재발할 가능성이 높다.
- 적용: ComfyUI는 이미지 제작 엔진으로만 취급하고, 방향 판단은 `design_brain_wiki`, `assets/rules`, `assets/reference_training` 쪽에서 먼저 수행한다.
- 재개 조건: `03_reference_research`의 selected bad signal 0, fallback clean true, selected coverage 통과, senior designer feedback reason이 명확할 때만 04 이후 소량 테스트를 진행한다.

## 2026-06-20 — 방향 전환: 제품 비주얼 중심 + product_hero 정본화

- **결정**: 사람+주얼리(SDXL 인물→Qwen 삽입→USDU) 파이프라인은 튜닝 대비 품질이 안 나와 **중단**. 앞으로는 **제품 누끼 단독 Qwen Image-Edit 기반 제품 비주얼/브랜드 캠페인 이미지** 중심으로 간다.
- **검증된 정본 그래프 = `jewelry/jewelry_product_hero_v2.json`** (구조적으로 "좋음" 폴더 키퍼 컷과 동일함을 PNG prompt 메타로 확인).
  - 출처 키퍼: `output/Automation/jewelry/좋음/{lux_velvet, lux_waterripple_Q4, ring_FINAL_UPSCALED, ring_Q4_ctrl}`
  - 노드: UnetLoaderGGUF(qwen-image-edit-2511 Q6_K) + CLIPLoader(qwen_2.5_vl_7b) + VAELoader + LoadImage(누끼) + ImageScaleToTotalPixels(1.6MP) + TextEncodeQwenImageEditPlus×2 + FluxKontextMultiReferenceLatentMethod×2(index_timestep_zero) + ModelSamplingAuraFlow(shift 3.1) + CFGNorm(1) + KSampler(euler/simple, denoise 1.0) + (옵션) Remacri 4x → 5MP.
- **정본화 수정**: control-mode 기본 샘플러값을 드래프트값에서 **검증된 키퍼값으로 정렬** → CFG 3→**3.5**, Steps 20→**24** (node id13/id16/id20, MarkdownNote 동기화). Lightning 토글은 OFF 유지(CFG1에서 네거티브 죽는 함정 그대로 유효).
- **프롬프트 구조(주입 시드)**: ①고정 제품-충실도 절(silhouette/stone count/cut/prong/metal 유지) + ②씬 절(브리프의 mood/배경/조명을 여기 주입) + ③그라운딩 절(never pasted, contact shadow, matched light). 네거티브는 person/hand/mascot/3d toy/fake text 고정.
- **다음**: 누끼 입력(C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\0_자동화 샘플 이미지\다이아 누끼\) → 정본 템플릿 → 라이브 1~2컷으로 자동화 연결(03_visual_candidates) 재검증.
- **연결 아키텍처 원칙(재확인)**: 스킬/자동화는 브리프를 읽되 **ComfyUI 그래프를 새로 생성하지 않는다.** 역할 = (템플릿 선택 + 누끼/프롬프트힌트/채널해상도 프리셋 주입). 그래프는 사람이 검증한 정본 라이브러리(`02_workflows`)에만 추가.
