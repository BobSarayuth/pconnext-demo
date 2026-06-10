FROM python:3.12-alpine AS builder
COPY --from=ghcr.io/astral-sh/uv:alpine /usr/local/bin/uv /usr/local/bin/uvx /bin/

WORKDIR /app

RUN apk add --no-cache build-base cargo

COPY pyproject.toml uv.lock .

RUN uv sync --no-dev --frozen

FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache libstdc++ && adduser -D pyuser

COPY --from=builder --chown=pyuser:pyuser /app/.venv /app/.venv

USER pyuser

COPY --chown=pyuser:pyuser pyproject.toml ./
COPY --chown=pyuser:pyuser entrypoint.sh ./
COPY ./*.py ./
COPY ./agentic/ ./agentic/
COPY ./chatapi/ ./chatapi/

RUN chmod +x entrypoint.sh

CMD ["/app/entrypoint.sh"]
