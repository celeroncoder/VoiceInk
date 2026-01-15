"""SQLite database connection management"""

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Global database instance
_database: Optional["Database"] = None
_lock = threading.Lock()


def get_data_dir() -> Path:
    """Get XDG data directory for VoiceInk"""
    from gi.repository import GLib
    data_dir = Path(GLib.get_user_data_dir()) / "voiceink"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_database() -> "Database":
    """Get the global database instance (singleton)"""
    global _database
    with _lock:
        if _database is None:
            db_path = get_data_dir() / "voiceink.db"
            _database = Database(db_path)
        return _database


class Database:
    """SQLite database connection manager

    Handles connection lifecycle, migrations, and thread-safe access.
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path):
        """Initialize database

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()

    @property
    def connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection

    def _init_database(self):
        """Initialize database schema"""
        conn = self.connection

        # Check schema version
        cursor = conn.execute("PRAGMA user_version")
        version = cursor.fetchone()[0]

        if version < self.SCHEMA_VERSION:
            self._migrate(version)

    def _migrate(self, from_version: int):
        """Run database migrations"""
        conn = self.connection

        if from_version < 1:
            logger.info("Creating initial database schema")
            conn.executescript("""
                -- Transcriptions table
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL DEFAULT '',
                    enhanced_text TEXT,
                    raw_text TEXT,
                    duration REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    -- Model info
                    model_name TEXT,
                    transcription_duration REAL,
                    ai_model_name TEXT,
                    enhancement_duration REAL,
                    prompt_name TEXT,

                    -- Status
                    status TEXT DEFAULT 'pending',

                    -- Power mode
                    power_mode_name TEXT,
                    power_mode_emoji TEXT,

                    -- Files
                    audio_file_path TEXT,

                    -- Computed
                    word_count INTEGER DEFAULT 0
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at
                    ON transcriptions(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_transcriptions_status
                    ON transcriptions(status);

                -- FTS for search
                CREATE VIRTUAL TABLE IF NOT EXISTS transcriptions_fts USING fts5(
                    text,
                    enhanced_text,
                    content='transcriptions',
                    content_rowid='rowid'
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS transcriptions_ai AFTER INSERT ON transcriptions BEGIN
                    INSERT INTO transcriptions_fts(rowid, text, enhanced_text)
                    VALUES (new.rowid, new.text, new.enhanced_text);
                END;

                CREATE TRIGGER IF NOT EXISTS transcriptions_ad AFTER DELETE ON transcriptions BEGIN
                    INSERT INTO transcriptions_fts(transcriptions_fts, rowid, text, enhanced_text)
                    VALUES('delete', old.rowid, old.text, old.enhanced_text);
                END;

                CREATE TRIGGER IF NOT EXISTS transcriptions_au AFTER UPDATE ON transcriptions BEGIN
                    INSERT INTO transcriptions_fts(transcriptions_fts, rowid, text, enhanced_text)
                    VALUES('delete', old.rowid, old.text, old.enhanced_text);
                    INSERT INTO transcriptions_fts(rowid, text, enhanced_text)
                    VALUES (new.rowid, new.text, new.enhanced_text);
                END;

                -- Vocabulary table
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id TEXT PRIMARY KEY,
                    word TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Word replacements table
                CREATE TABLE IF NOT EXISTS word_replacements (
                    id TEXT PRIMARY KEY,
                    original TEXT NOT NULL,
                    replacement TEXT NOT NULL,
                    is_enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                PRAGMA user_version = 1;
            """)
            conn.commit()
            logger.info("Database schema created")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute SQL statement

        Args:
            sql: SQL statement
            params: Parameters tuple

        Returns:
            Cursor with results
        """
        return self.connection.execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """Execute SQL statement multiple times

        Args:
            sql: SQL statement
            params_list: List of parameter tuples

        Returns:
            Cursor
        """
        return self.connection.executemany(sql, params_list)

    def commit(self):
        """Commit current transaction"""
        self.connection.commit()

    def rollback(self):
        """Rollback current transaction"""
        self.connection.rollback()

    def close(self):
        """Close the database connection"""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
