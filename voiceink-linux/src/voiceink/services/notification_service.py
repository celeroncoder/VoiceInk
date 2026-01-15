"""Desktop notification service"""

import logging
from enum import Enum
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")

from gi.repository import Gio, GLib

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Notification types for styling"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationService:
    """Sends desktop notifications

    Uses Gio.Notification for GNOME integration.
    """

    def __init__(self, app: Optional[Gio.Application] = None):
        """Initialize notification service

        Args:
            app: Gio.Application instance (required for notifications)
        """
        self._app = app
        self._notification_id = 0

    def set_application(self, app: Gio.Application):
        """Set the application instance

        Args:
            app: Gio.Application instance
        """
        self._app = app

    def send(
        self,
        title: str,
        body: Optional[str] = None,
        notification_type: NotificationType = NotificationType.INFO,
        icon: Optional[str] = None,
        action: Optional[tuple[str, str]] = None,
    ) -> bool:
        """Send a desktop notification

        Args:
            title: Notification title
            body: Optional notification body
            notification_type: Type for icon/styling
            icon: Optional custom icon name
            action: Optional (action_id, label) tuple

        Returns:
            True if sent successfully
        """
        if not self._app:
            logger.warning("No application set, cannot send notification")
            return False

        try:
            notification = Gio.Notification.new(title)

            if body:
                notification.set_body(body)

            # Set icon based on type or custom
            if icon:
                notification.set_icon(Gio.ThemedIcon.new(icon))
            else:
                type_icons = {
                    NotificationType.INFO: "dialog-information-symbolic",
                    NotificationType.SUCCESS: "emblem-ok-symbolic",
                    NotificationType.WARNING: "dialog-warning-symbolic",
                    NotificationType.ERROR: "dialog-error-symbolic",
                }
                notification.set_icon(
                    Gio.ThemedIcon.new(type_icons.get(notification_type, "dialog-information-symbolic"))
                )

            # Add action if provided
            if action:
                action_id, label = action
                notification.add_button(label, f"app.{action_id}")

            # Send with unique ID
            self._notification_id += 1
            notification_id = f"voiceink-{self._notification_id}"

            self._app.send_notification(notification_id, notification)
            logger.debug(f"Sent notification: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def notify_transcription_complete(self, word_count: int):
        """Send notification for completed transcription

        Args:
            word_count: Number of words transcribed
        """
        self.send(
            "Transcription Complete",
            f"{word_count} words transcribed",
            NotificationType.SUCCESS,
            icon="audio-input-microphone-symbolic",
        )

    def notify_recording_started(self):
        """Send notification for recording started"""
        self.send(
            "Recording Started",
            "Speak now...",
            NotificationType.INFO,
            icon="media-record-symbolic",
        )

    def notify_error(self, message: str):
        """Send error notification

        Args:
            message: Error message
        """
        self.send(
            "VoiceInk Error",
            message,
            NotificationType.ERROR,
        )

    def notify_model_downloaded(self, model_name: str):
        """Send notification for model download complete

        Args:
            model_name: Name of downloaded model
        """
        self.send(
            "Model Downloaded",
            f"{model_name} is ready to use",
            NotificationType.SUCCESS,
        )

    def withdraw(self, notification_id: str):
        """Withdraw a notification

        Args:
            notification_id: ID of notification to withdraw
        """
        if self._app:
            self._app.withdraw_notification(notification_id)
