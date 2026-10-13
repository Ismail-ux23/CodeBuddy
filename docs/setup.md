# Setup

## Requirements

Node 24, npm, Python 3.12–3.14, uv, PostgreSQL 17 with pgvector, Redis 7. The containers and CI use Python 3.12. Use the committed lockfiles. No uploaded repository dependencies are installed.

## Containers

1. Copy `.env.example` to `.env`.
2. Generate a secret with `python3 -c "import secrets; print(secrets.token_hex(32))"` and put it in `APP_SECRET_KEY`.
3. For live AI, configure `GEMINI_API_KEY`. Confirm model availability and billing for your account.
4. Run `docker compose up --build -d`, then `docker compose logs migrate api worker scheduler`.
5. Visit `http://localhost:8080`, register, create a project, upload `demo/quiz-garden.zip`, inspect the preview, and approve indexing.
6. Wait for the real job to finish; ask “What happens when a quiz is submitted?” and inspect each citation.

PostgreSQL and Redis are private to the Compose network. Only Nginx publishes a port. Database defaults are for local development. For production set a strong `POSTGRES_PASSWORD` in `.env` and update `DATABASE_URL` to match.

## Local services

Start PostgreSQL with `CREATE EXTENSION vector` privileges for the migration user and Redis. Export the variables from `.env` in each backend terminal, replacing container hostnames with localhost. Avoid shell-sourcing an untrusted environment file.

```sh
export DATABASE_URL=postgresql+psycopg://codebuddy:codebuddy@localhost:5432/codebuddy
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/1
export CELERY_RESULT_BACKEND=redis://localhost:6379/2
export STORAGE_PATH=/tmp/codebuddy-source
cd backend
uv sync --frozen
uv run alembic upgrade head
uv run flask --app wsgi run --port 5001
```

Separate terminal, same environment:

```sh
cd backend
uv run celery -A app.tasks.worker:celery worker -B --concurrency=2 --loglevel=INFO
```

`-B` combines beat with a single development worker. Production Compose runs a separate scheduler; never run two schedulers intentionally.

```sh
cd frontend
npm ci
npm run dev
```

Next routes `/api` to port 5001 by default. Browser calls are same-origin. `API_INTERNAL_URL` is a server/build setting; Compose builds it for the internal API hostname.

## Configuration limits

ZIP 100 MiB; expansion 500 MiB; 50,000 archive entries; 2000 included files; 1 MiB per text file; 100:1 compression ratio; 10,000 chunks; 1,000,000 estimated embedding tokens per snapshot; 10,000 context token estimate; 6000 question characters; 20 projects and 500 MiB sanitized source per account; 100 AI jobs per rolling day. Model token estimates use characters/4, not a provider tokenizer. Job retry is capped at three attempts. Preview retention is 24 hours; metadata audit/usage retention is 30 days.

All environment settings are documented in `.env.example`. `LIVE_DEMO_ENABLED` is reserved and does not enable arbitrary public AI calls in this implementation. `LOG_LEVEL` is intended for deployment logging; worker commands currently set INFO explicitly. Never assume a missing key means free live AI.

## Integration tests

Use an isolated database with `test` in its name; fixtures drop its tables.

```sh
export TEST_DATABASE_URL=postgresql+psycopg://codebuddy:codebuddy@localhost:5432/codebuddy_test
export TEST_REDIS_URL=redis://localhost:6379/4
cd backend
uv run pytest
```
