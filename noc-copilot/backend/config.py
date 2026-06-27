import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_FILE = DATA_DIR / "logs.json"
ALERTS_FILE = DATA_DIR / "alerts.json"
INCIDENTS_FILE = DATA_DIR / "incidents.json"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = "llama3.1:latest"
OLLAMA_REQUEST_TIMEOUT = 180
OLLAMA_RETRIES = 2

ANOMALY_ALERT_THRESHOLD = 60
DEFAULT_DEVICE_NAME = "SD-WAN Edge Gateway 01"
MAX_HISTORY_ITEMS = 100
MAX_ALERT_ITEMS = 200
MAX_INCIDENT_ITEMS = 100
MAX_CHAT_MESSAGES = 200
