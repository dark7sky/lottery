# DH Lottery Auto Add-on

이 add-on은 동행복권에 로그인해 지정한 게임 수만큼 자동 구매를 진행하고, 결과를 상태 파일에 저장하며, Telegram이 설정된 경우 Telegram으로도 전달합니다.

## Configuration

- `dhlottery_id`: 동행복권 아이디
- `dhlottery_pw`: 동행복권 비밀번호
- `telegram_bot_token`: Telegram 봇 토큰. 선택사항입니다.
- `telegram_chat_id`: Telegram 채팅 ID. 선택사항입니다.
- `games_per_purchase`: 한 번 실행할 때 구매할 게임 수. `1`에서 `5`까지 설정할 수 있고 기본값은 `5`입니다.
- `interval_days`: 자동 구매 주기

Telegram 알림을 쓰려면 `telegram_bot_token` 과 `telegram_chat_id` 를 둘 다 입력해야 합니다. 둘 다 비워두면 Telegram 전송은 하지 않습니다.

## Runtime Files

- `/config/dh_lottery_auto/state.json`: add-on이 마지막 실행 결과와 다음 실행 예정 시각을 저장합니다.
- `/config/dh_lottery_auto/request.json`: Home Assistant 쪽에서 즉시 구매를 요청할 때 쓰는 파일입니다.

## Behavior

- add-on은 `interval_days` 에 맞춰 주기적으로 구매를 시도합니다.
- 수동 요청 파일이 있으면 예약 실행보다 먼저 처리합니다.
- 구매 전 잔액이 부족하면 구매하지 않고 잔액 부족 상태를 저장합니다.
- 구매 성공 시 구매 결과와 이번 주 구매 번호를 상태에 남깁니다.
- 구매 실패나 예외가 발생하면 실패 메시지를 저장하고, Telegram이 설정된 경우 Telegram 알림을 보냅니다.

## Home Assistant Integration

companion custom integration은 이 상태 파일을 읽어서 다음 기능을 제공합니다.

- 현재 실행 상태를 보여주는 sensor
- 마지막 구매 결과를 보여주는 sensor
- 이번 주 구매 번호를 보여주는 sensor
- 마지막 실행 시각, 마지막 성공 시각, 다음 예정 시각을 보여주는 sensor
- 즉시 구매를 요청하는 button
- 즉시 구매를 요청하는 service `dh_lottery_auto.request_purchase`

integration 설정에서는 추가로 Home Assistant 알림 방식을 고를 수 있습니다.

- `none`: Home Assistant 알림 없음
- `persistent_notification`: Home Assistant UI persistent notification
- `notify_entity`: 선택한 `notify` 엔티티로 알림 전송

## Scheduling

- 첫 시작 후에는 `interval_days` 를 기준으로 다음 자동 실행 시각이 계산됩니다.
- 수동 실행이 끝나면 그 시각을 기준으로 다음 예약 시각이 다시 계산됩니다.
- add-on은 폴링 방식으로 request 파일과 예약 시각을 함께 확인합니다.

## Notes

- Playwright selector는 동행복권 사이트 구조 변경에 영향을 받을 수 있습니다.
- add-on은 headless Chromium으로 실행됩니다.
- Telegram 알림은 선택사항입니다.
