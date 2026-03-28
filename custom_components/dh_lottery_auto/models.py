from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .const import DEFAULT_GAMES_PER_PURCHASE, DEFAULT_INTERVAL_DAYS, STALE_AFTER

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILURE = "failure"
STATUS_INSUFFICIENT_BALANCE = "insufficient_balance"
STATUS_MISSING = "missing"
STATUS_STALE = "stale"
STATUS_ERROR = "error"


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc).astimezone()
    return parsed.astimezone()


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _clean_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]


def _summarize_text(value: str, limit: int = 255) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def _week_window(reference: datetime | None = None) -> tuple[datetime, datetime]:
    ref = (reference or _now_local()).astimezone()
    start = ref.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=ref.weekday()
    )
    end = start + timedelta(days=7)
    return start, end


@dataclass(slots=True)
class PurchaseAttempt:
    request_id: str
    trigger: str
    status: str
    message: str
    games_requested: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    balance: int | None = None
    ticket_lines: list[str] = field(default_factory=list)
    raw_message: str | None = None
    error: str | None = None

    @property
    def display_ticket_lines(self) -> list[str]:
        if self.ticket_lines:
            return [line.strip() for line in self.ticket_lines if line.strip()]
        return _clean_lines(self.raw_message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "trigger": self.trigger,
            "status": self.status,
            "message": self.message,
            "games_requested": self.games_requested,
            "started_at": _format_datetime(self.started_at),
            "finished_at": _format_datetime(self.finished_at),
            "balance": self.balance,
            "ticket_lines": list(self.ticket_lines),
            "raw_message": self.raw_message,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PurchaseAttempt":
        return cls(
            request_id=str(payload.get("request_id", "")),
            trigger=str(payload.get("trigger", "")),
            status=str(payload.get("status", STATUS_IDLE)),
            message=str(payload.get("message", "")),
            games_requested=int(payload.get("games_requested", 0) or 0),
            started_at=_parse_datetime(payload.get("started_at")),
            finished_at=_parse_datetime(payload.get("finished_at")),
            balance=payload.get("balance"),
            ticket_lines=list(payload.get("ticket_lines", [])),
            raw_message=payload.get("raw_message"),
            error=payload.get("error"),
        )


@dataclass(slots=True)
class LotteryState:
    status: str = STATUS_MISSING
    running: bool = False
    games_per_purchase: int = DEFAULT_GAMES_PER_PURCHASE
    interval_days: int = DEFAULT_INTERVAL_DAYS
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
    source_exists: bool = False
    source_mtime: datetime | None = None
    load_error: str | None = None

    @property
    def is_missing(self) -> bool:
        return not self.source_exists

    @property
    def is_stale(self) -> bool:
        if not self.source_exists:
            return True
        if self.last_heartbeat_at is not None:
            return _now_local() - self.last_heartbeat_at > STALE_AFTER
        if self.source_mtime is not None:
            return _now_local() - self.source_mtime > STALE_AFTER
        return False

    @property
    def status_label(self) -> str:
        if self.load_error:
            return STATUS_ERROR
        if self.is_missing:
            return STATUS_MISSING
        if self.is_stale:
            return STATUS_STALE
        if self.running:
            return STATUS_RUNNING
        return self.status or STATUS_IDLE

    @property
    def last_result(self) -> str:
        if self.is_missing:
            return STATUS_MISSING
        if self.load_error:
            return STATUS_ERROR
        if self.running:
            return STATUS_RUNNING
        if self.last_message:
            return _summarize_text(self.last_message)
        return self.status or STATUS_IDLE

    @property
    def state_age_seconds(self) -> int | None:
        if self.source_mtime is None:
            return None
        return int((_now_local() - self.source_mtime).total_seconds())

    @property
    def weekly_window(self) -> tuple[datetime, datetime]:
        return _week_window()

    @property
    def weekly_attempts(self) -> list[PurchaseAttempt]:
        start, end = self.weekly_window
        attempts: list[PurchaseAttempt] = []
        for attempt in self.history:
            finished = attempt.finished_at
            if finished is None:
                continue
            finished = finished.astimezone()
            if start <= finished < end and attempt.status == STATUS_SUCCESS:
                attempts.append(attempt)
        attempts.sort(key=lambda item: item.finished_at or datetime.min.replace(tzinfo=timezone.utc))
        return attempts

    @property
    def weekly_ticket_lines(self) -> list[str]:
        lines: list[str] = []
        for attempt in self.weekly_attempts:
            lines.extend(attempt.display_ticket_lines)
        return lines

    @property
    def weekly_games_count(self) -> int:
        return len(self.weekly_ticket_lines)

    @property
    def weekly_summary(self) -> str:
        lines = self.weekly_ticket_lines
        if not lines:
            return "no games"

        summary = " | ".join(lines)
        if len(summary) <= 255:
            return summary
        return f"{len(lines)} games"

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        games_per_purchase: int = DEFAULT_GAMES_PER_PURCHASE,
        interval_days: int = DEFAULT_INTERVAL_DAYS,
    ) -> "LotteryState":
        if not path.exists():
            return cls(
                status=STATUS_MISSING,
                games_per_purchase=games_per_purchase,
                interval_days=interval_days,
                source_exists=False,
            )

        source_mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).astimezone()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return cls(
                status=STATUS_ERROR,
                games_per_purchase=games_per_purchase,
                interval_days=interval_days,
                source_exists=True,
                source_mtime=source_mtime,
                load_error=str(exc),
            )

        if not isinstance(raw, dict):
            return cls(
                status=STATUS_ERROR,
                games_per_purchase=games_per_purchase,
                interval_days=interval_days,
                source_exists=True,
                source_mtime=source_mtime,
                load_error="state file does not contain a JSON object",
            )

        history = [
            PurchaseAttempt.from_dict(item)
            for item in raw.get("history", [])
            if isinstance(item, dict)
        ]
        return cls(
            status=str(raw.get("status", STATUS_IDLE)),
            running=bool(raw.get("running", False)),
            games_per_purchase=int(raw.get("games_per_purchase", games_per_purchase)),
            interval_days=int(raw.get("interval_days", interval_days)),
            last_message=raw.get("last_message"),
            last_error=raw.get("last_error"),
            last_run_at=_parse_datetime(raw.get("last_run_at")),
            last_success_at=_parse_datetime(raw.get("last_success_at")),
            next_run_at=_parse_datetime(raw.get("next_run_at")),
            last_heartbeat_at=_parse_datetime(raw.get("last_heartbeat_at")),
            current_request_id=raw.get("current_request_id"),
            current_trigger=raw.get("current_trigger"),
            last_balance=raw.get("last_balance"),
            last_ticket_lines=list(raw.get("last_ticket_lines", [])),
            history=history,
            source_exists=True,
            source_mtime=source_mtime,
        )
