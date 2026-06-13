# 1단계 이벤트 브리프 생성

관리자가 이벤트 기본 정보를 입력하면 이후 2~6단계에서 공통으로 사용할 브리프 파일을 생성한다.

## 폴더 구조

```text
01_event_brief/
  input/
    event-input.example.json
    brand-guide.example.json
  output/
    brief.json
    brief.md
  src/
    generate-brief.js
  docs/
    brief-schema.json
```

## 실행 방법

```bash
cd "/Users/design/Downloads/자동화 프로젝트/01_event_brief"
node src/generate-brief.js
```

기본 실행은 `input/event-input.example.json`과 `input/brand-guide.example.json`을 읽고 `output/brief.json`, `output/brief.md`를 만든다.

다른 입력 파일을 쓰려면 아래처럼 실행한다.

```bash
node src/generate-brief.js ./input/my-event.json ./input/my-brand-guide.json
```

## 입력값

- 브랜드명
- 이벤트명
- 목적
- 타깃
- 채널
- 일정
- 오퍼/혜택
- 참고 레퍼런스
- 금지어 또는 필수 포함 문구

## 출력값

- 핵심 메시지
- 이벤트 요약
- 톤앤매너 방향
- 콘텐츠 제작 기준
- 공통 브리프 JSON
- 공통 브리프 Markdown

## 다음 단계 연결

2단계 콘텐츠 기획 분기는 `output/brief.json`을 입력값으로 사용하면 된다.
