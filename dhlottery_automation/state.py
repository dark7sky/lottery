from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from .models import AddonState, RuntimeConfig, STATUS_FAILURE, now_local


def load_state(state_path: Path, config: RuntimeConfig) -> AddonState:
    if not state_path.exists():
        state = AddonState()
        state.apply_config(config)
        state.update_heartbeat()
        return state

    data = json.loads(state_path.read_text(encoding="utf-8"))
    state = AddonState.from_dict(data)
    state.apply_config(config)
    if state.running:
        interrupted_at = now_local()
        state.running = False
        state.status = STATUS_FAILURE
        state.last_error = "이전 구매 작업이 add-on 재시작으로 중단되었습니다."
        state.last_message = (
            "이전 구매 작업이 add-on 재시작으로 중단되었습니다. "
            "동행복권 계정에서 실제 구매 여부를 확인하세요."
        )
        state.current_request_id = None
        state.current_trigger = None
        state.last_run_at = interrupted_at
        state.next_run_at = interrupted_at + timedelta(days=config.interval_days)
        state.update_heartbeat()
    return state


def save_state(state_path: Path, state: AddonState) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = state_path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(state_path)
