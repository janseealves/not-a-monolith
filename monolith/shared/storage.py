import asyncio
import logging
from urllib.parse import urlparse

import boto3
from botocore.client import Config

from monolith.shared.config import Settings

logger = logging.getLogger(__name__)

_SCHEME = "s3"


class ObjectStore:
    """Acesso ao MinIO pela API S3.

    Mantém dois clients de propósito. A assinatura de uma presigned URL cobre o
    host, então o link que vai para o browser precisa ser assinado com o
    endpoint público: assinar com o endpoint interno da rede do Compose produz
    uma URL que o cliente recebe como 403, sem pista nenhuma do motivo.
    """

    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.MINIO_BUCKET
        self._ttl = settings.MINIO_URL_TTL_SECONDS
        self._client = _build_client(settings, settings.MINIO_ENDPOINT)
        self._signer = _build_client(settings, settings.MINIO_PUBLIC_ENDPOINT)

    @property
    def url_ttl(self) -> int:
        return self._ttl

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Grava o objeto e devolve a URI `s3://` que passa a identificá-lo."""
        # boto3 é síncrono e vai à rede: fora da thread do event loop.
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info("Uploaded %d bytes to %s/%s", len(data), self._bucket, key)
        return f"{_SCHEME}://{self._bucket}/{key}"

    def presigned_url(self, uri: str) -> str:
        """Link temporário de leitura. Só assina localmente, não vai à rede."""
        bucket, key = parse_uri(uri)
        return self._signer.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=self._ttl,
        )


def parse_uri(uri: str) -> tuple[str, str]:
    """`s3://bucket/caminho/arquivo.pdf` -> `("bucket", "caminho/arquivo.pdf")`."""
    parsed = urlparse(uri)
    key = parsed.path.lstrip("/")
    if parsed.scheme != _SCHEME or not parsed.netloc or not key:
        raise ValueError(f"URI de object store inválida: {uri}")
    return parsed.netloc, key


def _build_client(settings: Settings, endpoint: str):
    password = (
        settings.MINIO_ROOT_PASSWORD.get_secret_value()
        if settings.MINIO_ROOT_PASSWORD
        else None
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=password,
        region_name="us-east-1",  # MinIO ignora, mas boto3 exige uma região.
        # MinIO serve o bucket no path, não como subdomínio do host.
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
