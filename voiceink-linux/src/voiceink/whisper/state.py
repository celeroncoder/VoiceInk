"""Whisper state management - orchestrates model loading and transcription"""

import logging
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Any
import numpy as np

from .bindings import WhisperContext, WhisperError
from .model_manager import ModelManager, ModelSize, WhisperModel

logger = logging.getLogger(__name__)


class RecordingState(Enum):
    """Recording state machine states"""
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    ENHANCING = "enhancing"
    BUSY = "busy"


@dataclass
class TranscriptionResult:
    """Result of a transcription"""
    text: str
    duration: float
    model_name: str
    language: Optional[str] = None


class WhisperState:
    """Manages whisper model state and transcription workflow

    Thread-safe state manager for whisper context. Handles model loading,
    unloading, and transcription requests.
    """

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        on_state_change: Optional[Callable[[RecordingState], None]] = None,
    ):
        """Initialize whisper state manager

        Args:
            models_dir: Custom models directory
            on_state_change: Callback when recording state changes
        """
        self._model_manager = ModelManager(models_dir)
        self._context: Optional[WhisperContext] = None
        self._current_model: Optional[WhisperModel] = None
        self._state = RecordingState.IDLE
        self._lock = threading.Lock()
        self._on_state_change = on_state_change

        # Configuration
        self._language: Optional[str] = None
        self._initial_prompt: Optional[str] = None
        self._use_gpu: bool = True

    @property
    def state(self) -> RecordingState:
        """Current recording state"""
        return self._state

    @state.setter
    def state(self, value: RecordingState):
        """Set recording state and notify callback"""
        self._state = value
        if self._on_state_change:
            self._on_state_change(value)

    @property
    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded"""
        return self._context is not None and self._context.is_loaded

    @property
    def current_model(self) -> Optional[WhisperModel]:
        """Currently loaded model"""
        return self._current_model

    @property
    def model_manager(self) -> ModelManager:
        """Access the model manager"""
        return self._model_manager

    def set_language(self, language: Optional[str]):
        """Set transcription language (None or 'auto' for auto-detect)"""
        self._language = language if language != "auto" else None
        if self._context:
            self._context.set_language(self._language)

    def set_initial_prompt(self, prompt: Optional[str]):
        """Set initial prompt for transcription context"""
        self._initial_prompt = prompt
        if self._context:
            self._context.set_initial_prompt(self._initial_prompt)

    def set_use_gpu(self, use_gpu: bool):
        """Set whether to use GPU acceleration"""
        self._use_gpu = use_gpu

    def load_model(
        self,
        size: ModelSize = ModelSize.BASE,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """Load a whisper model

        Args:
            size: Model size to load
            progress_callback: Optional download progress callback

        Returns:
            True if model loaded successfully
        """
        with self._lock:
            # Unload existing model
            if self._context:
                self._context.free()
                self._context = None
                self._current_model = None

            try:
                # Ensure model is downloaded
                model_path = self._model_manager.ensure_model(size, progress_callback)

                # Load the context
                self._context = WhisperContext(str(model_path), use_gpu=self._use_gpu)

                # Apply settings
                if self._language:
                    self._context.set_language(self._language)
                if self._initial_prompt:
                    self._context.set_initial_prompt(self._initial_prompt)

                # Update current model info
                self._current_model = self._model_manager.get_model(size)

                logger.info(f"Loaded model: {self._current_model.display_name if self._current_model else size.value}")
                return True

            except (WhisperError, RuntimeError) as e:
                logger.error(f"Failed to load model: {e}")
                return False

    def load_model_from_path(self, model_path: Path) -> bool:
        """Load a model from a specific path

        Args:
            model_path: Path to the model file

        Returns:
            True if loaded successfully
        """
        with self._lock:
            if self._context:
                self._context.free()
                self._context = None
                self._current_model = None

            try:
                self._context = WhisperContext(str(model_path), use_gpu=self._use_gpu)

                if self._language:
                    self._context.set_language(self._language)
                if self._initial_prompt:
                    self._context.set_initial_prompt(self._initial_prompt)

                # Create a custom model entry
                self._current_model = WhisperModel(
                    name=model_path.stem,
                    size=ModelSize.BASE,
                    filename=model_path.name,
                    url="",
                    sha256="",
                    size_mb=int(model_path.stat().st_size / 1024 / 1024),
                    is_downloaded=True,
                    local_path=model_path,
                )

                logger.info(f"Loaded model from: {model_path}")
                return True

            except WhisperError as e:
                logger.error(f"Failed to load model: {e}")
                return False

    def unload_model(self):
        """Unload the current model to free memory"""
        with self._lock:
            if self._context:
                self._context.free()
                self._context = None
                self._current_model = None
                logger.info("Unloaded model")

    def transcribe(
        self,
        samples: np.ndarray,
        translate: bool = False,
    ) -> TranscriptionResult:
        """Transcribe audio samples

        Args:
            samples: Audio samples as float32, mono, 16kHz
            translate: Whether to translate to English

        Returns:
            TranscriptionResult with text and metadata

        Raises:
            WhisperError: If transcription fails
        """
        if not self.is_model_loaded:
            raise WhisperError("No model loaded")

        with self._lock:
            import time
            start_time = time.time()

            old_state = self._state
            self.state = RecordingState.TRANSCRIBING

            try:
                text = self._context.transcribe(
                    samples,
                    translate=translate,
                )

                duration = time.time() - start_time

                return TranscriptionResult(
                    text=text.strip(),
                    duration=duration,
                    model_name=self._current_model.display_name if self._current_model else "unknown",
                    language=self._language,
                )
            finally:
                self.state = old_state

    def transcribe_file(
        self,
        audio_path: Path,
        translate: bool = False,
    ) -> TranscriptionResult:
        """Transcribe an audio file

        Args:
            audio_path: Path to audio file (WAV preferred)
            translate: Whether to translate to English

        Returns:
            TranscriptionResult with text and metadata
        """
        from ..audio.utils import load_audio_file

        samples = load_audio_file(audio_path)
        return self.transcribe(samples, translate=translate)
