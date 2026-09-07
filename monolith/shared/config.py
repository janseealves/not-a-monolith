import logging
import sys
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NOT A PROJECT"
    LLM_API_KEY: SecretStr | None = None
    LLM_MODEL: str = "qwen2.5:3b"
    LLM_MODEL_PROVIDER: str = "ollama"
    # Chat pode ir pra cloud; embeddings ficam self-hosted (consistência do índice).
    LLM_BASE_URL: str = "http://localhost:11434"
    EMBEDDINGS_BASE_URL: str = "http://localhost:11434"
    EMBEDDINGS_MODEL: str = "embeddinggemma:300m"
    LANGSMITH_API_KEY: SecretStr | None = None
    LANGSMITH_TRACING: bool = False
    LOGGING_LEVEL: str = "INFO"
    POSTGRES_HOST: str = "127.0.0.1:5432"
    POSTGRES_USER: str | None = "postgres"
    POSTGRES_PASSWORD: SecretStr | None = None
    POSTGRES_DB: str | None = "not-a-database-dev"

    # ─── Object store (MinIO) ───
    MINIO_ROOT_USER: str | None = None
    MINIO_ROOT_PASSWORD: SecretStr | None = None
    MINIO_BUCKET: str = "documents"
    # Endpoint interno da rede do Compose: usado para ler e gravar objetos.
    MINIO_ENDPOINT: str = "http://minio:9000"
    # Host que o BROWSER alcança. A assinatura da presigned URL cobre o host, e
    # assinar com o endpoint interno geraria uma URL que o cliente recebe como
    # 403 sem nenhuma pista do motivo.
    MINIO_PUBLIC_ENDPOINT: str = "http://localhost:9000"
    # Validade da presigned URL. Curta o bastante para o link vazar pouco,
    # longa o bastante para o usuário ler a resposta antes de clicar.
    MINIO_URL_TTL_SECONDS: int = 900

    # ─── Agent ───
    # "memory": estado só em RAM (perde no restart). "postgres": persiste threads.
    AGENT_CHECKPOINTER: Literal["memory", "postgres"] = "memory"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def get_database_url(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@{self.POSTGRES_HOST}/{self.POSTGRES_DB}"

    @property
    def get_checkpointer_url(self) -> str:
        # psycopg puro não entende o sufixo "+psycopg" do driver SQLAlchemy.
        pwd = (
            self.POSTGRES_PASSWORD.get_secret_value() if self.POSTGRES_PASSWORD else ""
        )
        return f"postgresql://{self.POSTGRES_USER}:{pwd}@{self.POSTGRES_HOST}/{self.POSTGRES_DB}"


settings = Settings()


def setup_logger(level="INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
