import copy
import csv
import io
import json
from typing import Any

from apps.analyzer.models import AnalysisResult
from apps.analyzer.services.placeholder_checker import placeholders_match
from apps.localization.models import LocalizationEntry, LocalizationFile
from apps.reviews.models import Review


class ExportError(ValueError):
    pass


def _approved_corrections(localization_file: LocalizationFile) -> dict[tuple[int, str], str]:
    reviews = Review.objects.filter(
        review_status__in=[Review.Status.APPROVED, Review.Status.EDITED],
        analysis_result__localization_entry__localization_file=localization_file,
    ).select_related("analysis_result").order_by("-reviewed_at")
    corrections: dict[tuple[int, str], str] = {}
    for review in reviews:
        key = (review.analysis_result.localization_entry_id, review.analysis_result.language)
        corrections.setdefault(key, review.final_translation)
    return corrections


def _target_text(entry: LocalizationEntry, language: str, approved_only: bool, corrections: dict[tuple[int, str], str], original: str = "") -> str:
    if approved_only:
        return corrections.get((entry.pk, language), original)
    return entry.kazakh_text if language == "kk" else entry.uzbek_text


def validate_export_placeholders(localization_file: LocalizationFile, approved_only: bool = False) -> None:
    corrections = _approved_corrections(localization_file) if approved_only else {}
    structure = localization_file.original_structure
    mapping = localization_file.column_mapping
    csv_rows = {}
    if localization_file.file_format == "csv" and isinstance(structure, dict):
        csv_rows = {row.get(mapping.get("key", "key"), ""): row for row in structure.get("rows", [])}
    errors = []
    for entry in localization_file.entries.all():
        if localization_file.file_format == "csv":
            base_row = csv_rows.get(entry.external_key, {})
        for language, label in (("kk", "Kazakh"), ("uz", "Uzbek")):
            if localization_file.file_format == "csv":
                column = mapping.get(language, "kazakh" if language == "kk" else "uzbek")
                original = base_row.get(column, "")
            else:
                original = _get_json_value(structure, entry.source_path, language) if structure is not None else ""
            translation = _target_text(entry, language, approved_only, corrections, original)
            if not placeholders_match(entry.english_text, translation):
                errors.append(f"{entry.external_key} ({label})")
    if errors:
        examples = ", ".join(errors[:10])
        suffix = "…" if len(errors) > 10 else ""
        raise ExportError(f"Placeholder mismatch found in: {examples}{suffix}")


def _set_path(node: Any, path: list[str | int], language_key: str, value: str) -> None:
    current = node
    for part in path:
        current = current[part]
    current[language_key] = value


def _get_json_value(node: Any, path: list[str | int], language_key: str) -> str:
    current = node
    for part in path:
        current = current[part]
    return current.get(language_key, "")


def build_export(localization_file: LocalizationFile, file_format: str, approved_only: bool = False) -> tuple[str, str]:
    if file_format not in {"csv", "json"} or localization_file.file_format != file_format:
        raise ExportError("Choose the same format as the original uploaded file.")
    if localization_file.upload_status != LocalizationFile.Status.PARSED:
        raise ExportError("Invalid uploads cannot be exported.")
    validate_export_placeholders(localization_file, approved_only)
    entries = list(localization_file.entries.all())
    corrections = _approved_corrections(localization_file) if approved_only else {}
    if file_format == "csv":
        structure = localization_file.original_structure
        if not isinstance(structure, dict) or not isinstance(structure.get("headers"), list) or not isinstance(structure.get("rows"), list):
            raise ExportError("Original CSV structure is unavailable for this upload.")
        mapping = localization_file.column_mapping
        entry_by_key = {entry.external_key: entry for entry in entries}
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=structure["headers"], extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for raw_row in structure["rows"]:
            row = dict(raw_row)
            key = row.get(mapping.get("key", "key"), "")
            entry = entry_by_key.get(key)
            if entry:
                for language in ("kk", "uz"):
                    column = mapping.get(language, "kazakh" if language == "kk" else "uzbek")
                    original = row.get(column, "")
                    row[column] = _target_text(entry, language, approved_only, corrections, original)
            writer.writerow(row)
        return output.getvalue(), "text/csv; charset=utf-8"

    structure = localization_file.original_structure
    if structure is None:
        raise ExportError("Original JSON structure is unavailable for this upload.")
    exported = copy.deepcopy(structure)
    for entry in entries:
        for language in ("kk", "uz"):
            original = _get_json_value(structure, entry.source_path, language)
            _set_path(exported, entry.source_path, language, _target_text(entry, language, approved_only, corrections, original))
    return json.dumps(exported, ensure_ascii=False, indent=2), "application/json; charset=utf-8"
