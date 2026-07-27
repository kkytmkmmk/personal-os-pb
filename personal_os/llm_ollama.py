"""Ollama transport used by the local LLM provider.

This module deliberately knows nothing about SQLite or application settings.
The caller supplies the resolved base URL and model name, which keeps provider
selection and safety policy in the application layer.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class OllamaClient:
    """Minimal Ollama native/OpenAI-compatible client for chat and vision."""

    def __init__(self, base_url: str, model: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    @property
    def is_native(self) -> bool:
        return "127.0.0.1:11434" in self.base_url or "localhost:11434" in self.base_url

    @property
    def native_base(self) -> str:
        return self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url

    def chat(
        self,
        messages: list[dict[str, object]],
        response_format: dict | None = None,
        max_predict: int = 1024,
        images: list[bytes] | None = None,
    ) -> str | None:
        if not self.base_url:
            return None
        if self.is_native:
            native_messages = [dict(message) for message in messages]
            if images:
                native_messages[-1]["images"] = [
                    base64.b64encode(image).decode("ascii") for image in images
                ]
            payload: dict[str, object] = {
                "model": self.model,
                "messages": native_messages,
                "stream": False,
                "think": False,
                "options": {"temperature": 0, "num_predict": max_predict},
            }
            if response_format:
                payload["format"] = "json"
            request = urllib.request.Request(
                f"{self.native_base}/api/chat",
                data=_json_bytes(payload),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
            return str(result.get("message", {}).get("content", ""))

        if images:
            raise ValueError("Vision input requires the native Ollama URL")
        payload = {"model": self.model, "messages": messages, "temperature": 0.2}
        if response_format:
            payload["response_format"] = response_format
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=_json_bytes(payload),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        choices = result.get("choices", [])
        return str(choices[0].get("message", {}).get("content", "")) if choices else None

    def unload(self) -> bool:
        """Ask native Ollama to release this model from memory."""
        if not self.is_native:
            return False
        request = urllib.request.Request(
            f"{self.native_base}/api/generate",
            data=_json_bytes({"model": self.model, "keep_alive": 0}),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15):
                return True
        except (urllib.error.HTTPError, urllib.error.URLError):
            return False
