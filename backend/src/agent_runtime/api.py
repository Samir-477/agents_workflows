from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request, status

from agent_runtime.history import AgentRunHistoryResponse, AgentRunHistoryService
from agent_runtime.provider_settings import (
    MemoryProviderCredentialRepository,
    ProviderCredentialRepository,
    ProviderKeyUpdate,
    ProviderSettingsResponse,
    ModelSelectionUpdate,
)
from agent_runtime.registry import AgentRegistration
from meta_generator.api import create_metadata_router
from meta_generator.generation import MetadataGenerator
from meta_generator.storage import MetadataGenerationRepository
from seo_audit.api import create_app as create_seo_app
from seo_audit.config import Settings
from seo_audit.storage import AuditRepository


def create_app(
    settings: Settings | None = None,
    audit_repository: AuditRepository | None = None,
    metadata_repository: MetadataGenerationRepository | None = None,
    metadata_generator: MetadataGenerator | None = None,
    provider_repository: ProviderCredentialRepository | None = None,
) -> FastAPI:
    """Compose independently implemented agents into one deployable API."""

    settings = settings or Settings.from_env()
    audit_repository = audit_repository or AuditRepository(settings.database_url)
    metadata_repository = metadata_repository or MetadataGenerationRepository(
        settings.database_url
    )
    provider_repository = provider_repository or (
        ProviderCredentialRepository(settings.database_url)
        if settings.database_url
        else MemoryProviderCredentialRepository()
    )
    metadata_generator = metadata_generator or MetadataGenerator(
        settings,
        provider_repository.resolve_api_key,
        provider_repository.resolve_model,
    )
    app = create_seo_app(
        settings,
        audit_repository,
        api_key_resolver=provider_repository.resolve_api_key,
        model_resolver=provider_repository.resolve_model,
    )
    original_lifespan = app.router.lifespan_context
    registrations = [
        AgentRegistration(
            slug="meta-title-description",
            router=create_metadata_router(
                settings,
                metadata_repository,
                generator=metadata_generator,
            ),
            initialize=metadata_repository.initialize,
        )
    ]
    history_service = AgentRunHistoryService(audit_repository, metadata_repository)

    def settings_response() -> ProviderSettingsResponse:
        return provider_repository.list_statuses(
            environment_keys={
                "groq": os.getenv("GROQ_API_KEY"),
            },
            active_provider=settings.llm_provider,
            active_model=settings.llm_model,
        )

    def require_admin(request: Request) -> None:
        if request.cookies.get("stellar_demo_session") != "stellar-admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to manage provider API keys.",
            )

    shared_router = APIRouter()

    @shared_router.get("/api/agent-runs", response_model=AgentRunHistoryResponse)
    def list_agent_runs(
        limit: int = 10,
        offset: int = 0,
        query: str | None = None,
        agent: str | None = None,
    ) -> AgentRunHistoryResponse:
        return history_service.list_runs(
            limit=max(1, min(limit, 50)),
            offset=max(0, offset),
            query=query,
            agent=agent,
        )

    @shared_router.get("/api/settings/providers", response_model=ProviderSettingsResponse)
    def list_provider_settings(request: Request) -> ProviderSettingsResponse:
        require_admin(request)
        return settings_response()

    @shared_router.put(
        "/api/settings/model",
        response_model=ProviderSettingsResponse,
    )
    def save_model_selection(
        payload: ModelSelectionUpdate, request: Request
    ) -> ProviderSettingsResponse:
        require_admin(request)
        try:
            provider_repository.save_model(payload.model)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return settings_response()

    @shared_router.put(
        "/api/settings/providers/{provider}",
        response_model=ProviderSettingsResponse,
    )
    def save_provider_key(
        provider: str, payload: ProviderKeyUpdate, request: Request
    ) -> ProviderSettingsResponse:
        require_admin(request)
        try:
            provider_repository.save_api_key(provider, payload.api_key)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return settings_response()

    @shared_router.delete(
        "/api/settings/providers/{provider}",
        response_model=ProviderSettingsResponse,
    )
    def delete_provider_key(
        provider: str, request: Request
    ) -> ProviderSettingsResponse:
        require_admin(request)
        try:
            provider_repository.delete_api_key(provider)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return settings_response()

    @asynccontextmanager
    async def combined_lifespan(application: FastAPI):
        async with original_lifespan(application):
            for registration in registrations:
                registration.initialize()
            provider_repository.initialize()
            yield

    app.router.lifespan_context = combined_lifespan
    app.title = "Stellar Agents API"
    app.description = "Persisted workflows for Stellar's specialized agents."
    app.state.metadata_repository = metadata_repository
    app.state.provider_repository = provider_repository
    app.include_router(shared_router)
    for registration in registrations:
        app.include_router(registration.router)
    return app
