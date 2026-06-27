import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import MAX_CHAT_MESSAGES
from backend.context import build_system_context
from backend.correlation_engine import correlation_engine
from backend.incident_engine import incident_engine
from backend.storage import get_alerts, get_history, get_incidents, get_chat_history, save_chat_history, append_chat_message
from backend.timeline_engine import timeline_engine


class ChatRequest(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    incident_data: Dict[str, Any]


router = APIRouter()
logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    return text.strip().lower()


def _is_alert_query(question: str) -> bool:
    q = _normalize_text(question)
    return any(
        phrase in q
        for phrase in [
            "recent alerts",
            "what alerts",
            "show alerts",
            "list alerts",
            "active alerts",
            "alerts?",
        ]
    )


def _is_incident_query(question: str) -> bool:
    q = _normalize_text(question)
    return any(
        phrase in q
        for phrase in [
            "what incidents",
            "active incidents",
            "show incidents",
            "list incidents",
            "current incidents",
            "incidents?",
        ]
    )


def _is_status_query(question: str) -> bool:
    q = _normalize_text(question)
    return any(
        phrase in q
        for phrase in [
            "what is happening",
            "system status",
            "current issues",
            "what is going on",
            "status?",
        ]
    )


def _format_alerts(alerts: List[Dict[str, Any]]) -> str:
    if not alerts:
        return "No relevant data found"
    lines = []
    for alert in alerts[-10:]:
        summary = (
            alert.get("summary")
            or alert.get("message")
            or alert.get("title")
            or alert.get("root_cause")
            or "Alert"
        )
        timestamp = alert.get("timestamp", "unknown time")
        severity = str(alert.get("severity", "UNKNOWN")).upper()
        lines.append(f"[{timestamp}] {severity}: {summary}")
    return "\n".join(lines)


def _format_incidents(incidents: List[Dict[str, Any]]) -> str:
    if not incidents:
        return "No relevant data found"
    lines = []
    for incident in incidents[-10:]:
        summary = incident.get("summary") or incident.get("incident") or "Incident"
        timestamp = incident.get("timestamp", "unknown time")
        severity = str(incident.get("severity", "UNKNOWN")).upper()
        service = incident.get("service", "network")
        lines.append(f"[{timestamp}] {severity} {service}: {summary}")
    return "\n".join(lines)


def _format_status(context: Dict[str, Any]) -> str:
    alerts = context.get("recent_alerts", [])
    incidents = context.get("recent_incidents", [])
    if not alerts and not incidents:
        return "No relevant data found"
    lines = []
    if alerts:
        lines.append(f"Recent alerts: {len(alerts)}")
    if incidents:
        lines.append(f"Active incidents: {len(incidents)}")
    status = "Healthy"
    if incidents or alerts:
        status = "Degraded"
    return " \n".join(lines + [f"System Status: {status}"])


def _analysis_response(question: str, context: Dict[str, Any], incidents: List[Dict[str, Any]], alerts: List[Dict[str, Any]]) -> str:
    q = _normalize_text(question)
    telemetry = context.get("current_telemetry", {})
    rca = context.get("current_rca", {})

    if any(metric in q for metric in ["latency", "packet loss", "jitter", "bandwidth", "throughput"]):
        if telemetry:
            metrics = []
            if telemetry.get("latency") is not None:
                metrics.append(f"latency={telemetry.get('latency')}ms")
            if telemetry.get("packet_loss") is not None:
                metrics.append(f"packet_loss={telemetry.get('packet_loss')}%")
            if telemetry.get("jitter") is not None:
                metrics.append(f"jitter={telemetry.get('jitter')}ms")
            if telemetry.get("bandwidth") is not None:
                metrics.append(f"bandwidth={telemetry.get('bandwidth')}%")
            metric_text = ", ".join(metrics) if metrics else "no telemetry metrics available"
            cause = rca.get("cause") or "Cause not available"
            impact = rca.get("impact") or "Impact not available"
            return f"{cause}. {metric_text}. {impact}".strip()

    if any(term in q for term in ["incident", "outage", "degraded", "failure", "down", "problem", "error"]):
        if incidents:
            latest = incidents[-1]
            summary = latest.get("summary") or latest.get("incident") or "Issue detected"
            cause = latest.get("root_cause") or "Cause not available"
            return f"{latest.get('severity', 'UNKNOWN')} incident: {summary}. Cause: {cause}."
        if alerts:
            alert = alerts[-1]
            summary = alert.get("summary") or alert.get("message") or "Alert detected"
            severity = str(alert.get("severity", "UNKNOWN")).upper()
            return f"{severity} alert: {summary}."

    if any(term in q for term in ["cpu", "server", "disk", "memory", "load"]):
        return "No relevant data found"

    if incidents:
        latest = incidents[-1]
        summary = latest.get("summary") or latest.get("incident") or "Issue detected"
        return f"Active incident: {summary}."
    if alerts:
        alert = alerts[-1]
        summary = alert.get("summary") or alert.get("message") or "Alert detected"
        return f"Recent alert: {summary}."

    return "No relevant data found"


@router.post("/chat", response_model=ChatResponse)
async def post_chat(request: ChatRequest):
    user_question = request.message or request.question
    if not user_question:
        raise HTTPException(status_code=400, detail="Missing message or question field")

    previous_history = get_chat_history()[-MAX_CHAT_MESSAGES:]
    user_entry = {"role": "user", "content": user_question}
    conversation_history = previous_history + [user_entry]
    append_chat_message(user_entry)
    try:
        save_chat_history(conversation_history)
    except Exception as exc:
        logger.error('Failed to save user chat history: %s', exc)

    history = get_history()
    alerts = get_alerts()
    incidents = incident_engine.parse_incidents(history, alerts)
    correlations = correlation_engine.correlate(incidents)
    timeline = timeline_engine.build_timeline(incidents)
    context = build_system_context()

    if _is_alert_query(user_question):
        assistant_content = _format_alerts(alerts)
    elif _is_incident_query(user_question):
        assistant_content = _format_incidents(incidents)
    elif _is_status_query(user_question):
        assistant_content = _format_status(context)
    else:
        assistant_content = _analysis_response(user_question, context, incidents, alerts)

    assistant_entry = {"role": "assistant", "content": assistant_content}
    append_chat_message(assistant_entry)
    conversation_history.append(assistant_entry)
    try:
        save_chat_history(conversation_history)
    except Exception as exc:
        logger.error('Failed to save assistant chat history: %s', exc)

    incident_data = {
        "incidents": incidents,
        "correlations": correlations,
        "timeline": timeline,
    }

    return {"reply": assistant_content, "incident_data": incident_data}


@router.get("/chat/history")
async def get_chat_history_api():
    return get_chat_history()
