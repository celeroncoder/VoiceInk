"""History view for displaying transcription history"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gio, GLib, GObject, Gdk
from datetime import datetime
from typing import Optional, Callable

from ..models.transcription import Transcription, TranscriptionStatus
from ..services.history_service import HistoryService


class TranscriptionObject(GObject.Object):
    """GObject wrapper for Transcription for use in ListView"""

    __gtype_name__ = "TranscriptionObject"

    def __init__(self, transcription: Transcription):
        super().__init__()
        self.transcription = transcription

    @property
    def id(self) -> str:
        return self.transcription.id

    @property
    def text(self) -> str:
        return self.transcription.final_text

    @property
    def preview(self) -> str:
        text = self.text[:100]
        if len(self.text) > 100:
            text += "..."
        return text

    @property
    def created_at(self) -> datetime:
        return self.transcription.created_at

    @property
    def formatted_date(self) -> str:
        now = datetime.now()
        diff = now - self.created_at

        if diff.days == 0:
            return self.created_at.strftime("%H:%M")
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return self.created_at.strftime("%A")
        else:
            return self.created_at.strftime("%b %d")

    @property
    def duration_text(self) -> str:
        duration = self.transcription.duration
        if duration < 60:
            return f"{int(duration)}s"
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}m {seconds}s"

    @property
    def word_count(self) -> int:
        return len(self.text.split())


class HistoryView(Gtk.Box):
    """View for displaying and managing transcription history

    Features:
    - Scrollable list of transcriptions
    - Search/filter
    - Selection and actions (copy, delete)
    - Empty state
    """

    def __init__(
        self,
        history_service: Optional[HistoryService] = None,
        on_select: Optional[Callable[[Transcription], None]] = None,
    ):
        """Initialize the history view

        Args:
            history_service: Service for history operations
            on_select: Callback when transcription is selected
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._service = history_service or HistoryService()
        self._on_select = on_select
        self._model = Gio.ListStore.new(TranscriptionObject)

        self._build_ui()
        self._load_history()

        # Subscribe to changes
        self._service.set_on_change(self._load_history)

    def _build_ui(self):
        """Build the UI components"""
        # Search bar
        search_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_bar.set_margin_start(12)
        search_bar.set_margin_end(12)
        search_bar.set_margin_top(12)
        search_bar.set_margin_bottom(8)
        self.append(search_bar)

        # Search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search transcriptions...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_bar.append(self.search_entry)

        # Clear history button
        clear_button = Gtk.Button()
        clear_button.set_icon_name("edit-clear-all-symbolic")
        clear_button.set_tooltip_text("Clear History")
        clear_button.add_css_class("flat")
        clear_button.connect("clicked", self._on_clear_clicked)
        search_bar.append(clear_button)

        # Stats label
        self.stats_label = Gtk.Label(label="")
        self.stats_label.add_css_class("dim-label")
        self.stats_label.add_css_class("caption")
        self.stats_label.set_margin_start(12)
        self.stats_label.set_margin_bottom(8)
        self.stats_label.set_halign(Gtk.Align.START)
        self.append(self.stats_label)

        # Stack for list/empty state
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_vexpand(True)
        self.append(self.stack)

        # Empty state
        empty_page = Adw.StatusPage()
        empty_page.set_icon_name("document-open-recent-symbolic")
        empty_page.set_title("No History")
        empty_page.set_description("Your transcriptions will appear here")
        self.stack.add_named(empty_page, "empty")

        # List view
        self._setup_list_view()

    def _setup_list_view(self):
        """Setup the list view for history"""
        # Scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.stack.add_named(scrolled, "list")

        # Selection model
        self.selection = Gtk.SingleSelection.new(self._model)
        self.selection.connect("selection-changed", self._on_selection_changed)

        # List view
        self.list_view = Gtk.ListView.new(self.selection, self._create_factory())
        self.list_view.add_css_class("navigation-sidebar")
        scrolled.set_child(self.list_view)

    def _create_factory(self) -> Gtk.ListItemFactory:
        """Create factory for list items"""
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)
        return factory

    def _on_factory_setup(self, factory, list_item):
        """Setup list item widget"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Header row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(header)

        date_label = Gtk.Label()
        date_label.add_css_class("caption")
        date_label.add_css_class("dim-label")
        date_label.set_halign(Gtk.Align.START)
        header.append(date_label)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        duration_label = Gtk.Label()
        duration_label.add_css_class("caption")
        duration_label.add_css_class("dim-label")
        header.append(duration_label)

        # Preview text
        preview_label = Gtk.Label()
        preview_label.set_wrap(True)
        preview_label.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        preview_label.set_max_width_chars(50)
        preview_label.set_xalign(0)
        preview_label.set_lines(2)
        preview_label.set_ellipsize(True)
        box.append(preview_label)

        # Word count
        words_label = Gtk.Label()
        words_label.add_css_class("caption")
        words_label.add_css_class("dim-label")
        words_label.set_halign(Gtk.Align.START)
        box.append(words_label)

        # Store references
        box.date_label = date_label
        box.duration_label = duration_label
        box.preview_label = preview_label
        box.words_label = words_label

        list_item.set_child(box)

    def _on_factory_bind(self, factory, list_item):
        """Bind data to list item"""
        box = list_item.get_child()
        item = list_item.get_item()

        if item:
            box.date_label.set_label(item.formatted_date)
            box.duration_label.set_label(item.duration_text)
            box.preview_label.set_label(item.preview)
            box.words_label.set_label(f"{item.word_count} words")

    def _on_selection_changed(self, selection, position, n_items):
        """Handle selection change"""
        item = selection.get_selected_item()
        if item and self._on_select:
            self._on_select(item.transcription)

    def _on_search_changed(self, entry):
        """Handle search query change"""
        query = entry.get_text().strip()
        self._load_history(query)

    def _on_clear_clicked(self, button):
        """Handle clear history button"""
        # Show confirmation dialog
        dialog = Adw.MessageDialog.new(
            self.get_root(),
            "Clear History?",
            "This will permanently delete all transcription history."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_clear_response)
        dialog.present()

    def _on_clear_response(self, dialog, response):
        """Handle clear confirmation response"""
        if response == "clear":
            self._service.clear_history()
            self._load_history()

    def _load_history(self, query: str = ""):
        """Load transcription history

        Args:
            query: Optional search query
        """
        self._model.remove_all()

        if query:
            transcriptions = self._service.search(query)
        else:
            transcriptions = self._service.get_all()

        for t in transcriptions:
            self._model.append(TranscriptionObject(t))

        # Update stats
        stats = self._service.get_stats()
        self.stats_label.set_label(f"{stats['total']} transcriptions")

        # Show appropriate view
        if self._model.get_n_items() > 0:
            self.stack.set_visible_child_name("list")
        else:
            self.stack.set_visible_child_name("empty")

    def refresh(self):
        """Refresh the history list"""
        query = self.search_entry.get_text().strip()
        self._load_history(query)

    def get_selected(self) -> Optional[Transcription]:
        """Get currently selected transcription"""
        item = self.selection.get_selected_item()
        if item:
            return item.transcription
        return None

    def delete_selected(self) -> bool:
        """Delete the selected transcription

        Returns:
            True if deleted
        """
        item = self.selection.get_selected_item()
        if item:
            return self._service.delete_transcription(item.id)
        return False
