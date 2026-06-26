import json
import logging
import time
import requests
from typing import Dict, Any, List, Optional

from backend.config import (
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_REQUEST_TIMEOUT,
    OLLAMA_RETRIES,
)

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, url: str = OLLAMA_URL, model: str = OLLAMA_MODEL):
        self.url = url.rstrip('/')
        self.model = model

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.url}", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def model_installed(self) -> bool:
        try:
            response = requests.get(f"{self.url}/v1/models", timeout=4)
            if response.status_code != 200:
                return False
            payload = response.json()
            models = payload.get("data", []) if isinstance(payload, dict) else []
            return any(item.get("id") == self.model for item in models)
        except requests.RequestException:
            return False

    def create_prompt_payload(
        self,
        prompt: str,
        conversation: Optional[List[Dict[str, str]]] = None,
        stream: bool = True
    ) -> Dict[str, Any]:
        messages = []
        if conversation:
            for entry in conversation:
                role = entry.get("role", "user")
                messages.append({
                    "role": role,
                    "content": entry.get("content", "")
                })
        messages.append({"role": "user", "content": prompt})
        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "max_tokens": 800,
            "temperature": 0.3,
            "top_p": 0.9,
            "stop": None
        }

    def _log_response_details(self, response: requests.Response, attempt: int) -> None:
        try:
            body = response.text
        except Exception as exc:
            body = f"<unable to read response body: {exc}>"
        logger.error(
            'OLLAMA response attempt %s status=%s body=%s',
            attempt,
            response.status_code,
            body[:2000],
        )

    def _post_with_retries(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
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

                if response.status_code != 200:
                    self._log_response_details(response, attempt)
                    response.raise_for_status()

                return response
            except requests.HTTPError as exc:
                last_exception = exc
                logger.error('Ollama HTTP error on attempt %s: %s', attempt, exc)
            except requests.RequestException as exc:
                last_exception = exc
                logger.error('Ollama request failed on attempt %s: %s', attempt, exc)

            if attempt < max_attempts:
                logger.info('Retrying Ollama request after failure (attempt %s/%s)', attempt, max_attempts)
                time.sleep(1)

        raise RuntimeError(
            f"Ollama request failed after {max_attempts} attempts: {last_exception}"
        )

    def stream_chat(self, prompt: str, conversation: Optional[List[Dict[str, str]]] = None):
        payload = self.create_prompt_payload(prompt, conversation, stream=True)
        url = f"{self.url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}

        logger.info('OLLAMA stream_chat request start %s', url)
        logger.debug('OLLAMA stream_chat payload %s', payload)
        try:
            with requests.post(url, json=payload, headers=headers, stream=True, timeout=(10, OLLAMA_REQUEST_TIMEOUT)) as response:
                logger.info('OLLAMA stream_chat response status %s', response.status_code)
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        yield line
        except requests.HTTPError as exc:
            logger.error("Ollama HTTP error: %s", exc)
            raise
        except requests.RequestException as exc:
            logger.error("Ollama request failed: %s", exc)
            raise

    def chat(self, prompt: str, conversation: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        payload = self.create_prompt_payload(prompt, conversation, stream=False)
        url = f"{self.url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}

        logger.info('OLLAMA chat request start %s', url)
        logger.debug('OLLAMA chat payload %s', payload)
        response = self._post_with_retries(url, payload, headers)

        try:
            result = response.json()
        except ValueError as exc:
            logger.error('Failed to decode Ollama JSON response: %s', exc)
            raise RuntimeError('Ollama returned invalid JSON response.') from exc

        logger.debug('OLLAMA chat parsed response: %s', result)
        return result

    def health_text(self) -> str:
        if not self.is_available():
            return "Ollama server is unavailable. Please start Ollama locally and ensure it is reachable at http://127.0.0.1:11434."
        if not self.model_installed():
            return f"Ollama is running but the model '{self.model}' is not installed. Run 'ollama pull {self.model}' locally."
        return "Ollama local AI assistant is available."
