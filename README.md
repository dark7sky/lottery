# DH Lottery Auto

이 프로젝트는 동행복권 로또 자동 구매를 세 가지 방식으로 다룹니다.

- Home Assistant add-on이 주기적으로 구매를 실행합니다.
- Home Assistant companion custom integration이 상태를 sensor/button/service로 노출합니다.
- `dhlottery.py`는 로컬에서 바로 실행하는 CLI 진입점입니다.

## Architecture

add-on은 동행복권 로그인, 구매, 상태 저장을 담당하고, Telegram이 설정된 경우 Telegram 알림도 보냅니다. 상태는 `/config/dh_lottery_auto/state.json` 에 저장되고, 수동 실행 요청은 `/config/dh_lottery_auto/request.json` 파일로 전달됩니다.

companion custom integration은 이 상태 파일을 읽어서 Home Assistant entity를 만들고, 수동 구매 요청도 같은 request 파일로 기록합니다. Scheduled run과 manual run이 같은 경로를 쓰기 때문에 add-on과 Home Assistant가 분리되어 있어도 동작을 맞추기 쉽습니다.

`dhlottery.py`는 같은 구매 로직을 재사용하는 로컬 CLI입니다. Home Assistant 없이 단독 실행하거나 디버깅할 때 유용합니다.

## Install

1. Python 3.10+ 환경을 준비합니다.
2. 로컬 CLI를 쓸 경우 아래 명령으로 의존성을 설치합니다.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

3. Home Assistant add-on을 쓰려면 이 저장소를 add-on repository로 추가하거나 `addon_dh_lottery_auto` 폴더를 local add-on 경로에 배치합니다.
4. companion custom integration은 Home Assistant 설정 폴더의 `custom_components/dh_lottery_auto` 아래에 설치합니다.
5. Home Assistant에서 `DH Lottery Auto` integration을 추가합니다.
6. integration 설정에서 Home Assistant 알림 방식을 선택합니다.
7. `Notify entity` 를 고르면 알림을 받을 `notify` 엔티티를 선택합니다.

## Add-on Config

add-on 설정 화면에서 아래 값을 입력합니다.

- `dhlottery_id`: 동행복권 아이디
- `dhlottery_pw`: 동행복권 비밀번호
- `telegram_bot_token`: Telegram Bot API 토큰. 선택사항입니다.
- `telegram_chat_id`: 알림을 받을 Telegram 채팅 ID. 선택사항입니다.
- `games_per_purchase`: 한 번 실행할 때 구매할 게임 수. `1`에서 `5`까지 설정할 수 있고 기본값은 `5`입니다.
- `interval_days`: 며칠마다 자동 구매할지

`dhlottery_id`, `dhlottery_pw`, `games_per_purchase`, `interval_days` 는 필수입니다.

Telegram 알림을 쓰려면 `telegram_bot_token` 과 `telegram_chat_id` 를 둘 다 입력해야 합니다. 둘 다 비워두면 Telegram 전송은 생략됩니다.

## Home Assistant Entities

companion custom integration은 상태 파일을 바탕으로 다음 기능을 노출합니다.

- 현재 상태를 보여주는 sensor entity
- 마지막 실행 결과를 보여주는 sensor entity
- 이번 주에 구매한 게임 번호를 보여주는 sensor entity
- 마지막 실행 시각과 다음 예정 시각을 확인하는 sensor entity
- 즉시 구매를 요청하는 button entity
- 즉시 구매를 요청하는 service `dh_lottery_auto.request_purchase`

번호 센서는 마지막 구매 결과의 `ticket_lines` 를 읽어서 표시합니다. 구매가 성공하면 이번 주 구매 번호를 보여주고, 실패하면 마지막 오류나 실패 메시지를 보여줍니다.

integration은 추가로 Home Assistant 내부 알림도 보낼 수 있습니다.

- `none`: Home Assistant 알림을 보내지 않습니다.
- `persistent_notification`: Home Assistant UI 안에 persistent notification을 생성합니다.
- `notify_entity`: 선택한 `notify` 엔티티로 알림을 보냅니다. 모바일 앱 알림 엔티티를 선택하면 기기 알림처럼 쓸 수 있습니다.

## Scheduled And Manual Runs

add-on은 내부 폴링 루프에서 다음 조건을 확인합니다.

- `interval_days` 가 지나면 자동으로 구매를 실행합니다.
- Home Assistant가 `request.json` 을 기록하면 바로 수동 구매를 실행합니다.

수동 구매 버튼이나 service는 request 파일에 `request_id` 와 선택적 `games` 값을 기록합니다. add-on은 이를 읽은 뒤 실제 구매를 진행하고, 결과를 `state.json` 에 다시 저장합니다.

integration은 add-on 상태가 없거나 오래된 경우 수동 구매 요청을 막아서, 꺼져 있는 add-on으로 요청이 쌓이지 않게 합니다.

## Local CLI

로컬에서 바로 돌릴 때는 `.env` 에 아래 값을 넣습니다.

```env
DHLOTTERY_ID=<your_dhlottery_id>
DHLOTTERY_PW=<your_dhlottery_password>
TELEGRAM_BOT_TOKEN=<optional_telegram_bot_token>
TELEGRAM_CHAT_ID=<optional_telegram_chat_id>
```

실행은 다음처럼 합니다.

```powershell
python .\dhlottery.py
```

`dhlottery.py`는 add-on과 같은 구매 로직을 쓰며, 실패 시 예외를 올리고 Telegram이 설정된 경우 알림도 시도합니다.

## Notes

- 사이트 구조나 버튼 이름이 바뀌면 Playwright selector를 수정해야 할 수 있습니다.
- add-on은 headless Chromium을 사용합니다.
- Telegram 알림은 선택사항입니다.
- Home Assistant 알림은 companion integration이 상태 변화를 감지해서 보냅니다.
