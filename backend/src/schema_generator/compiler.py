from __future__ import annotations

import json
import re
from typing import Any

from schema_generator.models import (
    ParsedSchemaBrief,
    SchemaBlockResult,
    SchemaGenerationResult,
    ValidationIssue,
)
from schema_generator.validation import validate_schema_entity


_SAFE_KEY = re.compile(r"^(?:@[a-zA-Z]+|[a-zA-Z][a-zA-Z0-9]*)$")
_REQUIRED: dict[str, tuple[str, ...]] = {
    "Organization": ("name",),
    "LocalBusiness": ("name", "address"),
    "MedicalBusiness": ("name", "address"),
    "Product": ("name",),
    "Article": ("headline", "image", "datePublished"),
    "FAQPage": ("mainEntity",),
    "Event": ("name", "startDate", "location"),
    "SoftwareApplication": ("name", "applicationCategory", "operatingSystem"),
}
_RECOMMENDED: dict[str, tuple[str, ...]] = {
    "Organization": ("url", "logo", "sameAs"),
    "LocalBusiness": ("telephone", "openingHoursSpecification", "url", "geo"),
    "MedicalBusiness": ("telephone", "openingHoursSpecification", "url", "geo"),
    "Product": ("description", "image", "sku", "offers"),
    "Article": ("author", "publisher", "dateModified", "description"),
    "FAQPage": (),
    "Event": ("description", "image", "endDate", "offers", "organizer"),
    "SoftwareApplication": ("offers", "aggregateRating", "description"),
}


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not _SAFE_KEY.fullmatch(key) or key == "@context":
                continue
            normalized = _clean(item)
            if normalized not in (None, "", [], {}):
                cleaned[key] = normalized
        return cleaned
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := _clean(item)) not in (None, "", [], {})]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _placement(schema_type: str, scope: str) -> str:
    if scope == "site-wide" and schema_type == "Organization":
        return "Place this Organization identity block once in the shared site template, conventionally in the document head. Keep it consistent across the site."
    return "Place this JSON-LD on the page whose visible content it describes, conventionally in the document head. Do not reuse page-specific facts site-wide."


def compile_schema(
    generation_id: str,
    brief: ParsedSchemaBrief,
    *,
    source_prompt: str | None = None,
) -> SchemaGenerationResult:
    blocks: list[SchemaBlockResult] = []
    graph_items: list[dict[str, Any]] = []
    global_warnings = list(dict.fromkeys([*brief.mismatches, *brief.assumptions]))
    source_context = "\n".join(part for part in (source_prompt, brief.page_url) if part)

    for draft in brief.entities:
        properties = _clean(draft.properties)
        if not isinstance(properties, dict):
            properties = {}
        properties.pop("@type", None)
        properties.setdefault("name", draft.name)
        item = {"@type": draft.schema_type, **properties}
        issues: list[ValidationIssue] = []
        required = _REQUIRED[draft.schema_type]
        missing_required = [name for name in required if not item.get(name)]
        missing_recommended = [
            name for name in _RECOMMENDED[draft.schema_type] if not item.get(name)
        ]
        for name in missing_required:
            issues.append(ValidationIssue(
                severity="error",
                code="missing-required-property",
                message=f"Add {name} before relying on this type for rich-result eligibility.",
                schema_type=draft.schema_type,
            ))
        issues.extend(validate_schema_entity(draft.schema_type, item, source_context or None))
        if draft.schema_type == "Product" and not any(item.get(key) for key in ("offers", "review", "aggregateRating")):
            issues.append(ValidationIssue(
                severity="error",
                code="product-eligibility-property-missing",
                message="Product rich-result eligibility needs at least one of offers, review, or aggregateRating.",
                schema_type=draft.schema_type,
            ))
        serialized = json.dumps(item, ensure_ascii=False)
        if any(token in serialized for token in ('"aggregateRating"', '"review"')) and not any(
            any(word in evidence.casefold() for word in ("visible", "shown", "displayed"))
            for evidence in draft.visible_evidence
        ):
            issues.append(ValidationIssue(
                severity="warning",
                code="rating-visibility-unconfirmed",
                message="Confirm every marked-up rating or review is genuinely visible on this page and sourced from real users.",
                schema_type=draft.schema_type,
            ))
        if draft.schema_type == "FAQPage" and not draft.visible_evidence:
            issues.append(ValidationIssue(
                severity="error",
                code="faq-visibility-unconfirmed",
                message="FAQ markup must match questions and answers visible to visitors on this page.",
                schema_type=draft.schema_type,
            ))
        placement_scope = "site-wide" if draft.schema_type == "Organization" else "page-specific"
        if draft.schema_type == "FAQPage":
            global_warnings.append(
                "Google generally limits FAQ rich results to well-known authoritative government and health sites; valid FAQPage markup may still have no visible search-result effect."
            )
        block_ready = not any(issue.severity == "error" for issue in issues)
        blocks.append(SchemaBlockResult(
            schema_type=draft.schema_type,
            name=draft.name,
            json_ld=item,
            rationale=draft.rationale,
            placement_scope=placement_scope,
            placement_guidance=_placement(draft.schema_type, placement_scope),
            visible_evidence=draft.visible_evidence,
            missing_properties=list(dict.fromkeys([*missing_required, *missing_recommended])),
            issues=issues,
            publish_ready=block_ready,
        ))
        graph_items.append(item)

    graph: dict[str, Any] = {"@context": "https://schema.org"}
    if len(graph_items) == 1:
        graph.update(graph_items[0])
    else:
        graph["@graph"] = graph_items
    json_text = json.dumps(graph, ensure_ascii=False, indent=2)
    # Round-trip parsing proves the delivered block is syntactically valid JSON.
    json.loads(json_text)
    script = f'<script type="application/ld+json">\n{json_text}\n</script>'
    error_count = sum(issue.severity == "error" for block in blocks for issue in block.issues)
    warning_count = sum(issue.severity == "warning" for block in blocks for issue in block.issues)
    publish_ready = error_count == 0
    if publish_ready:
        summary = (
            f"Publish-ready draft: JSON syntax passed and no blocking issues were found across "
            f"{len(blocks)} schema type{'s' if len(blocks) != 1 else ''}. "
            f"Review {warning_count} warning{'s' if warning_count != 1 else ''}, then validate the live page in Google's Rich Results Test."
        )
    else:
        summary = (
            f"Draft only: JSON syntax passed, but {error_count} blocking issue{'s' if error_count != 1 else ''} "
            f"must be fixed before publishing. {warning_count} warning{'s' if warning_count != 1 else ''} also need review."
        )
        global_warnings.insert(0, "Do not publish this draft until every blocking validation issue is resolved.")
    global_warnings.append(
        "Valid structured data can make a page eligible for enhanced search results, but display is never guaranteed."
    )
    return SchemaGenerationResult(
        generation_id=generation_id,
        page_name=brief.page_name,
        page_url=brief.page_url,
        page_type=brief.page_type,
        script=script,
        graph=graph,
        blocks=blocks,
        warnings=list(dict.fromkeys(global_warnings)),
        validation_summary=summary,
        publish_ready=publish_ready,
        blocking_issue_count=error_count,
    )
