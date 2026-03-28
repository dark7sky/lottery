from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    DATA_DIR_NAME,
    PROCESSING_REQUEST_FILE_NAME,
    REQUEST_FILE_NAME,
    STATE_FILE_NAME,
)


def get_data_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DATA_DIR_NAME))


def get_state_path(hass: HomeAssistant) -> Path:
    return get_data_dir(hass) / STATE_FILE_NAME


def get_request_path(hass: HomeAssistant) -> Path:
    return get_data_dir(hass) / REQUEST_FILE_NAME


def get_processing_request_path(hass: HomeAssistant) -> Path:
    return get_data_dir(hass) / PROCESSING_REQUEST_FILE_NAME


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
