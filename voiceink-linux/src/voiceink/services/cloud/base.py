"""Base class for transcription services"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import numpy as np


class TranscriptionError(Exception):
    """Exception raised by transcription services"""
    pass


class ServiceProvider(Enum):
    """Transcription service providers"""
    LOCAL = "local"
    OPENAI = "openai"
    DEEPGRAM = "deepgram"
    GROQ = "groq"
    MISTRAL = "mistral"
    CUSTOM = "custom"


@dataclass
class TranscriptionResult:
    """Result from a transcription service"""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    confidence: Optional[float] = None
    segments: Optional[list] = None
    provider: ServiceProvider = ServiceProvider.LOCAL


class TranscriptionService(ABC):
    """Abstract base class for transcription services

    All transcription services (local and cloud) should inherit from this
    class and implement the required methods.
    """

    @property
    @abstractmethod
    def provider(self) -> ServiceProvider:
        """Get the service provider type"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable service name"""
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the service is properly configured (e.g., has API key)"""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe audio file

        Args:
            audio_path: Path to audio file
            language: Optional language hint
            **kwargs: Additional provider-specific options

        Returns:
            TranscriptionResult with transcribed text

        Raises:
            TranscriptionError: If transcription fails
        """
        pass

    async def transcribe_samples(
        self,
        samples: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe audio samples directly

        Default implementation saves to temp file and calls transcribe().
        Subclasses can override for more efficient handling.

        Args:
            samples: Audio samples as numpy array
            sample_rate: Sample rate of audio
            language: Optional language hint
            **kwargs: Additional provider-specific options

        Returns:
            TranscriptionResult with transcribed text
        """
        import tempfile
        import wave

        # Save samples to temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = Path(f.name)

            # Convert to int16 and write
            audio_int16 = (samples * 32767).astype(np.int16)
            with wave.open(str(temp_path), 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())

        try:
            return await self.transcribe(temp_path, language=language, **kwargs)
        finally:
            temp_path.unlink(missing_ok=True)
