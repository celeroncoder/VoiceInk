"""AI text enhancement service"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import httpx

from .credentials import CredentialManager

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """AI service providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class EnhancementResult:
    """Result from AI enhancement"""
    text: str
    original_text: str
    provider: AIProvider
    model: str
    duration: float = 0.0


class AIEnhancementService:
    """Service for enhancing text with AI

    Supports multiple providers:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Groq (fast inference)
    - Ollama (local)
    - Custom OpenAI-compatible endpoints
    """

    DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant that improves transcribed text.
Fix any transcription errors, improve grammar and punctuation, and make the text clearer.
Preserve the original meaning and tone. Do not add new information.
Return only the improved text without explanations."""

    def __init__(
        self,
        provider: AIProvider = AIProvider.OPENAI,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        custom_endpoint: Optional[str] = None,
        credential_manager: Optional[CredentialManager] = None,
    ):
        """Initialize AI enhancement service

        Args:
            provider: AI provider to use
            model: Model name (uses default for provider if not specified)
            api_key: API key (if not provided, uses credential manager)
            custom_endpoint: Custom API endpoint URL
            credential_manager: Optional credential manager
        """
        self.provider = provider
        self._model = model
        self._api_key = api_key
        self._custom_endpoint = custom_endpoint
        self._creds = credential_manager or CredentialManager()

        self.system_prompt = self.DEFAULT_SYSTEM_PROMPT
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """Check if enhancement is enabled"""
        return self._enabled

    @is_enabled.setter
    def is_enabled(self, value: bool):
        """Enable or disable enhancement"""
        self._enabled = value

    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured"""
        if self.provider == AIProvider.OLLAMA:
            return True  # Ollama doesn't need API key
        return bool(self._get_api_key())

    @property
    def model(self) -> str:
        """Get the model name"""
        if self._model:
            return self._model

        defaults = {
            AIProvider.OPENAI: "gpt-4o-mini",
            AIProvider.ANTHROPIC: "claude-3-haiku-20240307",
            AIProvider.GROQ: "llama-3.1-8b-instant",
            AIProvider.OLLAMA: "llama3.2",
            AIProvider.CUSTOM: "gpt-3.5-turbo",
        }
        return defaults.get(self.provider, "gpt-3.5-turbo")

    def _get_api_key(self) -> Optional[str]:
        """Get API key from instance or credential manager"""
        if self._api_key:
            return self._api_key

        key_names = {
            AIProvider.OPENAI: "openai_api_key",
            AIProvider.ANTHROPIC: "anthropic_api_key",
            AIProvider.GROQ: "groq_api_key",
            AIProvider.CUSTOM: "custom_ai_api_key",
        }
        key_name = key_names.get(self.provider)
        if key_name:
            return self._creds.get(key_name)
        return None

    def set_api_key(self, api_key: str):
        """Set and store API key

        Args:
            api_key: API key for current provider
        """
        self._api_key = api_key

        key_names = {
            AIProvider.OPENAI: "openai_api_key",
            AIProvider.ANTHROPIC: "anthropic_api_key",
            AIProvider.GROQ: "groq_api_key",
            AIProvider.CUSTOM: "custom_ai_api_key",
        }
        key_name = key_names.get(self.provider)
        if key_name:
            self._creds.set(key_name, api_key)

    def set_system_prompt(self, prompt: str):
        """Set custom system prompt

        Args:
            prompt: System prompt for AI enhancement
        """
        self.system_prompt = prompt

    async def enhance(self, text: str) -> EnhancementResult:
        """Enhance text using AI

        Args:
            text: Text to enhance

        Returns:
            EnhancementResult with enhanced text

        Raises:
            Exception: If enhancement fails
        """
        if not text.strip():
            return EnhancementResult(
                text=text,
                original_text=text,
                provider=self.provider,
                model=self.model,
            )

        import time
        start_time = time.time()

        if self.provider == AIProvider.OPENAI:
            enhanced = await self._enhance_openai(text)
        elif self.provider == AIProvider.ANTHROPIC:
            enhanced = await self._enhance_anthropic(text)
        elif self.provider == AIProvider.GROQ:
            enhanced = await self._enhance_groq(text)
        elif self.provider == AIProvider.OLLAMA:
            enhanced = await self._enhance_ollama(text)
        elif self.provider == AIProvider.CUSTOM:
            enhanced = await self._enhance_custom(text)
        else:
            enhanced = text

        duration = time.time() - start_time

        return EnhancementResult(
            text=enhanced,
            original_text=text,
            provider=self.provider,
            model=self.model,
            duration=duration,
        )

    async def _enhance_openai(self, text: str) -> str:
        """Enhance using OpenAI API"""
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("OpenAI API key not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.3,
                },
            )

            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.text}")

            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def _enhance_anthropic(self, text: str) -> str:
        """Enhance using Anthropic API"""
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("Anthropic API key not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    "system": self.system_prompt,
                    "messages": [
                        {"role": "user", "content": text},
                    ],
                },
            )

            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.text}")

            result = response.json()
            return result["content"][0]["text"]

    async def _enhance_groq(self, text: str) -> str:
        """Enhance using Groq API"""
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("Groq API key not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.3,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Groq API error: {response.text}")

            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def _enhance_ollama(self, text: str) -> str:
        """Enhance using local Ollama"""
        endpoint = self._custom_endpoint or "http://localhost:11434"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{endpoint}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "stream": False,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.text}")

            result = response.json()
            return result["message"]["content"]

    async def _enhance_custom(self, text: str) -> str:
        """Enhance using custom OpenAI-compatible endpoint"""
        if not self._custom_endpoint:
            raise ValueError("Custom endpoint not configured")

        api_key = self._get_api_key()

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._custom_endpoint}/v1/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.3,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Custom API error: {response.text}")

            result = response.json()
            return result["choices"][0]["message"]["content"]
