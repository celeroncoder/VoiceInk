"""VoiceInk data models"""

from .transcription import Transcription, TranscriptionStatus
from .vocabulary import VocabularyWord, WordReplacement
from .power_mode import PowerModeConfig, ActiveWindow

__all__ = [
    "Transcription",
    "TranscriptionStatus",
    "VocabularyWord",
    "WordReplacement",
    "PowerModeConfig",
    "ActiveWindow",
]
