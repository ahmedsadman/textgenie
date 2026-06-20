.PHONY: dev dev-build dev-down prod prod-build prod-down logs logs-backend logs-frontend

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

dev-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

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
