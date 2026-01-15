"""VoiceInk main window"""

import gi
import logging
import threading
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gio, GLib

from .views import RecordingView, TranscriptionView, PreferencesWindow
from .audio import AudioRecorder, DeviceManager
from .whisper import WhisperState
from .whisper.model_manager import ModelSize
from .services import LocalTranscriptionService

logger = logging.getLogger(__name__)


class VoiceInkWindow(Adw.ApplicationWindow):
    """Main application window

    Orchestrates recording, transcription, and display.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("VoiceInk")
        self.set_default_size(500, 700)

        # Initialize services
        self._device_manager = DeviceManager()
        self._recorder = AudioRecorder(
            device_manager=self._device_manager,
            on_level_change=self._on_audio_level_change,
        )
        self._transcription_service = LocalTranscriptionService()
        self._is_model_loaded = False

        self._build_ui()
        self._setup_actions()

    def _build_ui(self):
        """Build the main UI"""
        # Toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)

        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(self._create_menu())
        header.pack_end(menu_button)

        # Preferences button
        prefs_button = Gtk.Button()
        prefs_button.set_icon_name("emblem-system-symbolic")
        prefs_button.set_tooltip_text("Preferences")
        prefs_button.connect("clicked", self._on_preferences_clicked)
        header.pack_end(prefs_button)

        # Model status button
        self.model_button = Gtk.Button()
        self.model_button.set_icon_name("folder-download-symbolic")
        self.model_button.set_tooltip_text("Download Model")
        self.model_button.connect("clicked", self._on_model_clicked)
        header.pack_start(self.model_button)

        # Content with clamp for responsive width
        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)
        clamp.set_vexpand(True)
        main_box.append(clamp)

        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        clamp.set_child(content_box)

        # Recording view
        self.recording_view = RecordingView(
            on_record_start=self._on_record_start,
            on_record_stop=self._on_record_stop,
            on_record_cancel=self._on_record_cancel,
        )
        content_box.append(self.recording_view)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_start(24)
        separator.set_margin_end(24)
        content_box.append(separator)

        # Transcription view
        self.transcription_view = TranscriptionView(
            on_copy=self._on_text_copied,
            on_clear=self._on_text_cleared,
        )
        self.transcription_view.set_vexpand(True)
        content_box.append(self.transcription_view)

        # Status bar
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_bar.set_margin_start(24)
        status_bar.set_margin_end(24)
        status_bar.set_margin_bottom(12)
        main_box.append(status_bar)

        # Model status
        self.model_status = Gtk.Label(label="No model loaded")
        self.model_status.add_css_class("dim-label")
        self.model_status.add_css_class("caption")
        self.model_status.set_halign(Gtk.Align.START)
        self.model_status.set_hexpand(True)
        status_bar.append(self.model_status)

        # Backend status
        backend = self._device_manager.backend.value if self._device_manager.is_available else "unavailable"
        backend_label = Gtk.Label(label=f"Audio: {backend}")
        backend_label.add_css_class("dim-label")
        backend_label.add_css_class("caption")
        status_bar.append(backend_label)

    def _create_menu(self):
        """Create the application menu"""
        menu = Gio.Menu()

        # Transcription section
        transcription_section = Gio.Menu()
        transcription_section.append("New Transcription", "win.new")
        transcription_section.append("History", "win.history")
        menu.append_section(None, transcription_section)

        # App section
        app_section = Gio.Menu()
        app_section.append("Preferences", "win.preferences")
        app_section.append("Keyboard Shortcuts", "win.shortcuts")
        app_section.append("About VoiceInk", "app.about")
        menu.append_section(None, app_section)

        return menu

    def _setup_actions(self):
        """Setup window actions"""
        # New transcription
        action = Gio.SimpleAction.new("new", None)
        action.connect("activate", lambda a, p: self.transcription_view.clear())
        self.add_action(action)

        # History (placeholder)
        action = Gio.SimpleAction.new("history", None)
        action.connect("activate", lambda a, p: self._show_toast("History coming soon"))
        self.add_action(action)

        # Preferences
        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", lambda a, p: self._on_preferences_clicked(None))
        self.add_action(action)

        # Shortcuts (placeholder)
        action = Gio.SimpleAction.new("shortcuts", None)
        action.connect("activate", lambda a, p: self._show_toast("Shortcuts coming soon"))
        self.add_action(action)

    def _on_preferences_clicked(self, button):
        """Show preferences window"""
        prefs = PreferencesWindow(parent=self)

        # Populate devices
        device_names = [d.name for d in self._device_manager.devices]
        prefs.set_devices(device_names)

        prefs.present()

    def _on_model_clicked(self, button):
        """Download/manage model"""
        if self._is_model_loaded:
            self._show_toast("Model already loaded")
            return

        self._show_toast("Downloading model...")
        self.model_status.set_label("Downloading...")

        # Download in background
        def download():
            try:
                success = self._transcription_service.configure(
                    model_size=ModelSize.BASE,
                    progress_callback=self._on_download_progress,
                )
                GLib.idle_add(self._on_model_loaded, success)
            except Exception as e:
                logger.error(f"Model download failed: {e}")
                GLib.idle_add(self._on_model_loaded, False)

        thread = threading.Thread(target=download, daemon=True)
        thread.start()

    def _on_download_progress(self, progress: float):
        """Update download progress"""
        GLib.idle_add(
            self.model_status.set_label,
            f"Downloading: {progress * 100:.0f}%"
        )

    def _on_model_loaded(self, success: bool):
        """Handle model loaded callback"""
        if success:
            self._is_model_loaded = True
            self.model_status.set_label("Model: Base (ready)")
            self.model_button.set_icon_name("emblem-ok-symbolic")
            self._show_toast("Model loaded successfully")
        else:
            self.model_status.set_label("Model download failed")
            self._show_toast("Failed to download model")

    def _on_record_start(self):
        """Handle recording start"""
        if not self._is_model_loaded:
            self._show_toast("Please download a model first")
            self.recording_view.stop_recording()
            return

        success = self._recorder.start()
        if not success:
            self._show_toast("Failed to start recording")
            self.recording_view.stop_recording()

    def _on_record_stop(self):
        """Handle recording stop"""
        audio = self._recorder.stop()
        if audio is None:
            self._show_toast("No audio recorded")
            self.recording_view.set_ready()
            return

        # Transcribe in background
        self.recording_view.set_transcribing()
        self.transcription_view.set_loading(True)

        def transcribe():
            try:
                text = self._transcription_service.transcribe_samples(audio)
                GLib.idle_add(self._on_transcription_complete, text)
            except Exception as e:
                logger.error(f"Transcription failed: {e}")
                GLib.idle_add(self._on_transcription_complete, None)

        thread = threading.Thread(target=transcribe, daemon=True)
        thread.start()

    def _on_record_cancel(self):
        """Handle recording cancel"""
        self._recorder.cancel()
        self._show_toast("Recording cancelled")

    def _on_transcription_complete(self, text: str | None):
        """Handle transcription complete"""
        self.recording_view.set_ready()
        self.transcription_view.set_loading(False)

        if text:
            self.transcription_view.set_text(text)
            self._show_toast("Transcription complete")
        else:
            self._show_toast("Transcription failed")

    def _on_audio_level_change(self, level: float):
        """Update audio level display"""
        GLib.idle_add(self.recording_view.set_level, level)

    def _on_text_copied(self, text: str):
        """Handle text copied"""
        self._show_toast("Copied to clipboard")

    def _on_text_cleared(self):
        """Handle text cleared"""
        pass

    def _show_toast(self, message: str):
        """Show a toast notification"""
        toast = Adw.Toast.new(message)
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)
