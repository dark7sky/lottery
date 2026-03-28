from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from datetime import timedelta
from pathlib import Path

from dhlottery_automation import (
    MAX_GAMES_PER_PURCHASE,
    MIN_GAMES_PER_PURCHASE,
    STATUS_FAILURE,
    BrowserConfig,
    LotteryCredentials,
    RuntimeConfig,
    TelegramConfig,
    load_state,
    now_local,
    run_purchase,
    save_state,
)

OPTIONS_PATH = Path("/data/options.json")
CONFIG_DIR = Path("/homeassistant/dh_lottery_auto")
STATE_PATH = CONFIG_DIR / "state.json"
REQUEST_PATH = CONFIG_DIR / "request.json"
PROCESSING_REQUEST_PATH = CONFIG_DIR / "request.processing.json"
POLL_INTERVAL_SECONDS = 10
HEARTBEAT_SAVE_INTERVAL_SECONDS = 30


def detect_chromium_executable() -> str | None:
    candidates = (
        os.getenv("CHROMIUM_EXECUTABLE"),
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    )
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def detect_chromium_version(executable_path: str) -> str:
    try:
        result = subprocess.run(
            [executable_path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"

    output = (result.stdout or result.stderr).strip()
    return output or "unknown"


def require_option(options: dict, name: str) -> str:
    value = str(options.get(name, "")).strip()
    if not value:
        raise RuntimeError(f"{name} 설정값이 비어 있습니다.")
    return value


def optional_option(options: dict, name: str) -> str:
    return str(options.get(name, "")).strip()


def parse_positive_int(value: object, name: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise RuntimeError(f"{name} 값은 1 이상이어야 합니다.")
    return parsed


def parse_games_count(value: object, name: str) -> int:
    parsed = int(value)
    if not MIN_GAMES_PER_PURCHASE <= parsed <= MAX_GAMES_PER_PURCHASE:
        raise RuntimeError(
            f"{name} 값은 {MIN_GAMES_PER_PURCHASE}에서 "
            f"{MAX_GAMES_PER_PURCHASE} 사이여야 합니다."
        )
    return parsed


def load_runtime_config() -> RuntimeConfig:
    options = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    chromium_executable = detect_chromium_executable()
    if chromium_executable:
        print(f"Using Chromium: {chromium_executable}")
        print(f"Chromium version: {detect_chromium_version(chromium_executable)}")
    else:
        print("Using Playwright bundled Chromium")
    telegram_bot_token = optional_option(options, "telegram_bot_token")
    telegram_chat_id = optional_option(options, "telegram_chat_id")
    telegram_config = None
    if telegram_bot_token or telegram_chat_id:
        if not telegram_bot_token or not telegram_chat_id:
            raise RuntimeError(
                "Telegram 알림을 사용하려면 telegram_bot_token 과 "
                "telegram_chat_id 를 함께 설정해야 합니다."
            )
        telegram_config = TelegramConfig(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
        )

    return RuntimeConfig(
        credentials=LotteryCredentials(
            user_id=require_option(options, "dhlottery_id"),
            password=require_option(options, "dhlottery_pw"),
        ),
        telegram=telegram_config,
        games_per_purchase=parse_games_count(
            options.get("games_per_purchase", 5), "games_per_purchase"
        ),
        interval_days=parse_positive_int(
            options.get("interval_days", 7), "interval_days"
        ),
        browser=BrowserConfig(
            headless=True,
            executable_path=chromium_executable,
            args=("--no-sandbox", "--disable-dev-shm-usage"),
        ),
    )


def read_request() -> dict | None:
    if PROCESSING_REQUEST_PATH.exists():
        source_path = PROCESSING_REQUEST_PATH
    elif REQUEST_PATH.exists():
        PROCESSING_REQUEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        REQUEST_PATH.replace(PROCESSING_REQUEST_PATH)
        source_path = PROCESSING_REQUEST_PATH
    else:
        return None

    try:
        return json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        invalid_path = source_path.with_name(
            f"request.invalid.{int(time.time())}.json"
        )
        source_path.replace(invalid_path)
        raise RuntimeError(f"수동 요청 파일을 읽지 못했습니다: {exc}") from exc


def clear_processing_request() -> None:
    PROCESSING_REQUEST_PATH.unlink(missing_ok=True)


def record_loop_error(state, message: str) -> None:
    error_time = now_local()
    state.running = False
    state.status = STATUS_FAILURE
    state.last_error = message
    state.last_message = message
    state.current_request_id = None
    state.current_trigger = None
    state.last_run_at = error_time
    state.next_run_at = error_time + timedelta(days=state.interval_days)
    state.update_heartbeat()


def main() -> None:
    config = load_runtime_config()
    state = load_state(STATE_PATH, config)
    save_state(STATE_PATH, state)

    last_heartbeat_write = 0.0

    while True:
        try:
            now = time.monotonic()
            if now - last_heartbeat_write >= HEARTBEAT_SAVE_INTERVAL_SECONDS:
                state.update_heartbeat()
                save_state(STATE_PATH, state)
                last_heartbeat_write = now

            request = read_request()
            should_run_scheduled = (
                state.next_run_at is not None and now_local() >= state.next_run_at
            )
            if request is None and not should_run_scheduled:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            trigger = "manual" if request is not None else "scheduled"
            request_id = (
                str(request.get("request_id")).strip()
                if request and request.get("request_id")
                else str(uuid.uuid4())
            )
            games_override = None
            if request and request.get("games") is not None:
                games_override = parse_games_count(request["games"], "games")

            state.mark_running(request_id=request_id, trigger=trigger)
            state.update_heartbeat()
            save_state(STATE_PATH, state)
            if request is not None:
                clear_processing_request()

            attempt = run_purchase(
                config=config,
                trigger=trigger,
                request_id=request_id,
                games_requested=games_override,
            )
            state.record_attempt(attempt, interval_days=config.interval_days)
            save_state(STATE_PATH, state)
        except Exception as exc:
            record_loop_error(state, f"add-on 루프 오류: {exc}")
            save_state(STATE_PATH, state)
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
