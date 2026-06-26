import json
import threading
from pathlib import Path
from typing import Any, List

from backend.config import (
    ALERTS_FILE,
    CHAT_HISTORY_FILE,
    INCIDENTS_FILE,
    LOGS_FILE,
    DATA_DIR,
    MAX_ALERT_ITEMS,
    MAX_CHAT_MESSAGES,
    MAX_INCIDENT_ITEMS,
    MAX_HISTORY_ITEMS,
)

LOCK = threading.Lock()


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_file(path: Path) -> List[Any]:
    ensure_data_dir()
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except Exception:
        return []


def _save_file(path: Path, data: List[Any]) -> None:
    ensure_data_dir()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def append_record(path: Path, item: Any, max_items: int) -> None:
    with LOCK:
        records = _load_file(path)
        records.append(item)
        if len(records) > max_items:
            records = records[-max_items:]
        _save_file(path, records)


def get_history() -> List[Any]:
    return _load_file(LOGS_FILE)


def get_alerts() -> List[Any]:
    return _load_file(ALERTS_FILE)


def get_incidents() -> List[Any]:
    return _load_file(INCIDENTS_FILE)


def get_chat_history() -> List[Any]:
    return _load_file(CHAT_HISTORY_FILE)


def save_chat_history(messages: List[Any]) -> None:
    _save_file(CHAT_HISTORY_FILE, messages[-MAX_CHAT_MESSAGES:])


def append_alert(alert: Any) -> None:
    append_record(ALERTS_FILE, alert, MAX_ALERT_ITEMS)


def append_incident(incident: Any) -> None:
    append_record(INCIDENTS_FILE, incident, MAX_INCIDENT_ITEMS)


def append_chat_message(message: Any) -> None:
    append_record(CHAT_HISTORY_FILE, message, MAX_CHAT_MESSAGES)


def append_history(payload: Any) -> None:
    append_record(LOGS_FILE, payload, MAX_HISTORY_ITEMS)
