from typing import Any

from apps.analyzer.models import AnalysisResult
from apps.localization.models import LocalizationEntry

from .placeholder_checker import placeholders_match
from .prompt_builder import PROMPT_VERSION, build_analysis_prompt
from .response_validator import validate_analysis_response


class AnalysisError(RuntimeError):
    pass


def analyze_entry(entry: LocalizationEntry, language: str, provider: Any, project_context: dict[str, Any] | None = None) -> AnalysisResult:
    current = entry.kazakh_text if language == AnalysisResult.Language.KAZAKH else entry.uzbek_text
    english = entry.english_text
    if not placeholders_match(english, current):
        result = {
            "has_issue": True, "error_type": AnalysisResult.ErrorType.PLACEHOLDER,
            "severity": AnalysisResult.Severity.MAJOR,
            "error_description": "The translation does not preserve the same placeholders as the English source.",
            "suggested_translation": current, "confidence": 1.0,
        }
        provider_name, model_name = "local", "placeholder-checker"
    elif entry.max_length and len(current) > entry.max_length:
        result = {
            "has_issue": True, "error_type": AnalysisResult.ErrorType.LENGTH,
            "severity": AnalysisResult.Severity.MAJOR,
            "error_description": f"The translation is {len(current)} characters long; the configured limit is {entry.max_length}.",
            "suggested_translation": current, "confidence": 1.0,
        }
        provider_name, model_name = "local", "length-checker"
    else:
        if provider is None:
            raise AnalysisError("Configure an OpenAI or Gemini API key to run AI analysis for this text.")
        payload = {
            "key": entry.external_key, "language": language, "english_text": english,
            "current_translation": current, "game_genre": (project_context or {}).get("game_genre", ""),
            "game_context": (project_context or {}).get("game_context", ""),
            "entry_context": entry.context, "max_length": entry.max_length,
            "entry_metadata": entry.metadata,
            "terminology": (project_context or {}).get("terminology", []),
        }
        try:
            raw = provider.generate(build_analysis_prompt(payload))
            result = validate_analysis_response(raw, current, english)
        except Exception as exc:
            raise AnalysisError("Analysis failed or the provider returned an invalid response.") from exc
        provider_name = provider.name
        model_name = getattr(provider, "model", "")

    return AnalysisResult.objects.create(
        localization_entry=entry,
        language=language,
        error_type=result["error_type"],
        severity=result["severity"],
        error_description=result["error_description"],
        current_translation=current,
        suggested_translation=result["suggested_translation"],
        confidence=result["confidence"],
        requires_human_review=result["has_issue"],
        analysis_provider=provider_name,
        model_name=model_name,
        prompt_version=PROMPT_VERSION,
        status=AnalysisResult.Status.PENDING if result["has_issue"] else AnalysisResult.Status.NO_ISSUE,
    )
