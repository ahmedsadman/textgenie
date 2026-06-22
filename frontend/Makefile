DOCKER_CMD = docker compose -f ../docker-compose.yml -f ../docker-compose.dev.yml exec frontend

.PHONY: test lint format format-check build typecheck

test:
	$(DOCKER_CMD) yarn test

lint:
	$(DOCKER_CMD) yarn lint

format:
	$(DOCKER_CMD) yarn format

format-check:
	$(DOCKER_CMD) yarn format:check

build:
	$(DOCKER_CMD) yarn build

typecheck:
	$(DOCKER_CMD) yarn tsc --noEmit
