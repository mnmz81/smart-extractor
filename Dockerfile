# Build: docker build -t smart-extractor .
# Run:   docker run --rm -p 127.0.0.1:8000:8000 --env-file .env -v "$PWD/data/private:/app/data/private" smart-extractor
# The API keys come from --env-file at run time and are never copied into the image.
# Publish the port on 127.0.0.1 only: the API has no auth and spends API money per request.

FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# dependencies first: this layer is cached until pyproject.toml or uv.lock change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data/private \
    && chown -R app /app/data
WORKDIR /app
COPY --from=build --chown=app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000
CMD ["uvicorn", "--factory", "smart_extractor.api:create_app", "--host", "0.0.0.0", "--port", "8000"]
