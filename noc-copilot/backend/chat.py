import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import MAX_CHAT_MESSAGES
from backend.context import build_system_context
from backend.correlation_engine import correlation_engine
from backend.incident_engine import incident_engine
from backend.ollama_client import OllamaClient
from backend.storage import get_alerts, get_history, get_chat_history, save_chat_history, append_chat_message
from backend.timeline_engine import timeline_engine


class ChatRequest(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    incident_data: Dict[str, Any]


router = APIRouter()
logger = logging.getLogger(__name__)
client = OllamaClient()


def _format_incident_list(incidents: List[Dict[str, Any]]) -> str:
    if not incidents:
        return "No active incidents found."
    lines = []
    for incident in incidents[:5]:
        lines.append(
            f"[{incident.get('timestamp')}] {incident.get('severity')} {incident.get('service')} - {incident.get('summary')}"
        )
    return "\n".join(lines)


def _format_correlations(correlations: List[Dict[str, Any]]) -> str:
    if not correlations:
        return "No correlated incident patterns detected."
    lines = []
    for group in correlations[:3]:
        primary = group.get("primary_incident", {})
        related = len(group.get("related_incidents", []))
        lines.append(
            f"Primary incident {primary.get('id')} correlated with {related} related incident(s)."
        )
    return "\n".join(lines)


def _format_timeline(timeline: List[Dict[str, Any]]) -> str:
    if not timeline:
        return "No incident timeline available."
    return "\n".join([f"[{step.get('timestamp')}] {step.get('description')}" for step in timeline[:5]])


def _build_prompt(user_question: str, context: Dict[str, Any], incidents: List[Dict[str, Any]], correlations: List[Dict[str, Any]], timeline: List[Dict[str, Any]]) -> str:
    instructions = [
        "You are an offline AI NOC Copilot assistant for a network operations center.",
        "Use only the provided incident context, telemetry, alerts, and correlated incident data.",
        "Do not hallucinate or invent information outside the given data.",
        "If the requested information is unavailable, state that it is unavailable and provide concrete next-step troubleshooting guidance.",
        "Answer clearly, professionally, and with NOC operations style."
    ]

    incident_summary = _format_incident_list(incidents)
    correlation_summary = _format_correlations(correlations)
    timeline_summary = _format_timeline(timeline)

    prompt_parts = [
        "System Context:\n", context.get("summary", "No system context available."),
        "\n\nActive Incidents:\n", incident_summary,
        "\n\nCorrelated Incident Patterns:\n", correlation_summary,
        "\n\nIncident Timeline:\n", timeline_summary,
        "\n\nCurrent Telemetry:\n", json.dumps(context.get("current_telemetry", {}), indent=2),
        "\n\nCurrent RCA:\n", json.dumps(context.get("current_rca", {}), indent=2),
        "\n\nUser Question:\n", user_question,
        "\n\nProvide a structured, incident-aware answer that references active incidents and root cause analysis when applicable."
    ]

    return "\n".join(instructions + ["".join(prompt_parts)])


def _extract_assistant_reply(response_data: Any) -> Optional[str]:
    if isinstance(response_data, dict):
        if isinstance(response_data.get("reply"), str):
            return response_data["reply"]
        if isinstance(response_data.get("assistant"), str):
            return response_data["assistant"]

        for choice in response_data.get("choices", []):
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(choice.get("text"), str):
                return choice["text"]
            delta = choice.get("delta")
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                return delta["content"]

    if isinstance(response_data, str):
        return response_data

    return None


def _fallback_reply(user_question: str, incidents: List[Dict[str, Any]]) -> str:
    if incidents:
        top_incident = incidents[0]
        return (
            f"The local model is unavailable. Based on the active incident '{top_incident.get('summary')}', "
            f"investigate {top_incident.get('service')} issues and validate the root cause: {top_incident.get('root_cause')}."
        )

    normalized = user_question.lower()
    if any(term in normalized for term in ["latency", "packet loss", "jitter", "bandwidth"]):
        return "The local model is unavailable. Investigate interface and WAN path health for latency or packet loss issues."
    if any(term in normalized for term in ["alert", "incident", "down", "critical"]):
        return "The local model is unavailable. Review active alerts and incident summaries, then validate the most severe incident impact."
    return "The local model is unavailable. Use existing telemetry and alerts to verify device health and routing stability."


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
    prompt = _build_prompt(user_question, context, incidents, correlations, timeline)

    assistant_content = ""
    try:
        response_data = await asyncio.to_thread(client.chat, prompt, previous_history)
        assistant_content = _extract_assistant_reply(response_data) or ""
        if not assistant_content:
            assistant_content = _fallback_reply(user_question, incidents)
    except Exception as exc:
        logger.error('Ollama chat failed: %s', exc)
        assistant_content = _fallback_reply(user_question, incidents)

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
