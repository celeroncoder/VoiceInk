"""Transcription display view"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gdk, GLib
from typing import Optional, Callable


class TranscriptionView(Gtk.Box):
    """View for displaying transcription results

    Contains:
    - Scrollable text view for transcription
    - Copy to clipboard button
    - Clear button
    - Word count display
    """

    def __init__(
        self,
        on_copy: Optional[Callable[[str], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
    ):
        """Initialize the transcription view

        Args:
            on_copy: Callback when text is copied
            on_clear: Callback when text is cleared
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._on_copy = on_copy
        self._on_clear = on_clear

        self._build_ui()

    def _build_ui(self):
        """Build the UI components"""
        # Main content box with frame
        frame = Gtk.Frame()
        frame.set_margin_start(24)
        frame.set_margin_end(24)
        frame.set_vexpand(True)
        self.append(frame)

        # Scrolled window for text
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(200)
        frame.set_child(scrolled)

        # Text view
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_top_margin(12)
        self.text_view.set_bottom_margin(12)
        self.text_view.set_left_margin(12)
        self.text_view.set_right_margin(12)
        self.text_view.add_css_class("transcription-text")
        scrolled.set_child(self.text_view)

        # Get the buffer
        self.buffer = self.text_view.get_buffer()
        self.buffer.connect("changed", self._on_buffer_changed)

        # Placeholder when empty
        self._set_placeholder()

        # Bottom action bar
        action_bar = Gtk.ActionBar()
        action_bar.set_margin_start(24)
        action_bar.set_margin_end(24)
        action_bar.set_margin_bottom(24)
        self.append(action_bar)

        # Word count label
        self.word_count_label = Gtk.Label(label="0 words")
        self.word_count_label.add_css_class("dim-label")
        self.word_count_label.add_css_class("caption")
        action_bar.pack_start(self.word_count_label)

        # Copy button
        self.copy_button = Gtk.Button()
        self.copy_button.set_icon_name("edit-copy-symbolic")
        self.copy_button.set_tooltip_text("Copy to Clipboard")
        self.copy_button.add_css_class("flat")
        self.copy_button.set_sensitive(False)
        self.copy_button.connect("clicked", self._on_copy_clicked)
        action_bar.pack_end(self.copy_button)

        # Clear button
        self.clear_button = Gtk.Button()
        self.clear_button.set_icon_name("edit-clear-symbolic")
        self.clear_button.set_tooltip_text("Clear")
        self.clear_button.add_css_class("flat")
        self.clear_button.set_sensitive(False)
        self.clear_button.connect("clicked", self._on_clear_clicked)
        action_bar.pack_end(self.clear_button)

    def _set_placeholder(self):
        """Set placeholder text"""
        self.buffer.set_text("Transcription will appear here...")
        # Mark as placeholder
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        tag = self.buffer.create_tag("placeholder", foreground="#888888")
        self.buffer.apply_tag(tag, start, end)
        self._is_placeholder = True

    def _clear_placeholder(self):
        """Clear placeholder if present"""
        if getattr(self, '_is_placeholder', False):
            self.buffer.set_text("")
            self._is_placeholder = False

    def _on_buffer_changed(self, buffer):
        """Handle buffer content changes"""
        text = self.get_text()
        word_count = len(text.split()) if text and not self._is_placeholder else 0
        self.word_count_label.set_label(f"{word_count} word{'s' if word_count != 1 else ''}")

        has_text = bool(text) and not getattr(self, '_is_placeholder', False)
        self.copy_button.set_sensitive(has_text)
        self.clear_button.set_sensitive(has_text)

    def _on_copy_clicked(self, button):
        """Handle copy button click"""
        text = self.get_text()
        if text:
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(text)

            if self._on_copy:
                self._on_copy(text)

    def _on_clear_clicked(self, button):
        """Handle clear button click"""
        self.clear()
        if self._on_clear:
            self._on_clear()

    def set_text(self, text: str):
        """Set the transcription text

        Args:
            text: Text to display
        """
        self._clear_placeholder()
        self.buffer.set_text(text)
        self._is_placeholder = False

    def append_text(self, text: str):
        """Append text to the transcription

        Args:
            text: Text to append
        """
        self._clear_placeholder()
        end_iter = self.buffer.get_end_iter()
        self.buffer.insert(end_iter, text)
        self._is_placeholder = False

    def get_text(self) -> str:
        """Get the current transcription text

        Returns:
            Current text content
        """
        if getattr(self, '_is_placeholder', False):
            return ""
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        return self.buffer.get_text(start, end, False)

    def clear(self):
        """Clear the transcription"""
        self._set_placeholder()

    def set_loading(self, loading: bool):
        """Set loading state

        Args:
            loading: Whether transcription is loading
        """
        self.text_view.set_sensitive(not loading)
        if loading:
            self._clear_placeholder()
            self.buffer.set_text("Transcribing...")
            self._is_placeholder = True
