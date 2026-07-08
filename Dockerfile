# == Base ==
# Estágio comum a dev e prd: interpretador, uv e as dependências em cache.
FROM python:3.13-slim AS base
# Instala o uv (gerenciador de pacotes/venv). Copiamos os binários da imagem oficial.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# PYTHONDONTWRITEBYTECODE: não gera arquivos .pyc.
# PYTHONUNBUFFERED: não bufferiza stdout/stderr — evita perder logs se o app cair.
# PLAYWRIGHT_BROWSERS_PATH: instala o Chromium num caminho fixo e fora do home do
#   usuário, pra funcionar mesmo depois de trocarmos pra um usuário non-root na prd.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
# Copiamos só os manifests primeiro: enquanto eles não mudam, o Docker reaproveita
# a camada de dependências em cache e não reinstala tudo a cada build.
COPY pyproject.toml uv.lock ./

# == Developer ==
# Imagem de desenvolvimento: TODAS as deps (inclui o grupo `dev`: ruff, poe).
FROM base AS developer
# Instala as dependências sem instalar o projeto ainda (melhor cache).
RUN uv sync --frozen --no-install-project
# Copia o código e finaliza a instalação (o projeto em si).
COPY . .
RUN uv sync --frozen
# crawl4ai roda em cima do Playwright: instala o Chromium + libs de sistema.
RUN uv run playwright install --with-deps chromium
EXPOSE 8000
# CMD padrão da imagem dev — o docker-compose.override.yml sobrescreve com --reload.
CMD ["uv", "run", "uvicorn", "monolith.interfaces.api.main:app", "--host=0.0.0.0", "--port=8000", "--reload"]

# == Production ==
# Imagem de produção: SEM o grupo `dev`, código imutável dentro da imagem,
# rodando como usuário non-root.
FROM base AS production
# --no-dev: ignora o grupo de dev (ruff/poe não vão pra produção).
RUN uv sync --frozen --no-install-project --no-dev
COPY . .
RUN uv sync --frozen --no-dev
# Instala o Chromium ainda como root (apt precisa de root para --with-deps).
RUN uv run playwright install --with-deps chromium
# Cria um usuário sem privilégios e entrega a ele o código e os browsers.
# Rodar como root em produção é uma superfície de ataque desnecessária.
RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app /ms-playwright
USER appuser
EXPOSE 8000
# CMD padrão — o docker-compose.prod.yml sobrescreve com o número de workers.
CMD ["uv", "run", "uvicorn", "monolith.interfaces.api.main:app", "--host=0.0.0.0", "--port=8000", "--workers=4"]
