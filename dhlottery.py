from __future__ import annotations

import argparse
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError as exc:  # pragma: no cover - user environment issue
    raise ModuleNotFoundError(
        "python-dotenv is not installed. Use the OpenClaw wrapper at "
        "'skills/dh-lottery-cli/scripts/run_lottery.py' or install "
        "requirements.txt into a virtualenv first."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parent

from dhlottery_automation import (  # noqa: E402
    BrowserConfig,
    LotteryCredentials,
    RuntimeConfig,
    STATUS_FAILURE,
    TelegramConfig,
    run_purchase,
)
from dhlottery_automation.models import (  # noqa: E402
    MAX_GAMES_PER_PURCHASE,
    MIN_GAMES_PER_PURCHASE,
)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def optional_env(name: str) -> str:
    value = os.getenv(name)
    return value.strip() if value else ""


def parse_positive_int(value: str | int, name: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise RuntimeError(f"{name} must be 1 or greater.")
    return parsed


def parse_games_count(value: str | int) -> int:
    games = int(value)
    if not MIN_GAMES_PER_PURCHASE <= games <= MAX_GAMES_PER_PURCHASE:
        raise RuntimeError(
            f"DHLOTTERY_GAMES must be between "
            f"{MIN_GAMES_PER_PURCHASE} and {MAX_GAMES_PER_PURCHASE}."
        )
    return games


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the DH Lottery Playwright automation from this repository."
    )
    parser.add_argument(
        "--env-file",
        help="Optional dotenv path. Defaults to .env in the repository root when present.",
    )
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="Skip loading dotenv files and only use process environment variables.",
    )
    parser.add_argument(
        "--games",
        type=int,
        help="Override the number of games to buy for this run (1-5).",
    )
    parser.add_argument(
        "--interval-days",
        type=int,
        help="Override the interval_days value in the runtime config.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Chromium with a visible window for debugging.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate configuration and print a safe summary without buying.",
    )
    parser.add_argument(
        "--request-id",
        default="cli",
        help="Request identifier recorded in the purchase attempt.",
    )
    parser.add_argument(
        "--trigger",
        default="manual",
        choices=("manual", "scheduled"),
        help="Trigger label recorded in the purchase attempt.",
    )
    return parser


def load_environment(env_file: str | None, *, no_dotenv: bool) -> None:
    if no_dotenv:
        return

    if env_file:
        dotenv_path = Path(env_file)
        if not dotenv_path.is_absolute():
            dotenv_path = (Path.cwd() / dotenv_path).resolve()
        if not dotenv_path.exists():
            raise RuntimeError(f"Dotenv file not found: {dotenv_path}")
        load_dotenv(dotenv_path=dotenv_path, override=False)
        return

    default_env = REPO_ROOT / ".env"
    if default_env.exists():
        load_dotenv(dotenv_path=default_env, override=False)


def build_runtime_config(args: argparse.Namespace) -> RuntimeConfig:
    telegram_bot_token = optional_env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = optional_env("TELEGRAM_CHAT_ID")
    telegram_config = None
    if telegram_bot_token or telegram_chat_id:
        if not telegram_bot_token or not telegram_chat_id:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must both be set."
            )
        telegram_config = TelegramConfig(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
        )

    games_value = args.games if args.games is not None else os.getenv("DHLOTTERY_GAMES", "5")
    interval_value = (
        args.interval_days
        if args.interval_days is not None
        else os.getenv("DHLOTTERY_INTERVAL_DAYS", "7")
    )

    return RuntimeConfig(
        credentials=LotteryCredentials(
            user_id=require_env("DHLOTTERY_ID"),
            password=require_env("DHLOTTERY_PW"),
        ),
        telegram=telegram_config,
        games_per_purchase=parse_games_count(games_value),
        interval_days=parse_positive_int(interval_value, "DHLOTTERY_INTERVAL_DAYS"),
        browser=BrowserConfig(headless=not args.headed),
    )


def print_config_summary(config: RuntimeConfig) -> None:
    print("Configuration OK")
    print(f"user_id={config.credentials.user_id}")
    print(f"games_per_purchase={config.games_per_purchase}")
    print(f"interval_days={config.interval_days}")
    print(f"telegram_enabled={'yes' if config.telegram else 'no'}")
    print(f"headless={'yes' if config.browser.headless else 'no'}")


def main() -> None:
    args = build_parser().parse_args()
    load_environment(args.env_file, no_dotenv=args.no_dotenv)
    config = build_runtime_config(args)

    if args.check_config:
        print_config_summary(config)
        return

    attempt = run_purchase(
        config=config,
        trigger=args.trigger,
        request_id=args.request_id,
    )
    print(attempt.message)
    if attempt.ticket_lines:
        print("\n".join(attempt.ticket_lines))
    if attempt.status == STATUS_FAILURE:
        raise RuntimeError(attempt.message)


if __name__ == "__main__":
    main()
