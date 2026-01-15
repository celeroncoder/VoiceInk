"""Power Mode manager for context-aware settings"""

import json
import logging
from pathlib import Path
from typing import Optional, Callable

from gi.repository import GLib

from ..models.power_mode import PowerModeConfig, ActiveWindow
from ..database import get_database
from .active_window import ActiveWindowService

logger = logging.getLogger(__name__)


class PowerModeManager:
    """Manages Power Mode configurations and context detection

    Provides:
    - Per-app configuration storage
    - Active window monitoring
    - Automatic config switching
    """

    _instance = None

    def __new__(cls):
        """Singleton instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._db = get_database()
        self._active_window_service = ActiveWindowService()
        self._configs: dict[str, PowerModeConfig] = {}
        self._current_config: Optional[PowerModeConfig] = None
        self._on_config_changed: Optional[Callable[[Optional[PowerModeConfig]], None]] = None
        self._monitor_timeout_id: Optional[int] = None

        self._ensure_table()
        self._load_configs()
        self._initialized = True

    def _ensure_table(self):
        """Ensure power_modes table exists"""
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS power_modes (
                id TEXT PRIMARY KEY,
                app_identifier TEXT NOT NULL UNIQUE,
                display_name TEXT,
                emoji TEXT,
                config_json TEXT NOT NULL,
                is_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.commit()

    def _load_configs(self):
        """Load all configurations from database"""
        cursor = self._db.execute(
            "SELECT * FROM power_modes WHERE is_enabled = 1"
        )

        self._configs.clear()
        for row in cursor.fetchall():
            try:
                config_data = json.loads(row["config_json"])
                config = PowerModeConfig.from_dict(config_data)
                self._configs[config.app_identifier.lower()] = config
            except Exception as e:
                logger.error(f"Failed to load power mode config: {e}")

        logger.info(f"Loaded {len(self._configs)} power mode configurations")

    @property
    def current_config(self) -> Optional[PowerModeConfig]:
        """Get the currently active configuration"""
        return self._current_config

    @property
    def configs(self) -> list[PowerModeConfig]:
        """Get all configurations"""
        return list(self._configs.values())

    def set_on_config_changed(self, callback: Callable[[Optional[PowerModeConfig]], None]):
        """Set callback for when the active config changes

        Args:
            callback: Function to call with new config (or None)
        """
        self._on_config_changed = callback

    def save_config(self, config: PowerModeConfig) -> bool:
        """Save a Power Mode configuration

        Args:
            config: Configuration to save

        Returns:
            True if saved successfully
        """
        try:
            config_json = json.dumps(config.to_dict())

            self._db.execute(
                """
                INSERT OR REPLACE INTO power_modes
                (id, app_identifier, display_name, emoji, config_json, is_enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    config.id,
                    config.app_identifier,
                    config.display_name,
                    config.emoji,
                    config_json,
                    1 if config.is_enabled else 0,
                    config.created_at.isoformat(),
                )
            )
            self._db.commit()

            # Update in-memory cache
            self._configs[config.app_identifier.lower()] = config
            logger.info(f"Saved power mode: {config.display_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to save power mode: {e}")
            return False

    def delete_config(self, config_id: str) -> bool:
        """Delete a Power Mode configuration

        Args:
            config_id: ID of configuration to delete

        Returns:
            True if deleted
        """
        try:
            cursor = self._db.execute(
                "DELETE FROM power_modes WHERE id = ?",
                (config_id,)
            )
            self._db.commit()

            # Remove from cache
            for key, config in list(self._configs.items()):
                if config.id == config_id:
                    del self._configs[key]
                    break

            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to delete power mode: {e}")
            return False

    def get_config_for_window(self, window: ActiveWindow) -> Optional[PowerModeConfig]:
        """Get configuration matching a window

        Args:
            window: Active window info

        Returns:
            Matching config or None
        """
        if not window:
            return None

        # Try exact match on window class
        identifier = window.app_identifier
        if identifier in self._configs:
            return self._configs[identifier]

        # Try partial match
        for key, config in self._configs.items():
            if key in identifier or identifier in key:
                return config

        return None

    def detect_and_apply(self) -> Optional[PowerModeConfig]:
        """Detect active window and apply matching configuration

        Returns:
            Applied configuration or None
        """
        window = self._active_window_service.update()

        if not window:
            if self._current_config:
                self._current_config = None
                if self._on_config_changed:
                    self._on_config_changed(None)
            return None

        config = self.get_config_for_window(window)

        if config != self._current_config:
            self._current_config = config
            if self._on_config_changed:
                self._on_config_changed(config)

            if config:
                logger.info(f"Power Mode activated: {config.display_name}")
            else:
                logger.debug("Power Mode deactivated")

        return config

    def start_monitoring(self, interval_ms: int = 1000):
        """Start monitoring active window

        Args:
            interval_ms: Check interval in milliseconds
        """
        if self._monitor_timeout_id:
            return

        def monitor():
            self.detect_and_apply()
            return True  # Continue monitoring

        self._monitor_timeout_id = GLib.timeout_add(interval_ms, monitor)
        logger.info("Power Mode monitoring started")

    def stop_monitoring(self):
        """Stop monitoring active window"""
        if self._monitor_timeout_id:
            GLib.source_remove(self._monitor_timeout_id)
            self._monitor_timeout_id = None
            logger.info("Power Mode monitoring stopped")

    def get_predefined_configs(self) -> list[PowerModeConfig]:
        """Get list of predefined Power Mode configurations

        Returns:
            List of common app configurations
        """
        return [
            PowerModeConfig(
                app_identifier="slack",
                display_name="Slack",
                emoji="💬",
                ai_enhancement_enabled=True,
                ai_prompt="Format this as a professional Slack message.",
            ),
            PowerModeConfig(
                app_identifier="code",
                display_name="VS Code",
                emoji="💻",
                ai_enhancement_enabled=True,
                ai_prompt="Format this as code comments or documentation.",
            ),
            PowerModeConfig(
                app_identifier="firefox",
                display_name="Firefox",
                emoji="🌐",
            ),
            PowerModeConfig(
                app_identifier="chrome",
                display_name="Chrome",
                emoji="🌐",
            ),
            PowerModeConfig(
                app_identifier="thunderbird",
                display_name="Thunderbird",
                emoji="📧",
                ai_enhancement_enabled=True,
                ai_prompt="Format this as a professional email.",
            ),
            PowerModeConfig(
                app_identifier="libreoffice",
                display_name="LibreOffice",
                emoji="📝",
            ),
        ]
