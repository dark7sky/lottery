from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILURE = "failure"
STATUS_INSUFFICIENT_BALANCE = "insufficient_balance"
MIN_GAMES_PER_PURCHASE = 1
MAX_GAMES_PER_PURCHASE = 5

TRIGGER_SCHEDULED = "scheduled"
TRIGGER_MANUAL = "manual"


def now_local() -> datetime:
    """Return an aware datetime in the local timezone."""
    return datetime.now().astimezone()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def datetime_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


@dataclass(frozen=True)
class LotteryCredentials:
    user_id: str
    password: str


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


@dataclass(frozen=True)
class BrowserConfig:
    headless: bool = True
    device_name: str = "Galaxy S24"
    executable_path: str | None = None
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeConfig:
    credentials: LotteryCredentials
    telegram: TelegramConfig | None
    games_per_purchase: int
    interval_days: int
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    purchase_timeout_ms: int = 10000

    def __post_init__(self) -> None:
        if not self.credentials.user_id.strip():
            raise ValueError("동행복권 아이디가 비어 있습니다.")
        if not self.credentials.password.strip():
            raise ValueError("동행복권 비밀번호가 비어 있습니다.")
        if self.telegram is not None:
            if not self.telegram.bot_token.strip():
                raise ValueError("Telegram 봇 토큰이 비어 있습니다.")
            if not self.telegram.chat_id.strip():
                raise ValueError("Telegram 채팅 ID가 비어 있습니다.")
        if not MIN_GAMES_PER_PURCHASE <= self.games_per_purchase <= MAX_GAMES_PER_PURCHASE:
            raise ValueError(
                f"games_per_purchase 는 {MIN_GAMES_PER_PURCHASE}에서 "
                f"{MAX_GAMES_PER_PURCHASE} 사이여야 합니다."
            )
        if self.interval_days < 1:
            raise ValueError("interval_days 는 1 이상이어야 합니다.")
        if self.purchase_timeout_ms < 1:
            raise ValueError("purchase_timeout_ms 는 1 이상이어야 합니다.")


@dataclass
class PurchaseAttempt:
    request_id: str
    trigger: str
    status: str
    message: str
    games_requested: int
    started_at: datetime = field(default_factory=now_local)
    finished_at: datetime | None = None
    balance: int | None = None
    ticket_lines: list[str] = field(default_factory=list)
    raw_message: str | None = None
    error: str | None = None

    def finish(self) -> None:
        self.finished_at = now_local()

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "trigger": self.trigger,
            "status": self.status,
            "message": self.message,
            "games_requested": self.games_requested,
            "started_at": datetime_to_iso(self.started_at),
            "finished_at": datetime_to_iso(self.finished_at),
            "balance": self.balance,
            "ticket_lines": list(self.ticket_lines),
            "raw_message": self.raw_message,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "PurchaseAttempt":
        return cls(
            request_id=payload.get("request_id", ""),
            trigger=payload.get("trigger", TRIGGER_SCHEDULED),
            status=payload.get("status", STATUS_IDLE),
            message=payload.get("message", ""),
            games_requested=int(payload.get("games_requested", 0)),
            started_at=parse_datetime(payload.get("started_at")) or now_local(),
            finished_at=parse_datetime(payload.get("finished_at")),
            balance=payload.get("balance"),
            ticket_lines=list(payload.get("ticket_lines", [])),
            raw_message=payload.get("raw_message"),
            error=payload.get("error"),
        )


@dataclass
class AddonState:
    status: str = STATUS_IDLE
    running: bool = False
    games_per_purchase: int = 5
    interval_days: int = 7
    last_message: str | None = None
    last_error: str | None = None
    last_run_at: datetime | None = None
    last_success_at: datetime | None = None
    next_run_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    current_request_id: str | None = None
    current_trigger: str | None = None
    last_balance: int | None = None
    last_ticket_lines: list[str] = field(default_factory=list)
    history: list[PurchaseAttempt] = field(default_factory=list)

    def apply_config(self, config: RuntimeConfig) -> None:
        self.games_per_purchase = config.games_per_purchase
        self.interval_days = config.interval_days
        if self.last_run_at is None and self.next_run_at is None:
            self.next_run_at = now_local()
        elif self.last_run_at is not None:
            self.next_run_at = self.last_run_at + timedelta(days=config.interval_days)

    def mark_running(self, request_id: str, trigger: str) -> None:
        self.running = True
        self.status = STATUS_RUNNING
        self.current_request_id = request_id
        self.current_trigger = trigger
        self.last_error = None

    def update_heartbeat(self) -> None:
        self.last_heartbeat_at = now_local()

    def record_attempt(self, attempt: PurchaseAttempt, interval_days: int) -> None:
        self.running = False
        self.status = attempt.status
        self.last_message = attempt.message
        self.last_error = attempt.error
        self.last_run_at = attempt.finished_at
        self.current_request_id = None
        self.current_trigger = None
        self.last_balance = attempt.balance
        self.last_ticket_lines = list(attempt.ticket_lines)
        if attempt.status == STATUS_SUCCESS:
            self.last_success_at = attempt.finished_at
        reference_time = attempt.finished_at or now_local()
        self.next_run_at = reference_time + timedelta(days=interval_days)
        self.history.insert(0, attempt)
        self.history = self.history[:30]
        self.update_heartbeat()

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "running": self.running,
            "games_per_purchase": self.games_per_purchase,
            "interval_days": self.interval_days,
            "last_message": self.last_message,
            "last_error": self.last_error,
            "last_run_at": datetime_to_iso(self.last_run_at),
            "last_success_at": datetime_to_iso(self.last_success_at),
            "next_run_at": datetime_to_iso(self.next_run_at),
            "last_heartbeat_at": datetime_to_iso(self.last_heartbeat_at),
            "current_request_id": self.current_request_id,
            "current_trigger": self.current_trigger,
            "last_balance": self.last_balance,
            "last_ticket_lines": list(self.last_ticket_lines),
            "history": [attempt.to_dict() for attempt in self.history],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "AddonState":
        return cls(
            status=payload.get("status", STATUS_IDLE),
            running=bool(payload.get("running", False)),
            games_per_purchase=int(payload.get("games_per_purchase", 5)),
            interval_days=int(payload.get("interval_days", 7)),
            last_message=payload.get("last_message"),
            last_error=payload.get("last_error"),
            last_run_at=parse_datetime(payload.get("last_run_at")),
            last_success_at=parse_datetime(payload.get("last_success_at")),
            next_run_at=parse_datetime(payload.get("next_run_at")),
            last_heartbeat_at=parse_datetime(payload.get("last_heartbeat_at")),
            current_request_id=payload.get("current_request_id"),
            current_trigger=payload.get("current_trigger"),
            last_balance=payload.get("last_balance"),
            last_ticket_lines=list(payload.get("last_ticket_lines", [])),
            history=[PurchaseAttempt.from_dict(item) for item in payload.get("history", [])],
        )
