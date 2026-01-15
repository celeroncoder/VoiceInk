"""Local transcription service using whisper.cpp"""

import logging
from pathlib import Path
from typing import Optional, Callable

from ..whisper import WhisperState, WhisperError
from ..whisper.model_manager import ModelSize
from ..audio.utils import load_audio_file

logger = logging.getLogger(__name__)


class LocalTranscriptionService:
    """Service for local transcription using whisper.cpp

    Provides a high-level interface for transcribing audio files
    using the local whisper model.
    """

    def __init__(
        self,
        whisper_state: Optional[WhisperState] = None,
        models_dir: Optional[Path] = None,
    ):
        """Initialize the transcription service

        Args:
            whisper_state: Existing WhisperState to use, or creates new one
            models_dir: Custom models directory
        """
        self._state = whisper_state or WhisperState(models_dir)
        self._is_configured = False

    @property
    def whisper_state(self) -> WhisperState:
        """Access the underlying whisper state"""
        return self._state

    @property
    def is_model_loaded(self) -> bool:
        """Check if a model is loaded and ready"""
        return self._state.is_model_loaded

    def configure(
        self,
        model_size: ModelSize = ModelSize.BASE,
        language: Optional[str] = None,
        use_gpu: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """Configure and load the transcription model

        Args:
            model_size: Whisper model size to use
            language: Language code or None for auto-detect
            use_gpu: Whether to use GPU acceleration
            progress_callback: Optional callback for download progress

        Returns:
            True if configuration succeeded
        """
        self._state.set_language(language)
        self._state.set_use_gpu(use_gpu)

        if self._state.load_model(model_size, progress_callback):
            self._is_configured = True
            return True
        return False

    def transcribe(
        self,
        audio_path: Path,
        initial_prompt: Optional[str] = None,
        translate: bool = False,
    ) -> str:
        """Transcribe an audio file

        Args:
            audio_path: Path to the audio file
            initial_prompt: Optional prompt for context
            translate: Whether to translate to English

        Returns:
            Transcribed text

        Raises:
            WhisperError: If transcription fails
            FileNotFoundError: If audio file not found
        """
        if not self._state.is_model_loaded:
            raise WhisperError("Model not loaded. Call configure() first.")

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Set prompt if provided
        if initial_prompt:
            self._state.set_initial_prompt(initial_prompt)

        # Load and transcribe
        samples = load_audio_file(audio_path)
        result = self._state.transcribe(samples, translate=translate)

        # Clear prompt after use
        if initial_prompt:
            self._state.set_initial_prompt(None)

        return result.text

    def transcribe_samples(
        self,
        samples,
        initial_prompt: Optional[str] = None,
        translate: bool = False,
    ) -> str:
        """Transcribe audio samples directly

        Args:
            samples: Audio samples as float32 numpy array (16kHz mono)
            initial_prompt: Optional prompt for context
            translate: Whether to translate to English

        Returns:
            Transcribed text
        """
        if not self._state.is_model_loaded:
            raise WhisperError("Model not loaded. Call configure() first.")

        if initial_prompt:
            self._state.set_initial_prompt(initial_prompt)

        result = self._state.transcribe(samples, translate=translate)

        if initial_prompt:
            self._state.set_initial_prompt(None)

        return result.text

    def unload(self):
        """Unload the model to free memory"""
        self._state.unload_model()
        self._is_configured = False
