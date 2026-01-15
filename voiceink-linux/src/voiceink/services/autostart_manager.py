"""XDG autostart manager"""

import logging
from pathlib import Path
from typing import Optional

from gi.repository import GLib

logger = logging.getLogger(__name__)

DESKTOP_FILE_TEMPLATE = """[Desktop Entry]
Type=Application
Name=VoiceInk
Comment=Voice to text transcription
Exec=voiceink
Icon=audio-input-microphone
Terminal=false
Categories=AudioVideo;Audio;Utility;
X-GNOME-Autostart-enabled={enabled}
X-GNOME-Autostart-Delay=5
StartupNotify=false
"""


class AutostartManager:
    """Manages XDG autostart configuration

    Creates/manages .desktop file in ~/.config/autostart/
    """

    def __init__(self, app_id: str = "org.voiceink.VoiceInk"):
        """Initialize autostart manager

        Args:
            app_id: Application ID for desktop file name
        """
        self._app_id = app_id
        self._config_dir = Path(GLib.get_user_config_dir())
        self._autostart_dir = self._config_dir / "autostart"
        self._desktop_file = self._autostart_dir / f"{app_id}.desktop"

    @property
    def autostart_path(self) -> Path:
        """Get path to autostart desktop file"""
        return self._desktop_file

    @property
    def is_enabled(self) -> bool:
        """Check if autostart is enabled"""
        if not self._desktop_file.exists():
            return False

        try:
            content = self._desktop_file.read_text()
            return "X-GNOME-Autostart-enabled=true" in content
        except Exception:
            return False

    def enable(self) -> bool:
        """Enable autostart

        Returns:
            True if successful
        """
        try:
            # Create autostart directory if needed
            self._autostart_dir.mkdir(parents=True, exist_ok=True)

            # Write desktop file
            content = DESKTOP_FILE_TEMPLATE.format(enabled="true")
            self._desktop_file.write_text(content)

            logger.info(f"Autostart enabled: {self._desktop_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable autostart: {e}")
            return False

    def disable(self) -> bool:
        """Disable autostart

        Returns:
            True if successful
        """
        try:
            if self._desktop_file.exists():
                # Option 1: Delete the file
                # self._desktop_file.unlink()

                # Option 2: Set enabled=false (preserves user's choice)
                content = DESKTOP_FILE_TEMPLATE.format(enabled="false")
                self._desktop_file.write_text(content)

                logger.info(f"Autostart disabled: {self._desktop_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable autostart: {e}")
            return False

    def toggle(self) -> bool:
        """Toggle autostart state

        Returns:
            New state (True = enabled)
        """
        if self.is_enabled:
            self.disable()
            return False
        else:
            self.enable()
            return True

    def remove(self) -> bool:
        """Remove autostart file completely

        Returns:
            True if successful
        """
        try:
            if self._desktop_file.exists():
                self._desktop_file.unlink()
                logger.info(f"Autostart file removed: {self._desktop_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove autostart file: {e}")
            return False
