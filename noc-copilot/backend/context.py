import datetime
from fastapi import APIRouter

from backend.ollama_client import OllamaClient
from backend.storage import get_history, get_alerts, get_incidents

router = APIRouter()


def _parse_timestamp(timestamp: str) -> datetime.datetime:
    try:
        dt = datetime.datetime.fromisoformat(timestamp)
        # Normalize to naive UTC datetime for consistent arithmetic
        if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return datetime.datetime.utcnow()


def _latest_history_payload(history):
    if not history:
        return None
    return history[-1]


def build_system_context() -> dict:
    history = get_history()
    alerts = get_alerts()
    incidents = get_incidents()
    latest = _latest_history_payload(history)

    current_telemetry = latest["metrics"] if latest else {}
    current_anomaly = latest["anomaly"] if latest else {}
    current_rca = latest["rca"] if latest else {}
    latest_timestamp = _parse_timestamp(latest["timestamp"]) if latest and latest.get("timestamp") else None

    network_status = "Offline"
    simulator_state = "Idle"
    if latest_timestamp:
        delta = datetime.datetime.utcnow() - latest_timestamp
        if delta.total_seconds() < 20:
            network_status = "Active"
            simulator_state = "Streaming"
        else:
            network_status = "Delayed"
            simulator_state = "Waiting for Telemetry"

    historical_anomalies = [item for item in history if item.get("anomaly", {}).get("is_anomaly")]
    recent_incidents = incidents[-10:]

    ollama_status = OllamaClient().health_text()
    context_summary = {
        "current_telemetry": current_telemetry,
        "current_anomaly": current_anomaly,
        "current_rca": current_rca,
        "network_status": network_status,
        "simulator_state": simulator_state,
        "ollama_status": ollama_status,
        "recent_alerts": alerts[-10:],
        "recent_incidents": recent_incidents,
        "historical_anomalies": [{
            "timestamp": item.get("timestamp"),
            "metrics": item.get("metrics"),
            "anomaly_score": item.get("anomaly", {}).get("anomaly_score"),
            "rca": item.get("rca")
        } for item in historical_anomalies[-20:]],
        "summary": _build_summary(latest, alerts, recent_incidents, simulator_state)
    }

    return context_summary


def _build_summary(latest, alerts, recent_incidents, simulator_state):
    if not latest:
        return "No telemetry has been received yet."

    metrics = latest.get("metrics", {})
    anomaly = latest.get("anomaly", {})
    rca = latest.get("rca", {})

    summary = [
        f"Latest telemetry at {latest.get('timestamp')}: latency={metrics.get('latency', 'N/A')}ms, packet_loss={metrics.get('packet_loss', 'N/A')}%, jitter={metrics.get('jitter', 'N/A')}ms, bandwidth={metrics.get('bandwidth', 'N/A')}%.",
        f"Anomaly score is {anomaly.get('anomaly_score', 'N/A')}.",
        f"RCA indicates '{rca.get('cause', 'N/A')}' with impact: {rca.get('impact', 'N/A')}.",
        f"Network status is {simulator_state}."
    ]

    if alerts:
        summary.append(f"There are {len(alerts)} stored alerts, and {len(recent_incidents)} recent incidents.")
    if recent_incidents:
        summary.append(f"Most recent incident severity is {recent_incidents[-1].get('severity', 'N/A')}.")

    return " ".join(summary)


from backend.storage import get_alerts, get_incidents


@router.get("/system/context")
async def get_system_context():
    return build_system_context()


@router.get("/alerts")
async def get_alerts_api():
    return get_alerts()


@router.get("/incidents")
async def get_incidents_api():
    return get_incidents()


@router.get("/ollama/status")
async def get_ollama_status():
    return {"status": OllamaClient().health_text()}
