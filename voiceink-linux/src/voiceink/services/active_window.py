"""Active window detection service"""

import logging
import os
import subprocess
from typing import Optional

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio, GLib

from ..models.power_mode import ActiveWindow
from .hotkey_manager import DisplayServer

logger = logging.getLogger(__name__)

# Try to import Wnck for X11
try:
    gi.require_version("Wnck", "3.0")
    from gi.repository import Wnck
    HAS_WNCK = True
except (ValueError, ImportError):
    HAS_WNCK = False


class ActiveWindowService:
    """Detects the currently active window

    Uses multiple backends:
    - Wnck library (X11)
    - xdotool command (X11 fallback)
    - GNOME Shell D-Bus (Wayland, limited)
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

        self._display_server = self._detect_display_server()
        self._screen = None
        self._last_window: Optional[ActiveWindow] = None

        # Initialize Wnck if on X11
        if self._display_server == DisplayServer.X11 and HAS_WNCK:
            try:
                self._screen = Wnck.Screen.get_default()
                self._screen.force_update()
            except Exception as e:
                logger.warning(f"Failed to initialize Wnck: {e}")

        self._initialized = True
        logger.info(f"ActiveWindowService initialized ({self._display_server.value})")

    def _detect_display_server(self) -> DisplayServer:
        """Detect display server"""
        wayland = os.environ.get("WAYLAND_DISPLAY")
        xdg = os.environ.get("XDG_SESSION_TYPE", "").lower()

        if wayland and xdg != "x11":
            return DisplayServer.WAYLAND
        elif os.environ.get("DISPLAY"):
            return DisplayServer.X11
        return DisplayServer.UNKNOWN

    def get_active_window(self) -> Optional[ActiveWindow]:
        """Get information about the currently active window

        Returns:
            ActiveWindow or None if detection failed
        """
        if self._display_server == DisplayServer.X11:
            return self._get_x11_window()
        elif self._display_server == DisplayServer.WAYLAND:
            return self._get_wayland_window()

        return None

    def _get_x11_window(self) -> Optional[ActiveWindow]:
        """Get active window on X11"""
        # Try Wnck first
        if HAS_WNCK and self._screen:
            try:
                self._screen.force_update()
                window = self._screen.get_active_window()

                if window:
                    return ActiveWindow(
                        window_id=window.get_xid(),
                        window_class=window.get_class_group_name() or "",
                        window_name=window.get_name() or "",
                        pid=window.get_pid(),
                    )
            except Exception as e:
                logger.warning(f"Wnck failed: {e}")

        # Fallback to xdotool
        return self._get_xdotool_window()

    def _get_xdotool_window(self) -> Optional[ActiveWindow]:
        """Get active window using xdotool"""
        try:
            # Get window ID
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode != 0:
                return None

            window_id = int(result.stdout.strip())

            # Get window name
            result = subprocess.run(
                ["xdotool", "getwindowname", str(window_id)],
                capture_output=True,
                text=True,
                timeout=2,
            )
            window_name = result.stdout.strip() if result.returncode == 0 else ""

            # Get window class using xprop
            window_class = ""
            try:
                result = subprocess.run(
                    ["xprop", "-id", str(window_id), "WM_CLASS"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0 and "=" in result.stdout:
                    # Parse: WM_CLASS(STRING) = "instance", "class"
                    parts = result.stdout.split("=")[1].strip().split(",")
                    if len(parts) >= 2:
                        window_class = parts[1].strip().strip('"')
            except Exception:
                pass

            return ActiveWindow(
                window_id=window_id,
                window_class=window_class,
                window_name=window_name,
            )

        except FileNotFoundError:
            logger.warning("xdotool not found")
        except Exception as e:
            logger.warning(f"xdotool failed: {e}")

        return None

    def _get_wayland_window(self) -> Optional[ActiveWindow]:
        """Get active window on Wayland

        Note: Wayland restricts window information access for security.
        This provides limited functionality through GNOME Shell.
        """
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

            # Try GNOME Shell eval (requires GNOME)
            proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.gnome.Shell",
                "/org/gnome/Shell",
                "org.gnome.Shell",
                None,
            )

            if proxy:
                # Get focused window info
                result = proxy.call_sync(
                    "Eval",
                    GLib.Variant("(s)", ("global.display.focus_window?.get_wm_class() || ''",)),
                    Gio.DBusCallFlags.NONE,
                    1000,
                    None,
                )

                if result:
                    success, wm_class = result.unpack()
                    if success and wm_class:
                        # Clean up the result (removes quotes)
                        wm_class = wm_class.strip('"\'')
                        return ActiveWindow(window_class=wm_class)

        except Exception as e:
            logger.debug(f"Wayland window detection failed: {e}")

        return None

    @property
    def last_window(self) -> Optional[ActiveWindow]:
        """Get the last detected active window"""
        return self._last_window

    def update(self) -> Optional[ActiveWindow]:
        """Update and return the active window"""
        self._last_window = self.get_active_window()
        return self._last_window
