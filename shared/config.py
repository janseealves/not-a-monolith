from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NOT A PROJECT"
    DATABASE_URL: str | None = None
    LLM_API_KEY: SecretStr
    LLM_MODEL: str = "gpt-4-mini"
    EMBEDDINGS_MODEL: str = "text-embedding-3-small"
    LANGSMITH_API_KEY: SecretStr | None = None
    LANGSMITH_TRACING: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
