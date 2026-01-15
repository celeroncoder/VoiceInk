"""Secure credential management using libsecret/keyring"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import keyring
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    logger.warning("keyring not installed, credentials will not be persisted securely")


class CredentialManager:
    """Secure credential storage using Secret Service API

    Uses keyring (libsecret on Linux) for secure credential storage.
    Falls back to in-memory storage if keyring is unavailable.
    """

    SERVICE_NAME = "org.voiceink.VoiceInk"

    def __init__(self):
        """Initialize credential manager"""
        self._fallback_store: dict[str, str] = {}

    @property
    def is_secure(self) -> bool:
        """Check if secure storage is available"""
        return HAS_KEYRING

    def get(self, key: str) -> Optional[str]:
        """Get a credential

        Args:
            key: Credential key

        Returns:
            Credential value or None if not found
        """
        if HAS_KEYRING:
            try:
                return keyring.get_password(self.SERVICE_NAME, key)
            except Exception as e:
                logger.warning(f"Failed to get credential from keyring: {e}")

        return self._fallback_store.get(key)

    def set(self, key: str, value: str):
        """Store a credential

        Args:
            key: Credential key
            value: Credential value
        """
        if HAS_KEYRING:
            try:
                keyring.set_password(self.SERVICE_NAME, key, value)
                logger.debug(f"Stored credential: {key}")
                return
            except Exception as e:
                logger.warning(f"Failed to store credential in keyring: {e}")

        # Fallback to memory
        self._fallback_store[key] = value

    def delete(self, key: str) -> bool:
        """Delete a credential

        Args:
            key: Credential key

        Returns:
            True if deleted successfully
        """
        if HAS_KEYRING:
            try:
                keyring.delete_password(self.SERVICE_NAME, key)
                logger.debug(f"Deleted credential: {key}")
                return True
            except keyring.errors.PasswordDeleteError:
                pass
            except Exception as e:
                logger.warning(f"Failed to delete credential from keyring: {e}")

        if key in self._fallback_store:
            del self._fallback_store[key]
            return True

        return False

    def has(self, key: str) -> bool:
        """Check if a credential exists

        Args:
            key: Credential key

        Returns:
            True if credential exists
        """
        return self.get(key) is not None


# Global instance
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """Get the global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
