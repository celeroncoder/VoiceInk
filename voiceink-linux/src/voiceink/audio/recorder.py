"""Audio recorder for capturing microphone input"""

import logging
import threading
import time
import wave
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Callable
import numpy as np

from .device_manager import DeviceManager, AudioDevice, HAS_SOUNDDEVICE

if HAS_SOUNDDEVICE:
    import sounddevice as sd

logger = logging.getLogger(__name__)

# Whisper expects 16kHz mono float32
WHISPER_SAMPLE_RATE = 16000
WHISPER_CHANNELS = 1
WHISPER_DTYPE = np.float32


class RecorderState(Enum):
    """Recorder state"""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"


@dataclass
class RecordingConfig:
    """Recording configuration"""
    sample_rate: int = WHISPER_SAMPLE_RATE
    channels: int = WHISPER_CHANNELS
    dtype: type = WHISPER_DTYPE
    device_id: Optional[int] = None  # None = default device


class AudioRecorder:
    """Records audio from microphone

    Features:
    - Start/stop/pause recording
    - Real-time audio level metering
    - Device selection
    - Automatic resampling to 16kHz for Whisper
    - WAV file export
    """

    def __init__(
        self,
        device_manager: Optional[DeviceManager] = None,
        on_level_change: Optional[Callable[[float], None]] = None,
        on_state_change: Optional[Callable[[RecorderState], None]] = None,
    ):
        """Initialize the recorder

        Args:
            device_manager: Optional device manager, creates new one if None
            on_level_change: Callback for audio level updates (0.0-1.0)
            on_state_change: Callback for state changes
        """
        self._device_manager = device_manager or DeviceManager()
        self._on_level_change = on_level_change
        self._on_state_change = on_state_change

        self._state = RecorderState.IDLE
        self._config = RecordingConfig()
        self._stream: Optional["sd.InputStream"] = None
        self._lock = threading.Lock()

        # Recording buffer
        self._chunks: list[np.ndarray] = []
        self._chunk_lock = threading.Lock()

        # Level metering
        self._current_level: float = 0.0
        self._peak_level: float = 0.0

        # Recording metadata
        self._start_time: Optional[float] = None
        self._actual_sample_rate: int = WHISPER_SAMPLE_RATE

    @property
    def state(self) -> RecorderState:
        """Current recorder state"""
        return self._state

    @state.setter
    def state(self, value: RecorderState):
        """Set state and notify callback"""
        self._state = value
        if self._on_state_change:
            self._on_state_change(value)

    @property
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self._state == RecorderState.RECORDING

    @property
    def is_paused(self) -> bool:
        """Check if recording is paused"""
        return self._state == RecorderState.PAUSED

    @property
    def current_level(self) -> float:
        """Current audio level (0.0-1.0)"""
        return self._current_level

    @property
    def peak_level(self) -> float:
        """Peak audio level since recording started"""
        return self._peak_level

    @property
    def duration(self) -> float:
        """Current recording duration in seconds"""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def device_manager(self) -> DeviceManager:
        """Access the device manager"""
        return self._device_manager

    def configure(
        self,
        sample_rate: int = WHISPER_SAMPLE_RATE,
        channels: int = WHISPER_CHANNELS,
        device_id: Optional[int] = None,
    ):
        """Configure recording parameters

        Args:
            sample_rate: Target sample rate (will resample if device differs)
            channels: Number of channels (1 for mono)
            device_id: Device ID or None for default
        """
        self._config = RecordingConfig(
            sample_rate=sample_rate,
            channels=channels,
            device_id=device_id,
        )

    def start(self) -> bool:
        """Start recording

        Returns:
            True if recording started successfully
        """
        if not HAS_SOUNDDEVICE:
            logger.error("sounddevice not available")
            return False

        with self._lock:
            if self._state == RecorderState.RECORDING:
                logger.warning("Already recording")
                return False

            # Clear previous recording
            with self._chunk_lock:
                self._chunks.clear()

            self._current_level = 0.0
            self._peak_level = 0.0
            self._start_time = time.time()

            # Determine device and sample rate
            device_id = self._config.device_id
            if device_id is None:
                device = self._device_manager.default_device
                device_id = device.id if device else None

            # Get device's native sample rate
            if device_id is not None:
                device_info = sd.query_devices(device_id)
                self._actual_sample_rate = int(device_info.get("default_samplerate", 48000))
            else:
                self._actual_sample_rate = 48000  # Common default

            try:
                self._stream = sd.InputStream(
                    device=device_id,
                    samplerate=self._actual_sample_rate,
                    channels=self._config.channels,
                    dtype=np.float32,
                    callback=self._audio_callback,
                    blocksize=1024,
                )
                self._stream.start()
                self.state = RecorderState.RECORDING
                logger.info(f"Recording started (device={device_id}, sr={self._actual_sample_rate})")
                return True

            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                return False

    def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return audio samples

        Returns:
            Audio samples as float32 numpy array (16kHz mono), or None if failed
        """
        with self._lock:
            if self._state == RecorderState.IDLE:
                logger.warning("Not recording")
                return None

            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.error(f"Error stopping stream: {e}")
                self._stream = None

            self.state = RecorderState.IDLE
            self._current_level = 0.0

        # Combine chunks
        with self._chunk_lock:
            if not self._chunks:
                logger.warning("No audio recorded")
                return None

            audio = np.concatenate(self._chunks)
            self._chunks.clear()

        # Resample if needed
        if self._actual_sample_rate != self._config.sample_rate:
            audio = self._resample(audio, self._actual_sample_rate, self._config.sample_rate)

        duration = len(audio) / self._config.sample_rate
        logger.info(f"Recording stopped ({duration:.2f}s)")

        return audio

    def pause(self):
        """Pause recording"""
        with self._lock:
            if self._state == RecorderState.RECORDING and self._stream:
                self._stream.stop()
                self.state = RecorderState.PAUSED
                logger.info("Recording paused")

    def resume(self):
        """Resume recording"""
        with self._lock:
            if self._state == RecorderState.PAUSED and self._stream:
                self._stream.start()
                self.state = RecorderState.RECORDING
                logger.info("Recording resumed")

    def cancel(self):
        """Cancel recording and discard audio"""
        with self._lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

            with self._chunk_lock:
                self._chunks.clear()

            self.state = RecorderState.IDLE
            self._current_level = 0.0
            logger.info("Recording cancelled")

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Callback for audio input stream"""
        if status:
            logger.warning(f"Audio callback status: {status}")

        if self._state != RecorderState.RECORDING:
            return

        # Store chunk
        with self._chunk_lock:
            self._chunks.append(indata.copy().flatten())

        # Calculate level (RMS)
        rms = np.sqrt(np.mean(indata ** 2))
        # Convert to 0-1 range (assuming max is ~1.0 for float32)
        level = min(1.0, rms * 3)  # Scale up for better visualization

        self._current_level = level
        self._peak_level = max(self._peak_level, level)

        if self._on_level_change:
            self._on_level_change(level)

    def _resample(self, audio: np.ndarray, from_sr: int, to_sr: int) -> np.ndarray:
        """Resample audio to target sample rate

        Args:
            audio: Input audio samples
            from_sr: Source sample rate
            to_sr: Target sample rate

        Returns:
            Resampled audio
        """
        if from_sr == to_sr:
            return audio

        try:
            # Try scipy for high-quality resampling
            from scipy import signal
            num_samples = int(len(audio) * to_sr / from_sr)
            resampled = signal.resample(audio, num_samples)
            return resampled.astype(np.float32)
        except ImportError:
            # Fallback to simple linear interpolation
            ratio = to_sr / from_sr
            new_length = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_length)
            resampled = np.interp(indices, np.arange(len(audio)), audio)
            return resampled.astype(np.float32)

    def save_wav(self, audio: np.ndarray, path: Path) -> bool:
        """Save audio to WAV file

        Args:
            audio: Audio samples (float32)
            path: Output file path

        Returns:
            True if saved successfully
        """
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Convert float32 to int16
            audio_int16 = (audio * 32767).astype(np.int16)

            with wave.open(str(path), 'w') as wf:
                wf.setnchannels(self._config.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self._config.sample_rate)
                wf.writeframes(audio_int16.tobytes())

            logger.info(f"Saved WAV: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save WAV: {e}")
            return False

    @staticmethod
    def load_wav(path: Path) -> Optional[np.ndarray]:
        """Load audio from WAV file

        Args:
            path: Path to WAV file

        Returns:
            Audio samples as float32, or None if failed
        """
        try:
            with wave.open(str(path), 'r') as wf:
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16)
                audio = audio.astype(np.float32) / 32767.0
                return audio
        except Exception as e:
            logger.error(f"Failed to load WAV: {e}")
            return None
