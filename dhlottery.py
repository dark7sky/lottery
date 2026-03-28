from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).parent / "addon_dh_lottery_auto" / "app"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from dhlottery_automation import (  # noqa: E402
    BrowserConfig,
    MAX_GAMES_PER_PURCHASE,
    MIN_GAMES_PER_PURCHASE,
    LotteryCredentials,
    RuntimeConfig,
    STATUS_FAILURE,
    TelegramConfig,
    run_purchase,
)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} 환경변수가 설정되지 않았습니다.")
    return value


def optional_env(name: str) -> str:
    value = os.getenv(name)
    return value.strip() if value else ""


def parse_games_count(value: str) -> int:
    games = int(value)
    if not MIN_GAMES_PER_PURCHASE <= games <= MAX_GAMES_PER_PURCHASE:
        raise RuntimeError(
            f"DHLOTTERY_GAMES 는 {MIN_GAMES_PER_PURCHASE}에서 "
            f"{MAX_GAMES_PER_PURCHASE} 사이여야 합니다."
        )
    return games


def main() -> None:
    load_dotenv()
    telegram_bot_token = optional_env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = optional_env("TELEGRAM_CHAT_ID")
    telegram_config = None
    if telegram_bot_token or telegram_chat_id:
        if not telegram_bot_token or not telegram_chat_id:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN 과 TELEGRAM_CHAT_ID 는 함께 설정해야 합니다."
            )
        telegram_config = TelegramConfig(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
        )

    config = RuntimeConfig(
        credentials=LotteryCredentials(
            user_id=require_env("DHLOTTERY_ID"),
            password=require_env("DHLOTTERY_PW"),
        ),
        telegram=telegram_config,
        games_per_purchase=parse_games_count(os.getenv("DHLOTTERY_GAMES", "5")),
        interval_days=int(os.getenv("DHLOTTERY_INTERVAL_DAYS", "7")),
        browser=BrowserConfig(headless=True),
    )

    attempt = run_purchase(
        config=config,
        trigger="manual",
        request_id="cli",
    )
    print(attempt.message)
    if attempt.ticket_lines:
        print("\n".join(attempt.ticket_lines))
    if attempt.status == STATUS_FAILURE:
        raise RuntimeError(attempt.message)


if __name__ == "__main__":
    main()
