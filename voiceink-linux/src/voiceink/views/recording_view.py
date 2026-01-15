"""Recording view with controls and level meter"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, GLib, Gdk
from typing import Optional, Callable


class RecordingView(Gtk.Box):
    """Recording controls and audio level visualization

    Contains:
    - Record/stop button
    - Audio level meter
    - Recording duration display
    - Cancel button
    """

    def __init__(
        self,
        on_record_start: Optional[Callable[[], None]] = None,
        on_record_stop: Optional[Callable[[], None]] = None,
        on_record_cancel: Optional[Callable[[], None]] = None,
    ):
        """Initialize the recording view

        Args:
            on_record_start: Callback when recording starts
            on_record_stop: Callback when recording stops
            on_record_cancel: Callback when recording is cancelled
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        self._on_record_start = on_record_start
        self._on_record_stop = on_record_stop
        self._on_record_cancel = on_record_cancel

        self._is_recording = False
        self._duration = 0.0
        self._level = 0.0
        self._timer_id: Optional[int] = None

        self._build_ui()

    def _build_ui(self):
        """Build the UI components"""
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)

        # Status icon/animation area
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.status_box.set_halign(Gtk.Align.CENTER)
        self.append(self.status_box)

        # Microphone icon
        self.mic_icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic")
        self.mic_icon.set_pixel_size(64)
        self.mic_icon.add_css_class("dim-label")
        self.status_box.append(self.mic_icon)

        # Duration label
        self.duration_label = Gtk.Label(label="0:00")
        self.duration_label.add_css_class("title-1")
        self.duration_label.set_opacity(0.0)
        self.status_box.append(self.duration_label)

        # Audio level meter
        level_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        level_box.set_halign(Gtk.Align.CENTER)
        self.append(level_box)

        level_label = Gtk.Label(label="Audio Level")
        level_label.add_css_class("dim-label")
        level_label.add_css_class("caption")
        level_box.append(level_label)

        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0.0)
        self.level_bar.set_max_value(1.0)
        self.level_bar.set_value(0.0)
        self.level_bar.set_size_request(300, 8)
        self.level_bar.add_css_class("recording-level")
        level_box.append(self.level_bar)

        # Button row
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(16)
        self.append(button_box)

        # Cancel button (hidden by default)
        self.cancel_button = Gtk.Button()
        self.cancel_button.set_icon_name("process-stop-symbolic")
        self.cancel_button.set_tooltip_text("Cancel Recording")
        self.cancel_button.add_css_class("circular")
        self.cancel_button.add_css_class("flat")
        self.cancel_button.set_visible(False)
        self.cancel_button.connect("clicked", self._on_cancel_clicked)
        button_box.append(self.cancel_button)

        # Main record button
        self.record_button = Gtk.Button()
        self.record_button.set_icon_name("media-record-symbolic")
        self.record_button.set_tooltip_text("Start Recording")
        self.record_button.add_css_class("circular")
        self.record_button.add_css_class("suggested-action")
        self.record_button.set_size_request(64, 64)
        self.record_button.connect("clicked", self._on_record_clicked)
        button_box.append(self.record_button)

        # Spacer for cancel button balance
        spacer = Gtk.Box()
        spacer.set_size_request(40, 40)
        button_box.append(spacer)

        # Status label
        self.status_label = Gtk.Label(label="Press to start recording")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_margin_top(8)
        self.append(self.status_label)

        # Add custom CSS
        self._add_css()

    def _add_css(self):
        """Add custom CSS styles"""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .recording-active {
                color: @error_color;
            }
            .recording-level {
                border-radius: 4px;
            }
            levelbar block.filled {
                background-color: @accent_color;
                border-radius: 4px;
            }
            levelbar block.recording-high {
                background-color: @warning_color;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _on_record_clicked(self, button):
        """Handle record button click"""
        if self._is_recording:
            self.stop_recording()
            if self._on_record_stop:
                self._on_record_stop()
        else:
            self.start_recording()
            if self._on_record_start:
                self._on_record_start()

    def _on_cancel_clicked(self, button):
        """Handle cancel button click"""
        self.stop_recording()
        if self._on_record_cancel:
            self._on_record_cancel()

    def start_recording(self):
        """Start recording UI state"""
        self._is_recording = True
        self._duration = 0.0

        # Update button
        self.record_button.set_icon_name("media-playback-stop-symbolic")
        self.record_button.set_tooltip_text("Stop Recording")
        self.record_button.remove_css_class("suggested-action")
        self.record_button.add_css_class("destructive-action")

        # Show cancel and duration
        self.cancel_button.set_visible(True)
        self.duration_label.set_opacity(1.0)

        # Update icon
        self.mic_icon.remove_css_class("dim-label")
        self.mic_icon.add_css_class("recording-active")

        # Update status
        self.status_label.set_label("Recording...")

        # Start timer
        self._timer_id = GLib.timeout_add(100, self._update_timer)

    def stop_recording(self):
        """Stop recording UI state"""
        self._is_recording = False

        # Stop timer
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

        # Update button
        self.record_button.set_icon_name("media-record-symbolic")
        self.record_button.set_tooltip_text("Start Recording")
        self.record_button.remove_css_class("destructive-action")
        self.record_button.add_css_class("suggested-action")

        # Hide cancel
        self.cancel_button.set_visible(False)

        # Update icon
        self.mic_icon.add_css_class("dim-label")
        self.mic_icon.remove_css_class("recording-active")

        # Reset level
        self.set_level(0.0)

    def set_transcribing(self):
        """Set transcribing state"""
        self.status_label.set_label("Transcribing...")
        self.record_button.set_sensitive(False)

    def set_ready(self):
        """Set ready state"""
        self.status_label.set_label("Press to start recording")
        self.record_button.set_sensitive(True)
        self.duration_label.set_opacity(0.0)

    def _update_timer(self) -> bool:
        """Update duration timer"""
        if not self._is_recording:
            return False

        self._duration += 0.1
        minutes = int(self._duration // 60)
        seconds = int(self._duration % 60)
        self.duration_label.set_label(f"{minutes}:{seconds:02d}")

        return True

    def set_level(self, level: float):
        """Set the audio level (0.0 - 1.0)"""
        self._level = max(0.0, min(1.0, level))
        self.level_bar.set_value(self._level)

    @property
    def is_recording(self) -> bool:
        """Check if currently in recording state"""
        return self._is_recording

    @property
    def duration(self) -> float:
        """Get current recording duration"""
        return self._duration
