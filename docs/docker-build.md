# Rodando com Docker

A aplicação sobe via Docker Compose, usando o estágio `developer` do `Dockerfile`
(FastAPI + Uvicorn com `--reload`).

## Pré-requisitos

- Docker e Docker Compose instalados.
- Um arquivo `.env` na raiz com os segredos. Use o template como ponto de partida:

  ```bash
  cp .env.example .env
  ```

  Depois preencha as variáveis (`LANGSMITH_API_KEY`, `LLM_API_KEY`, `LLM_MODEL`, etc.).
  O `.env` é injetado no container em runtime (`env_file` no compose) e **não** é
  copiado para a imagem — ele está no `.dockerignore` e no `.gitignore`.

## Modelos locais (Ollama)

A imagem da aplicação **não** carrega modelos. A inferência roda num
[Ollama](https://ollama.com/) que sobe **no host** (fora do Compose) — assim ele
aproveita a GPU da máquina sem `nvidia-container-toolkit`, e os pesos baixados
persistem entre `docker compose down`.

A app depende de dois modelos, definidos em `shared/config.py`:

| Variável           | Default               | Uso                     |
| ------------------ | --------------------- | ----------------------- |
| `LLM_MODEL`        | `qwen2.5:3b`          | geração de respostas    |
| `EMBEDDINGS_MODEL` | `embeddinggemma:300m` | embeddings (vetores)    |

Antes de subir a aplicação, com o Ollama rodando no host, baixe os dois:

```bash
ollama pull qwen2.5:3b
ollama pull embeddinggemma:300m
ollama list                      # confirma que ambos estão presentes
```

> Se você mudar `LLM_MODEL`/`EMBEDDINGS_MODEL` no `.env`, lembre de dar
> `ollama pull` no modelo novo — senão a primeira chamada falha com *model not found*.

Como a app roda no container e o Ollama no host, o container alcança o host por
`host.docker.internal` (habilitado via `extra_hosts` no `docker-compose.yml`).
A URL vai no `.env`, dentro de `LLM_MODEL_KWARGS`:

```bash
LLM_MODEL_KWARGS={"base_url": "http://host.docker.internal:11434"}
```

## Subir a aplicação

```bash
docker compose up -d --build
```

- `--build` garante que a imagem seja reconstruída quando o `Dockerfile` ou as
  dependências mudarem.
- `-d` roda em background. Omita para ver os logs no terminal.

A API fica disponível em:

- App: http://localhost:8000
- Health check: http://localhost:8000/health
- Docs (Swagger): http://localhost:8000/docs

## Comandos úteis

```bash
docker compose logs -f app    # acompanhar logs
docker compose ps             # status dos serviços
docker compose down           # parar e remover os containers
docker compose up -d --build  # rebuild após mudar dependências
```

## Hot-reload em desenvolvimento

O estágio `developer` roda o Uvicorn com `--reload`, e o `docker-compose.yml` já
vem com os volumes que fazem isso funcionar:

```yaml
    volumes:
      - .:/app          # espelha o código do host em /app (ao vivo)
      - /app/.venv      # preserva a .venv do container (não sobrescreve com a do host)
```

Por isso, ao desenvolver:

- Editar um arquivo `.py` no host reflete na hora dentro do container.
- O `--reload` detecta a mudança e reinicia o Uvicorn sozinho — sem rebuild.

## Adicionando dependências

Editar código é instantâneo (hot-reload), mas instalar um package novo mexe na
`.venv` do container, que é isolada do host. O fluxo é:

```bash
docker compose exec app uv add <package>   # instala na .venv do container e
                                           # atualiza pyproject.toml + uv.lock
```

Como `pyproject.toml` e `uv.lock` são espelhados pelo volume, a mudança volta
para o repo automaticamente. Antes de commitar, valide com um build limpo:

```bash
docker compose up -d --build -V            # -V recria o volume anônimo da .venv
```

> O `Dockerfile` usa `uv sync --frozen`: o build falha se `uv.lock` estiver
> dessincronizado do `pyproject.toml`. Sempre use `uv add` (mantém os dois em
> sincronia) em vez de editar `pyproject.toml` na mão.
