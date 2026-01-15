"""Power Mode configuration model"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class PowerModeConfig:
    """Configuration for a Power Mode profile

    Power Mode allows automatic switching of transcription settings
    based on the currently active application.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # App identification
    app_identifier: str = ""  # WM_CLASS or window class
    display_name: str = ""
    emoji: str = ""  # Visual identifier

    # Transcription settings
    transcription_model: Optional[str] = None
    language: Optional[str] = None

    # AI enhancement
    ai_enhancement_enabled: bool = False
    ai_model: Optional[str] = None
    ai_prompt: Optional[str] = None

    # Behavior
    auto_send_enabled: bool = False  # Press Enter after paste
    is_enabled: bool = True

    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "app_identifier": self.app_identifier,
            "display_name": self.display_name,
            "emoji": self.emoji,
            "transcription_model": self.transcription_model,
            "language": self.language,
            "ai_enhancement_enabled": self.ai_enhancement_enabled,
            "ai_model": self.ai_model,
            "ai_prompt": self.ai_prompt,
            "auto_send_enabled": self.auto_send_enabled,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PowerModeConfig":
        """Create from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            app_identifier=data.get("app_identifier", ""),
            display_name=data.get("display_name", ""),
            emoji=data.get("emoji", ""),
            transcription_model=data.get("transcription_model"),
            language=data.get("language"),
            ai_enhancement_enabled=data.get("ai_enhancement_enabled", False),
            ai_model=data.get("ai_model"),
            ai_prompt=data.get("ai_prompt"),
            auto_send_enabled=data.get("auto_send_enabled", False),
            is_enabled=data.get("is_enabled", True),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


@dataclass
class ActiveWindow:
    """Information about the currently active window"""

    window_id: int = 0
    window_class: str = ""  # WM_CLASS
    window_name: str = ""  # Window title
    process_name: str = ""
    pid: int = 0

    @property
    def app_identifier(self) -> str:
        """Get identifier for matching with PowerModeConfig"""
        # Use window class as primary identifier
        return self.window_class.lower() if self.window_class else ""
