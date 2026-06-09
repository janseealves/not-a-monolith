import logging
import sys

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NOT A PROJECT"
    LLM_API_KEY: SecretStr | None = None
    LLM_MODEL: str = "qwen2.5:3b"
    LLM_MODEL_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDINGS_MODEL: str = "embeddinggemma:300m"
    LANGSMITH_API_KEY: SecretStr | None = None
    LANGSMITH_TRACING: bool = False
    LOGGING_LEVEL: str = "INFO"
    POSTGRES_HOST: str = "127.0.0.1:5432"
    POSTGRES_USER: str | None = "postgres"
    POSTGRES_PASSWORD: SecretStr | None = None
    POSTGRES_DB: str | None = "not-a-database-dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def get_database_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@{self.POSTGRES_HOST}/{self.POSTGRES_DB}"


settings = Settings()


def setup_logger(level="INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
