"""System tray manager using AppIndicator3"""

import logging
from typing import Optional, Callable

import gi

gi.require_version("Gtk", "4.0")

# Try AppIndicator3 (Ubuntu)
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
    HAS_APPINDICATOR = True
except (ValueError, ImportError):
    try:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3
        HAS_APPINDICATOR = True
    except (ValueError, ImportError):
        HAS_APPINDICATOR = False

from gi.repository import Gtk, GLib

logger = logging.getLogger(__name__)


class TrayManager:
    """Manages system tray icon and menu

    Uses AppIndicator3/AyatanaAppIndicator3 for Ubuntu compatibility.
    Falls back gracefully if not available.
    """

    def __init__(
        self,
        app_id: str = "org.voiceink.VoiceInk",
        icon_name: str = "audio-input-microphone-symbolic",
        on_show: Optional[Callable[[], None]] = None,
        on_record: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        """Initialize tray manager

        Args:
            app_id: Application ID
            icon_name: Icon name for the tray
            on_show: Callback for show/hide action
            on_record: Callback for record action
            on_quit: Callback for quit action
        """
        self._app_id = app_id
        self._icon_name = icon_name
        self._on_show = on_show
        self._on_record = on_record
        self._on_quit = on_quit

        self._indicator = None
        self._menu = None
        self._is_recording = False
        self._is_visible = False

    @property
    def is_available(self) -> bool:
        """Check if system tray is available"""
        return HAS_APPINDICATOR

    @property
    def is_active(self) -> bool:
        """Check if tray is active"""
        return self._indicator is not None

    def setup(self) -> bool:
        """Setup the system tray

        Returns:
            True if setup successful
        """
        if not HAS_APPINDICATOR:
            logger.warning("AppIndicator not available, tray disabled")
            return False

        try:
            # Create indicator
            self._indicator = AppIndicator3.Indicator.new(
                self._app_id,
                self._icon_name,
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )

            # Build menu
            self._menu = self._build_menu()
            self._indicator.set_menu(self._menu)

            # Set status
            self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

            logger.info("System tray initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to setup tray: {e}")
            return False

    def _build_menu(self) -> Gtk.Menu:
        """Build the tray menu"""
        menu = Gtk.Menu()

        # Show/Hide window
        self._show_item = Gtk.MenuItem(label="Show Window")
        self._show_item.connect("activate", self._on_show_clicked)
        menu.append(self._show_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Record
        self._record_item = Gtk.MenuItem(label="Start Recording")
        self._record_item.connect("activate", self._on_record_clicked)
        menu.append(self._record_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit_clicked)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _on_show_clicked(self, item):
        """Handle show/hide menu item"""
        if self._on_show:
            self._on_show()

    def _on_record_clicked(self, item):
        """Handle record menu item"""
        if self._on_record:
            self._on_record()

    def _on_quit_clicked(self, item):
        """Handle quit menu item"""
        if self._on_quit:
            self._on_quit()

    def set_recording(self, is_recording: bool):
        """Update recording state

        Args:
            is_recording: Whether currently recording
        """
        self._is_recording = is_recording

        if self._record_item:
            if is_recording:
                self._record_item.set_label("Stop Recording")
            else:
                self._record_item.set_label("Start Recording")

        if self._indicator:
            if is_recording:
                self._indicator.set_icon_full(
                    "media-record-symbolic",
                    "Recording"
                )
            else:
                self._indicator.set_icon_full(
                    self._icon_name,
                    "VoiceInk"
                )

    def set_window_visible(self, visible: bool):
        """Update window visibility state

        Args:
            visible: Whether window is visible
        """
        self._is_visible = visible

        if self._show_item:
            if visible:
                self._show_item.set_label("Hide Window")
            else:
                self._show_item.set_label("Show Window")

    def set_tooltip(self, text: str):
        """Set tray tooltip

        Args:
            text: Tooltip text
        """
        if self._indicator:
            self._indicator.set_title(text)

    def destroy(self):
        """Cleanup tray resources"""
        if self._indicator:
            self._indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
            self._indicator = None
