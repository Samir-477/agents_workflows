from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str | None = None
    report_output_dir: Path | None = None
    write_report_files: bool = True
    request_timeout_seconds: float = 12.0
    crawl_timeout_seconds: float = 240.0
    maximum_response_bytes: int = 5_000_000
    crawl_delay_seconds: float = 0.15
    default_crawl_limit: int = 20
    maximum_crawl_limit: int = 100
    worker_poll_seconds: float = 1.0
    user_agent: str = "SEO-AEO-Audit-Agent/0.1 (+read-only audit)"
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    # Providers reserve `max_tokens` against the account's output-tokens-per-minute
    # allowance before running the request, so a budget above the plan's ceiling is
    # rejected outright rather than rate-limited. Every agent sizes its calls under
    # this value; lower it to match a smaller plan, raise it on a larger one.
    llm_max_output_tokens: int = 900
    serper_api_key: str | None = None
    allow_private_networks: bool = False
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
    cors_origin_regex: str | None = None

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        selected_env_file = env_file or Path(
            os.getenv("SEO_AUDIT_ENV_FILE", Path.cwd() / ".env")
        )
        load_dotenv(dotenv_path=selected_env_file, override=False)
        database_url = (os.getenv("DATABASE_URL") or "").strip() or None
        if database_url is None:
            raise ValueError(
                "DATABASE_URL is required. Configure the Supabase Postgres transaction-pooler URL."
            )
        llm_provider = (
            os.getenv("AGENT_LLM_PROVIDER")
            or os.getenv("SEO_AUDIT_LLM_PROVIDER")
            or ""
        ).strip().lower() or None
        if llm_provider not in {None, "groq", "openai"}:
            raise ValueError("SEO_AUDIT_LLM_PROVIDER must be 'groq' or 'openai'")
        if llm_provider == "groq":
            llm_api_key = os.getenv("GROQ_API_KEY") or None
        elif llm_provider == "openai":
            llm_api_key = os.getenv("OPENAI_API_KEY") or None
        else:
            llm_api_key = None
        cors_origins_env = os.getenv("SEO_AUDIT_CORS_ORIGINS")
        if cors_origins_env is not None:
            cors_origins = tuple(
                origin.strip()
                for origin in cors_origins_env.split(",")
                if origin.strip()
            )
        else:
            cors_origins = (
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "*",
            )
        return cls(
            database_url=database_url,
            report_output_dir=(
                Path(os.getenv("SEO_AUDIT_REPORTS_DIR", Path.cwd() / "reports"))
                if not os.getenv("VERCEL") or os.getenv("SEO_AUDIT_REPORTS_DIR")
                else None
            ),
            write_report_files=not bool(os.getenv("VERCEL")),
            request_timeout_seconds=float(os.getenv("SEO_AUDIT_REQUEST_TIMEOUT", "12")),
            crawl_timeout_seconds=float(os.getenv("SEO_AUDIT_CRAWL_TIMEOUT", "240")),
            maximum_response_bytes=max(
                100_000, int(os.getenv("SEO_AUDIT_MAX_RESPONSE_BYTES", "5000000"))
            ),
            crawl_delay_seconds=float(os.getenv("SEO_AUDIT_CRAWL_DELAY", "0.15")),
            default_crawl_limit=int(os.getenv("SEO_AUDIT_DEFAULT_CRAWL_LIMIT", "20")),
            maximum_crawl_limit=int(os.getenv("SEO_AUDIT_MAX_CRAWL_LIMIT", "100")),
            worker_poll_seconds=float(os.getenv("SEO_AUDIT_WORKER_POLL_SECONDS", "1")),
            user_agent=os.getenv(
                "SEO_AUDIT_USER_AGENT",
                "SEO-AEO-Audit-Agent/0.1 (+read-only audit)",
            ),
            llm_provider=llm_provider,
            llm_model=(
                os.getenv("AGENT_LLM_MODEL")
                or os.getenv("SEO_AUDIT_LLM_MODEL")
                or None
            ),
            llm_api_key=llm_api_key,
            llm_max_output_tokens=max(
                200, int(os.getenv("AGENT_LLM_MAX_OUTPUT_TOKENS", "900"))
            ),
            serper_api_key=(os.getenv("SERPER_API_KEY") or "").strip() or None,
            allow_private_networks=os.getenv("SEO_AUDIT_ALLOW_PRIVATE_NETWORKS", "false").lower()
            in {"1", "true", "yes"},
            cors_origins=cors_origins,
            cors_origin_regex=(
                os.getenv("SEO_AUDIT_CORS_ORIGIN_REGEX") or ""
            ).strip()
            or None,
        )
