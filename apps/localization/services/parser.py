import csv
import io
import json
from dataclasses import dataclass
from typing import Any


LANGUAGE_KEYS = {"en": "english_text", "kk": "kazakh_text", "uz": "uzbek_text"}
MAX_FILE_SIZE = 5 * 1024 * 1024


@dataclass
class ParseResult:
    entries: list[dict[str, Any]]
    report: dict[str, Any]
    original_structure: Any = None


class LocalizationParseError(ValueError):
    def __init__(self, report: dict[str, Any]):
        self.report = report
        super().__init__("Localization file contains validation errors.")


class DuplicateJSONKey(ValueError):
    pass


def parse_localization_file(filename: str, content: bytes, mapping: dict[str, str] | None = None) -> ParseResult:
    if len(content) > MAX_FILE_SIZE:
        raise LocalizationParseError({"errors": ["File exceeds the 5 MB upload limit."], "row_count": 0})
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in {"csv", "json"}:
        raise LocalizationParseError({"errors": ["Only CSV and JSON files are supported."], "row_count": 0})
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise LocalizationParseError({"errors": ["File must use UTF-8 encoding."], "row_count": 0}) from None
    return parse_csv(text, mapping or {}) if suffix == "csv" else parse_json(text)


def parse_csv(text: str, mapping: dict[str, str]) -> ParseResult:
    errors: list[str] = []
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        headers = next(reader)
    except StopIteration:
        raise LocalizationParseError({"errors": ["CSV file is empty."], "row_count": 0}) from None
    headers = [header.strip() for header in headers]
    if len(set(headers)) != len(headers):
        raise LocalizationParseError({"errors": ["CSV contains duplicate column names."], "row_count": 0})
    chosen = {"key": mapping.get("key", "key"), "en": mapping.get("en", "english"),
              "kk": mapping.get("kk", "kazakh"), "uz": mapping.get("uz", "uzbek")}
    optional = {name: mapping.get(name, "") for name in ("context", "max_length") if mapping.get(name, "")}
    missing = [column for column in [*chosen.values(), *optional.values()] if column not in headers]
    if missing:
        raise LocalizationParseError({"errors": [f"Mapped column(s) not found: {', '.join(missing)}."], "row_count": 0,
                                      "available_columns": headers})
    entries: list[dict[str, Any]] = []
    original_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    row_count = 0
    for row_number, values in enumerate(reader, start=2):
        row_count += 1
        if len(values) != len(headers):
            errors.append(f"Row {row_number}: expected {len(headers)} columns, found {len(values)}.")
            continue
        row = dict(zip(headers, values))
        original_rows.append(row)
        key = row[chosen["key"]].strip()
        if not key:
            errors.append(f"Row {row_number}: key is empty.")
            continue
        if key in seen:
            errors.append(f"Row {row_number}: duplicate key '{key}'.")
            continue
        seen.add(key)
        record = {"external_key": key, "source_path": [key]}
        for language, field in LANGUAGE_KEYS.items():
            value = row[chosen[language]].strip()
            if not value:
                errors.append(f"Row {row_number}: {language} translation is empty for '{key}'.")
            record[field] = value
        context_column = optional.get("context")
        record["context"] = row[context_column].strip() if context_column else ""
        length_column = optional.get("max_length")
        raw_length = row[length_column].strip() if length_column else ""
        if raw_length:
            try:
                max_length = int(raw_length)
                if max_length < 1:
                    raise ValueError
                record["max_length"] = max_length
            except ValueError:
                errors.append(f"Row {row_number}: max length for '{key}' must be a positive whole number.")
        record["metadata"] = {name: value for name, value in row.items() if name not in {*chosen.values(), *optional.values()}}
        entries.append(record)
    if row_count == 0:
        errors.append("CSV contains a header but no localization rows.")
    report = {"row_count": row_count, "valid_count": len(entries) if not errors else 0, "errors": errors,
              "available_columns": headers}
    if errors:
        raise LocalizationParseError(report)
    return ParseResult(entries, report, {"headers": headers, "rows": original_rows})


def parse_json(text: str) -> ParseResult:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateJSONKey(key)
            result[key] = value
        return result

    try:
        structure = json.loads(text, object_pairs_hook=reject_duplicate_keys)
    except DuplicateJSONKey as exc:
        raise LocalizationParseError({"errors": [f"Duplicate JSON key '{exc.args[0]}'."], "row_count": 0}) from None
    except json.JSONDecodeError as exc:
        raise LocalizationParseError({"errors": [f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"], "row_count": 0}) from None
    if not isinstance(structure, (dict, list)):
        raise LocalizationParseError({"errors": ["JSON root must be an object or array."], "row_count": 0})
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()

    def visit(node: Any, path: list[str | int]) -> None:
        if isinstance(node, dict):
            if set(node).intersection(LANGUAGE_KEYS):
                key = ".".join(str(part) for part in path)
                if not key:
                    errors.append("A localized JSON object must have a key path.")
                    return
                if key in seen:
                    errors.append(f"Duplicate localization key '{key}'.")
                    return
                seen.add(key)
                record: dict[str, Any] = {"external_key": key, "source_path": path}
                for language, field in LANGUAGE_KEYS.items():
                    value = node.get(language)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"JSON key '{key}': language '{language}' is missing or empty.")
                        record[field] = ""
                    else:
                        record[field] = value
                raw_context = node.get("context", "")
                if not isinstance(raw_context, str):
                    errors.append(f"JSON key '{key}': context must be text.")
                    raw_context = ""
                record["context"] = raw_context
                raw_length = node.get("max_length")
                if raw_length is not None:
                    if isinstance(raw_length, bool) or not isinstance(raw_length, int) or raw_length < 1:
                        errors.append(f"JSON key '{key}': max_length must be a positive whole number.")
                    else:
                        record["max_length"] = raw_length
                record["metadata"] = {name: value for name, value in node.items() if name not in {*LANGUAGE_KEYS, "context", "max_length"}}
                entries.append(record)
                return
            for key, value in node.items():
                visit(value, [*path, str(key)])
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, [*path, index])

    visit(structure, [])
    if not entries and not errors:
        errors.append("No localized objects with en, kk, and uz fields were found.")
    report = {"row_count": len(entries), "valid_count": len(entries) if not errors else 0, "errors": errors}
    if errors:
        raise LocalizationParseError(report)
    return ParseResult(entries, report, structure)
