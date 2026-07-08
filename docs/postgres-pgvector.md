# Postgres + pgvector

A camada de persistência de domínio usa **PostgreSQL** com a extensão
[**pgvector**](https://github.com/pgvector/pgvector) para guardar embeddings e
fazer busca por similaridade. O schema é versionado com **Alembic**.

> Estado de **domínio** vive no Postgres. Estado **efêmero de agente** (memória
> curta, traces, locks) vai no Redis - **WIP**

## Visão geral das peças

| Arquivo / serviço            | Papel                                                            |
| ---------------------------- | --------------------------------------------------------------- |
| `docker-compose.yml` (`db`)  | Sobe o Postgres com pgvector já compilado                       |
| `monolith/shared/config.py`           | `Settings` + a property `get_database_url` (fonte única da URL)  |
| `monolith/shared/db/base.py`          | `Base` declarativa que todos os models herdam                   |
| `monolith/shared/db/session.py`       | Engine **async** + fábrica de sessões + `get_db()`              |
| `migrations/`                | Ambiente do Alembic (`env.py`, `versions/`)                     |
| `monolith/<feature>/models.py`| Os models ORM de cada módulo                                     |

## Driver e o porquê de duas pontas (async + sync)

O projeto usa **psycopg3** (`psycopg[binary]`) — sucessor oficial do psycopg2 e o
único caminho pra async com Postgres no SQLAlchemy. Um driver só atende as duas
pontas, com a **mesma URL** (`postgresql+psycopg://`):

- **App → async.** A camada de adapters/agentes usa `create_async_engine`. Quando
  um grafo LangGraph faz I/O concorrente (várias queries/embeddings em paralelo),
  um adapter síncrono viraria gargalo.
- **Alembic → sync.** Migrations rodam fora do request, em CLI. Mantê-las síncronas
  evita o `env.py` async (mais verboso) sem perda nenhuma.

> Por que não asyncpg? Seria async-only e exigiria um **segundo** driver (psycopg2)
> só pro Alembic — duas URLs, dois prefixos, mais manha (pgbouncer, codecs). Um
> driver pra tudo é mais simples e suficiente no nosso volume.

Docs: [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) ·
[dialeto psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)

## Configuração

A URL do banco é montada **num lugar só**, a partir das variáveis de ambiente, na
property `get_database_url` (`monolith/shared/config.py`):

```python
@property
def get_database_url(self) -> str:
    return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@{self.POSTGRES_HOST}/{self.POSTGRES_DB}"
```

Tanto o app (`session.py`) quanto o Alembic (`env.py`) leem essa mesma property —
sem URL duplicada, sem divergência entre ferramenta de migração e runtime.

Variáveis no `.env` (template em `.env.example`):

| Variável            | Exemplo               | Observação                                  |
| ------------------- | --------------------- | ------------------------------------------- |
| `POSTGRES_HOST`     | `127.0.0.1:5432`      | **sem** `http://` — é `host:porta`, não URL |
| `POSTGRES_USER`     | `postgres`            |                                             |
| `POSTGRES_PASSWORD` | `...`                 | `SecretStr`; lido via `.get_secret_value()` |
| `POSTGRES_DB`       | `not-a-database-dev`  | criado no 1º boot pela imagem do Postgres   |

> O serviço `db` no compose recebe `POSTGRES_DB` no `environment` — é isso que faz a
> imagem criar o database custom no primeiro boot. Sem essa variável, só existiria o
> `postgres` default e o `alembic upgrade` falharia.

## A sessão async (`monolith/shared/db/session.py`)

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from monolith.shared.config import settings

engine = create_async_engine(settings.get_database_url, echo=True)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as session:
        yield session
```

- **`engine`** — pool de conexões, criado **uma vez** no processo (thread-safe, caro).
- **`SessionLocal`** — *fábrica* de sessões; cada `SessionLocal()` devolve uma
  `AsyncSession` nova amarrada no engine.
  - `expire_on_commit=False`: evita que o ORM expire objetos no commit e dispare I/O
    lazy fora do `async with` (estouraria em async).
  - `autoflush=False`: você controla quando as mudanças vão pro banco.
- **`get_db()`** — generator que **empresta** a sessão e garante a faxina. O
  `async with` fecha a conexão e faz **rollback** de qualquer transação não-commitada
  na saída (inclusive em exceção). `echo=True` loga o SQL — útil em dev, troque pra
  `False` quando enjoar.

### Quem dá o commit

`get_db()` **não commita** — quem usa decide. Isso mantém a fronteira de transação
explícita (importante quando um agente faz vários passos numa mesma sessão e você não
quer commitar trabalho pela metade):

```python
async for session in get_db():
    session.add(documento)
    await session.commit()        # ← a transação fecha AQUI, de propósito
```

Se você esquecer o commit, o `async with` faz rollback e nada é gravado — falha
segura. (Em FastAPI, use `Depends(get_db)`.)

## Setup do zero

Ordem de execução pra subir o banco a partir de um clone limpo:

```bash
# 1. .env preenchido (POSTGRES_USER/PASSWORD/DB)
cp .env.example .env

# 2. sobe SÓ o Postgres (o app pode subir depois)
docker compose up -d db

# 3. aplica o schema (cria extensão vector + tabelas)
alembic upgrade head
```

`alembic current` deve responder com a revision do head, sem erro.

> O Alembic precisa do banco **no ar** antes do `upgrade`/`--autogenerate` — ele
> conecta pra comparar o estado real com os models. Por isso o passo 2 vem antes.

## Fluxo de trabalho: mudando o schema

Toda alteração de schema passa por migration — **nunca** edite tabela na mão.

```bash
# 1. altere os models (ex.: monolith/rag/models.py)

# 2. gere a migration a partir do diff dos models
alembic revision --autogenerate -m "descrição curta"

# 3. REVISE o arquivo gerado em migrations/versions/ (passo obrigatório)

# 4. aplique
alembic upgrade head
```

Comandos úteis:

```bash
alembic current            # em qual revision o banco está
alembic history            # histórico de migrations
alembic downgrade -1       # desfaz a última migration
alembic upgrade head       # aplica tudo que falta
```

### Por que o passo 3 (revisar) é obrigatório

O `--autogenerate` é um **rascunho**, não verdade final. No nosso stack ele
sistematicamente erra/esquece três coisas:

1. **Import do pgvector.** Ele renderiza a coluna como
   `pgvector.sqlalchemy.vector.VECTOR(...)` mas **não** adiciona o import no topo do
   arquivo. Sem isso, o `upgrade` morre com `NameError`. Adicione à mão:

   ```python
   import pgvector.sqlalchemy.vector
   ```

2. **Índices de similaridade (HNSW / IVFFlat).** O autogenerate **não** cria índice de
   vetor sozinho. Enquanto não houver índice, a busca por similaridade faz full scan
   (ok pra poucos registros, lento em escala). Quando precisar, adicione na migration:

   ```python
   op.create_index(
       "ix_chunks_embedding_hnsw",
       "chunks",
       ["embedding"],
       postgresql_using="hnsw",
       postgresql_with={"m": 16, "ef_construction": 64},
       postgresql_ops={"embedding": "vector_cosine_ops"},
   )
   ```

   Doc: [pgvector — indexing](https://github.com/pgvector/pgvector#indexing)

3. **`server_default`, check constraints, mudança de tipo** — confira sempre se o diff
   reflete a sua intenção.

## A extensão pgvector

`CREATE EXTENSION` instala o tipo `vector` **no banco**, não "na migration" — uma vez
instalado, persiste. Por isso ele entra **uma única vez**, na primeira migration que
usa o tipo `Vector`, no topo do `upgrade()` e **antes** do `create_table` que tem a
coluna:

```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.create_table("chunks", ...)
```

As migrations seguintes **não** repetem isso — apenas usam o tipo.

> No `downgrade`, **não** removemos a extensão (`DROP EXTENSION`). Outros objetos
> podem depender dela; derrubá-la num rollback é arriscado. Deixar instalada é o
> comportamento seguro.

A dimensão do vetor (`Vector(768)`) tem que bater com o modelo de embeddings
(`embeddinggemma:300m` → 768). Mudar a dimensão depois exige migration nova **e**
re-embeddar tudo — confira antes de gerar a primeira migration.

## Verificando o estado do banco

```bash
# extensão, versão e tabelas, direto no container
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dx"   # extensões
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"   # tabelas
```

## Dependências (`pyproject.toml`)

```toml
"sqlalchemy>=2.0.48"     # ORM + engine async
"psycopg[binary]>=3.3.4" # driver psycopg3 (sync + async)
"pgvector>=0.4.2"        # tipo Vector pro SQLAlchemy
"alembic>=1.18.4"        # migrations
```

> Adicione/remova deps sempre com `uv add` / `uv remove` (mantém `pyproject.toml` e
> `uv.lock` em sincronia — o build usa `uv sync --frozen`).
