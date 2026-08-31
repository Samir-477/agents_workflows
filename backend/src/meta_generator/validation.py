from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from meta_generator.models import (
    DraftGenerationResult,
    DraftMetadataOption,
    LengthStatus,
    MetadataGenerationResult,
    MetadataOption,
    PageMetadataResult,
    ParsedGenerationBrief,
    ParsedPageBrief,
)


_NUMBER_RE = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?%?(?![\w])")
_SPACE_RE = re.compile(r"\s+")
_SENSITIVE_CLAIMS = (
    "affordable",
    "best",
    "cheap",
    "cheapest",
    "discounted",
    "flexible",
    "flexible pricing",
    "free",
    "guaranteed",
    "industry-leading",
    "leading",
    "lowest",
    "robust",
    "save",
)


@dataclass(slots=True)
class ValidationOutcome:
    result: MetadataGenerationResult
    repair_instructions: list[str]


def _normalized(text: str) -> str:
    return _SPACE_RE.sub(" ", re.sub(r"[^\w\s]", " ", text.casefold())).strip()


def _length_status(count: int, kind: str) -> LengthStatus:
    low, high = (50, 60) if kind == "title" else (140, 160)
    if count < low:
        return LengthStatus.SHORT
    if count > high:
        return LengthStatus.LONG
    return LengthStatus.GOOD


def _option_score(
    option: DraftMetadataOption,
    *,
    kind: str,
    keyword: str | None,
    issues: list[str],
) -> float:
    count = len(option.text)
    target = 55 if kind == "title" else 150
    score = 82.0 - min(25.0, abs(count - target) * 0.8)
    if _length_status(count, kind) == LengthStatus.GOOD:
        score += 10
    if keyword and _normalized(keyword) in _normalized(option.text):
        score += 8
    score -= 18 * len(issues)
    return round(max(0, min(100, score)), 1)


def _validate_option(
    option: DraftMetadataOption,
    *,
    kind: str,
    keyword: str | None,
    allowed_numbers: set[str],
    source_text: str,
) -> MetadataOption:
    text = _SPACE_RE.sub(" ", option.text).strip()
    issues: list[str] = []
    count = len(text)
    # Search snippets do not have true character hard limits. These broad bounds
    # reject unusable/truncated model output while practical ranges remain a
    # scoring, repair, and warning concern.
    hard_low, hard_high = (15, 100) if kind == "title" else (40, 300)
    if count < hard_low:
        issues.append(f"{kind.capitalize()} is too short to be useful ({count} characters).")
    if count > hard_high:
        issues.append(f"{kind.capitalize()} exceeds the hard limit ({count} characters).")
    unsupported = sorted(set(_NUMBER_RE.findall(text)) - allowed_numbers)
    if unsupported:
        issues.append(
            "Contains numeric content not supplied by the user: " + ", ".join(unsupported)
        )
    for number in set(_NUMBER_RE.findall(text)) & allowed_numbers:
        source_position = source_text.find(number)
        if source_position < 0:
            continue
        source_context = source_text[max(0, source_position - 50) : source_position]
        needs_starting_qualifier = bool(
            re.search(r"\b(?:from|start(?:s|ing|ed)?)\b", source_context, re.IGNORECASE)
        )
        option_position = text.find(number)
        option_context = text[max(0, option_position - 50) : option_position]
        retains_qualifier = bool(
            re.search(r"\b(?:from|start(?:s|ing|ed)?)\b", option_context, re.IGNORECASE)
        )
        if needs_starting_qualifier and not retains_qualifier:
            issues.append(
                f"Drops the supplied starting/from qualifier for the numeric claim {number}."
            )
    normalized_source = source_text.casefold()
    normalized_option = text.casefold()
    unsupported_claims = [
        claim
        for claim in _SENSITIVE_CLAIMS
        if claim in normalized_option and claim not in normalized_source
    ]
    if unsupported_claims:
        issues.append(
            "Contains a value claim not supplied by the user: "
            + ", ".join(unsupported_claims)
        )
    return MetadataOption(
        text=text,
        character_count=count,
        length_status=_length_status(count, kind),
        intent=option.intent,
        angle=option.angle,
        rationale=option.rationale,
        score=_option_score(
            option.model_copy(update={"text": text}),
            kind=kind,
            keyword=keyword,
            issues=issues,
        ),
        issues=issues,
    )


def _mark_local_duplicates(options: list[MetadataOption], label: str) -> list[str]:
    repairs: list[str] = []
    for index, option in enumerate(options):
        for earlier in options[:index]:
            similarity = SequenceMatcher(
                None, _normalized(option.text), _normalized(earlier.text)
            ).ratio()
            if similarity >= 0.9:
                message = f"{label} option {index + 1} is too similar to another option."
                option.issues.append(message)
                option.score = max(0, option.score - 25)
                repairs.append(message)
                break
    return repairs


def _select_recommended(options: list[MetadataOption]) -> str:
    preferred = [
        item
        for item in options
        if not item.issues and item.length_status == LengthStatus.GOOD
    ]
    eligible = preferred or [item for item in options if not item.issues] or options
    selected = max(eligible, key=lambda item: (item.score, -len(item.issues)))
    for option in options:
        option.recommended = option.id == selected.id
    return selected.id


