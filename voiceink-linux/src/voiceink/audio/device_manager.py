"""Audio device management for Linux (PipeWire/PulseAudio/ALSA)"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import threading

logger = logging.getLogger(__name__)

# Try to import sounddevice
try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    logger.warning("sounddevice not installed, audio recording unavailable")


class AudioBackend(Enum):
    """Available audio backends"""
    PIPEWIRE = "pipewire"
    PULSEAUDIO = "pulseaudio"
    ALSA = "alsa"
    UNKNOWN = "unknown"


@dataclass
class AudioDevice:
    """Audio input device information"""
    id: int
    name: str
    channels: int
    sample_rate: float
    is_default: bool = False
    host_api: str = ""

    @property
    def display_name(self) -> str:
        """User-friendly display name"""
        if self.is_default:
            return f"{self.name} (Default)"
        return self.name


class DeviceManager:
    """Manages audio input devices

    Provides device enumeration, selection, and hot-plug monitoring.
    Uses sounddevice (PortAudio) which works with PipeWire, PulseAudio, and ALSA.
    """

    def __init__(self):
        """Initialize the device manager"""
        self._devices: list[AudioDevice] = []
        self._current_device: Optional[AudioDevice] = None
        self._lock = threading.Lock()
        self._backend = AudioBackend.UNKNOWN

        if HAS_SOUNDDEVICE:
            self._detect_backend()
            self.refresh_devices()

    @property
    def is_available(self) -> bool:
        """Check if audio is available"""
        return HAS_SOUNDDEVICE

    @property
    def backend(self) -> AudioBackend:
        """Get the detected audio backend"""
        return self._backend

    @property
    def devices(self) -> list[AudioDevice]:
        """Get list of available input devices"""
        with self._lock:
            return self._devices.copy()

    @property
    def current_device(self) -> Optional[AudioDevice]:
        """Get currently selected device"""
        return self._current_device

    @property
    def default_device(self) -> Optional[AudioDevice]:
        """Get the default input device"""
        with self._lock:
            for device in self._devices:
                if device.is_default:
                    return device
            return self._devices[0] if self._devices else None

    def _detect_backend(self):
        """Detect which audio backend is in use"""
        if not HAS_SOUNDDEVICE:
            return

        try:
            # Check host APIs
            host_apis = sd.query_hostapis()
            for api in host_apis:
                name = api.get("name", "").lower()
                if "pipewire" in name:
                    self._backend = AudioBackend.PIPEWIRE
                    break
                elif "pulse" in name:
                    self._backend = AudioBackend.PULSEAUDIO
                    break
                elif "alsa" in name:
                    self._backend = AudioBackend.ALSA
                    # Don't break - PipeWire or Pulse might come later

            logger.info(f"Detected audio backend: {self._backend.value}")
        except Exception as e:
            logger.error(f"Error detecting audio backend: {e}")

    def refresh_devices(self) -> list[AudioDevice]:
        """Refresh the list of available devices

        Returns:
            Updated list of devices
        """
        if not HAS_SOUNDDEVICE:
            return []

        with self._lock:
            self._devices.clear()

            try:
                devices = sd.query_devices()
                default_input = sd.default.device[0]
                host_apis = sd.query_hostapis()

                for i, dev in enumerate(devices):
                    # Only include input devices
                    if dev.get("max_input_channels", 0) > 0:
                        host_api_idx = dev.get("hostapi", 0)
                        host_api_name = ""
                        if host_api_idx < len(host_apis):
                            host_api_name = host_apis[host_api_idx].get("name", "")

                        device = AudioDevice(
                            id=i,
                            name=dev.get("name", f"Device {i}"),
                            channels=dev.get("max_input_channels", 1),
                            sample_rate=dev.get("default_samplerate", 48000),
                            is_default=(i == default_input),
                            host_api=host_api_name,
                        )
                        self._devices.append(device)

                logger.info(f"Found {len(self._devices)} input devices")

            except Exception as e:
                logger.error(f"Error enumerating devices: {e}")

            return self._devices.copy()

    def select_device(self, device_id: int) -> bool:
        """Select a device by ID

        Args:
            device_id: Device ID to select

        Returns:
            True if device was selected successfully
        """
        with self._lock:
            for device in self._devices:
                if device.id == device_id:
                    self._current_device = device
                    logger.info(f"Selected device: {device.name}")
                    return True

        logger.warning(f"Device not found: {device_id}")
        return False

    def select_device_by_name(self, name: str) -> bool:
        """Select a device by name (partial match)

        Args:
            name: Device name to search for

        Returns:
            True if a matching device was selected
        """
        name_lower = name.lower()
        with self._lock:
            for device in self._devices:
                if name_lower in device.name.lower():
                    self._current_device = device
                    logger.info(f"Selected device: {device.name}")
                    return True

        logger.warning(f"No device matching: {name}")
        return False

    def select_default(self) -> bool:
        """Select the default input device

        Returns:
            True if default device was selected
        """
        default = self.default_device
        if default:
            self._current_device = default
            logger.info(f"Selected default device: {default.name}")
            return True
        return False

    def get_device(self, device_id: int) -> Optional[AudioDevice]:
        """Get device by ID

        Args:
            device_id: Device ID

        Returns:
            AudioDevice or None if not found
        """
        with self._lock:
            for device in self._devices:
                if device.id == device_id:
                    return device
        return None
