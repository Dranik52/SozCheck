ANALYSIS_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "has_issue": {"type": "boolean"},
        "error_type": {"type": "string", "enum": [
            "none", "grammar", "spelling", "meaning", "context", "terminology", "tone",
            "placeholder", "length", "naturalness",
        ]},
        "severity": {"type": "string", "enum": ["critical", "major", "minor", "suggestion"]},
        "error_description": {"type": "string"},
        "suggested_translation": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["has_issue", "error_type", "severity", "error_description", "suggested_translation", "confidence"],
}
