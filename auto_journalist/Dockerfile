# Stage 1: build dependencies
FROM python:3.11-slim AS builder
WORKDIR /app

# Copy only requirements to leverage caching
COPY pyproject.toml poetry.lock ./
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev
COPY . .

# Stage 2: runtime image
FROM python:3.11-slim
WORKDIR /app
# Copy installed packages and application code
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/poetry /usr/local/bin/poetry
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command: run migrations and then execute daily pipeline
CMD ["sh", "-c", "alembic upgrade head && python -m auto_journalist.main run_daily"]