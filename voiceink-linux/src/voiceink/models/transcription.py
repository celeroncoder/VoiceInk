"""Transcription data model"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import uuid


class TranscriptionStatus(Enum):
    """Status of a transcription"""
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Transcription:
    """Transcription record"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    enhanced_text: Optional[str] = None
    duration: float = 0.0
    audio_file_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Status
    status: TranscriptionStatus = TranscriptionStatus.PENDING

    # Model info
    transcription_model_name: Optional[str] = None
    transcription_duration: Optional[float] = None
    ai_enhancement_model_name: Optional[str] = None
    enhancement_duration: Optional[float] = None
    prompt_name: Optional[str] = None

    # Power mode info
    power_mode_name: Optional[str] = None
    power_mode_emoji: Optional[str] = None

    # AI request details (for debugging)
    ai_request_system_message: Optional[str] = None
    ai_request_user_message: Optional[str] = None

    @property
    def final_text(self) -> str:
        """Get the final text (enhanced if available, otherwise raw)"""
        return self.enhanced_text if self.enhanced_text else self.text

    @property
    def audio_path(self) -> Optional[Path]:
        """Get audio file path as Path object"""
        if self.audio_file_path:
            return Path(self.audio_file_path)
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "text": self.text,
            "enhanced_text": self.enhanced_text,
            "duration": self.duration,
            "audio_file_path": self.audio_file_path,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "transcription_model_name": self.transcription_model_name,
            "transcription_duration": self.transcription_duration,
            "ai_enhancement_model_name": self.ai_enhancement_model_name,
            "enhancement_duration": self.enhancement_duration,
            "prompt_name": self.prompt_name,
            "power_mode_name": self.power_mode_name,
            "power_mode_emoji": self.power_mode_emoji,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transcription":
        """Create from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            text=data.get("text", ""),
            enhanced_text=data.get("enhanced_text"),
            duration=data.get("duration", 0.0),
            audio_file_path=data.get("audio_file_path"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            status=TranscriptionStatus(data.get("status", "pending")),
            transcription_model_name=data.get("transcription_model_name"),
            transcription_duration=data.get("transcription_duration"),
            ai_enhancement_model_name=data.get("ai_enhancement_model_name"),
            enhancement_duration=data.get("enhancement_duration"),
            prompt_name=data.get("prompt_name"),
            power_mode_name=data.get("power_mode_name"),
            power_mode_emoji=data.get("power_mode_emoji"),
        )
