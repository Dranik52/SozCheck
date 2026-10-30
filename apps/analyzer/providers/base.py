from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    """A provider could not return a usable response."""


class BaseProvider(ABC):
    name = "base"

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the provider's response text or raise ProviderError."""
