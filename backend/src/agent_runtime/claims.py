"""Shared detection of value claims that the user's own source text does not support.

Copy-writing agents each had their own idea of what counts as an unsupported claim, so
a phrase blocked by one agent shipped unchallenged from another. The vocabulary lives
here once, and every agent that turns supplied facts into prose checks against it.

Detection is deliberately conservative: a term only counts as unsupported when it does
not appear anywhere in the source the user actually provided.
"""

from __future__ import annotations

import re

# Quality, price and reputation words that assert something a reader would expect the
# business to be able to evidence. Ordinary descriptive language is not listed here.
UNSUPPORTED_VALUE_TERMS: tuple[str, ...] = (
    "affordable",
    "award-winning",
    "best",
    "best-in-class",
    "budget",
    "cheap",
    "cheapest",
    "discounted",
    "exceptional",
    "exclusive",
    "fastest",
    "finest",
    "five-star",
    "flexible",
    "free",
    "guaranteed",
    "highly rated",
    "industry-leading",
    "leading",
    "lowest",
    "luxurious",
    "luxury",
    "number one",
    "premier",
    "premium",
    "renowned",
    "top-rated",
    "trusted",
    "unmatched",
    "unrivalled",
    "unrivaled",
    "world-class",
)

# Phrases asserting a reputation the supplied facts cannot establish, even when every
# individual word above is absent.
REPUTATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bknown for\b", re.IGNORECASE),
    re.compile(r"\brenowned for\b", re.IGNORECASE),
    re.compile(r"\bfamous for\b", re.IGNORECASE),
    re.compile(r"\bcelebrated for\b", re.IGNORECASE),
    re.compile(r"\bvoted\b", re.IGNORECASE),
    re.compile(r"\bloved by\b", re.IGNORECASE),
    re.compile(r"\brecognized as\b", re.IGNORECASE),
    re.compile(r"\brecognised as\b", re.IGNORECASE),
)


def _mentions(term: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE) is not None


def unsupported_claims(generated_text: str, source_text: str) -> list[str]:
    """Return value claims present in generated copy but absent from the source.

    `source_text` should be everything the user supplied for the run, concatenated.
    A term the user used themselves is treated as supported and never reported.
    """
    found: list[str] = []
    for term in UNSUPPORTED_VALUE_TERMS:
        if _mentions(term, generated_text) and not _mentions(term, source_text):
            found.append(term)
    for pattern in REPUTATION_PATTERNS:
        match = pattern.search(generated_text)
        if match and not pattern.search(source_text):
            found.append(match.group(0).lower())
    return list(dict.fromkeys(found))
