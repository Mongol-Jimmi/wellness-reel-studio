#!/usr/bin/env python3
"""Mechanical copy checks for Reel Specs written without a human copy read.

`src/spec_reel.py` validates shape: timing, lengths, sources, em dashes. These checks
cover the two ways generated wellness copy goes wrong that shape checks cannot see.
They do not make a claim true. Spelled-out quantities and causal framing in ordinary
words still pass, so the rendered output is a Preview for review, never a publication.
"""

from __future__ import annotations

import re

# Promises the copy style forbids outright. Matched on word boundaries, case-insensitive.
BANNED_PHRASES = (
    "cure",
    "cures",
    "cured",
    "guarantee",
    "guaranteed",
    "prevents",
    "eliminates",
    "eliminate",
    "instantly",
    "instant relief",
    "miracle",
    "risk free",
    "always works",
    "will fix",
    "fixes your",
    "resets your",
    "clinically proven",
    "scientifically proven",
    "doctors recommend",
    "you should",
    "you must",
    "you need to",
)
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def visible_strings(spec: dict) -> list[tuple[str, str]]:
    """Every string a viewer reads, paired with where it came from."""
    strings = [("safety[0]", spec["safety"][0])]
    for index, beat in enumerate(spec["beats"]):
        strings.append((f"beats[{index}].headline", beat["headline"]))
        strings.append((f"beats[{index}].body", beat["body"]))
        if beat.get("source_label"):
            strings.append((f"beats[{index}].source_label", beat["source_label"]))
    return strings


def check_language(spec: dict) -> None:
    for where, value in visible_strings(spec):
        lowered = value.lower()
        for phrase in BANNED_PHRASES:
            if re.search(rf"\b{re.escape(phrase)}\b", lowered):
                raise ValueError(f"{where} uses a forbidden promise: {phrase!r}")


def digits(text: str) -> set[str]:
    """Numbers in a comparable form, so 1,350 and 1350 match."""
    return {match.group().replace(",", "").rstrip(".") for match in NUMBER.finditer(text)}


def check_grounding(spec: dict, evidence: str) -> None:
    """Every number a viewer reads must appear in the source abstract or reviewed claim."""
    allowed = digits(evidence)
    for where, value in visible_strings(spec):
        for number in digits(value):
            if number not in allowed:
                raise ValueError(f"{where} states {number}, which is not in the evidence text")


def check_safety_verbatim(spec: dict, expected: str) -> None:
    """The safety boundary is the reviewer's wording and may not be rewritten."""
    if " ".join(spec["safety"][0].split()) != " ".join(expected.split()):
        raise ValueError("safety[0] must repeat the Issue's safety boundary word for word")


def check_beats_cite_numbers(spec: dict) -> None:
    """A beat that shows a number must show where the number came from."""
    for index, beat in enumerate(spec["beats"]):
        if digits(beat["headline"]) | digits(beat["body"]):
            if not beat.get("source_label"):
                raise ValueError(f"beats[{index}] states a number without a source_label")


def guard(spec: dict, evidence: str, safety: str) -> None:
    check_language(spec)
    check_grounding(spec, evidence)
    check_safety_verbatim(spec, safety)
    check_beats_cite_numbers(spec)
