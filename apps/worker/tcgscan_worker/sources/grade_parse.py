"""Parse grading company + grade from listing titles."""

from __future__ import annotations

import re
from dataclasses import dataclass

_GRADE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("PSA", re.compile(r"\bPSA\s*(\d+(?:\.\d+)?)\b", re.I)),
    ("BGS", re.compile(r"\b(?:BGS|BECKETT)\s*(\d+(?:\.\d+)?)\b", re.I)),
    ("CGC", re.compile(r"\bCGC\s*(\d+(?:\.\d+)?)\b", re.I)),
    ("ACE", re.compile(r"\bACE\s*(\d+(?:\.\d+)?)\b", re.I)),
    ("SGC", re.compile(r"\bSGC\s*(\d+(?:\.\d+)?)\b", re.I)),
]


@dataclass(frozen=True)
class ParsedGrade:
    grade_company: str | None
    grade: str | None


def parse_grade_from_text(text: str | None) -> ParsedGrade:
    if not text:
        return ParsedGrade(None, None)
    for company, pattern in _GRADE_PATTERNS:
        match = pattern.search(text)
        if match:
            return ParsedGrade(company, f"{company} {match.group(1)}")
    return ParsedGrade(None, "raw")
