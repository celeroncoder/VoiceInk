"""Vocabulary and word replacement models"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid
import re


@dataclass
class VocabularyWord:
    """Custom vocabulary word for transcription hints"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    word: str = ""
    pronunciation: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "word": self.word,
            "pronunciation": self.pronunciation,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VocabularyWord":
        """Create from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            word=data.get("word", ""),
            pronunciation=data.get("pronunciation"),
            category=data.get("category"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


@dataclass
class WordReplacement:
    """Word replacement rule"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    find_text: str = ""
    replace_text: str = ""
    is_regex: bool = False
    case_sensitive: bool = False
    is_enabled: bool = True
    order_index: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def apply(self, text: str) -> str:
        """Apply this replacement rule to text

        Args:
            text: Input text

        Returns:
            Text with replacements applied
        """
        if not self.is_enabled or not self.find_text:
            return text

        if self.is_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                return re.sub(self.find_text, self.replace_text, text, flags=flags)
            except re.error:
                return text
        else:
            if self.case_sensitive:
                return text.replace(self.find_text, self.replace_text)
            else:
                # Case-insensitive string replacement
                pattern = re.escape(self.find_text)
                return re.sub(pattern, self.replace_text, text, flags=re.IGNORECASE)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "find_text": self.find_text,
            "replace_text": self.replace_text,
            "is_regex": self.is_regex,
            "case_sensitive": self.case_sensitive,
            "is_enabled": self.is_enabled,
            "order_index": self.order_index,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WordReplacement":
        """Create from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            find_text=data.get("find_text", ""),
            replace_text=data.get("replace_text", ""),
            is_regex=data.get("is_regex", False),
            case_sensitive=data.get("case_sensitive", False),
            is_enabled=data.get("is_enabled", True),
            order_index=data.get("order_index", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )
