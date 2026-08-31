from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_runtime.postgres import PostgresRepository


ProviderName = Literal["groq"]
PROVIDERS: tuple[ProviderName, ...] = ("groq",)
SUPPORTED_GROQ_MODELS = {
    "qwen/qwen3.6-27b": ("Qwen 3.6 27B", "preview"),
    "qwen/qwen3.8-27b": ("Qwen 3.8 27B", "preview"),
    "openai/gpt-oss-120b": ("GPT-OSS 120B", "production"),
    "openai/gpt-oss-20b": ("GPT-OSS 20B", "production"),
}


class ProviderKeyUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    api_key: str = Field(min_length=12, max_length=500)


class ModelSelectionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    model: str = Field(min_length=1, max_length=120)


class ModelOption(BaseModel):
    id: str
    label: str
    release_tier: Literal["production", "preview"]


class ProviderKeyStatus(BaseModel):
    provider: ProviderName
    label: str
    configured: bool
    source: Literal["database", "environment", "not_configured"]
    masked_key: str | None = None
    updated_at: datetime | None = None


class ProviderSettingsResponse(BaseModel):
    providers: list[ProviderKeyStatus]
    active_provider: str | None = None
    active_model: str | None = None
    model_source: Literal["database", "environment"] = "environment"
    model_options: list[ModelOption]


