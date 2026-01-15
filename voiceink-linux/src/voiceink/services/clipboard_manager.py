"""Clipboard and paste management"""

import logging
import subprocess
import shutil
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, GLib

from .hotkey_manager import DisplayServer, HotkeyManager

logger = logging.getLogger(__name__)


class ClipboardManager:
    """Manages clipboard operations and paste-at-cursor"""

    def __init__(self):
        """Initialize clipboard manager"""
        self._display = Gdk.Display.get_default()
        self._clipboard = self._display.get_clipboard() if self._display else None

        # Detect display server for paste tool selection
        hotkey_mgr = HotkeyManager()
        self._display_server = hotkey_mgr.display_server

        # Find available paste tools
        self._paste_tool = self._find_paste_tool()

    def _find_paste_tool(self) -> Optional[str]:
        """Find available tool for typing/pasting text"""
        # Wayland tools
        if self._display_server == DisplayServer.WAYLAND:
            for tool in ["wtype", "ydotool", "wl-paste"]:
                if shutil.which(tool):
                    logger.info(f"Using paste tool: {tool}")
                    return tool

        # X11 tools
        if self._display_server == DisplayServer.X11:
            for tool in ["xdotool", "xclip", "xsel"]:
                if shutil.which(tool):
                    logger.info(f"Using paste tool: {tool}")
                    return tool

        logger.warning("No paste tool found, paste-at-cursor disabled")
        return None

    @property
    def can_paste_at_cursor(self) -> bool:
        """Check if paste-at-cursor is available"""
        return self._paste_tool in ["wtype", "ydotool", "xdotool"]

    def copy(self, text: str) -> bool:
        """Copy text to clipboard

        Args:
            text: Text to copy

        Returns:
            True if successful
        """
        if not self._clipboard:
            return False

        try:
            self._clipboard.set(text)
            logger.debug(f"Copied {len(text)} chars to clipboard")
            return True
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            return False

    def get(self) -> Optional[str]:
        """Get text from clipboard

        Returns:
            Clipboard text or None
        """
        # GTK4 clipboard is async, use sync tool as fallback
        try:
            if self._display_server == DisplayServer.X11:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    return result.stdout
            elif self._display_server == DisplayServer.WAYLAND:
                result = subprocess.run(
                    ["wl-paste"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    return result.stdout
        except Exception as e:
            logger.error(f"Failed to get clipboard: {e}")

        return None

    def paste_at_cursor(self, text: str) -> bool:
        """Paste text at current cursor position

        This types the text directly rather than using clipboard paste.

        Args:
            text: Text to paste

        Returns:
            True if successful
        """
        if not self._paste_tool:
            logger.warning("No paste tool available")
            return False

        try:
            if self._paste_tool == "xdotool":
                # X11: Use xdotool type
                subprocess.run(
                    ["xdotool", "type", "--clearmodifiers", "--delay", "0", text],
                    timeout=10,
                    check=True,
                )
                return True

            elif self._paste_tool == "wtype":
                # Wayland: Use wtype
                subprocess.run(
                    ["wtype", text],
                    timeout=10,
                    check=True,
                )
                return True

            elif self._paste_tool == "ydotool":
                # Wayland: Use ydotool (requires ydotoold daemon)
                subprocess.run(
                    ["ydotool", "type", "--key-delay", "0", text],
                    timeout=10,
                    check=True,
                )
                return True

            else:
                # Fallback: copy to clipboard and suggest Ctrl+V
                self.copy(text)
                logger.info("Text copied to clipboard, use Ctrl+V to paste")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Paste operation timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Paste tool failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Paste failed: {e}")
            return False

    def paste_with_enter(self, text: str) -> bool:
        """Paste text and press Enter

        Args:
            text: Text to paste

        Returns:
            True if successful
        """
        if not self.paste_at_cursor(text):
            return False

        try:
            if self._paste_tool == "xdotool":
                subprocess.run(["xdotool", "key", "Return"], timeout=2)
            elif self._paste_tool == "wtype":
                subprocess.run(["wtype", "-k", "Return"], timeout=2)
            elif self._paste_tool == "ydotool":
                subprocess.run(["ydotool", "key", "28:1", "28:0"], timeout=2)
            return True
        except Exception as e:
            logger.error(f"Failed to press Enter: {e}")
            return False
