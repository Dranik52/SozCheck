import json
import math
from typing import Any

from apps.analyzer.models import AnalysisResult

from .placeholder_checker import placeholders_match


class InvalidAnalysisResponse(ValueError):
    pass


def validate_analysis_response(raw: str | dict[str, Any], current_translation: str, english_text: str) -> dict[str, Any]:
    try:
        data = raw if isinstance(raw, dict) else json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise InvalidAnalysisResponse("Provider response is not valid JSON.") from None
    required = {"has_issue", "error_type", "severity", "error_description", "suggested_translation", "confidence"}
    if not isinstance(data, dict) or not required.issubset(data):
        raise InvalidAnalysisResponse("Provider response is missing required fields.")
    if not isinstance(data["has_issue"], bool):
        raise InvalidAnalysisResponse("has_issue must be a boolean.")
    if data["error_type"] not in AnalysisResult.ErrorType.values:
        raise InvalidAnalysisResponse("Unknown error type.")
    if data["severity"] not in AnalysisResult.Severity.values:
        raise InvalidAnalysisResponse("Unknown severity.")
    for field in ("error_description", "suggested_translation"):
        if not isinstance(data[field], str):
            raise InvalidAnalysisResponse(f"{field} must be text.")
    confidence = data["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise InvalidAnalysisResponse("confidence must be between 0 and 1.")
    if data["has_issue"] == (data["error_type"] == AnalysisResult.ErrorType.NONE):
        raise InvalidAnalysisResponse("has_issue and error_type disagree.")
    if not data["has_issue"] and data["suggested_translation"] != current_translation:
        raise InvalidAnalysisResponse("No-issue responses must preserve the current translation.")
    if not placeholders_match(english_text, data["suggested_translation"]):
        raise InvalidAnalysisResponse("Suggested translation changes or omits placeholders.")
    return {**data, "confidence": float(confidence)}
