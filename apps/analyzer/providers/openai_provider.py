from django.conf import settings

from .base import BaseProvider, ProviderError


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or getattr(settings, "OPENAI_API_KEY", "")
        if not key:
            raise ProviderError("OpenAI API key is not configured.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError("Install the optional OpenAI SDK to use this provider.") from exc
        self.model = model or getattr(settings, "OPENAI_MODEL", "gpt-5-mini")
        self.client = OpenAI(api_key=key, timeout=30.0, max_retries=2)

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                text={"format": {"type": "json_schema", "name": "localization_analysis",
                                 "schema": ANALYSIS_JSON_SCHEMA, "strict": True}},
            )
            if not response.output_text:
                raise ProviderError("OpenAI returned an empty response.")
            return response.output_text
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError("OpenAI analysis request failed.") from exc


from apps.analyzer.schemas.analysis import ANALYSIS_JSON_SCHEMA
