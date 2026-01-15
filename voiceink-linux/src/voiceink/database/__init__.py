"""Database layer for VoiceInk"""

from .connection import Database, get_database
from .repository import TranscriptionRepository

__all__ = [
    "Database",
    "get_database",
    "TranscriptionRepository",
]
