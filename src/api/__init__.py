"""Application settings, loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Runtime configuration."""

    # App
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    # Auth: local JWT (HS256) always available; Azure AD SSO (RS256) if configured.
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-before-deploying")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expiry_minutes: int = int(os.getenv("JWT_EXPIRY_MINUTES", "480"))
    azure_tenant_id: str = os.getenv("AZURE_TENANT_ID", "")
    azure_client_id: str = os.getenv("AZURE_CLIENT_ID", "")
    default_team_id: str = os.getenv("DEFAULT_TEAM_ID", "default-team")

    # Postgres — one DSN used for both the app's own tables (teams/users/runs-cache/audit)
    # and LangGraph's checkpoint tables (different table names, no collision). Split into
    # two DSNs if you want them on physically separate databases/instances.
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/orchestrator?sslmode=disable"
    )
    checkpoint_database_url: str = os.getenv("CHECKPOINT_DATABASE_URL", "") or database_url

    # LLM generation: "bedrock" (default at this tier) or "openai"
    llm_provider: str = os.getenv("LLM_PROVIDER", "bedrock")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    # Orchestrator
    max_turns: int = int(os.getenv("MAX_TURNS", "8"))  # safety cap on supervisor loop iterations


settings = Settings()

__all__ = ["settings"]
