from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from memory_metadata_repository import MemoryMetadataGenerationRepository
from meta_generator.api import create_metadata_router
from meta_generator.generation import MetadataGenerator
from meta_generator.models import (
    DraftGenerationResult,
    DraftMetadataOption,
    DraftPageMetadata,
    MetadataGenerationCreate,
    ParsedGenerationBrief,
    ParsedPageBrief,
)
from meta_generator.validation import validate_draft
from meta_generator.workflow import build_metadata_graph
from seo_audit.config import Settings


def option(text: str, angle: str = "benefit") -> DraftMetadataOption:
    return DraftMetadataOption(
        text=text,
        intent="commercial",
        angle=angle,
        rationale="Matches the page intent using only supplied information.",
    )


def sample_brief() -> ParsedGenerationBrief:
    return ParsedGenerationBrief(
        pages=[
            ParsedPageBrief(
                page_key="pricing",
                page_name="Pricing page",
                page_type="pricing",
                topic="Project management software plans",
                primary_keyword="project management software pricing",
                keyword_source="provided",
                audience="Small teams",
                search_intent="commercial-transactional",
                brand="Planora",
                verified_facts=["Plans for small teams"],
            )
        ]
    )


def sample_draft() -> DraftGenerationResult:
    return DraftGenerationResult(
        pages=[
            DraftPageMetadata(
                page_key="pricing",
                titles=[
                    option("Project Management Software Pricing for Teams | Planora", "keyword"),
                    option("Compare Project Management Plans for Small Teams", "comparison"),
                    option("Flexible Project Management Plans Built for Teams", "benefit"),
                    option("Planora Pricing: Project Management Plans for Teams", "brand"),
                ],
                descriptions=[
                    option(
                        "Compare Planora project management software plans for small teams. Review practical options and choose the plan that best matches how your team works.",
                        "comparison",
                    ),
                    option(
                        "Explore project management software pricing designed for small teams. Compare Planora plans and find an option that supports the way your team works.",
                        "keyword",
                    ),
                    option(
                        "Find a Planora project management plan for your small team. Compare the available options, understand the differences and choose with confidence.",
                        "benefit",
                    ),
                ],
                brand_guidance="Use Planora at the end unless the page is primarily navigational.",
            )
        ]
    )


class FakeGenerator:
    def __init__(self) -> None:
        self.generate_calls = 0

    async def parse(self, prompt: str) -> ParsedGenerationBrief:
        return sample_brief()

    async def generate(self, prompt, brief, **kwargs) -> DraftGenerationResult:
        self.generate_calls += 1
        return sample_draft()


class RepairingGenerator(FakeGenerator):
    async def generate(self, prompt, brief, **kwargs) -> DraftGenerationResult:
        self.generate_calls += 1
        draft = sample_draft()
        if self.generate_calls == 1:
            draft.pages[0].descriptions[0].text += " Save 25% today."
        return draft


def test_validation_calculates_counts_and_recommends_options():
    outcome = validate_draft(
        "generation-1",
        "Write pricing metadata for Planora project management software for small teams.",
        sample_brief(),
        sample_draft(),
    )

    page = outcome.result.pages[0]
    assert all(item.character_count == len(item.text) for item in page.titles)
    assert sum(item.recommended for item in page.titles) == 1
    assert sum(item.recommended for item in page.descriptions) == 1
    assert page.recommended_title_id in {item.id for item in page.titles}


def test_validation_flags_numeric_claims_not_present_in_the_prompt():
    draft = sample_draft()
    draft.pages[0].descriptions[0].text += " Save 25% today."

    outcome = validate_draft(
        "generation-2",
        "Write pricing metadata for Planora project management software.",
        sample_brief(),
        draft,
    )

    issues = outcome.result.pages[0].descriptions[0].issues
    assert any("25%" in issue for issue in issues)
    assert outcome.repair_instructions


def test_generator_requires_an_explicit_model_configuration():
    generator = MetadataGenerator(Settings())

    try:
        generator._model()
    except RuntimeError as exc:
        assert "requires an LLM provider" in str(exc)
    else:
        raise AssertionError("Metadata generation must not use a fake deterministic fallback")


