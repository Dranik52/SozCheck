from django.conf import settings

from .base import BaseProvider, ProviderError


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        if not key:
            raise ProviderError("Gemini API key is not configured.")
        try:
            from google import genai
        except ImportError as exc:
            raise ProviderError("Install the optional Google GenAI SDK to use this provider.") from exc
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        self.client = genai.Client(api_key=key)

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.interactions.create(
                model=self.model,
                input=prompt,
                response_format={
                    "type": "text", "mime_type": "application/json",
                    "schema": {key: value for key, value in ANALYSIS_JSON_SCHEMA.items() if key != "additionalProperties"},
                },
            )
            if not response.output_text:
                raise ProviderError("Gemini returned an empty response.")
            return response.output_text
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError("Gemini analysis request failed.") from exc


from apps.analyzer.schemas.analysis import ANALYSIS_JSON_SCHEMA
