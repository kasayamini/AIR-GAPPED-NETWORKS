import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import MAX_CHAT_MESSAGES
from backend.context import build_system_context
from backend.ollama_client import OllamaClient
from backend.storage import get_chat_history, save_chat_history, append_chat_message


class ChatRequest(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str


router = APIRouter()
logger = logging.getLogger(__name__)
client = OllamaClient()


def _build_prompt(user_question: str, context: Dict[str, Any]) -> str:
    instructions = [
        "You are an offline AI NOC Copilot assistant for a network operations center.",
        "Answer using the provided network context and current telemetry. Do not hallucinate.",
        "If the information is unavailable, say it is unavailable clearly.",
        "Support networking, Cisco, routing, switching, SD-WAN, MPLS, TCP/IP, OSI, VLAN, STP, EtherChannel, OSPF, EIGRP, BGP, RIP, QoS, ACL, NAT, VPN, Firewall, DNS, DHCP, Linux, Windows, Python, FastAPI, Machine Learning, Network Security, and troubleshooting.",
        "Include recommended commands and steps when applicable."
    ]

    summary = context.get("summary", "No system context available.")
    recent_alerts = context.get("recent_alerts", [])

    alert_lines = []
    for alert in recent_alerts[-5:]:
        alert_lines.append(f"[{alert.get('timestamp')}] {alert.get('severity')}: {alert.get('root_cause')}.")

    prompt_parts = [
        "System Context:\n", summary,
        "\n\nCurrent Telemetry:\n", json.dumps(context.get("current_telemetry", {}), indent=2),
        "\n\nCurrent RCA:\n", json.dumps(context.get("current_rca", {}), indent=2),
        "\n\nRecent Alerts:\n", "\n".join(alert_lines) if alert_lines else "No recent alerts.",
        "\n\nRecent Incidents:\n", json.dumps(context.get("recent_incidents", []), indent=2),
        "\n\nHistorical Anomalies:\n", json.dumps(context.get("historical_anomalies", []), indent=2),
        "\n\nUser Question:\n", user_question,
        "\n\nAnswer in a concise but professional NOC operator style."
    ]

    return "\n".join(instructions + ["".join(prompt_parts)])


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

    context = build_system_context()
    prompt = _build_prompt(user_question, context)

    print('CHAT REQUEST START', user_question)
    assistant_content = ""
    try:
        print('CALLING OLLAMA CHAT (thread)')
        response_data = await asyncio.to_thread(client.chat, prompt, previous_history)
        print('OLLAMA RESPONSE RECEIVED')

        if isinstance(response_data, dict):
            choices = response_data.get("choices") or []
            for choice in choices:
                if isinstance(choice, dict):
                    message = choice.get("message")
                    if isinstance(message, dict) and message.get("content"):
                        assistant_content += message.get("content")
                    elif choice.get("text"):
                        assistant_content += choice.get("text")
                    elif choice.get("delta") and isinstance(choice.get("delta"), dict):
                        assistant_content += choice["delta"].get("content", "")
        if not assistant_content:
            assistant_content = json.dumps(response_data)
    except Exception as exc:
        error_message = str(exc)
        logger.error('Ollama chat failed: %s', error_message)
        assistant_content = (
            'Unable to fetch assistant response from Ollama. '
            'Please check the Ollama server, model availability, and request timeout settings. '
            f'Error: {error_message}'
        )

    assistant_entry = {"role": "assistant", "content": assistant_content}
    append_chat_message(assistant_entry)
    conversation_history.append(assistant_entry)
    try:
        save_chat_history(conversation_history)
    except Exception as exc:
        logger.error('Failed to save assistant chat history: %s', exc)

    return {"reply": assistant_content}


@router.get("/chat/history")
async def get_chat_history_api():
    return get_chat_history()
