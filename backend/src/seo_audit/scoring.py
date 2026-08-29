from __future__ import annotations

import math
from urllib.parse import urlsplit, urlunsplit

from seo_audit.models import Confidence, Finding, Severity


SEVERITY_WEIGHT = {
    Severity.CRITICAL: 100.0,
    Severity.IMPORTANT: 60.0,
    Severity.MINOR: 25.0,
}

CONFIDENCE_WEIGHT = {
    Confidence.HIGH: 1.0,
    Confidence.MEDIUM: 0.8,
    Confidence.LOW: 0.6,
}


def score_findings(
    findings: list[Finding], important_urls: list[str]
) -> list[Finding]:
    normalized_important = {_normalize_comparison_url(url) for url in important_urls}
    scored: list[Finding] = []
    for finding in findings:
        affected_factor = min(1.5, 1.0 + math.log10(max(1, len(finding.affected_urls))) / 4)
        important_factor = (
            1.25
            if any(
                _normalize_comparison_url(url) in normalized_important
                for url in finding.affected_urls
            )
            else 1.0
        )
        score = (
            SEVERITY_WEIGHT[finding.severity]
            * CONFIDENCE_WEIGHT[finding.confidence]
            * affected_factor
            * important_factor
        )
        scored.append(finding.model_copy(update={"score": round(min(150, score), 2)}))
    return sorted(scored, key=lambda item: (-item.score, item.rule_id))


def _normalize_comparison_url(url: str) -> str:
    candidate = url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", "")
    )
