from __future__ import annotations

from datetime import timedelta

DOMAIN = "dh_lottery_auto"
NAME = "DH Lottery Auto"

DEFAULT_GAMES_PER_PURCHASE = 5
DEFAULT_INTERVAL_DAYS = 7
MIN_GAMES_PER_PURCHASE = 1
MAX_GAMES_PER_PURCHASE = 5

DATA_DIR_NAME = "dh_lottery_auto"
STATE_FILE_NAME = "state.json"
REQUEST_FILE_NAME = "request.json"
PROCESSING_REQUEST_FILE_NAME = "request.processing.json"
NOTIFIER_STORAGE_VERSION = 1

CONF_GAMES = "games"
CONF_NOTIFICATION_MODE = "notification_mode"
CONF_NOTIFY_ENTITY_ID = "notify_entity_id"

SERVICE_REQUEST_PURCHASE = "request_purchase"

UPDATE_INTERVAL = timedelta(seconds=30)
STALE_AFTER = timedelta(minutes=5)

NOTIFICATION_MODE_NONE = "none"
NOTIFICATION_MODE_PERSISTENT = "persistent_notification"
NOTIFICATION_MODE_NOTIFY_ENTITY = "notify_entity"
