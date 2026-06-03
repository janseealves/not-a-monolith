# == Base ==
FROM python:3.13-slim AS base
# Install uv and its dependencies. This will allow us to use uv to install the application dependencies and run the application.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1 \
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./

# == Developer  ==
FROM base AS developer
# Caching dependencies. This will allow us to take advantage of Docker's layer caching to speed up subsequent builds when the dependencies haven't changed.
RUN uv sync --frozen --no-install-project
# Copy the source code into the container.
COPY . .
RUN uv sync --frozen
# Expose the port that the application listens on.
EXPOSE 8000
# Run the application.
CMD ["uv", "run", "uvicorn", "interfaces.api.main:app", "--host=0.0.0.0", "--port=8000", "--reload"]

# == Production Builder==
# FROM base AS builder
# RUN uv sync --frozen --no-install-project --no-dev
# COPY . .
# RUN uv sync --frozen --no-dev

# # == Production Final Image == 
# FROM python:3.13-slim AS production 
# WORKDIR /app
# COPY --from=builder /app /app
# ENV PATH="/app/.venv/bin:$PATH"
# CMD ["uvicorn", "interfaces.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
