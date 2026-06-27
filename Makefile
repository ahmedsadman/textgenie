.PHONY: dev dev-build dev-down prod prod-build prod-down logs logs-backend logs-frontend migrate generate-migration

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

dev-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

dev-down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

prod:
	docker compose up

prod-build:
	docker compose up --build

prod-down:
	docker compose down

logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

logs-backend:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend

logs-frontend:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend

migrate:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend uv run alembic upgrade head

generate-migration:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend uv run alembic revision --autogenerate -m "$(name)"
