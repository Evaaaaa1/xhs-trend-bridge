"""Minimal OpenAI-compatible chat client (works with Meta Model API, SubQ, DeepSeek, Kimi...)."""
from __future__ import annotations

import json
import os
import re
import urllib.request


class LLM:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "")

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def chat(self, system: str, user: str, temperature: float = 0.7) -> str:
        body = json.dumps({
            "model": self.model,
            "temperature": temperature,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]


def extract_json(text: str):
    """Pull the first JSON object/array out of a model reply (handles ```json fences)."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i != -1], default=-1)
    if start == -1:
        raise ValueError("no JSON in reply")
    return json.loads(text[start:])
