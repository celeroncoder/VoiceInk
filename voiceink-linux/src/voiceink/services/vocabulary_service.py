"""Vocabulary and word replacement service"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..database import get_database
from ..models.vocabulary import VocabularyWord, WordReplacement

logger = logging.getLogger(__name__)


class VocabularyService:
    """Manages custom vocabulary and word replacements

    Provides:
    - Vocabulary word management
    - Word replacement rules
    - Text processing pipeline
    - Import/export functionality
    """

    def __init__(self):
        """Initialize vocabulary service"""
        self._db = get_database()

    # ============= Vocabulary Words =============

    def add_word(self, word: VocabularyWord) -> VocabularyWord:
        """Add a vocabulary word

        Args:
            word: Word to add

        Returns:
            Added word
        """
        self._db.execute(
            """
            INSERT OR REPLACE INTO vocabulary (id, word, created_at)
            VALUES (?, ?, ?)
            """,
            (word.id, word.word, word.created_at.isoformat())
        )
        self._db.commit()
        return word

    def get_words(self) -> list[VocabularyWord]:
        """Get all vocabulary words

        Returns:
            List of words
        """
        cursor = self._db.execute(
            "SELECT * FROM vocabulary ORDER BY word"
        )
        return [
            VocabularyWord(
                id=row["id"],
                word=row["word"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            )
            for row in cursor.fetchall()
        ]

    def delete_word(self, word_id: str) -> bool:
        """Delete a vocabulary word

        Args:
            word_id: ID of word to delete

        Returns:
            True if deleted
        """
        cursor = self._db.execute(
            "DELETE FROM vocabulary WHERE id = ?",
            (word_id,)
        )
        self._db.commit()
        return cursor.rowcount > 0

    def get_vocabulary_prompt(self) -> str:
        """Get vocabulary as a prompt string for Whisper

        Returns:
            Comma-separated vocabulary words
        """
        words = self.get_words()
        return ", ".join(w.word for w in words)

    # ============= Word Replacements =============

    def add_replacement(self, replacement: WordReplacement) -> WordReplacement:
        """Add a word replacement rule

        Args:
            replacement: Replacement rule to add

        Returns:
            Added replacement
        """
        # Get next order index
        cursor = self._db.execute(
            "SELECT MAX(order_index) FROM word_replacements"
        )
        max_order = cursor.fetchone()[0] or 0
        replacement.order_index = max_order + 1

        self._db.execute(
            """
            INSERT OR REPLACE INTO word_replacements
            (id, original, replacement, is_enabled, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                replacement.id,
                replacement.find_text,
                replacement.replace_text,
                1 if replacement.is_enabled else 0,
                replacement.created_at.isoformat()
            )
        )
        self._db.commit()
        return replacement

    def get_replacements(self, enabled_only: bool = False) -> list[WordReplacement]:
        """Get all word replacements

        Args:
            enabled_only: Only return enabled replacements

        Returns:
            List of replacements
        """
        if enabled_only:
            cursor = self._db.execute(
                "SELECT * FROM word_replacements WHERE is_enabled = 1 ORDER BY id"
            )
        else:
            cursor = self._db.execute(
                "SELECT * FROM word_replacements ORDER BY id"
            )

        return [
            WordReplacement(
                id=row["id"],
                find_text=row["original"],
                replace_text=row["replacement"],
                is_enabled=bool(row["is_enabled"]),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            )
            for row in cursor.fetchall()
        ]

    def update_replacement(self, replacement: WordReplacement) -> bool:
        """Update a replacement rule

        Args:
            replacement: Replacement with updated values

        Returns:
            True if updated
        """
        cursor = self._db.execute(
            """
            UPDATE word_replacements SET
                original = ?,
                replacement = ?,
                is_enabled = ?
            WHERE id = ?
            """,
            (
                replacement.find_text,
                replacement.replace_text,
                1 if replacement.is_enabled else 0,
                replacement.id
            )
        )
        self._db.commit()
        return cursor.rowcount > 0

    def delete_replacement(self, replacement_id: str) -> bool:
        """Delete a replacement rule

        Args:
            replacement_id: ID of replacement to delete

        Returns:
            True if deleted
        """
        cursor = self._db.execute(
            "DELETE FROM word_replacements WHERE id = ?",
            (replacement_id,)
        )
        self._db.commit()
        return cursor.rowcount > 0

    # ============= Text Processing =============

    def apply_replacements(self, text: str) -> str:
        """Apply all enabled replacements to text

        Args:
            text: Input text

        Returns:
            Processed text
        """
        replacements = self.get_replacements(enabled_only=True)

        for replacement in replacements:
            text = replacement.apply(text)

        return text

    def process_transcription(self, text: str) -> str:
        """Process transcription text through vocabulary pipeline

        Args:
            text: Raw transcription

        Returns:
            Processed text
        """
        # Apply word replacements
        text = self.apply_replacements(text)

        return text

    # ============= Import/Export =============

    def export_to_json(self, path: Path) -> bool:
        """Export vocabulary and replacements to JSON

        Args:
            path: Output file path

        Returns:
            True if successful
        """
        try:
            data = {
                "version": 1,
                "exported_at": datetime.now().isoformat(),
                "vocabulary": [w.to_dict() for w in self.get_words()],
                "replacements": [r.to_dict() for r in self.get_replacements()],
            }

            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2))

            logger.info(f"Exported vocabulary to {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export vocabulary: {e}")
            return False

    def import_from_json(self, path: Path, merge: bool = True) -> tuple[int, int]:
        """Import vocabulary and replacements from JSON

        Args:
            path: Input file path
            merge: If True, merge with existing; if False, replace all

        Returns:
            Tuple of (words_imported, replacements_imported)
        """
        try:
            path = Path(path)
            data = json.loads(path.read_text())

            words_count = 0
            replacements_count = 0

            # Clear existing if not merging
            if not merge:
                self._db.execute("DELETE FROM vocabulary")
                self._db.execute("DELETE FROM word_replacements")
                self._db.commit()

            # Import vocabulary
            for word_data in data.get("vocabulary", []):
                word = VocabularyWord.from_dict(word_data)
                self.add_word(word)
                words_count += 1

            # Import replacements
            for repl_data in data.get("replacements", []):
                replacement = WordReplacement.from_dict(repl_data)
                self.add_replacement(replacement)
                replacements_count += 1

            logger.info(f"Imported {words_count} words, {replacements_count} replacements")
            return words_count, replacements_count

        except Exception as e:
            logger.error(f"Failed to import vocabulary: {e}")
            return 0, 0

    def get_stats(self) -> dict:
        """Get vocabulary statistics

        Returns:
            Statistics dictionary
        """
        cursor = self._db.execute("SELECT COUNT(*) FROM vocabulary")
        words_count = cursor.fetchone()[0]

        cursor = self._db.execute("SELECT COUNT(*) FROM word_replacements")
        replacements_count = cursor.fetchone()[0]

        cursor = self._db.execute(
            "SELECT COUNT(*) FROM word_replacements WHERE is_enabled = 1"
        )
        enabled_count = cursor.fetchone()[0]

        return {
            "vocabulary_words": words_count,
            "total_replacements": replacements_count,
            "enabled_replacements": enabled_count,
        }
