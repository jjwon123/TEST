# Pinterest Board Collector Extension

PinBoard처럼 Chrome 안에서 Pinterest 보드를 열고, 확장 프로그램 버튼으로 보드 이미지를 안전하게 수집하는 MVP다.

이 방식은 Playwright 로그인 자동화보다 덜 수상하다. 사용자가 평소 쓰는 Chrome에서 직접 로그인하고, 확장은 현재 보드 화면의 실제 `/pin/` 링크만 수집한다.

## Install

1. Chrome 주소창에 입력한다.

```txt
chrome://extensions
```

2. 오른쪽 위 `Developer mode`를 켠다.
3. `Load unpacked`를 누른다.
4. 아래 폴더를 선택한다.

```txt
C:\Users\jinkiwon\iCloudDrive\자동화 프로젝트\tools\pinterest-board-collector-extension
```

업데이트 후에는 `chrome://extensions`에서 이 확장의 새로고침 버튼을 누른다.

## Use

1. 일반 Chrome에서 Pinterest에 로그인한다.
2. 다운로드할 보드 페이지를 연다.
3. 보드를 손으로 조금 천천히 스크롤한다.
4. 확장 프로그램 아이콘을 누른다.
5. 원본이 필요하면 `Originals via gallery-dl`을 누른다.
6. 확장 단독 모드가 필요하면 `Start Safe Download`를 누른다.

확장이 자동으로 한다:

- 보드 핀 수집
- 천천히 랜덤 딜레이 다운로드
- 중복 건너뛰기
- 실패/성공 상태 표시
- `metadata.json` 저장

## Original Downloads

원본 사이즈는 `Originals via gallery-dl` 버튼을 쓴다. 이 버튼은 로컬 Native Messaging helper를 통해 gallery-dl을 실행한다.

처음 한 번:

1. `pinterest-board-collector/install_native_host.bat` 실행
2. `chrome://extensions`의 확장 ID 입력
3. 확장 reload

저장 위치:

```txt
assets/references/inbox/[board-name]-originals/
```

다운로드 위치:

```txt
Downloads/pinterest-board/[board-name]/
```

## Safety Presets

- `Safe`: 20장, 스크롤 3회, 4~8초 랜덤 딜레이
- `Gentle`: 50장, 스크롤 8회, 6~12초 랜덤 딜레이
- `Manual`: 값을 직접 조정

권장:

- 처음은 `Safe`만 쓴다.
- 같은 보드를 반복 실행하지 않는다.
- `Original quality`는 필요할 때만 켠다. 켜면 `i.pinimg.com/originals/...` 원본 후보를 시도하고, 실패하면 표시용 preview 이미지로 자동 fallback한다.
- robot/rate-limit 문구가 보이면 즉시 멈추고 몇 시간 쉰다.

## Controls

- `Start Safe Download`: 수집 후 백그라운드 다운로드 큐 시작
- `Scan Only`: 다운로드 없이 현재 보드 핀만 확인
- `Stop`: 현재 항목 이후 중단하고 metadata 저장
- `Reset`: 상태 표시 초기화

## Metadata

작업이 끝나면 아래 파일이 함께 저장된다.

```txt
Downloads/pinterest-board/[board-name]/metadata.json
```

포함 내용:

- board URL
- pin URL
- image URL
- filename
- downloaded / failed / skipped_duplicate 상태
- recorded timestamp
