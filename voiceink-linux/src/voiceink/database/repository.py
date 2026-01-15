"""Repository pattern for database operations"""

import logging
from datetime import datetime
from typing import Optional
import uuid

from .connection import Database, get_database
from ..models.transcription import Transcription, TranscriptionStatus

logger = logging.getLogger(__name__)


class TranscriptionRepository:
    """Repository for transcription CRUD operations"""

    def __init__(self, database: Optional[Database] = None):
        """Initialize repository

        Args:
            database: Database instance (uses global if not provided)
        """
        self._db = database or get_database()

    def create(self, transcription: Transcription) -> Transcription:
        """Create a new transcription record

        Args:
            transcription: Transcription to create

        Returns:
            Created transcription with ID
        """
        if not transcription.id:
            transcription.id = str(uuid.uuid4())

        word_count = len(transcription.text.split()) if transcription.text else 0

        self._db.execute(
            """
            INSERT INTO transcriptions (
                id, text, enhanced_text, raw_text, duration, created_at,
                model_name, transcription_duration, ai_model_name,
                enhancement_duration, prompt_name, status,
                power_mode_name, power_mode_emoji, audio_file_path, word_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transcription.id,
                transcription.text,
                transcription.enhanced_text,
                transcription.text,  # raw_text
                transcription.duration,
                transcription.created_at.isoformat(),
                transcription.transcription_model_name,
                transcription.transcription_duration,
                transcription.ai_enhancement_model_name,
                transcription.enhancement_duration,
                transcription.prompt_name,
                transcription.status.value,
                transcription.power_mode_name,
                transcription.power_mode_emoji,
                transcription.audio_file_path,
                word_count,
            ),
        )
        self._db.commit()

        logger.debug(f"Created transcription: {transcription.id}")
        return transcription

    def get(self, transcription_id: str) -> Optional[Transcription]:
        """Get a transcription by ID

        Args:
            transcription_id: ID to look up

        Returns:
            Transcription or None if not found
        """
        cursor = self._db.execute(
            "SELECT * FROM transcriptions WHERE id = ?",
            (transcription_id,)
        )
        row = cursor.fetchone()

        if row:
            return self._row_to_transcription(row)
        return None

    def update(self, transcription: Transcription) -> bool:
        """Update a transcription

        Args:
            transcription: Transcription with updated values

        Returns:
            True if updated successfully
        """
        word_count = len(transcription.text.split()) if transcription.text else 0

        cursor = self._db.execute(
            """
            UPDATE transcriptions SET
                text = ?,
                enhanced_text = ?,
                duration = ?,
                model_name = ?,
                transcription_duration = ?,
                ai_model_name = ?,
                enhancement_duration = ?,
                prompt_name = ?,
                status = ?,
                power_mode_name = ?,
                power_mode_emoji = ?,
                audio_file_path = ?,
                word_count = ?
            WHERE id = ?
            """,
            (
                transcription.text,
                transcription.enhanced_text,
                transcription.duration,
                transcription.transcription_model_name,
                transcription.transcription_duration,
                transcription.ai_enhancement_model_name,
                transcription.enhancement_duration,
                transcription.prompt_name,
                transcription.status.value,
                transcription.power_mode_name,
                transcription.power_mode_emoji,
                transcription.audio_file_path,
                word_count,
                transcription.id,
            ),
        )
        self._db.commit()

        return cursor.rowcount > 0

    def delete(self, transcription_id: str) -> bool:
        """Delete a transcription

        Args:
            transcription_id: ID to delete

        Returns:
            True if deleted successfully
        """
        cursor = self._db.execute(
            "DELETE FROM transcriptions WHERE id = ?",
            (transcription_id,)
        )
        self._db.commit()

        return cursor.rowcount > 0

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[TranscriptionStatus] = None,
    ) -> list[Transcription]:
        """List transcriptions with pagination

        Args:
            limit: Maximum number to return
            offset: Number to skip
            status: Filter by status

        Returns:
            List of transcriptions
        """
        if status:
            cursor = self._db.execute(
                """
                SELECT * FROM transcriptions
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (status.value, limit, offset)
            )
        else:
            cursor = self._db.execute(
                """
                SELECT * FROM transcriptions
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )

        return [self._row_to_transcription(row) for row in cursor.fetchall()]

    def search(self, query: str, limit: int = 50) -> list[Transcription]:
        """Search transcriptions by text

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Matching transcriptions
        """
        cursor = self._db.execute(
            """
            SELECT t.* FROM transcriptions t
            INNER JOIN transcriptions_fts fts ON t.rowid = fts.rowid
            WHERE transcriptions_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit)
        )

        return [self._row_to_transcription(row) for row in cursor.fetchall()]

    def count(self, status: Optional[TranscriptionStatus] = None) -> int:
        """Count transcriptions

        Args:
            status: Filter by status

        Returns:
            Count of transcriptions
        """
        if status:
            cursor = self._db.execute(
                "SELECT COUNT(*) FROM transcriptions WHERE status = ?",
                (status.value,)
            )
        else:
            cursor = self._db.execute("SELECT COUNT(*) FROM transcriptions")

        return cursor.fetchone()[0]

    def get_recent(self, limit: int = 10) -> list[Transcription]:
        """Get most recent transcriptions

        Args:
            limit: Maximum number to return

        Returns:
            Recent transcriptions
        """
        return self.list(limit=limit, status=TranscriptionStatus.COMPLETED)

    def delete_old(self, days: int = 30) -> int:
        """Delete transcriptions older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of deleted records
        """
        cursor = self._db.execute(
            """
            DELETE FROM transcriptions
            WHERE created_at < datetime('now', '-' || ? || ' days')
            """,
            (days,)
        )
        self._db.commit()

        return cursor.rowcount

    def _row_to_transcription(self, row) -> Transcription:
        """Convert database row to Transcription object"""
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return Transcription(
            id=row["id"],
            text=row["text"] or "",
            enhanced_text=row["enhanced_text"],
            duration=row["duration"] or 0.0,
            audio_file_path=row["audio_file_path"],
            created_at=created_at,
            status=TranscriptionStatus(row["status"]) if row["status"] else TranscriptionStatus.PENDING,
            transcription_model_name=row["model_name"],
            transcription_duration=row["transcription_duration"],
            ai_enhancement_model_name=row["ai_model_name"],
            enhancement_duration=row["enhancement_duration"],
            prompt_name=row["prompt_name"],
            power_mode_name=row["power_mode_name"],
            power_mode_emoji=row["power_mode_emoji"],
        )
