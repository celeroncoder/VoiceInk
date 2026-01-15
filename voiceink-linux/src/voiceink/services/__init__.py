"""VoiceInk services module"""

from .local_transcription import LocalTranscriptionService
from .history_service import HistoryService
from .credentials import CredentialManager, get_credential_manager
from .ai_enhancement import AIEnhancementService, AIProvider
from .service_registry import TranscriptionServiceRegistry
from .tray_manager import TrayManager
from .hotkey_manager import HotkeyManager, Hotkey, DisplayServer
from .clipboard_manager import ClipboardManager
from .notification_service import NotificationService, NotificationType
from .autostart_manager import AutostartManager
from .vocabulary_service import VocabularyService

__all__ = [
    "LocalTranscriptionService",
    "HistoryService",
    "CredentialManager",
    "get_credential_manager",
    "AIEnhancementService",
    "AIProvider",
    "TranscriptionServiceRegistry",
    "TrayManager",
    "HotkeyManager",
    "Hotkey",
    "DisplayServer",
    "ClipboardManager",
    "NotificationService",
    "NotificationType",
    "AutostartManager",
    "VocabularyService",
]
