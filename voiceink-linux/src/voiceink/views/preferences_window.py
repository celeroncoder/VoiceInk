"""Preferences window for VoiceInk settings"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Gio
from typing import Optional


class PreferencesWindow(Adw.PreferencesWindow):
    """Application preferences window

    Contains settings for:
    - Transcription model selection
    - Audio device selection
    - Language settings
    - Hotkey configuration
    - AI enhancement settings
    """

    def __init__(self, parent: Optional[Gtk.Window] = None, **kwargs):
        """Initialize the preferences window

        Args:
            parent: Parent window
        """
        super().__init__(**kwargs)

        self.set_title("Preferences")
        self.set_default_size(600, 700)
        self.set_modal(True)

        if parent:
            self.set_transient_for(parent)

        self._build_ui()

    def _build_ui(self):
        """Build the preferences UI"""
        # Transcription page
        self._build_transcription_page()

        # Audio page
        self._build_audio_page()

        # AI Enhancement page
        self._build_ai_page()

        # About page
        self._build_about_page()

    def _build_transcription_page(self):
        """Build transcription settings page"""
        page = Adw.PreferencesPage()
        page.set_title("Transcription")
        page.set_icon_name("audio-input-microphone-symbolic")
        self.add(page)

        # Model group
        model_group = Adw.PreferencesGroup()
        model_group.set_title("Whisper Model")
        model_group.set_description("Select the model for local transcription")
        page.add(model_group)

        # Model selector
        self.model_row = Adw.ComboRow()
        self.model_row.set_title("Model Size")
        self.model_row.set_subtitle("Larger models are more accurate but slower")

        model_list = Gtk.StringList.new([
            "Tiny (75 MB) - Fastest",
            "Base (142 MB) - Recommended",
            "Small (466 MB) - Better quality",
            "Medium (1.5 GB) - High quality",
            "Large (3.1 GB) - Best quality",
        ])
        self.model_row.set_model(model_list)
        self.model_row.set_selected(1)  # Default to Base
        model_group.add(self.model_row)

        # Download button
        download_row = Adw.ActionRow()
        download_row.set_title("Download Model")
        download_row.set_subtitle("Download selected model if not already available")

        download_button = Gtk.Button(label="Download")
        download_button.set_valign(Gtk.Align.CENTER)
        download_button.add_css_class("suggested-action")
        download_row.add_suffix(download_button)
        model_group.add(download_row)

        # Language group
        lang_group = Adw.PreferencesGroup()
        lang_group.set_title("Language")
        page.add(lang_group)

        # Language selector
        self.language_row = Adw.ComboRow()
        self.language_row.set_title("Transcription Language")
        self.language_row.set_subtitle("Select language or auto-detect")

        lang_list = Gtk.StringList.new([
            "Auto-detect",
            "English",
            "Spanish",
            "French",
            "German",
            "Chinese",
            "Japanese",
            "Korean",
            "Portuguese",
            "Russian",
        ])
        self.language_row.set_model(lang_list)
        self.language_row.set_selected(0)
        lang_group.add(self.language_row)

        # Translate option
        self.translate_row = Adw.SwitchRow()
        self.translate_row.set_title("Translate to English")
        self.translate_row.set_subtitle("Translate non-English audio to English")
        lang_group.add(self.translate_row)

    def _build_audio_page(self):
        """Build audio settings page"""
        page = Adw.PreferencesPage()
        page.set_title("Audio")
        page.set_icon_name("audio-card-symbolic")
        self.add(page)

        # Input device group
        device_group = Adw.PreferencesGroup()
        device_group.set_title("Input Device")
        device_group.set_description("Select the microphone for recording")
        page.add(device_group)

        # Device selector
        self.device_row = Adw.ComboRow()
        self.device_row.set_title("Microphone")
        self.device_row.set_subtitle("Select audio input device")

        # Will be populated with actual devices
        device_list = Gtk.StringList.new(["Default"])
        self.device_row.set_model(device_list)
        device_group.add(self.device_row)

        # Refresh button
        refresh_row = Adw.ActionRow()
        refresh_row.set_title("Refresh Devices")
        refresh_row.set_subtitle("Scan for audio input devices")

        refresh_button = Gtk.Button()
        refresh_button.set_icon_name("view-refresh-symbolic")
        refresh_button.set_valign(Gtk.Align.CENTER)
        refresh_row.add_suffix(refresh_button)
        device_group.add(refresh_row)

        # Audio settings group
        audio_group = Adw.PreferencesGroup()
        audio_group.set_title("Recording Settings")
        page.add(audio_group)

        # Auto-stop silence
        self.silence_row = Adw.SwitchRow()
        self.silence_row.set_title("Auto-stop on Silence")
        self.silence_row.set_subtitle("Stop recording after silence is detected")
        audio_group.add(self.silence_row)

        # Sound feedback
        self.sound_row = Adw.SwitchRow()
        self.sound_row.set_title("Sound Feedback")
        self.sound_row.set_subtitle("Play sounds when starting/stopping")
        self.sound_row.set_active(True)
        audio_group.add(self.sound_row)

    def _build_ai_page(self):
        """Build AI enhancement settings page"""
        page = Adw.PreferencesPage()
        page.set_title("AI Enhancement")
        page.set_icon_name("starred-symbolic")
        self.add(page)

        # Enable group
        enable_group = Adw.PreferencesGroup()
        enable_group.set_title("AI Enhancement")
        enable_group.set_description("Use AI to improve transcription quality")
        page.add(enable_group)

        # Enable switch
        self.ai_enable_row = Adw.SwitchRow()
        self.ai_enable_row.set_title("Enable AI Enhancement")
        self.ai_enable_row.set_subtitle("Process transcriptions with AI for better results")
        enable_group.add(self.ai_enable_row)

        # Provider group
        provider_group = Adw.PreferencesGroup()
        provider_group.set_title("AI Provider")
        page.add(provider_group)

        # Provider selector
        self.provider_row = Adw.ComboRow()
        self.provider_row.set_title("Provider")
        self.provider_row.set_subtitle("Select AI service provider")

        provider_list = Gtk.StringList.new([
            "OpenAI",
            "Anthropic",
            "Groq",
            "Ollama (Local)",
            "Custom API",
        ])
        self.provider_row.set_model(provider_list)
        provider_group.add(self.provider_row)

        # API key
        self.api_key_row = Adw.PasswordEntryRow()
        self.api_key_row.set_title("API Key")
        provider_group.add(self.api_key_row)

        # Prompt group
        prompt_group = Adw.PreferencesGroup()
        prompt_group.set_title("Enhancement Prompt")
        page.add(prompt_group)

        # Custom prompt
        prompt_row = Adw.ActionRow()
        prompt_row.set_title("Custom Prompt")
        prompt_row.set_subtitle("Configure how AI enhances your transcriptions")

        prompt_button = Gtk.Button(label="Edit")
        prompt_button.set_valign(Gtk.Align.CENTER)
        prompt_row.add_suffix(prompt_button)
        prompt_group.add(prompt_row)

    def _build_about_page(self):
        """Build about page"""
        page = Adw.PreferencesPage()
        page.set_title("About")
        page.set_icon_name("help-about-symbolic")
        self.add(page)

        # About group
        about_group = Adw.PreferencesGroup()
        page.add(about_group)

        # Version
        version_row = Adw.ActionRow()
        version_row.set_title("Version")
        version_row.set_subtitle("0.1.0")
        about_group.add(version_row)

        # License
        license_row = Adw.ActionRow()
        license_row.set_title("License")
        license_row.set_subtitle("GPL-3.0")
        about_group.add(license_row)

        # Links group
        links_group = Adw.PreferencesGroup()
        links_group.set_title("Links")
        page.add(links_group)

        # GitHub
        github_row = Adw.ActionRow()
        github_row.set_title("Source Code")
        github_row.set_subtitle("github.com/celeroncoder/VoiceInk")
        github_row.set_activatable(True)
        links_group.add(github_row)

        # Website
        website_row = Adw.ActionRow()
        website_row.set_title("Website")
        website_row.set_subtitle("tryvoiceink.com")
        website_row.set_activatable(True)
        links_group.add(website_row)

    def set_devices(self, devices: list[str]):
        """Update the device list

        Args:
            devices: List of device names
        """
        device_list = Gtk.StringList.new(devices if devices else ["Default"])
        self.device_row.set_model(device_list)

    def get_selected_model(self) -> int:
        """Get selected model index"""
        return self.model_row.get_selected()

    def get_selected_device(self) -> int:
        """Get selected device index"""
        return self.device_row.get_selected()

    def get_translate_enabled(self) -> bool:
        """Get translate to English setting"""
        return self.translate_row.get_active()

    def get_ai_enabled(self) -> bool:
        """Get AI enhancement enabled setting"""
        return self.ai_enable_row.get_active()
