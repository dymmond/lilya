from __future__ import annotations


class AIError(Exception):
    """
    Base exception for all AI contrib errors.
    """


class AIConfigurationError(AIError):
    """
    Raised when an AI client or provider is misconfigured.
    """


class ProviderNotConfigured(AIConfigurationError):
    """
    Raised when no provider has been configured where one is required.
    """


class AIProviderError(AIError):
    """
    Raised when a provider returns an error or cannot be reached.
    """


class AIResponseError(AIError):
    """
    Raised when a provider response cannot be parsed into Lilya's AI types.
    """
