from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NOT A PROJECT"
    DATABASE_URL: str | None = None
    LLM_API_KEY: SecretStr | None = None
    LLM_MODEL: str = "qwen2.5:3b"
    LLM_MODEL_PROVIDER: str = "ollama"
    LLM_MODEL_KWARGS: dict = {}
    EMBEDDINGS_MODEL: str = "embeddinggemma:300m"
    LANGSMITH_API_KEY: SecretStr | None = None
    LANGSMITH_TRACING: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
