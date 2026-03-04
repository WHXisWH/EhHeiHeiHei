from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", validation_alias="APP_ENV")
    http_host: str = Field(default="0.0.0.0", validation_alias="HTTP_HOST")
    http_port: int = Field(default=8000, validation_alias="HTTP_PORT")

    postgres_dsn: str | None = Field(default=None, validation_alias="POSTGRES_DSN")

    gcp_project_id: str | None = Field(default=None, validation_alias="GCP_PROJECT_ID")
    gcp_location: str = Field(default="asia-northeast1", validation_alias="GCP_LOCATION")
    vertex_gemini_model: str = Field(default="gemini-2.5-flash", validation_alias="VERTEX_GEMINI_MODEL")

    firestore_database: str = Field(default="(default)", validation_alias="FIRESTORE_DATABASE")

    shibuya_min_lat: float = Field(default=35.6500, validation_alias="SHIBUYA_MIN_LAT")
    shibuya_max_lat: float = Field(default=35.6900, validation_alias="SHIBUYA_MAX_LAT")
    shibuya_min_lon: float = Field(default=139.6800, validation_alias="SHIBUYA_MIN_LON")
    shibuya_max_lon: float = Field(default=139.7200, validation_alias="SHIBUYA_MAX_LON")

    use_firestore: bool = Field(default=True, validation_alias="USE_FIRESTORE")
    enable_fake_ai: bool = Field(default=False, validation_alias="ENABLE_FAKE_AI")


def get_settings() -> Settings:
    return Settings()
