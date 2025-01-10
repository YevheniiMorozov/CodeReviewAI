FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry \
    && which poetry

COPY ../poetry.lock ../pyproject.toml ./

RUN poetry config virtualenvs.create false

RUN poetry install --no-root

COPY ../ ./app

ENV ENV_FILE=/app/.env

WORKDIR /app

RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["bash","/app/entrypoint.sh"]
