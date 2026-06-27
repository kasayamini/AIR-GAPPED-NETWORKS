import logging
import time
from typing import Dict, Any, List, Optional

import requests

from backend.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_REQUEST_TIMEOUT,
    OLLAMA_RETRIES,
)

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, url: Optional[str] = None, model: str = OLLAMA_MODEL):
        configured_url = (url or OLLAMA_BASE_URL or "http://127.0.0.1:11434").strip()
        self.url = configured_url.rstrip("/") if configured_url else None
        self.model = model

    def is_available(self) -> bool:
        if not self.url:
            return False
        try:
            response = requests.get(self.url, timeout=2)
            return response.status_code < 500
        except requests.RequestException:
            return False

    def model_installed(self) -> bool:
        if not self.url:
            return False
        try:
            response = requests.get(f"{self.url}/v1/models", timeout=4)
            if response.status_code != 200:
                return False
            payload = response.json()
            models = payload.get("data", []) if isinstance(payload, dict) else []
            return any(item.get("id") == self.model for item in models)
        except (requests.RequestException, ValueError):
            return False

    def _chat_targets(self) -> List[Dict[str, str]]:
        if not self.url:
            return []
        return [
            {"url": f"{self.url}/v1/chat/completions", "format": "messages"},
            {"url": f"{self.url}/api/chat", "format": "input"},
        ]

    def _create_payload(
        self,
        prompt: str,
        conversation: Optional[List[Dict[str, str]]],
        stream: bool,
        fmt: str,
    ) -> Dict[str, Any]:
        if fmt == "input":
            payload = {
                "model": self.model,
                "input": prompt,
                "stream": stream,
                "max_tokens": 800,
                "temperature": 0.3,
                "top_p": 0.9,
            }
            if conversation:
                payload["conversation"] = [
                    {"role": entry.get("role", "user"), "content": entry.get("content", "")} for entry in conversation
                ]
            return payload

        messages = []
        if conversation:
            for entry in conversation:
                messages.append({
                    "role": entry.get("role", "user"),
                    "content": entry.get("content", ""),
                })
        messages.append({"role": "user", "content": prompt})
        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "max_tokens": 800,
            "temperature": 0.3,
            "top_p": 0.9,
        }

    def _log_response_details(self, response: requests.Response, url: str, attempt: int) -> None:
        try:
            body = response.text
        except Exception as exc:
            body = f"<unable to read response body: {exc}>"
        logger.error(
            'OLLAMA response attempt %s url=%s status=%s body=%s',
            attempt,
            url,
            response.status_code,
            body[:2000],
        )

    def _post_with_retries(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        if not self.url:
            raise RuntimeError("Ollama base URL is not configured. Set OLLAMA_BASE_URL.")

        max_attempts = OLLAMA_RETRIES + 1
        last_exception = None

        for attempt in range(1, max_attempts + 1):
            logger.info('OLLAMA request attempt %s/%s to %s', attempt, max_attempts, url)
            logger.debug('OLLAMA request payload attempt %s: %s', attempt, payload)

            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=(10, OLLAMA_REQUEST_TIMEOUT),
                )
                logger.info('OLLAMA response attempt %s status %s', attempt, response.status_code)
                logger.debug('OLLAMA response body attempt %s: %s', attempt, response.text[:2000])

                if response.status_code in (404, 405):
                    raise RuntimeError(f"Endpoint {url} not supported by Ollama.")

                if response.status_code != 200:
                    self._log_response_details(response, url, attempt)
                    response.raise_for_status()

                return response
            except requests.HTTPError as exc:
                last_exception = exc
                logger.error('Ollama HTTP error on attempt %s: %s', attempt, exc)
            except requests.RequestException as exc:
                last_exception = exc
                logger.error('Ollama request failed on attempt %s: %s', attempt, exc)
            except RuntimeError as exc:
                last_exception = exc
                logger.info('Ollama endpoint error on attempt %s: %s', attempt, exc)
                break

            if attempt < max_attempts:
                logger.info('Retrying Ollama request after failure (attempt %s/%s)', attempt, max_attempts)
                time.sleep(1)

        raise RuntimeError(
            f"Ollama request failed after {max_attempts} attempts: {last_exception}"
        )

    def _try_chat_endpoints(self, prompt: str, conversation: Optional[List[Dict[str, str]]], stream: bool):
        headers = {"Content-Type": "application/json"}
        last_exception = None

        for target in self._chat_targets():
            payload = self._create_payload(prompt, conversation, stream, target["format"])
            try:
                return self._post_with_retries(target["url"], payload, headers)
            except Exception as exc:
                last_exception = exc
                logger.warning('Ollama endpoint %s failed: %s', target["url"], exc)
                continue

        raise RuntimeError(f"Ollama request failed on all endpoints: {last_exception}")

    def _fallback_reply(self, prompt: str) -> str:
        normalized = prompt.lower()
        details = []

        if any(token in normalized for token in ["alert", "incident", "severity", "critical", "down", "outage"]):
            details.append(
                "Check active alerts and incident summaries, prioritize the highest severity items, "
                "and correlate them with the latest telemetry to isolate the impacted device or link."
            )
        if any(token in normalized for token in ["latency", "packet loss", "jitter", "bandwidth", "throughput", "delay"]):
            details.append(
                "Investigate WAN latency and packet loss, confirm QoS policies, and verify whether any overloaded or misconfigured interfaces are contributing to performance issues."
            )
        if any(token in normalized for token in ["config", "acl", "routing", "bgp", "ospf", "interface"]):
            details.append(
                "Review routing adjacency, ACL state, and interface configuration against the expected network design."
            )
        if not details:
            details.append(
                "The local model service is unavailable. Use current telemetry, alerts, and incident summaries to verify device health, routing, and security policy state."
            )

        return " ".join(details)

    def stream_chat(self, prompt: str, conversation: Optional[List[Dict[str, str]]] = None):
        if not self.url:
            yield self._fallback_reply(prompt)
            return

        last_error = None
        headers = {"Content-Type": "application/json"}

        for target in self._chat_targets():
            payload = self._create_payload(prompt, conversation, True, target["format"])
            try:
                with requests.post(target["url"], json=payload, headers=headers, stream=True, timeout=(10, OLLAMA_REQUEST_TIMEOUT)) as response:
                    logger.info('OLLAMA stream_chat response status %s', response.status_code)
                    if response.status_code in (404, 405):
                        continue
                    response.raise_for_status()
                    for line in response.iter_lines(decode_unicode=True):
                        if line:
                            yield line
                    return
            except requests.RequestException as exc:
                last_error = exc
                logger.warning('Ollama stream endpoint %s failed: %s', target["url"], exc)
                continue

        yield self._fallback_reply(prompt)
        logger.error('Ollama stream request failed on all endpoints: %s', last_error)

    def chat(self, prompt: str, conversation: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        if not self.url:
            return {
                "choices": [
                    {
                        "message": {
                            "content": self._fallback_reply(prompt)
                        }
                    }
                ]
            }

        last_error = None
        response = None
        for target in self._chat_targets():
            try:
                response = self._post_with_retries(target["url"], self._create_payload(prompt, conversation, False, target["format"]), {"Content-Type": "application/json"})
                break
            except Exception as exc:
                last_error = exc
                logger.warning('Ollama chat endpoint %s failed: %s', target["url"], exc)
                continue

        if response is None:
            logger.error('Ollama chat failed on all endpoints: %s', last_error)
            return {
                "choices": [
                    {
                        "message": {
                            "content": self._fallback_reply(prompt)
                        }
                    }
                ]
            }

        try:
            result = response.json()
        except ValueError as exc:
            logger.error('Failed to decode Ollama JSON response: %s', exc)
            return {
                "choices": [
                    {
                        "message": {
                            "content": self._fallback_reply(prompt)
                        }
                    }
                ]
            }

        if not isinstance(result, dict):
            return {
                "choices": [
                    {
                        "message": {
                            "content": self._fallback_reply(prompt)
                        }
                    }
                ]
            }

        return result

    def health_text(self) -> str:
        if not self.url:
            return "Ollama backend is not configured. Set OLLAMA_BASE_URL to a reachable local model host."
        if not self.is_available():
            return f"Ollama backend at {self.url} is unreachable."
        if not self.model_installed():
            return f"Ollama backend is reachable but the model '{self.model}' is not installed."
        return "Ollama model service is available."
