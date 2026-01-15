"""Service registry for managing transcription backends"""

import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Union
import asyncio

import numpy as np

from .local_transcription import LocalTranscriptionService
from .cloud import (
    TranscriptionService,
    TranscriptionResult,
    TranscriptionError,
    OpenAITranscriptionService,
    DeepgramTranscriptionService,
    GroqTranscriptionService,
)
from .cloud.base import ServiceProvider
from .ai_enhancement import AIEnhancementService
from ..whisper.model_manager import ModelSize

logger = logging.getLogger(__name__)


class TranscriptionServiceRegistry:
    """Registry for managing transcription and enhancement services

    Provides a unified interface for switching between local and cloud
    transcription backends, as well as AI enhancement.
    """

    def __init__(self):
        """Initialize the service registry"""
        # Local service
        self._local_service = LocalTranscriptionService()

        # Cloud services
        self._cloud_services: dict[ServiceProvider, TranscriptionService] = {
            ServiceProvider.OPENAI: OpenAITranscriptionService(),
            ServiceProvider.DEEPGRAM: DeepgramTranscriptionService(),
            ServiceProvider.GROQ: GroqTranscriptionService(),
        }

        # AI enhancement
        self._ai_service = AIEnhancementService()

        # Current active provider
        self._active_provider = ServiceProvider.LOCAL

    @property
    def active_provider(self) -> ServiceProvider:
        """Get the currently active provider"""
        return self._active_provider

    @active_provider.setter
    def active_provider(self, provider: ServiceProvider):
        """Set the active provider"""
        self._active_provider = provider
        logger.info(f"Active transcription provider: {provider.value}")

    @property
    def local_service(self) -> LocalTranscriptionService:
        """Get the local transcription service"""
        return self._local_service

    @property
    def ai_service(self) -> AIEnhancementService:
        """Get the AI enhancement service"""
        return self._ai_service

    def get_service(self, provider: Optional[ServiceProvider] = None) -> Union[LocalTranscriptionService, TranscriptionService]:
        """Get a transcription service by provider

        Args:
            provider: Provider to get (uses active if None)

        Returns:
            Transcription service instance
        """
        provider = provider or self._active_provider

        if provider == ServiceProvider.LOCAL:
            return self._local_service

        return self._cloud_services.get(provider)

    def is_configured(self, provider: Optional[ServiceProvider] = None) -> bool:
        """Check if a provider is configured

        Args:
            provider: Provider to check (uses active if None)

        Returns:
            True if configured
        """
        provider = provider or self._active_provider

        if provider == ServiceProvider.LOCAL:
            return self._local_service.is_model_loaded

        service = self._cloud_services.get(provider)
        return service.is_configured if service else False

    def configure_local(
        self,
        model_size: ModelSize = ModelSize.BASE,
        language: Optional[str] = None,
        progress_callback=None,
    ) -> bool:
        """Configure the local transcription service

        Args:
            model_size: Whisper model size
            language: Language code
            progress_callback: Download progress callback

        Returns:
            True if configured successfully
        """
        return self._local_service.configure(
            model_size=model_size,
            language=language,
            progress_callback=progress_callback,
        )

    def set_api_key(self, provider: ServiceProvider, api_key: str):
        """Set API key for a cloud provider

        Args:
            provider: Provider to configure
            api_key: API key
        """
        service = self._cloud_services.get(provider)
        if service:
            service.set_api_key(api_key)

    async def transcribe(
        self,
        audio: Union[Path, np.ndarray],
        language: Optional[str] = None,
        provider: Optional[ServiceProvider] = None,
    ) -> str:
        """Transcribe audio using the specified or active provider

        Args:
            audio: Audio file path or numpy array
            language: Language hint
            provider: Provider to use (uses active if None)

        Returns:
            Transcribed text

        Raises:
            TranscriptionError: If transcription fails
        """
        provider = provider or self._active_provider

        if provider == ServiceProvider.LOCAL:
            # Local service is synchronous
            if isinstance(audio, Path):
                return self._local_service.transcribe(audio, language=language)
            else:
                return self._local_service.transcribe_samples(audio)
        else:
            # Cloud services are async
            service = self._cloud_services.get(provider)
            if not service:
                raise TranscriptionError(f"Unknown provider: {provider}")

            if not service.is_configured:
                raise TranscriptionError(f"{service.name} API key not configured")

            if isinstance(audio, Path):
                result = await service.transcribe(audio, language=language)
            else:
                result = await service.transcribe_samples(audio, language=language)

            return result.text

    def transcribe_sync(
        self,
        audio: Union[Path, np.ndarray],
        language: Optional[str] = None,
        provider: Optional[ServiceProvider] = None,
    ) -> str:
        """Synchronous wrapper for transcribe

        Args:
            audio: Audio file path or numpy array
            language: Language hint
            provider: Provider to use

        Returns:
            Transcribed text
        """
        provider = provider or self._active_provider

        if provider == ServiceProvider.LOCAL:
            if isinstance(audio, Path):
                return self._local_service.transcribe(audio, language=language)
            else:
                return self._local_service.transcribe_samples(audio)
        else:
            # Run async in new event loop
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self.transcribe(audio, language=language, provider=provider)
                )
            finally:
                loop.close()

    async def enhance(self, text: str) -> str:
        """Enhance text using AI

        Args:
            text: Text to enhance

        Returns:
            Enhanced text (or original if enhancement disabled/failed)
        """
        if not self._ai_service.is_enabled:
            return text

        if not self._ai_service.is_configured:
            logger.warning("AI enhancement enabled but not configured")
            return text

        try:
            result = await self._ai_service.enhance(text)
            return result.text
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            return text

    def get_available_providers(self) -> list[ServiceProvider]:
        """Get list of available providers

        Returns:
            List of provider enums
        """
        providers = [ServiceProvider.LOCAL]
        for provider, service in self._cloud_services.items():
            if service.is_configured:
                providers.append(provider)
        return providers
