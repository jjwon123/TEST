# 2단계 콘텐츠 기획 분기

1단계에서 생성한 이벤트 브리프를 바탕으로 채널별 콘텐츠 플랜과 산출물 목록을 만든다.

## 폴더 구조

```text
02_content_planning/
  input/
    channel-rules.json
  output/
    content-plan.json
    content-plan.md
  src/
    generate-content-plan.js
  docs/
    content-plan-schema.json
```

## 실행 방법

```bash
cd "/Users/design/Downloads/자동화 프로젝트/02_content_planning"
node src/generate-content-plan.js
```

기본 실행은 1단계 결과물인 `../01_event_brief/output/brief.json`을 읽고 `output/content-plan.json`, `output/content-plan.md`를 만든다.

다른 브리프 파일을 쓰려면 아래처럼 실행한다.

```bash
node src/generate-content-plan.js ../01_event_brief/output/brief.json
```

## 입력값

- 1단계 공통 브리프 JSON
- 채널별 제작 규칙

## 출력값

- 채널별 콘텐츠 플랜
- 산출물 목록
- 콘텐츠 타입별 목적
- 이미지 필요 유형
- 다음 단계 이미지 후보 생성용 프롬프트 방향

## 다음 단계 연결

3단계 이미지 후보 생성은 `output/content-plan.json`의 `deliverables`와 `imageNeeds`를 입력으로 사용하면 된다.
