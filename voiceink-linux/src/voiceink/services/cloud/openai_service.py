"""OpenAI Whisper API transcription service"""

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


class OpenAITranscriptionService(TranscriptionService):
    """Transcription service using OpenAI Whisper API"""

    API_URL = "https://api.openai.com/v1/audio/transcriptions"
    DEFAULT_MODEL = "whisper-1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        credential_manager: Optional[CredentialManager] = None,
    ):
        """Initialize OpenAI service

        Args:
            api_key: API key (if not provided, uses credential manager)
            model: Whisper model to use
            credential_manager: Optional credential manager
        """
        self._api_key = api_key
        self._model = model
        self._creds = credential_manager or CredentialManager()

    @property
    def provider(self) -> ServiceProvider:
        return ServiceProvider.OPENAI

    @property
    def name(self) -> str:
        return "OpenAI Whisper"

    @property
    def is_configured(self) -> bool:
        return bool(self._get_api_key())

    def _get_api_key(self) -> Optional[str]:
        """Get API key from instance or credential manager"""
        if self._api_key:
            return self._api_key
        return self._creds.get("openai_api_key")

    def set_api_key(self, api_key: str):
        """Set and store API key

        Args:
            api_key: OpenAI API key
        """
        self._api_key = api_key
        self._creds.set("openai_api_key", api_key)

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe audio using OpenAI Whisper API

        Args:
            audio_path: Path to audio file
            language: Optional language code (ISO 639-1)
            **kwargs: Additional options (response_format, temperature, prompt)

        Returns:
            TranscriptionResult with transcribed text

        Raises:
            TranscriptionError: If API call fails
        """
        api_key = self._get_api_key()
        if not api_key:
            raise TranscriptionError("OpenAI API key not configured")

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        # Build request data
        data = {
            "model": self._model,
        }

        if language:
            data["language"] = language

        # Add optional parameters
        for key in ["response_format", "temperature", "prompt"]:
            if key in kwargs:
                data[key] = kwargs[key]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_path, "rb") as f:
                    response = await client.post(
                        self.API_URL,
                        headers={"Authorization": f"Bearer {api_key}"},
                        data=data,
                        files={"file": (audio_path.name, f, "audio/wav")},
                    )

                if response.status_code != 200:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", error_msg)
                    except Exception:
                        pass
                    raise TranscriptionError(f"OpenAI API error: {error_msg}")

                result = response.json()

                return TranscriptionResult(
                    text=result.get("text", ""),
                    language=result.get("language"),
                    provider=self.provider,
                )

        except httpx.RequestError as e:
            raise TranscriptionError(f"Network error: {e}")
