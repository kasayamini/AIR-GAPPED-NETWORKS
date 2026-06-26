
from backend.main import app
from fastapi.testclient import TestClient
from backend.ollama_client import OllamaClient
import time

orig_chat = OllamaClient.chat
def stub_chat(self, prompt, conversation=None):
    return {"choices": [{"index": 0, "message": {"role": "assistant", "content": "Stubbed response: backend route works."}, "finish_reason": "stop"}]}
OllamaClient.chat = stub_chat

print('starting TestClient POST with stubbed OllamaClient.chat')
start = time.perf_counter()
with TestClient(app) as client:
    r = client.post('/api/chat', json={'question': 'Are you alive?'}, timeout=30)
    print('status', r.status_code)
    print('text', r.text)
print('elapsed', time.perf_counter() - start)
