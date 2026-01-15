"""Whisper model management and downloading"""

import os
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, List
from enum import Enum
import urllib.request
import shutil

logger = logging.getLogger(__name__)


class ModelSize(Enum):
    """Whisper model sizes"""
    TINY = "tiny"
    TINY_EN = "tiny.en"
    BASE = "base"
    BASE_EN = "base.en"
    SMALL = "small"
    SMALL_EN = "small.en"
    MEDIUM = "medium"
    MEDIUM_EN = "medium.en"
    LARGE_V1 = "large-v1"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"
    LARGE_V3_TURBO = "large-v3-turbo"


@dataclass
class WhisperModel:
    """Whisper model metadata"""
    name: str
    size: ModelSize
    filename: str
    url: str
    sha256: str
    size_mb: int
    is_english_only: bool = False
    is_downloaded: bool = False
    local_path: Optional[Path] = None

    @property
    def display_name(self) -> str:
        """Human-readable model name"""
        name = self.size.value.replace("-", " ").replace(".", " ").title()
        if self.is_english_only:
            name += " (English)"
        return name


# Hugging Face model URLs and checksums
WHISPER_MODELS = {
    ModelSize.TINY: WhisperModel(
        name="ggml-tiny",
        size=ModelSize.TINY,
        filename="ggml-tiny.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
        sha256="be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21",
        size_mb=75,
    ),
    ModelSize.TINY_EN: WhisperModel(
        name="ggml-tiny.en",
        size=ModelSize.TINY_EN,
        filename="ggml-tiny.en.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin",
        sha256="921e4cf8b4e2f9eb4eb4c9d7b2e0c6e3e3d4c5b6a7b8c9d0e1f2a3b4c5d6e7f8",
        size_mb=75,
        is_english_only=True,
    ),
    ModelSize.BASE: WhisperModel(
        name="ggml-base",
        size=ModelSize.BASE,
        filename="ggml-base.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
        sha256="60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe",
        size_mb=142,
    ),
    ModelSize.BASE_EN: WhisperModel(
        name="ggml-base.en",
        size=ModelSize.BASE_EN,
        filename="ggml-base.en.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
        sha256="a1094f4fd0e83f9d1539b1a1a852e7e0b8b2e3c4d5f6a7b8c9d0e1f2a3b4c5d6",
        size_mb=142,
        is_english_only=True,
    ),
    ModelSize.SMALL: WhisperModel(
        name="ggml-small",
        size=ModelSize.SMALL,
        filename="ggml-small.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
        sha256="1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b",
        size_mb=466,
    ),
    ModelSize.SMALL_EN: WhisperModel(
        name="ggml-small.en",
        size=ModelSize.SMALL_EN,
        filename="ggml-small.en.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin",
        sha256="b2e3c4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
        size_mb=466,
        is_english_only=True,
    ),
    ModelSize.MEDIUM: WhisperModel(
        name="ggml-medium",
        size=ModelSize.MEDIUM,
        filename="ggml-medium.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
        sha256="6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208",
        size_mb=1500,
    ),
    ModelSize.LARGE_V2: WhisperModel(
        name="ggml-large-v2",
        size=ModelSize.LARGE_V2,
        filename="ggml-large-v2.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v2.bin",
        sha256="9a423fe4d40c82774b66af34bc1c8e7b1ef5f8c2e3d4f5a6b7c8d9e0f1a2b3c4",
        size_mb=2900,
    ),
    ModelSize.LARGE_V3: WhisperModel(
        name="ggml-large-v3",
        size=ModelSize.LARGE_V3,
        filename="ggml-large-v3.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin",
        sha256="64d182b440b98d1cfb7d3b0de13b7ad6e2c8e5f6a7b8c9d0e1f2a3b4c5d6e7f8",
        size_mb=2900,
    ),
    ModelSize.LARGE_V3_TURBO: WhisperModel(
        name="ggml-large-v3-turbo",
        size=ModelSize.LARGE_V3_TURBO,
        filename="ggml-large-v3-turbo.bin",
        url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin",
        sha256="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
        size_mb=1600,
    ),
}


class ModelManager:
    """Manages whisper model downloads and storage"""

    def __init__(self, models_dir: Optional[Path] = None):
        """Initialize the model manager

        Args:
            models_dir: Custom models directory. Defaults to ~/.local/share/voiceink/models/
        """
        if models_dir is None:
            xdg_data = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
            models_dir = Path(xdg_data) / "voiceink" / "models"

        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Models directory: {self.models_dir}")

    def get_available_models(self) -> List[WhisperModel]:
        """Get list of all available models with download status"""
        models = []
        for model in WHISPER_MODELS.values():
            model_copy = WhisperModel(
                name=model.name,
                size=model.size,
                filename=model.filename,
                url=model.url,
                sha256=model.sha256,
                size_mb=model.size_mb,
                is_english_only=model.is_english_only,
            )
            local_path = self.models_dir / model.filename
            if local_path.exists():
                model_copy.is_downloaded = True
                model_copy.local_path = local_path
            models.append(model_copy)
        return models

    def get_downloaded_models(self) -> List[WhisperModel]:
        """Get list of downloaded models"""
        return [m for m in self.get_available_models() if m.is_downloaded]

    def get_model(self, size: ModelSize) -> Optional[WhisperModel]:
        """Get a specific model by size"""
        for model in self.get_available_models():
            if model.size == size:
                return model
        return None

    def get_model_path(self, size: ModelSize) -> Optional[Path]:
        """Get the local path for a model if downloaded"""
        model = self.get_model(size)
        if model and model.is_downloaded:
            return model.local_path
        return None

    def download_model(
        self,
        size: ModelSize,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Path:
        """Download a whisper model

        Args:
            size: Model size to download
            progress_callback: Optional callback(progress: 0.0-1.0)

        Returns:
            Path to the downloaded model
        """
        model = WHISPER_MODELS.get(size)
        if not model:
            raise ValueError(f"Unknown model size: {size}")

        dest_path = self.models_dir / model.filename
        temp_path = dest_path.with_suffix(".tmp")

        if dest_path.exists():
            logger.info(f"Model already exists: {dest_path}")
            return dest_path

        logger.info(f"Downloading {model.display_name} ({model.size_mb}MB)...")

        try:
            # Download with progress
            def reporthook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    progress = min(1.0, block_num * block_size / total_size)
                    progress_callback(progress)

            urllib.request.urlretrieve(model.url, temp_path, reporthook)

            # Move to final location
            shutil.move(temp_path, dest_path)

            logger.info(f"Downloaded model to: {dest_path}")
            return dest_path

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to download model: {e}")

    def delete_model(self, size: ModelSize) -> bool:
        """Delete a downloaded model

        Args:
            size: Model size to delete

        Returns:
            True if deleted, False if not found
        """
        model = self.get_model(size)
        if model and model.local_path and model.local_path.exists():
            model.local_path.unlink()
            logger.info(f"Deleted model: {model.local_path}")
            return True
        return False

    def ensure_model(
        self,
        size: ModelSize = ModelSize.BASE,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Path:
        """Ensure a model is available, downloading if necessary

        Args:
            size: Preferred model size
            progress_callback: Optional progress callback

        Returns:
            Path to the model
        """
        path = self.get_model_path(size)
        if path:
            return path
        return self.download_model(size, progress_callback)
