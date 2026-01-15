"""Deepgram transcription service"""

import logging
from pathlib import Path
from typing import Optional

import httpx

from .base import (
    TranscriptionService,
    TranscriptionResult,
    TranscriptionError,
    ServiceProvider,
)
from ..credentials import CredentialManager

logger = logging.getLogger(__name__)


class DeepgramTranscriptionService(TranscriptionService):
    """Transcription service using Deepgram API"""

    API_URL = "https://api.deepgram.com/v1/listen"
    DEFAULT_MODEL = "nova-2"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        credential_manager: Optional[CredentialManager] = None,
    ):
        """Initialize Deepgram service

        Args:
            api_key: API key (if not provided, uses credential manager)
            model: Model to use (nova-2, enhanced, base)
            credential_manager: Optional credential manager
        """
        self._api_key = api_key
        self._model = model
        self._creds = credential_manager or CredentialManager()

    @property
    def provider(self) -> ServiceProvider:
        return ServiceProvider.DEEPGRAM

    @property
    def name(self) -> str:
        return "Deepgram"

    @property
    def is_configured(self) -> bool:
        return bool(self._get_api_key())

    def _get_api_key(self) -> Optional[str]:
        """Get API key from instance or credential manager"""
        if self._api_key:
            return self._api_key
        return self._creds.get("deepgram_api_key")

    def set_api_key(self, api_key: str):
        """Set and store API key

        Args:
            api_key: Deepgram API key
        """
        self._api_key = api_key
        self._creds.set("deepgram_api_key", api_key)

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe audio using Deepgram API

        Args:
            audio_path: Path to audio file
            language: Optional language code
            **kwargs: Additional options (punctuate, diarize, smart_format)

        Returns:
            TranscriptionResult with transcribed text

        Raises:
            TranscriptionError: If API call fails
        """
        api_key = self._get_api_key()
        if not api_key:
            raise TranscriptionError("Deepgram API key not configured")

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        # Build query parameters
        params = {
            "model": self._model,
            "punctuate": kwargs.get("punctuate", True),
            "smart_format": kwargs.get("smart_format", True),
        }

        if language:
            params["language"] = language

        if kwargs.get("diarize"):
            params["diarize"] = True

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_path, "rb") as f:
                    audio_data = f.read()

                # Determine content type
                suffix = audio_path.suffix.lower()
                content_types = {
                    ".wav": "audio/wav",
                    ".mp3": "audio/mpeg",
                    ".m4a": "audio/mp4",
                    ".flac": "audio/flac",
                    ".ogg": "audio/ogg",
                }
                content_type = content_types.get(suffix, "audio/wav")

                response = await client.post(
                    self.API_URL,
                    params=params,
                    headers={
                        "Authorization": f"Token {api_key}",
                        "Content-Type": content_type,
                    },
                    content=audio_data,
                )

                if response.status_code != 200:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("err_msg", error_msg)
                    except Exception:
                        pass
                    raise TranscriptionError(f"Deepgram API error: {error_msg}")

                result = response.json()

                # Extract transcript from response
                channels = result.get("results", {}).get("channels", [])
                if channels:
                    alternatives = channels[0].get("alternatives", [])
                    if alternatives:
                        transcript = alternatives[0].get("transcript", "")
                        confidence = alternatives[0].get("confidence")

                        return TranscriptionResult(
                            text=transcript,
                            language=result.get("results", {}).get("metadata", {}).get("language"),
                            confidence=confidence,
                            provider=self.provider,
                        )

                return TranscriptionResult(text="", provider=self.provider)

        except httpx.RequestError as e:
            raise TranscriptionError(f"Network error: {e}")
