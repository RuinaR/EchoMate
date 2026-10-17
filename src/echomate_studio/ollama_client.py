"""Local-only Ollama HTTP interface; no cloud dependencies."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    pass


def chat(messages: list[dict], *, model: str = "qwen3.5:9b-q4_K_M",
         base_url: str = "http://127.0.0.1:11434", timeout: float = 120.0,
         temperature: float = 0.7, max_tokens: int = 180) -> str:
    if not messages or any(m.get("role") not in {"system", "user", "assistant"} or
                           not isinstance(m.get("content"), str) for m in messages):
        raise ValueError("messages must be nonempty chat role/content objects")
    if not (base_url.startswith("http://127.0.0.1:") or base_url.startswith("http://localhost:")):
        raise ValueError("only local Ollama endpoints are permitted")
    if not 0 <= temperature <= 2 or max_tokens < 1:
        raise ValueError("invalid generation parameters")
    body = json.dumps({
        "model": model, "messages": messages, "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }).encode("utf-8")
    req = Request(base_url.rstrip("/") + "/api/chat", data=body,
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as response:
            obj = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise OllamaError(f"local Ollama request failed ({type(exc).__name__})") from exc
    answer = obj.get("message", {}).get("content")
    if not isinstance(answer, str):
        raise OllamaError("Ollama returned no text response")
    return answer
