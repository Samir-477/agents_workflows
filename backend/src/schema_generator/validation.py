from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from schema_generator.models import ValidationIssue


_COMMON_PROPERTIES = {
    "name", "description", "url", "image", "identifier", "sameAs", "mainEntityOfPage",
}
_TYPE_PROPERTIES: dict[str, set[str]] = {
    "Organization": {"logo", "telephone", "email", "address", "contactPoint", "founder", "foundingDate"},
    "LocalBusiness": {"address", "telephone", "email", "geo", "openingHours", "openingHoursSpecification", "priceRange"},
    "MedicalBusiness": {"address", "telephone", "email", "geo", "openingHours", "openingHoursSpecification", "priceRange"},
    "Product": {"sku", "mpn", "brand", "offers", "review", "aggregateRating", "category", "color", "material"},
    "Article": {"headline", "author", "publisher", "datePublished", "dateModified", "articleBody", "wordCount"},
    "FAQPage": {"mainEntity"},
    "Event": {"startDate", "endDate", "location", "eventStatus", "eventAttendanceMode", "offers", "organizer", "performer"},
    "SoftwareApplication": {"applicationCategory", "operatingSystem", "offers", "aggregateRating", "softwareVersion", "downloadUrl"},
}
_URL_KEYS = {"url", "image", "logo", "sameAs", "downloadUrl", "contentUrl", "embedUrl"}
_DATE_KEYS = {"datePublished", "dateModified", "startDate", "endDate", "foundingDate"}
_SOURCE_FACT_KEYS = {
    "price", "lowPrice", "highPrice", "priceCurrency", "ratingValue", "reviewCount",
    "ratingCount", "offerCount", "telephone", "email", "datePublished", "dateModified",
    "startDate", "endDate", "foundingDate", "openingHours", "availability",
}
_CURRENCY_MARKERS = {"GBP": ("£", "gbp"), "USD": ("$", "usd"), "EUR": ("€", "eur"), "INR": ("₹", "inr")}
_MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)


