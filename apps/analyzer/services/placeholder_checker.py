import re
from collections import Counter


PLACEHOLDER_PATTERN = re.compile(r"\{[^{}]+\}|%(?:\d+\$)?[sdif]")


def extract_placeholders(text: str) -> Counter[str]:
    return Counter(PLACEHOLDER_PATTERN.findall(text))


def placeholders_match(source: str, translation: str) -> bool:
    return extract_placeholders(source) == extract_placeholders(translation)
