from __future__ import annotations

import anyio
from google.cloud import speech, texttospeech

from parallelife.ports.ai import SttClient, TtsClient


class CloudSpeechSttClient(SttClient):
    def __init__(self) -> None:
        self._client = speech.SpeechClient()

    async def transcribe(self, content: bytes, language_code: str) -> str:
        def _run() -> str:
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                language_code=language_code,
                enable_automatic_punctuation=True,
            )
            resp = self._client.recognize(config=config, audio=audio)
            return " ".join([r.alternatives[0].transcript for r in resp.results if r.alternatives])

        return await anyio.to_thread.run_sync(_run)


class CloudTextToSpeechClient(TtsClient):
    def __init__(self) -> None:
        self._client = texttospeech.TextToSpeechClient()

    async def synthesize(self, text: str, language_code: str, voice_name: str) -> bytes:
        def _run() -> bytes:
            input_text = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
            resp = self._client.synthesize_speech(
                input=input_text,
                voice=voice,
                audio_config=audio_config,
            )
            return bytes(resp.audio_content)

        return await anyio.to_thread.run_sync(_run)