def _issue(severity: str, code: str, message: str, schema_type: str) -> ValidationIssue:
    return ValidationIssue(severity=severity, code=code, message=message, schema_type=schema_type)  # type: ignore[arg-type]


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_iso_date(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return bool(re.fullmatch(r"\d{4}(?:-\d{2})?", value))


def _walk(value: Any, path: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield child_path, key, child
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _fact_is_supported(key: str, value: Any, source: str) -> bool:
    folded = source.casefold()
    if key == "availability":
        marker = str(value).rsplit("/", 1)[-1].casefold()
        phrases = {
            "instock": ("in stock", "available"),
            "outofstock": ("out of stock", "sold out", "unavailable"),
            "preorder": ("preorder", "pre-order"),
        }
        return any(item in folded for item in phrases.get(marker, (marker,)))
    if key == "priceCurrency":
        currency = str(value).upper()
        return any(marker.casefold() in folded for marker in _CURRENCY_MARKERS.get(currency, (currency,)))
    if key in {"price", "lowPrice", "highPrice", "ratingValue", "reviewCount", "ratingCount", "offerCount"}:
        try:
            expected = float(value)
            return any(float(candidate.replace(",", "")) == expected for candidate in re.findall(r"\d[\d,]*(?:\.\d+)?", source))
        except (TypeError, ValueError):
            return False
    if key == "telephone":
        expected_digits = re.sub(r"\D", "", str(value))
        return bool(expected_digits) and expected_digits in re.sub(r"\D", "", source)
    if key in _DATE_KEYS and isinstance(value, str) and _is_iso_date(value):
        date_part = value[:10]
        if date_part in source:
            return True
        match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", date_part)
        if match:
            year, month, day = match.groups()
            month_name = _MONTH_NAMES[int(month) - 1]
            return year in folded and month_name in folded and str(int(day)) in re.findall(r"\d+", folded)
    rendered = str(value).strip().casefold()
    return rendered in folded


def _validate_offer(offer: Any, schema_type: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    offers = offer if isinstance(offer, list) else [offer]
    if not offers or any(not isinstance(item, dict) for item in offers):
        return [_issue("error", "invalid-offers-shape", "offers must be an Offer/AggregateOffer object or a list of Offer objects.", schema_type)]
    for item in offers:
        item_type = item.get("@type")
        if item_type not in {"Offer", "AggregateOffer"}:
            issues.append(_issue("error", "invalid-offer-type", "Each offers object must use @type Offer or AggregateOffer.", schema_type))
        price_key = "lowPrice" if item_type == "AggregateOffer" else "price"
        if item.get(price_key) in (None, ""):
            issues.append(_issue("error", "offer-price-missing", f"{item_type or 'Offer'} needs {price_key}.", schema_type))
        if not item.get("priceCurrency"):
            issues.append(_issue("error", "offer-currency-missing", "Each priced offer needs a three-letter priceCurrency value.", schema_type))
        elif not re.fullmatch(r"[A-Z]{3}", str(item["priceCurrency"])):
            issues.append(_issue("error", "invalid-price-currency", "priceCurrency must be a three-letter uppercase currency code such as USD or GBP.", schema_type))
    return issues


def _validate_rating(rating: Any, schema_type: str) -> list[ValidationIssue]:
    if not isinstance(rating, dict):
        return [_issue("error", "invalid-rating-shape", "aggregateRating must be an AggregateRating object.", schema_type)]
    issues: list[ValidationIssue] = []
    if rating.get("@type") != "AggregateRating":
        issues.append(_issue("error", "invalid-rating-type", "aggregateRating must use @type AggregateRating.", schema_type))
    if rating.get("ratingValue") in (None, ""):
        issues.append(_issue("error", "rating-value-missing", "aggregateRating needs ratingValue.", schema_type))
    if not any(rating.get(key) not in (None, "") for key in ("reviewCount", "ratingCount")):
        issues.append(_issue("error", "rating-count-missing", "aggregateRating needs reviewCount or ratingCount.", schema_type))
    return issues


def _validate_reviews(review: Any, schema_type: str) -> list[ValidationIssue]:
    reviews = review if isinstance(review, list) else [review]
    if not reviews or any(not isinstance(item, dict) for item in reviews):
        return [_issue("error", "invalid-review-shape", "review must be a Review object or list of Review objects.", schema_type)]
    issues: list[ValidationIssue] = []
    for item in reviews:
        if item.get("@type") != "Review":
            issues.append(_issue("error", "invalid-review-type", "Each review must use @type Review.", schema_type))
        rating = item.get("reviewRating")
        if not isinstance(rating, dict) or rating.get("@type") != "Rating" or rating.get("ratingValue") in (None, ""):
            issues.append(_issue("error", "invalid-review-rating", "Each review needs reviewRating with @type Rating and ratingValue.", schema_type))
        if not item.get("author"):
            issues.append(_issue("error", "review-author-missing", "Each review needs an author that is visible on the page.", schema_type))
    return issues


def _validate_typed_collection(value: Any, property_name: str, expected_type: str, schema_type: str) -> list[ValidationIssue]:
    items = value if isinstance(value, list) else [value]
    if not items or any(not isinstance(item, dict) for item in items):
        return [_issue("error", f"invalid-{property_name}-shape", f"{property_name} must be a {expected_type} object or list of those objects.", schema_type)]
    if any(item.get("@type") != expected_type for item in items):
        return [_issue("error", f"invalid-{property_name}-type", f"Every {property_name} object must use @type {expected_type}.", schema_type)]
    return []


def _validate_faq(main_entity: Any, schema_type: str) -> list[ValidationIssue]:
    if not isinstance(main_entity, list) or not main_entity:
        return [_issue("error", "invalid-faq-shape", "mainEntity must be a non-empty list of Question objects.", schema_type)]
    issues: list[ValidationIssue] = []
    for index, question in enumerate(main_entity, start=1):
        if not isinstance(question, dict) or question.get("@type") != "Question" or not question.get("name"):
            issues.append(_issue("error", "invalid-faq-question", f"FAQ item {index} needs @type Question and a visible question in name.", schema_type))
            continue
        answer = question.get("acceptedAnswer")
        if not isinstance(answer, dict) or answer.get("@type") != "Answer" or not answer.get("text"):
            issues.append(_issue("error", "invalid-faq-answer", f"FAQ item {index} needs an acceptedAnswer with @type Answer and visible text.", schema_type))
    return issues


def validate_schema_entity(schema_type: str, item: dict[str, Any], source_prompt: str | None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    allowed = _COMMON_PROPERTIES | _TYPE_PROPERTIES.get(schema_type, set())
    for key in item:
        if not key.startswith("@") and key not in allowed:
            issues.append(_issue("warning", "unknown-main-property", f"Review non-standard or unexpected {schema_type} property: {key}.", schema_type))

    for path, key, value in _walk(item):
        if key in _URL_KEYS:
            values = value if isinstance(value, list) else [value]
            for candidate in values:
                if isinstance(candidate, str) and not _is_url(candidate):
                    issues.append(_issue("error", "invalid-url", f"{path} must be an absolute http(s) URL.", schema_type))
                elif source_prompt and isinstance(candidate, str) and candidate.rstrip("/") not in source_prompt.replace("\n", " ").rstrip("/"):
                    issues.append(_issue("error", "unsupported-source-fact", f"Remove or verify {path}: this URL is not present in the submitted page facts.", schema_type))
        if key in _DATE_KEYS and isinstance(value, str) and not _is_iso_date(value):
            issues.append(_issue("error", "invalid-date", f"{path} must use an ISO 8601 date or date-time.", schema_type))
        if source_prompt and key in _SOURCE_FACT_KEYS and not isinstance(value, (dict, list)) and not _fact_is_supported(key, value, source_prompt):
            issues.append(_issue("error", "unsupported-source-fact", f"Remove or verify {path}: its value is not present in the submitted page facts.", schema_type))

    address = item.get("address")
    if address is not None and not isinstance(address, (str, dict)):
        issues.append(_issue("error", "invalid-address-shape", "address must be visible text or a PostalAddress object.", schema_type))
    if isinstance(address, dict) and address.get("@type") != "PostalAddress":
        issues.append(_issue("error", "invalid-address-type", "A structured address must use @type PostalAddress.", schema_type))
    if "offers" in item:
        issues.extend(_validate_offer(item["offers"], schema_type))
    if "aggregateRating" in item:
        issues.extend(_validate_rating(item["aggregateRating"], schema_type))
    if "review" in item:
        issues.extend(_validate_reviews(item["review"], schema_type))
    if schema_type == "FAQPage" and "mainEntity" in item:
        issues.extend(_validate_faq(item["mainEntity"], schema_type))
    if "openingHoursSpecification" in item:
        issues.extend(_validate_typed_collection(item["openingHoursSpecification"], "opening-hours", "OpeningHoursSpecification", schema_type))
    if "geo" in item:
        issues.extend(_validate_typed_collection(item["geo"], "geo", "GeoCoordinates", schema_type))
    location = item.get("location")
    if isinstance(location, dict) and location.get("@type") not in {"Place", "VirtualLocation"}:
        issues.append(_issue("error", "invalid-location-type", "A structured Event location must use @type Place or VirtualLocation.", schema_type))
    return issues
