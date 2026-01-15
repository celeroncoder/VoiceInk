"""VoiceInk main window"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, GLib


class VoiceInkWindow(Adw.ApplicationWindow):
    """Main application window"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("VoiceInk")
        self.set_default_size(800, 600)

        self._build_ui()

    def _build_ui(self):
        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        # Header bar
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(self._create_menu())
        self.header.pack_end(menu_button)

        # Content area with toolbar view
        toolbar_view = Adw.ToolbarView()
        self.main_box.append(toolbar_view)

        # Main content - placeholder for now
        content = Adw.Clamp()
        content.set_maximum_size(600)
        content.set_vexpand(True)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content_box.set_margin_top(48)
        content_box.set_margin_bottom(48)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        content.set_child(content_box)

        # Welcome status page
        status = Adw.StatusPage()
        status.set_icon_name("audio-input-microphone-symbolic")
        status.set_title("VoiceInk")
        status.set_description("Voice to text transcription powered by Whisper")
        content_box.append(status)

        # Record button
        self.record_button = Gtk.Button()
        self.record_button.set_label("Start Recording")
        self.record_button.add_css_class("suggested-action")
        self.record_button.add_css_class("pill")
        self.record_button.set_halign(Gtk.Align.CENTER)
        self.record_button.connect("clicked", self._on_record_clicked)
        content_box.append(self.record_button)

        # Transcription output
        self.transcription_view = Gtk.TextView()
        self.transcription_view.set_editable(False)
        self.transcription_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.transcription_view.set_vexpand(True)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.transcription_view)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(200)
        content_box.append(scrolled)

        toolbar_view.set_content(content)

        # State
        self.is_recording = False

    def _create_menu(self):
        menu = Gio.Menu()
        menu.append("About VoiceInk", "app.about")
        menu.append("Quit", "app.quit")
        return menu

    def _on_record_clicked(self, button):
        self.is_recording = not self.is_recording
        if self.is_recording:
            button.set_label("Stop Recording")
            button.remove_css_class("suggested-action")
            button.add_css_class("destructive-action")
            self._set_status("Recording...")
        else:
            button.set_label("Start Recording")
            button.remove_css_class("destructive-action")
            button.add_css_class("suggested-action")
            self._set_status("Ready")

    def _set_status(self, text):
        buffer = self.transcription_view.get_buffer()
        buffer.set_text(f"[{text}]")