def _page_result(
    page: ParsedPageBrief,
    draft_page,
    *,
    allowed_numbers: set[str],
    source_text: str,
) -> tuple[PageMetadataResult, list[str]]:
    titles = [
        _validate_option(
            item,
            kind="title",
            keyword=page.primary_keyword,
            allowed_numbers=allowed_numbers,
            source_text=source_text,
        )
        for item in draft_page.titles
    ]
    descriptions = [
        _validate_option(
            item,
            kind="description",
            keyword=page.primary_keyword,
            allowed_numbers=allowed_numbers,
            source_text=source_text,
        )
        for item in draft_page.descriptions
    ]
    repairs = [issue for item in [*titles, *descriptions] for issue in item.issues]
    repairs.extend(_mark_local_duplicates(titles, f"{page.page_name} title"))
    repairs.extend(
        _mark_local_duplicates(descriptions, f"{page.page_name} description")
    )
    for index, item in enumerate(titles, start=1):
        if item.length_status != LengthStatus.GOOD:
            repairs.append(
                f"{page.page_name} title option {index} is {item.character_count} characters; rewrite it naturally toward 50-60 characters."
            )
    for index, item in enumerate(descriptions, start=1):
        if item.length_status != LengthStatus.GOOD:
            repairs.append(
                f"{page.page_name} description option {index} is {item.character_count} characters; rewrite it naturally toward 140-160 characters."
            )
    warnings = list(page.missing_context)
    if page.keyword_source == "inferred":
        warnings.append(
            f"The target term '{page.primary_keyword}' was inferred from the brief, not supplied as confirmed keyword research."
        )
    if page.keyword_source == "not_supplied":
        warnings.append("No confirmed target keyword was supplied for this page.")
    if not any(
        not option.issues and option.length_status == LengthStatus.GOOD
        for option in titles
    ):
        warnings.append(
            "No title reached the preferred 50-60 character range after repair; the closest usable option was recommended."
        )
    if not any(
        not option.issues and option.length_status == LengthStatus.GOOD
        for option in descriptions
    ):
        warnings.append(
            "No description reached the preferred 140-160 character range after repair; the closest usable option was recommended."
        )
    return (
        PageMetadataResult(
            page_key=page.page_key,
            page_name=page.page_name,
            page_type=page.page_type,
            search_intent=page.search_intent,
            primary_keyword=page.primary_keyword,
            keyword_source=page.keyword_source,
            titles=titles,
            descriptions=descriptions,
            recommended_title_id=_select_recommended(titles),
            recommended_description_id=_select_recommended(descriptions),
            brand_guidance=draft_page.brand_guidance,
            warnings=list(dict.fromkeys(warnings)),
        ),
        repairs,
    )


def _batch_duplicates(pages: list[PageMetadataResult]) -> list[str]:
    warnings: list[str] = []
    for kind in ("titles", "descriptions"):
        seen: list[tuple[str, str]] = []
        threshold = 0.86 if kind == "titles" else 0.91
        for page in pages:
            for option in getattr(page, kind):
                normalized = _normalized(option.text)
                for prior_page, prior_text in seen:
                    if prior_page == page.page_key:
                        continue
                    if SequenceMatcher(None, normalized, prior_text).ratio() >= threshold:
                        warnings.append(
                            f"Possible cross-page duplicate {kind[:-1]} between '{prior_page}' and '{page.page_key}': {option.text}"
                        )
                        option.score = max(0, option.score - 20)
                        break
                seen.append((page.page_key, normalized))
    return list(dict.fromkeys(warnings))


def validate_draft(
    generation_id: str,
    prompt: str,
    brief: ParsedGenerationBrief,
    draft: DraftGenerationResult,
) -> ValidationOutcome:
    draft_by_key = {page.page_key: page for page in draft.pages}
    expected = {page.page_key for page in brief.pages}
    if set(draft_by_key) != expected:
        missing = sorted(expected - set(draft_by_key))
        extra = sorted(set(draft_by_key) - expected)
        raise ValueError(
            f"Generated pages did not match the parsed brief; missing={missing}, extra={extra}"
        )

    allowed_numbers = set(_NUMBER_RE.findall(prompt))
    page_results: list[PageMetadataResult] = []
    repair_instructions: list[str] = []
    for page in brief.pages:
        result, repairs = _page_result(
            page,
            draft_by_key[page.page_key],
            allowed_numbers=allowed_numbers,
            source_text=prompt,
        )
        page_results.append(result)
        repair_instructions.extend(
            f"{page.page_key}: {instruction}" for instruction in repairs
        )

    batch_warnings = _batch_duplicates(page_results)
    for page in page_results:
        page.recommended_title_id = _select_recommended(page.titles)
        page.recommended_description_id = _select_recommended(page.descriptions)
    repair_instructions.extend(batch_warnings)
    return ValidationOutcome(
        result=MetadataGenerationResult(
            generation_id=generation_id,
            pages=page_results,
            batch_warnings=list(dict.fromkeys([*brief.warnings, *batch_warnings])),
        ),
        repair_instructions=list(dict.fromkeys(repair_instructions)),
    )
