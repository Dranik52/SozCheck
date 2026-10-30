from django.conf import settings

from .base import ProviderError


def configured_provider():
    provider_name = getattr(settings, "AI_PROVIDER", "openai").lower()
    if provider_name == "openai":
        if not settings.OPENAI_API_KEY:
            return None
        from .openai_provider import OpenAIProvider
        return OpenAIProvider()
    if provider_name == "gemini":
        if not settings.GEMINI_API_KEY:
            return None
        from .gemini_provider import GeminiProvider
        return GeminiProvider()
    raise ProviderError("AI_PROVIDER must be set to 'openai' or 'gemini'.")
