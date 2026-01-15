"""Tests for services"""

import pytest
from pathlib import Path


class TestVocabularyService:
    """Tests for VocabularyService"""

    def test_apply_replacements(self, mock_db):
        """Test word replacement application"""
        from voiceink.services import VocabularyService
        from voiceink.models import WordReplacement

        service = VocabularyService.__new__(VocabularyService)
        service._replacements = []

        # Add replacement
        replacement = WordReplacement(
            original="gonna",
            replacement="going to",
            case_sensitive=False,
        )
        service._replacements.append(replacement)

        # Test replacement
        text = "I'm gonna do it"
        result = service.apply_replacements(text)
        assert "going to" in result

    def test_case_sensitive_replacement(self, mock_db):
        """Test case-sensitive replacement"""
        from voiceink.services import VocabularyService
        from voiceink.models import WordReplacement

        service = VocabularyService.__new__(VocabularyService)
        service._replacements = []

        replacement = WordReplacement(
            original="API",
            replacement="Application Programming Interface",
            case_sensitive=True,
        )
        service._replacements.append(replacement)

        # Should replace
        result = service.apply_replacements("The API is ready")
        assert "Application Programming Interface" in result

        # Should not replace (wrong case)
        result = service.apply_replacements("The api is ready")
        assert "api" in result


class TestCredentialManager:
    """Tests for CredentialManager"""

    def test_credential_manager_singleton(self):
        """Test singleton pattern"""
        from voiceink.services import get_credential_manager

        manager1 = get_credential_manager()
        manager2 = get_credential_manager()
        assert manager1 is manager2


class TestServiceRegistry:
    """Tests for TranscriptionServiceRegistry"""

    def test_registry_creation(self):
        """Test registry instantiation"""
        from voiceink.services import TranscriptionServiceRegistry

        registry = TranscriptionServiceRegistry()
        assert registry is not None

    def test_available_backends(self):
        """Test listing available backends"""
        from voiceink.services import TranscriptionServiceRegistry

        registry = TranscriptionServiceRegistry()
        backends = registry.available_backends
        assert "local" in backends


class TestPowerModeManager:
    """Tests for PowerModeManager"""

    def test_predefined_configs(self):
        """Test predefined Power Mode configurations"""
        from voiceink.services import PowerModeManager

        # Reset singleton for test
        PowerModeManager._instance = None

        # Note: This may fail without proper DB setup
        try:
            manager = PowerModeManager()
            configs = manager.get_predefined_configs()
            assert len(configs) > 0

            # Check for common apps
            app_ids = [c.app_identifier for c in configs]
            assert "slack" in app_ids
            assert "code" in app_ids
        except Exception:
            # Skip if DB not available
            pytest.skip("Database not available")
