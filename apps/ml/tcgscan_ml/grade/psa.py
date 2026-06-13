"""Map internal 1–10 overall score to estimated PSA grade range."""

from __future__ import annotations


def overall_to_psa_range(overall: float) -> tuple[int, int]:
    if overall >= 9.75:
        return 10, 10
    if overall >= 9.25:
        return 9, 10
    if overall >= 8.75:
        return 8, 9
    if overall >= 8.25:
        return 8, 8
    if overall >= 7.5:
        return 7, 8
    if overall >= 6.5:
        return 6, 7
    if overall >= 5.5:
        return 5, 6
    return 4, 5
