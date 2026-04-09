from __future__ import annotations

from dataclasses import dataclass, field

from lilya.contrib.ai.exceptions import AIConfigurationError


@dataclass(slots=True)
class AIProviderConfig:
    """
    Base configuration shared by all AI providers.
    """

    api_key: str
    base_url: str
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Validate common provider configuration.
        """
        if not self.api_key:
            raise AIConfigurationError("`api_key` is required for AI provider configuration.")
        if not self.base_url:
            raise AIConfigurationError("`base_url` is required for AI provider configuration.")
        if self.timeout <= 0:
            raise AIConfigurationError("`timeout` must be greater than zero.")


@dataclass(slots=True)
class OpenAICompatibleConfig(AIProviderConfig):
    """
    Configuration for providers exposing an OpenAI-compatible API surface.
    """

    base_url: str = "https://api.openai.com/v1"
    provider_name: str = "openai-compatible"
    organization: str | None = None
    project: str | None = None


@dataclass(slots=True)
class OpenAIConfig(OpenAICompatibleConfig):
    """
    Configuration for OpenAI's chat completion APIs.
    """

    provider_name: str = "openai"


@dataclass(slots=True)
class GroqConfig(OpenAICompatibleConfig):
    """
    Configuration for Groq's OpenAI-compatible chat completion APIs.
    """

    base_url: str = "https://api.groq.com/openai/v1"
    provider_name: str = "groq"


@dataclass(slots=True)
class MistralConfig(OpenAICompatibleConfig):
    """
    Configuration for Mistral's OpenAI-compatible chat completion APIs.
    """

    base_url: str = "https://api.mistral.ai/v1"
    provider_name: str = "mistral"


@dataclass(slots=True)
class AnthropicConfig(AIProviderConfig):
    """
    Configuration for Anthropic's messages API.
    """

    base_url: str = "https://api.anthropic.com/v1"
    anthropic_version: str = "2023-06-01"
    default_max_tokens: int = 1024

    def __post_init__(self) -> None:
        """
        Validate Anthropic-specific configuration.
        """
        AIProviderConfig.__post_init__(self)
        if self.default_max_tokens <= 0:
            raise AIConfigurationError("`default_max_tokens` must be greater than zero.")
