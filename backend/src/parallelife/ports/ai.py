from __future__ import annotations

from abc import ABC, abstractmethod

from parallelife.domain.decision import Decision


class AiDecisionClient(ABC):
    @abstractmethod
    async def decide(self, prompt: str) -> Decision: ...


class SttClient(ABC):
    @abstractmethod
    async def transcribe(self, content: bytes, language_code: str) -> str: ...


class TtsClient(ABC):
    @abstractmethod
    async def synthesize(self, text: str, language_code: str, voice_name: str) -> bytes: ...

