"""VoiceInk services module"""

from .local_transcription import LocalTranscriptionService
from .history_service import HistoryService

__all__ = [
    "LocalTranscriptionService",
    "HistoryService",
]