class ProviderCredentialRepository(PostgresRepository):
    """Store API keys in Supabase Vault and expose only masked metadata."""

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                "CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_provider_settings (
                    provider TEXT PRIMARY KEY,
                    vault_secret_id UUID,
                    key_suffix TEXT,
                    model_id TEXT,
                    updated_at TEXT NOT NULL,
                    CONSTRAINT agent_provider_settings_provider_check
                      CHECK (provider IN ('groq', 'openai'))
                )
                """
            )
            connection.execute(
                "ALTER TABLE agent_provider_settings ADD COLUMN IF NOT EXISTS model_id TEXT"
            )
            connection.execute(
                "ALTER TABLE agent_provider_settings ALTER COLUMN vault_secret_id DROP NOT NULL"
            )
            connection.execute(
                "ALTER TABLE agent_provider_settings ALTER COLUMN key_suffix DROP NOT NULL"
            )

    @staticmethod
    def _validate_provider(provider: str) -> ProviderName:
        if provider not in PROVIDERS:
            raise ValueError("Unsupported API provider")
        return provider  # type: ignore[return-value]

    @staticmethod
    def _mask(suffix: str) -> str:
        return f"••••••••{suffix}"

    def resolve_api_key(self, provider: str, fallback: str | None = None) -> str | None:
        provider = self._validate_provider(provider)
        with self.connect() as connection:
            row = self._execute(
                connection,
                """
                SELECT secrets.decrypted_secret
                FROM agent_provider_settings settings
                JOIN vault.decrypted_secrets secrets
                  ON secrets.id = settings.vault_secret_id
                WHERE settings.provider = ?
                """,
                (provider,),
            ).fetchone()
        return str(row["decrypted_secret"]) if row else fallback

    def resolve_model(self, fallback: str | None = None) -> str | None:
        with self.connect() as connection:
            row = self._execute(
                connection,
                "SELECT model_id FROM agent_provider_settings WHERE provider = 'groq'",
            ).fetchone()
        return str(row["model_id"]) if row and row["model_id"] else fallback

    def list_statuses(
        self,
        *,
        environment_keys: dict[str, str | None],
        active_provider: str | None,
        active_model: str | None,
    ) -> ProviderSettingsResponse:
        with self.connect() as connection:
            rows = self._execute(
                connection,
                """
                SELECT provider, vault_secret_id, key_suffix, model_id, updated_at
                FROM agent_provider_settings
                """,
            ).fetchall()
        saved = {row["provider"]: row for row in rows}
        labels = {"groq": "Groq"}
        statuses: list[ProviderKeyStatus] = []
        for provider in PROVIDERS:
            row = saved.get(provider)
            environment_key = environment_keys.get(provider)
            if row and row["vault_secret_id"] and row["key_suffix"]:
                statuses.append(
                    ProviderKeyStatus(
                        provider=provider,
                        label=labels[provider],
                        configured=True,
                        source="database",
                        masked_key=self._mask(row["key_suffix"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                    )
                )
            elif environment_key:
                statuses.append(
                    ProviderKeyStatus(
                        provider=provider,
                        label=labels[provider],
                        configured=True,
                        source="environment",
                        masked_key=self._mask(environment_key[-4:]),
                    )
                )
            else:
                statuses.append(
                    ProviderKeyStatus(
                        provider=provider,
                        label=labels[provider],
                        configured=False,
                        source="not_configured",
                    )
                )
        groq_row = saved.get("groq")
        saved_model = groq_row["model_id"] if groq_row else None
        return ProviderSettingsResponse(
            providers=statuses,
            active_provider="groq",
            active_model=saved_model or active_model,
            model_source="database" if saved_model else "environment",
            model_options=[
                ModelOption(id=model_id, label=details[0], release_tier=details[1])
                for model_id, details in SUPPORTED_GROQ_MODELS.items()
            ],
        )

    def save_model(self, model: str) -> None:
        if model not in SUPPORTED_GROQ_MODELS:
            raise ValueError("Unsupported Groq model")
        with self.connect() as connection:
            self._execute(
                connection,
                """
                INSERT INTO agent_provider_settings (provider, model_id, updated_at)
                VALUES ('groq', ?, ?)
                ON CONFLICT (provider) DO UPDATE SET
                    model_id = EXCLUDED.model_id,
                    updated_at = EXCLUDED.updated_at
                """,
                (model, datetime.now(UTC).isoformat()),
            )

    def save_api_key(self, provider: str, api_key: str) -> None:
        provider = self._validate_provider(provider)
        secret_name = f"stellar_{provider}_api_key"
        now = datetime.now(UTC).isoformat()
        with self.connect() as connection:
            existing = self._execute(
                connection,
                "SELECT vault_secret_id FROM agent_provider_settings WHERE provider = ?",
                (provider,),
            ).fetchone()
            if existing and existing["vault_secret_id"]:
                secret_id = existing["vault_secret_id"]
                self._execute(
                    connection,
                    "SELECT vault.update_secret(?::uuid, ?, ?, ?)",
                    (
                        secret_id,
                        api_key,
                        secret_name,
                        f"Stellar {provider} API key",
                    ),
                )
            else:
                secret_id = self._execute(
                    connection,
                    "SELECT vault.create_secret(?, ?, ?) AS id",
                    (api_key, secret_name, f"Stellar {provider} API key"),
                ).fetchone()["id"]
            self._execute(
                connection,
                """
                INSERT INTO agent_provider_settings (
                    provider, vault_secret_id, key_suffix, updated_at
                ) VALUES (?, ?::uuid, ?, ?)
                ON CONFLICT (provider) DO UPDATE SET
                    vault_secret_id = EXCLUDED.vault_secret_id,
                    key_suffix = EXCLUDED.key_suffix,
                    updated_at = EXCLUDED.updated_at
                """,
                (provider, secret_id, api_key[-4:], now),
            )

    def delete_api_key(self, provider: str) -> None:
        provider = self._validate_provider(provider)
        with self.connect() as connection:
            row = self._execute(
                connection,
                "SELECT vault_secret_id FROM agent_provider_settings WHERE provider = ?",
                (provider,),
            ).fetchone()
            if not row:
                return
            self._execute(
                connection,
                """
                UPDATE agent_provider_settings
                SET vault_secret_id = NULL, key_suffix = NULL, updated_at = ?
                WHERE provider = ?
                """,
                (datetime.now(UTC).isoformat(), provider),
            )
            if row["vault_secret_id"]:
                self._execute(
                    connection,
                    "DELETE FROM vault.secrets WHERE id = ?::uuid",
                    (row["vault_secret_id"],),
                )


class MemoryProviderCredentialRepository:
    """Test-only fallback used when the composed app has no database URL."""

    def initialize(self) -> None:
        return None

    def resolve_api_key(self, provider: str, fallback: str | None = None) -> str | None:
        return fallback

    def resolve_model(self, fallback: str | None = None) -> str | None:
        return fallback

    def list_statuses(self, **kwargs) -> ProviderSettingsResponse:
        environment_keys = kwargs.get("environment_keys", {})
        return ProviderSettingsResponse(
            providers=[
                ProviderKeyStatus(
                    provider=provider,
                    label="Groq",
                    configured=bool(environment_keys.get(provider)),
                    source=("environment" if environment_keys.get(provider) else "not_configured"),
                    masked_key=(
                        self._mask(environment_keys[provider][-4:])
                        if environment_keys.get(provider)
                        else None
                    ),
                )
                for provider in PROVIDERS
            ],
            active_provider=kwargs.get("active_provider"),
            active_model=kwargs.get("active_model"),
            model_source="environment",
            model_options=[
                ModelOption(id=model_id, label=details[0], release_tier=details[1])
                for model_id, details in SUPPORTED_GROQ_MODELS.items()
            ],
        )

    _mask = staticmethod(ProviderCredentialRepository._mask)

    def save_api_key(self, provider: str, api_key: str) -> None:
        raise RuntimeError("Provider key persistence requires DATABASE_URL")

    def delete_api_key(self, provider: str) -> None:
        raise RuntimeError("Provider key persistence requires DATABASE_URL")

    def save_model(self, model: str) -> None:
        raise RuntimeError("Model persistence requires DATABASE_URL")
