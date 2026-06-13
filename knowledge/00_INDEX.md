# 이벤트 콘텐츠 자동화 지식베이스

이 폴더는 Obsidian에서 여는 프로젝트 기준 문서 모음이다. 코드, 실행 결과, 이미지 산출물보다 한 단계 위에서 프로젝트의 목표, 판단 기준, 프롬프트 규칙, 실패 기록, 결정사항을 저장한다.

## 핵심 역할

- Obsidian: 기획, 기준, 지식, 결정사항 저장소
- Codex/OpenCode: 기준 문서를 참고해 코드와 산출물 수정
- LM Studio: 기준 문서를 RAG처럼 읽어 로컬 AI 생성/검토에 활용
- ComfyUI: 이미지 제작 워크플로 실행
- 웹 UI: 사람이 이벤트 입력, 실행, 검토, 승인하는 화면

## 바로 읽을 문서

- [[00_DASHBOARD]]: 현재 상태, 빠른 링크, 자동 업데이트 원칙
- [[01_PROJECT_GOAL]]: 프로젝트가 해결하려는 문제와 범위
- [[02_WORKFLOW]]: 이벤트 입력부터 QA/아카이브까지의 단계 흐름 (figma 제거됨)
- [[03_BRAND_GUIDE]]: 브랜드 톤, 디자인 방향, 금지 요소
- [[04_PROMPT_RULE]]: 텍스트/이미지 프롬프트 작성 기준
- [[05_MODEL_TEST]]: LM Studio, ComfyUI, 이미지 모델 테스트 기록
- [[06_TROUBLESHOOTING]]: 에러, 실패 사례, 해결법
- [[07_DECISIONS]]: 의사결정 기록 (최신: figma 제거, MD 구조 정리)
- [[08_COMFYUI_NOTES]]: ComfyUI 워크플로와 노드 운영 메모
- [[09_HANDOFF]]: 현재 구현 상태, 콘솔 사용법, 다음 우선순위

## 프로젝트 폴더 연결

- `CLAUDE.md` / `AGENTS.md`: Claude·Codex 공통 진입점 (동일 내용)
- `events/`: 이벤트별 입력 데이터
- `pipeline/01~07/`: 단계별 핸들러 + 스펙 (05 제거됨)
- `runs/`: 실행별 결과, 승인 상태, 버전 기록
- `assets/`: 승인된 재사용 자산과 레퍼런스
- `scripts/`: workflow.py, console_server.py
- `services/`: ComfyUI 등 외부 도구 연결 계층
- `docs/`: 기술 스펙 (schemas, states, qa, reference)
- `docs/archive/`: 레거시 문서 (참고용)

## 파일 관리 기준

- 파일 하나당 150줄 이하 유지
- 누적형 파일(07_DECISIONS 등)은 오래된 항목을 요약하거나 정리
- 단순 실행 로그·임시 파일은 여기에 넣지 않음

## 운영 원칙

1. 기준은 Obsidian에 먼저 남긴다.
2. 실행 규칙은 필요한 경우 `AGENTS.md`나 skill 문서로 옮긴다.
3. 이벤트별 입력과 결과는 `events/`, `runs/`에 둔다.
4. 결정의 이유는 [[07_DECISIONS]]에 날짜와 함께 기록한다.
5. 실패한 프롬프트와 해결법은 [[06_TROUBLESHOOTING]]에 쌓는다.
6. 작업 결과가 프로젝트 기준에 영향을 주면 [[00_DASHBOARD]]의 자동 업데이트 원칙에 따라 `knowledge/`를 갱신한다.
