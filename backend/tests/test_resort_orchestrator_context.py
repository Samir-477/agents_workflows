"""The parts of the orchestrator that don't need a live network call."""

from __future__ import annotations

from resort_orchestrator.context import PageFacts, build_fact_narrative, derive_keyword_from_url


def test_keyword_derives_from_the_url_slug_not_the_page_title():
    assert derive_keyword_from_url("https://example.com/resorts-hotels/lake-palace-alleppey") == "Lake Palace Alleppey"
    assert derive_keyword_from_url("https://example.com/resorts-hotels/goa-varca/") == "Goa Varca"
    assert derive_keyword_from_url("https://example.com/resorts-hotels/kodaikanal-lake") == "Kodaikanal Lake"


def test_keyword_derivation_drops_trailing_numeric_segments():
    assert derive_keyword_from_url("https://example.com/resorts-hotels/ooty-fern-hill-2") == "Ooty Fern Hill"


def test_keyword_derivation_falls_back_when_the_path_is_empty():
    assert derive_keyword_from_url("https://example.com/") == "this resort"


def _facts(**overrides) -> PageFacts:
    base = dict(
        url="https://example.com/resorts-hotels/kodaikanal-lake",
        title="Sterling Kodai Lake", meta_description="A resort by the lake.",
        h1=["Kodai Lake Resort"], h2=["Rooms", "Dining"],
        body_text="A 6.5-acre resort with 102 rooms, a spa, and multi-cuisine dining.",
        schema_types=["LodgingBusiness"], json_ld_errors=[], word_count=200,
        images_total=50, images_missing_alt=5, images_generic_alt=3, phone_numbers=["07969792009"],
    )
    base.update(overrides)
    return PageFacts(**base)


def test_narrative_contains_every_real_fact_verbatim():
    facts = _facts()
    narrative = build_fact_narrative(facts, "Kodaikanal Lake")
    for fact in (facts.title, facts.meta_description, facts.h1[0], facts.body_text, facts.phone_numbers[0]):
        assert fact in narrative


def test_narrative_never_asserts_a_fact_it_does_not_have():
    facts = _facts(phone_numbers=[], meta_description=None)
    narrative = build_fact_narrative(facts, "Kodaikanal Lake")
    assert "Telephone" not in narrative
    assert "Page description" not in narrative
    # The grounding instruction to the downstream agent must still be present.
    assert "Do not add amenities" in narrative
