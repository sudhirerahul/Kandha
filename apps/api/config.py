# Centralised settings for the Kandha API — loaded from environment variables
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # GMI Cloud / Kimi K2
    gmi_api_key: str = ""
    gmi_base_url: str = "https://api.gmi.ai/v1"
    gmi_model: str = "kimi-k2-5"

    # Dify
    dify_api_key: str = ""
    dify_base_url: str = "https://api.dify.ai/v1"
    dify_workflow_id_analyze: str = ""
    dify_workflow_id_migrate: str = ""
    dify_workflow_id_infra: str = ""

    # HydraDB
    hydra_api_key: str = ""
    hydra_base_url: str = ""
    hydra_tenant_id: str = "kandha"

    # Photon
    photon_api_key: str = ""
    photon_endpoint: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://kandha:kandha@localhost:5432/kandha"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "kandha"
    minio_secret_key: str = "kandha_secret"
    minio_bucket: str = "kandha-uploads"
    minio_secure: bool = False

    # App
    secret_key: str = "change_me_in_production"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
