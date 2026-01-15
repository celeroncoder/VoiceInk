"""Global hotkey manager for Wayland and X11"""

import logging
import os
import subprocess
from enum import Enum
from typing import Optional, Callable
from dataclasses import dataclass

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, GLib, Gio

logger = logging.getLogger(__name__)


class DisplayServer(Enum):
    """Display server types"""
    WAYLAND = "wayland"
    X11 = "x11"
    UNKNOWN = "unknown"


@dataclass
class Hotkey:
    """Hotkey definition"""
    id: str
    description: str
    key: str  # e.g., "<Control><Alt>r"
    callback: Optional[Callable[[], None]] = None


class HotkeyManager:
    """Manages global hotkeys for Wayland and X11

    Wayland: Uses XDG GlobalShortcuts Portal
    X11: Uses python-xlib (if available) or keybinder
    """

    def __init__(self):
        """Initialize hotkey manager"""
        self._display_server = self._detect_display_server()
        self._hotkeys: dict[str, Hotkey] = {}
        self._portal_proxy = None
        self._session_handle = None
        self._is_active = False

        logger.info(f"Display server: {self._display_server.value}")

    @property
    def display_server(self) -> DisplayServer:
        """Get detected display server"""
        return self._display_server

    @property
    def is_active(self) -> bool:
        """Check if hotkey manager is active"""
        return self._is_active

    def _detect_display_server(self) -> DisplayServer:
        """Detect the current display server"""
        # Check environment variables
        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        xdg_session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        gdk_backend = os.environ.get("GDK_BACKEND", "").lower()

        if gdk_backend == "wayland" or (wayland_display and xdg_session_type != "x11"):
            return DisplayServer.WAYLAND
        elif xdg_session_type == "x11" or os.environ.get("DISPLAY"):
            return DisplayServer.X11

        return DisplayServer.UNKNOWN

    def setup(self) -> bool:
        """Setup hotkey handling

        Returns:
            True if setup successful
        """
        if self._display_server == DisplayServer.WAYLAND:
            return self._setup_wayland()
        elif self._display_server == DisplayServer.X11:
            return self._setup_x11()

        logger.warning("Unknown display server, hotkeys disabled")
        return False

    def _setup_wayland(self) -> bool:
        """Setup Wayland global shortcuts via XDG Portal"""
        try:
            # Connect to GlobalShortcuts portal
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

            self._portal_proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.GlobalShortcuts",
                None,
            )

            if not self._portal_proxy:
                logger.warning("GlobalShortcuts portal not available")
                return False

            logger.info("Wayland GlobalShortcuts portal connected")
            self._is_active = True
            return True

        except Exception as e:
            logger.error(f"Failed to setup Wayland hotkeys: {e}")
            return False

    def _setup_x11(self) -> bool:
        """Setup X11 global hotkeys"""
        # Try keybinder-3.0
        try:
            gi.require_version("Keybinder", "3.0")
            from gi.repository import Keybinder
            Keybinder.init()
            self._keybinder = Keybinder
            self._is_active = True
            logger.info("X11 hotkeys initialized with keybinder")
            return True
        except (ValueError, ImportError):
            pass

        # Fallback: warn user to use gsettings or xbindkeys
        logger.warning(
            "X11 hotkey binding not available. "
            "Install gir1.2-keybinder-3.0 or use system hotkey settings."
        )
        return False

    def register(self, hotkey: Hotkey) -> bool:
        """Register a global hotkey

        Args:
            hotkey: Hotkey to register

        Returns:
            True if registered successfully
        """
        if not self._is_active:
            return False

        self._hotkeys[hotkey.id] = hotkey

        if self._display_server == DisplayServer.X11 and hasattr(self, "_keybinder"):
            try:
                self._keybinder.bind(
                    hotkey.key,
                    lambda key: self._on_hotkey_activated(hotkey.id),
                    None,
                )
                logger.info(f"Registered hotkey: {hotkey.id} ({hotkey.key})")
                return True
            except Exception as e:
                logger.error(f"Failed to register hotkey {hotkey.id}: {e}")
                return False

        elif self._display_server == DisplayServer.WAYLAND:
            # Portal registration is more complex, requires CreateSession first
            logger.info(f"Hotkey registered (pending portal session): {hotkey.id}")
            return True

        return False

    def unregister(self, hotkey_id: str) -> bool:
        """Unregister a hotkey

        Args:
            hotkey_id: ID of hotkey to unregister

        Returns:
            True if unregistered successfully
        """
        hotkey = self._hotkeys.pop(hotkey_id, None)
        if not hotkey:
            return False

        if self._display_server == DisplayServer.X11 and hasattr(self, "_keybinder"):
            try:
                self._keybinder.unbind(hotkey.key)
                return True
            except Exception:
                pass

        return True

    def _on_hotkey_activated(self, hotkey_id: str):
        """Handle hotkey activation

        Args:
            hotkey_id: ID of activated hotkey
        """
        hotkey = self._hotkeys.get(hotkey_id)
        if hotkey and hotkey.callback:
            GLib.idle_add(hotkey.callback)

    def get_default_record_hotkey(self) -> str:
        """Get default record hotkey string"""
        return "<Control><Alt>r"

    def destroy(self):
        """Cleanup hotkey resources"""
        for hotkey_id in list(self._hotkeys.keys()):
            self.unregister(hotkey_id)

        self._is_active = False
