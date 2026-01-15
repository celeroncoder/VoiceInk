"""Tests for audio utilities"""

import pytest
import numpy as np
from pathlib import Path


class TestAudioUtils:
    """Tests for audio utility functions"""

    def test_convert_to_16khz_mono(self, sample_audio_data):
        """Test audio conversion to 16kHz mono"""
        from voiceink.audio.utils import convert_to_16khz_mono

        # Input is already 16kHz mono
        result = convert_to_16khz_mono(sample_audio_data, 16000)
        assert result.dtype == np.float32
        assert len(result.shape) == 1

    def test_convert_stereo_to_mono(self):
        """Test stereo to mono conversion"""
        from voiceink.audio.utils import convert_to_16khz_mono

        # Create stereo audio
        duration = 0.1
        sample_rate = 16000
        samples = int(sample_rate * duration)
        stereo = np.random.randn(samples, 2).astype(np.float32)

        result = convert_to_16khz_mono(stereo, sample_rate)
        assert len(result.shape) == 1
        assert len(result) == samples


class TestDeviceManager:
    """Tests for audio device management"""

    def test_device_manager_creation(self):
        """Test DeviceManager instantiation"""
        from voiceink.audio import DeviceManager

        manager = DeviceManager()
        assert manager is not None

    def test_get_input_devices(self):
        """Test listing input devices"""
        from voiceink.audio import DeviceManager

        manager = DeviceManager()
        devices = manager.get_input_devices()
        # Should return a list (may be empty in CI)
        assert isinstance(devices, list)


class TestRecordingConfig:
    """Tests for recording configuration"""

    def test_default_config(self):
        """Test default recording config"""
        from voiceink.audio import RecordingConfig

        config = RecordingConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.dtype == np.float32