def test_explicit_target_term_is_not_left_labelled_as_inferred():
    brief = sample_brief().model_copy(deep=True)
    brief.pages[0].keyword_source = "inferred"

    corrected = MetadataGenerator._correct_keyword_sources(
        "Target the term 'project management software pricing' for this page.", brief
    )

    assert corrected.pages[0].keyword_source == "provided"
    assert corrected.pages[0].search_intent == "commercial-transactional"


def test_validation_flags_unsupported_value_claims():
    draft = sample_draft()
    draft.pages[0].titles[0].text = "Affordable Project Management Software Pricing | Planora"

    outcome = validate_draft(
        "generation-3",
        "Write pricing metadata for Planora project management software.",
        sample_brief(),
        draft,
    )

    assert any(
        "affordable" in issue.casefold()
        for issue in outcome.result.pages[0].titles[0].issues
    )


def test_validation_preserves_starting_price_qualifiers():
    draft = sample_draft()
    draft.pages[0].titles[0].text = (
        "Planora Pricing: $9 per User per Month for Small Teams"
    )

    outcome = validate_draft(
        "generation-4",
        "Planora plans start at $9 per user per month.",
        sample_brief(),
        draft,
    )

    assert any(
        "qualifier" in issue.casefold()
        for issue in outcome.result.pages[0].titles[0].issues
    )


def test_preferred_length_failure_becomes_a_page_warning():
    draft = sample_draft()
    for index, title in enumerate(draft.pages[0].titles, start=1):
        title.text = f"Planora Pricing Option {index} for Teams"

    outcome = validate_draft(
        "generation-5",
        "Write Planora pricing metadata for teams.",
        sample_brief(),
        draft,
    )

    assert any(
        "preferred 50-60" in warning for warning in outcome.result.pages[0].warnings
    )


async def test_workflow_persists_a_structured_result():
    repository = MemoryMetadataGenerationRepository()
    run = repository.create_generation(
        MetadataGenerationCreate(
            prompt="Write pricing metadata for Planora project management software."
        )
    )
    graph = build_metadata_graph(
        Settings(), repository, generator=FakeGenerator()
    )

    await graph.ainvoke({"generation_id": run.id})

    completed = repository.get_generation(run.id)
    assert completed.status == "complete"
    assert completed.result is not None
    assert completed.result.pages[0].page_key == "pricing"


async def test_workflow_repairs_output_that_fails_deterministic_validation():
    repository = MemoryMetadataGenerationRepository()
    run = repository.create_generation(
        MetadataGenerationCreate(
            prompt="Write pricing metadata for Planora project management software."
        )
    )
    generator = RepairingGenerator()
    graph = build_metadata_graph(Settings(), repository, generator=generator)

    await graph.ainvoke({"generation_id": run.id})

    completed = repository.get_generation(run.id)
    assert generator.generate_calls >= 2
    assert completed.status == "complete"
    assert all(
        "25%" not in option.text
        for option in completed.result.pages[0].descriptions
    )


def test_metadata_api_creates_processes_and_returns_a_result():
    repository = MemoryMetadataGenerationRepository()
    app = FastAPI()
    app.include_router(
        create_metadata_router(Settings(), repository, generator=FakeGenerator())
    )

    with TestClient(app) as client:
        created = client.post(
            "/api/agents/meta-title-description/generations",
            json={
                "prompt": "Write pricing metadata for Planora project management software."
            },
        )
        assert created.status_code == 202
        generation_id = created.json()["generation"]["id"]

        pending = client.get(
            f"/api/agents/meta-title-description/generations/{generation_id}/result"
        )
        assert pending.status_code == 409

        processed = client.post(
            f"/api/agents/meta-title-description/generations/{generation_id}/process"
        )
        assert processed.status_code == 200
        assert processed.json()["generation"]["status"] == "complete"

        result = client.get(
            f"/api/agents/meta-title-description/generations/{generation_id}/result"
        )
        assert result.status_code == 200
        assert len(result.json()["pages"][0]["titles"]) == 4
