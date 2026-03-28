"""DH Lottery automation package."""

from .buyer import run_purchase
from .models import (
    STATUS_FAILURE,
    STATUS_IDLE,
    STATUS_INSUFFICIENT_BALANCE,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    AddonState,
    BrowserConfig,
    LotteryCredentials,
    PurchaseAttempt,
    RuntimeConfig,
    TelegramConfig,
    now_local,
)
from .state import load_state, save_state

__all__ = [
    "AddonState",
    "BrowserConfig",
    "LotteryCredentials",
    "PurchaseAttempt",
    "RuntimeConfig",
    "STATUS_FAILURE",
    "STATUS_IDLE",
    "STATUS_INSUFFICIENT_BALANCE",
    "STATUS_RUNNING",
    "STATUS_SUCCESS",
    "TelegramConfig",
    "load_state",
    "now_local",
    "run_purchase",
    "save_state",
]
