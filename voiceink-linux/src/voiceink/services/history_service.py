"""Service for managing transcription history"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from ..database import TranscriptionRepository, get_database
from ..models.transcription import Transcription, TranscriptionStatus

logger = logging.getLogger(__name__)


class HistoryService:
    """Service for managing transcription history

    Provides high-level operations for transcription history management
    including creation, retrieval, search, and cleanup.
    """

    def __init__(self, repository: Optional[TranscriptionRepository] = None):
        """Initialize history service

        Args:
            repository: Repository instance (creates new if not provided)
        """
        self._repo = repository or TranscriptionRepository()
        self._on_change_callback: Optional[Callable[[], None]] = None

    def set_on_change(self, callback: Callable[[], None]):
        """Set callback for when history changes

        Args:
            callback: Function to call on changes
        """
        self._on_change_callback = callback

    def _notify_change(self):
        """Notify listeners of history change"""
        if self._on_change_callback:
            self._on_change_callback()

    def create_transcription(
        self,
        text: str,
        duration: float = 0.0,
        model_name: Optional[str] = None,
        audio_path: Optional[Path] = None,
    ) -> Transcription:
        """Create a new transcription record

        Args:
            text: Transcribed text
            duration: Recording duration in seconds
            model_name: Name of transcription model used
            audio_path: Path to audio file

        Returns:
            Created transcription
        """
        transcription = Transcription(
            text=text,
            duration=duration,
            status=TranscriptionStatus.COMPLETED,
            transcription_model_name=model_name,
            audio_file_path=str(audio_path) if audio_path else None,
        )

        result = self._repo.create(transcription)
        self._notify_change()
        logger.info(f"Created transcription: {result.id[:8]}...")

        return result

    def save_transcription(self, transcription: Transcription) -> Transcription:
        """Save a transcription (create or update)

        Args:
            transcription: Transcription to save

        Returns:
            Saved transcription
        """
        existing = self._repo.get(transcription.id) if transcription.id else None

        if existing:
            self._repo.update(transcription)
            logger.debug(f"Updated transcription: {transcription.id[:8]}...")
        else:
            transcription = self._repo.create(transcription)
            logger.debug(f"Created transcription: {transcription.id[:8]}...")

        self._notify_change()
        return transcription

    def get_transcription(self, transcription_id: str) -> Optional[Transcription]:
        """Get a transcription by ID

        Args:
            transcription_id: ID to look up

        Returns:
            Transcription or None
        """
        return self._repo.get(transcription_id)

    def get_recent(self, limit: int = 20) -> list[Transcription]:
        """Get recent transcriptions

        Args:
            limit: Maximum number to return

        Returns:
            List of recent transcriptions
        """
        return self._repo.get_recent(limit)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Transcription]:
        """Get all transcriptions with pagination

        Args:
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of transcriptions
        """
        return self._repo.list(limit=limit, offset=offset)

    def search(self, query: str, limit: int = 50) -> list[Transcription]:
        """Search transcriptions

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Matching transcriptions
        """
        if not query.strip():
            return self.get_recent(limit)

        return self._repo.search(query, limit)

    def delete_transcription(self, transcription_id: str) -> bool:
        """Delete a transcription

        Args:
            transcription_id: ID to delete

        Returns:
            True if deleted
        """
        result = self._repo.delete(transcription_id)
        if result:
            self._notify_change()
            logger.info(f"Deleted transcription: {transcription_id[:8]}...")
        return result

    def clear_history(self) -> int:
        """Clear all transcription history

        Returns:
            Number of deleted records
        """
        count = self._repo.count()
        # Delete all by iterating (to trigger proper cleanup)
        transcriptions = self._repo.list(limit=10000)
        for t in transcriptions:
            self._repo.delete(t.id)

        self._notify_change()
        logger.info(f"Cleared {count} transcriptions")
        return count

    def cleanup_old(self, days: int = 30) -> int:
        """Delete old transcriptions

        Args:
            days: Age threshold

        Returns:
            Number of deleted records
        """
        count = self._repo.delete_old(days)
        if count > 0:
            self._notify_change()
            logger.info(f"Cleaned up {count} old transcriptions")
        return count

    def get_stats(self) -> dict:
        """Get history statistics

        Returns:
            Dictionary with stats
        """
        total = self._repo.count()
        completed = self._repo.count(TranscriptionStatus.COMPLETED)
        failed = self._repo.count(TranscriptionStatus.FAILED)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": total - completed - failed,
        }
