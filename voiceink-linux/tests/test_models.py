"""Tests for data models"""

import pytest
from datetime import datetime


class TestTranscription:
    """Tests for Transcription model"""

    def test_transcription_creation(self):
        """Test creating a transcription"""
        from voiceink.models import Transcription, TranscriptionStatus

        t = Transcription(
            text="Hello world",
            status=TranscriptionStatus.COMPLETED,
        )

        assert t.text == "Hello world"
        assert t.status == TranscriptionStatus.COMPLETED
        assert t.id is not None
        assert isinstance(t.created_at, datetime)

    def test_transcription_to_dict(self):
        """Test converting transcription to dict"""
        from voiceink.models import Transcription, TranscriptionStatus

        t = Transcription(
            text="Test text",
            status=TranscriptionStatus.COMPLETED,
            duration=5.5,
            model="base",
        )

        data = t.to_dict()
        assert data["text"] == "Test text"
        assert data["duration"] == 5.5
        assert data["model"] == "base"

    def test_transcription_from_dict(self):
        """Test creating transcription from dict"""
        from voiceink.models import Transcription

        data = {
            "id": "test-id",
            "text": "From dict",
            "status": "completed",
            "created_at": "2025-01-15T12:00:00",
        }

        t = Transcription.from_dict(data)
        assert t.id == "test-id"
        assert t.text == "From dict"


class TestVocabulary:
    """Tests for Vocabulary models"""

    def test_vocabulary_word(self):
        """Test VocabularyWord model"""
        from voiceink.models import VocabularyWord

        word = VocabularyWord(
            word="VoiceInk",
            pronunciation="voice ink",
            category="product",
        )

        assert word.word == "VoiceInk"
        assert word.pronunciation == "voice ink"

    def test_word_replacement(self):
        """Test WordReplacement model"""
        from voiceink.models import WordReplacement

        replacement = WordReplacement(
            original="gonna",
            replacement="going to",
            case_sensitive=False,
        )

        assert replacement.original == "gonna"
        assert replacement.replacement == "going to"
        assert not replacement.case_sensitive


class TestPowerMode:
    """Tests for PowerMode models"""

    def test_power_mode_config(self):
        """Test PowerModeConfig model"""
        from voiceink.models import PowerModeConfig

        config = PowerModeConfig(
            app_identifier="code",
            display_name="VS Code",
            emoji="💻",
            ai_enhancement_enabled=True,
            ai_prompt="Format as code",
        )

        assert config.app_identifier == "code"
        assert config.display_name == "VS Code"
        assert config.ai_enhancement_enabled

    def test_power_mode_to_dict(self):
        """Test PowerModeConfig serialization"""
        from voiceink.models import PowerModeConfig

        config = PowerModeConfig(
            app_identifier="slack",
            display_name="Slack",
        )

        data = config.to_dict()
        assert data["app_identifier"] == "slack"
        assert "id" in data
        assert "created_at" in data

    def test_active_window(self):
        """Test ActiveWindow model"""
        from voiceink.models import ActiveWindow

        window = ActiveWindow(
            window_class="code.Code",
            window_title="main.py - VoiceInk",
            pid=1234,
        )

        assert window.window_class == "code.Code"
        assert window.app_identifier == "code.code"  # lowercase
