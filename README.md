# DH Lottery CLI

동행복권 자동 구매 로직을 로컬 Python CLI와 OpenClaw skill로 실행하는 저장소입니다.

## 구성

- `dhlottery.py`: 직접 실행 가능한 CLI 진입점
- `dhlottery_automation/`: Playwright 자동화와 런타임 모델
- `skills/dh-lottery-cli/`: OpenClaw에서 사용할 skill
- `requirements.txt`: 로컬 실행에 필요한 Python 패키지

## 빠른 시작

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python .\dhlottery.py --check-config
```

실제 구매는 아래처럼 명시적으로 실행합니다.

```powershell
python .\dhlottery.py --games 5
```

## 환경 변수

필수:

```env
DHLOTTERY_ID=<your_dhlottery_id>
DHLOTTERY_PW=<your_dhlottery_password>
```

선택:

```env
DHLOTTERY_GAMES=5
DHLOTTERY_INTERVAL_DAYS=7
TELEGRAM_BOT_TOKEN=<optional_telegram_bot_token>
TELEGRAM_CHAT_ID=<optional_telegram_chat_id>
```

기본적으로 저장소 루트의 `.env`를 자동으로 읽습니다.

## OpenClaw 사용

이 저장소를 OpenClaw workspace로 열면 `skills/dh-lottery-cli` 를 사용할 수 있습니다.

설정만 확인:

```powershell
python .\skills\dh-lottery-cli\scripts\run_lottery.py --check-config
```

실제 구매:

```powershell
python .\skills\dh-lottery-cli\scripts\run_lottery.py --games 5
```

이 래퍼는 필요하면 `venv` 생성, `requirements.txt` 설치, Playwright Chromium 설치까지 자동으로 수행합니다.

## 주의

- 실제 구매가 발생할 수 있으므로 `--check-config` 로 먼저 검증하는 것을 권장합니다.
- 동행복권 사이트 구조가 바뀌면 Playwright selector 수정이 필요할 수 있습니다.
