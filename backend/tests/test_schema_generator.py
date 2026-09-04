from __future__ import annotations

import json

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from schema_generator.api import create_schema_router
from schema_generator.compiler import compile_schema
from schema_generator.models import ParsedSchemaBrief, SchemaEntityDraft, SchemaGenerationCreate
from schema_generator.storage import MemorySchemaGenerationRepository
from schema_generator.workflow import build_schema_graph
from seo_audit.config import Settings


def product_brief() -> ParsedSchemaBrief:
    return ParsedSchemaBrief(
        page_name="Handmade candle",
        page_type="product page",
        entities=[SchemaEntityDraft(
            schema_type="Product",
            name="Cedar candle",
            properties={
                "description": "A handmade cedar candle.",
                "offers": {"@type": "Offer", "price": 24, "priceCurrency": "GBP", "availability": "https://schema.org/InStock"},
            },
            rationale="The page describes one purchasable product.",
            visible_evidence=["The price and availability are visible on the page."],
        )],
    )


class FakeInterpreter:
    async def interpret(self, prompt: str) -> ParsedSchemaBrief:
        return product_brief()


def test_compiler_emits_parseable_json_ld_and_script():
    result = compile_schema("schema-1", product_brief())
    assert result.graph["@context"] == "https://schema.org"
    assert result.graph["@type"] == "Product"
    assert json.loads(result.script.split("\n", 1)[1].rsplit("\n", 1)[0]) == result.graph
    assert not any(issue.severity == "error" for issue in result.blocks[0].issues)
    assert result.publish_ready is True
    assert result.blocking_issue_count == 0


def test_compiler_flags_incomplete_faq_markup():
    brief = ParsedSchemaBrief(
        page_name="Pricing",
        page_type="pricing page",
        entities=[SchemaEntityDraft(
            schema_type="FAQPage",
            name="Pricing FAQs",
            properties={},
            rationale="FAQ markup was requested.",
        )],
    )
    result = compile_schema("schema-2", brief)
    codes = {issue.code for issue in result.blocks[0].issues}
    assert "missing-required-property" in codes
    assert "faq-visibility-unconfirmed" in codes
    assert result.publish_ready is False


def test_compiler_rejects_malformed_product_offer():
    brief = product_brief()
    brief.entities[0].properties["offers"] = {"@type": "Offer", "price": 24}
    result = compile_schema("schema-bad-offer", brief)
    codes = {issue.code for issue in result.blocks[0].issues}
    assert "offer-currency-missing" in codes
    assert result.publish_ready is False


def test_compiler_blocks_facts_not_present_in_source_prompt():
    result = compile_schema(
        "schema-invented-fact",
        product_brief(),
        source_prompt="Create Product schema for a handmade candle named Cedar candle.",
    )
    unsupported = [issue for issue in result.blocks[0].issues if issue.code == "unsupported-source-fact"]
    assert unsupported
    assert result.publish_ready is False


def test_compiler_accepts_supported_price_currency_and_availability():
    result = compile_schema(
        "schema-supported-facts",
        product_brief(),
        source_prompt="Product schema for Cedar candle, priced at £24 GBP and visibly in stock.",
    )
    assert not any(issue.code == "unsupported-source-fact" for issue in result.blocks[0].issues)
    assert result.publish_ready is True


def test_compiler_validates_article_url_and_date_formats():
    brief = ParsedSchemaBrief(
        page_name="News article",
        page_type="article",
        entities=[SchemaEntityDraft(
            schema_type="Article",
            name="Launch news",
            properties={"headline": "Launch news", "image": "not-a-url", "datePublished": "next Friday"},
            rationale="The page is a news article.",
        )],
    )
    result = compile_schema("schema-invalid-article", brief)
    codes = {issue.code for issue in result.blocks[0].issues}
    assert {"invalid-url", "invalid-date"} <= codes


def test_compiler_accepts_complete_visible_faq_structure():
    brief = ParsedSchemaBrief(
        page_name="Support FAQs",
        page_type="faq page",
        entities=[SchemaEntityDraft(
            schema_type="FAQPage",
            name="Support FAQs",
            properties={"mainEntity": [{"@type": "Question", "name": "When are you open?", "acceptedAnswer": {"@type": "Answer", "text": "We are open Monday to Friday."}}]},
            rationale="The page visibly displays this question and answer.",
            visible_evidence=["The question and answer are visible on the page."],
        )],
    )
    result = compile_schema("schema-valid-faq", brief)
    assert result.publish_ready is True


@pytest.mark.parametrize(
    ("schema_type", "properties"),
    [
        ("Organization", {"url": "https://example.com"}),
        ("LocalBusiness", {"address": {"@type": "PostalAddress", "streetAddress": "1 High Street"}}),
        ("MedicalBusiness", {"address": "1 Clinic Road"}),
        ("Product", {"offers": {"@type": "Offer", "price": 10, "priceCurrency": "USD"}}),
        ("Article", {"headline": "An article", "image": "https://example.com/article.jpg", "datePublished": "2026-09-04"}),
        ("FAQPage", {"mainEntity": [{"@type": "Question", "name": "A question?", "acceptedAnswer": {"@type": "Answer", "text": "An answer."}}]}),
        ("Event", {"startDate": "2026-10-01T18:00:00+05:30", "location": "Town Hall"}),
        ("SoftwareApplication", {"applicationCategory": "BusinessApplication", "operatingSystem": "Web"}),
    ],
)
def test_supported_schema_types_compile_without_blocking_shape_errors(schema_type, properties):
    brief = ParsedSchemaBrief(
        page_name=f"{schema_type} page",
        page_type="test page",
        entities=[SchemaEntityDraft(
            schema_type=schema_type,
            name=f"Example {schema_type}",
            properties=properties,
            rationale="The supplied page facts support this type.",
            visible_evidence=["The questions and answers are visible on the page."] if schema_type == "FAQPage" else [],
        )],
    )
    result = compile_schema(f"schema-{schema_type}", brief)
    assert result.publish_ready is True


async def test_schema_workflow_persists_compiled_result():
    repository = MemorySchemaGenerationRepository()
    run = repository.create_generation(SchemaGenerationCreate(prompt="Product schema for a handmade candle priced at £24 and shown in stock."))
    await build_schema_graph(Settings(), repository, interpreter=FakeInterpreter()).ainvoke({"generation_id": run.id})
    completed = repository.get_generation(run.id)
    assert completed.status == "complete"
    assert completed.result is not None
    assert completed.result.blocks[0].schema_type == "Product"


def test_schema_api_create_process_result_cycle():
    repository = MemorySchemaGenerationRepository()
    app = FastAPI()
    app.include_router(create_schema_router(Settings(), repository, interpreter=FakeInterpreter()))
    with TestClient(app) as client:
        created = client.post("/api/agents/schema-markup/generations", json={"prompt": "Product schema for a handmade candle priced at £24 and shown in stock."})
        assert created.status_code == 202
        generation_id = created.json()["generation"]["id"]
        processed = client.post(f"/api/agents/schema-markup/generations/{generation_id}/process")
        assert processed.status_code == 200
        result = client.get(f"/api/agents/schema-markup/generations/{generation_id}/result")
        assert result.status_code == 200
        assert result.json()["graph"]["@type"] == "Product"
