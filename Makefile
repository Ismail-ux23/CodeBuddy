.PHONY: install migrate seed-demo dev test lint build docker-up
install:
	cd frontend && npm ci
	cd backend && uv sync --frozen --group dev
migrate:
	cd backend && uv run alembic upgrade head
seed-demo:
	python3 scripts/verify_demo.py
dev:
	@echo "Start API: cd backend && uv run flask --app wsgi run --port 5001"
	@echo "Start worker: cd backend && uv run celery -A app.tasks.worker:celery worker -B --concurrency=2"
	cd frontend && npm run dev
test:
	cd backend && uv run pytest
	cd frontend && npm test
lint:
	cd backend && uv run ruff check app tests --select F
	cd frontend && npm run lint
build:
	cd frontend && npm run build
docker-up:
	docker compose up --build -d
