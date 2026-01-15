"""Audio utility functions"""

import logging
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Whisper expects 16kHz mono audio
WHISPER_SAMPLE_RATE = 16000


def load_audio_file(
    audio_path: Path,
    target_sample_rate: int = WHISPER_SAMPLE_RATE,
) -> np.ndarray:
    """Load an audio file and convert to format expected by whisper

    Args:
        audio_path: Path to audio file
        target_sample_rate: Target sample rate (default 16000 for whisper)

    Returns:
        Audio samples as float32 numpy array, mono, normalized
    """
    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    suffix = audio_path.suffix.lower()

    # Try to load WAV directly first
    if suffix == ".wav":
        try:
            return _load_wav(audio_path, target_sample_rate)
        except Exception as e:
            logger.debug(f"Direct WAV load failed, trying ffmpeg: {e}")

    # Use ffmpeg for conversion
    return _load_with_ffmpeg(audio_path, target_sample_rate)


def _load_wav(audio_path: Path, target_sample_rate: int) -> np.ndarray:
    """Load a WAV file directly"""
    with wave.open(str(audio_path), "rb") as wav:
        sample_rate = wav.getframerate()
        n_channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        n_frames = wav.getnframes()

        # Read raw audio data
        raw_data = wav.readframes(n_frames)

    # Convert to numpy array based on sample width
    if sample_width == 1:
        dtype = np.uint8
        max_val = 128.0
        offset = 128
    elif sample_width == 2:
        dtype = np.int16
        max_val = 32768.0
        offset = 0
    elif sample_width == 4:
        dtype = np.int32
        max_val = 2147483648.0
        offset = 0
    else:
        raise ValueError(f"Unsupported sample width: {sample_width}")

    samples = np.frombuffer(raw_data, dtype=dtype).astype(np.float32)

    # Apply offset for unsigned types
    if offset:
        samples = samples - offset

    # Normalize to [-1, 1]
    samples = samples / max_val

    # Convert to mono if stereo
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    # Resample if necessary
    if sample_rate != target_sample_rate:
        samples = _resample(samples, sample_rate, target_sample_rate)

    return samples.astype(np.float32)


def _load_with_ffmpeg(audio_path: Path, target_sample_rate: int) -> np.ndarray:
    """Load audio file using ffmpeg for conversion"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp_path = tmp.name

        # Convert to 16kHz mono WAV using ffmpeg
        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-ar", str(target_sample_rate),
            "-ac", "1",  # mono
            "-f", "wav",
            "-acodec", "pcm_s16le",
            "-y",  # overwrite
            tmp_path,
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"ffmpeg conversion failed: {e.stderr.decode()}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Please install: sudo apt install ffmpeg"
            )

        # Load the converted file
        return _load_wav(Path(tmp_path), target_sample_rate)


def _resample(samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Simple resampling using linear interpolation"""
    if orig_sr == target_sr:
        return samples

    duration = len(samples) / orig_sr
    target_length = int(duration * target_sr)

    # Create interpolation indices
    indices = np.linspace(0, len(samples) - 1, target_length)

    # Linear interpolation
    lower = np.floor(indices).astype(int)
    upper = np.ceil(indices).astype(int)
    upper = np.clip(upper, 0, len(samples) - 1)

    frac = indices - lower
    resampled = samples[lower] * (1 - frac) + samples[upper] * frac

    return resampled


def convert_to_16khz_mono(
    input_path: Path,
    output_path: Optional[Path] = None,
) -> Path:
    """Convert an audio file to 16kHz mono WAV

    Args:
        input_path: Input audio file
        output_path: Output path (default: same name with _16k suffix)

    Returns:
        Path to converted file
    """
    input_path = Path(input_path)

    if output_path is None:
        output_path = input_path.with_stem(input_path.stem + "_16k").with_suffix(".wav")

    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-ar", str(WHISPER_SAMPLE_RATE),
        "-ac", "1",
        "-f", "wav",
        "-acodec", "pcm_s16le",
        "-y",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path
