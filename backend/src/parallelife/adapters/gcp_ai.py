from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass

import anyio
import google.auth
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
import httpx

from parallelife.domain.decision import Decision
from parallelife.ports.ai import AiDecisionClient


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(text: str) -> str:
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text.strip())
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        raise ValueError(f"Gemini response did not contain a JSON object. Raw: {text[:500]}")
    return match.group(0)


@dataclass
class _TokenCache:
    token: str | None = None
    expires_at_epoch: float = 0.0

    def valid(self) -> bool:
        return bool(self.token) and time.time() < self.expires_at_epoch - 30


class VertexAIGeminiDecisionClient(AiDecisionClient):
    def __init__(
        self,
        *,
        project_id: str,
        location: str,
        model: str,
        temperature: float = 1.0,
        max_output_tokens: int = 1024,
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._model = model
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._creds: Credentials | None = None
        self._token_cache = _TokenCache()

    def _get_creds(self) -> Credentials:
        if self._creds is None:
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            self._creds = creds
        return self._creds

    async def _get_bearer_token(self) -> str:
        if self._token_cache.valid():
            return self._token_cache.token or ""

        def _refresh() -> tuple[str, float]:
            creds = self._get_creds()
            creds.refresh(Request())
            token = creds.token
            expiry = getattr(creds, "expiry", None)
            if token is None:
                raise RuntimeError("Failed to refresh GCP access token.")
            expires_at = float(getattr(expiry, "timestamp", lambda: time.time() + 300)())
            return token, expires_at

        token, expires_at = await anyio.to_thread.run_sync(_refresh)
        self._token_cache.token = token
        self._token_cache.expires_at_epoch = expires_at
        return token

    async def decide(self, prompt: str) -> Decision:
        token = await self._get_bearer_token()
        url = (
            f"https://{self._location}-aiplatform.googleapis.com/v1/"
            f"projects/{self._project_id}/locations/{self._location}/publishers/google/"
            f"models/{self._model}:generateContent"
        )

        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_output_tokens,
                # Force structured JSON output — supported by Gemini 2.0+
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Vertex AI returned no candidates: {json.dumps(data)[:1000]}")

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []

        # Find the last non-thinking text part (Gemini 2.5 may emit thought parts first)
        text = None
        for part in reversed(parts):
            if "text" in part and not part.get("thought"):
                text = str(part["text"])
                break

        if text is None:
            raise RuntimeError(f"Vertex AI response missing text part: {json.dumps(data)[:1000]}")

        json_text = _extract_json_object(text)
        return Decision.model_validate_json(json_text)
