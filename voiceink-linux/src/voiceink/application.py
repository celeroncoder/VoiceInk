"""VoiceInk GTK Application"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib

from voiceink import __app_id__, __version__
from voiceink.window import VoiceInkWindow


class VoiceInkApplication(Adw.Application):
    """Main application class"""

    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.set_resource_base_path("/org/voiceink/VoiceInk")

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = VoiceInkWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._setup_actions()

    def _setup_actions(self):
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def _on_about(self, action, param):
        about = Adw.AboutDialog(
            application_name="VoiceInk",
            application_icon=__app_id__,
            version=__version__,
            developer_name="VoiceInk Team",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/celeroncoder/VoiceInk",
            issue_url="https://github.com/celeroncoder/VoiceInk/issues",
            developers=["VoiceInk Team"],
            copyright="© 2024 VoiceInk",
            comments="Voice to text transcription powered by Whisper",
        )
        about.present(self.props.active_window)


# Need Gtk import for License enum
from gi.repository import Gtk
