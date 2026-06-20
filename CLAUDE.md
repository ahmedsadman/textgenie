# TextGenie

TextGenie subscribes to your phone's SMS and helps you categorize messages, identify transactions and keep a digital record

## Testing

All features should have comprehensive unit tests in place.

## Running Commands

The application is containerized with Docker, and all commands must run inside the docker container. Do NOT run commands
inside the host directly. Some command examples are given below:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend yarn test
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend uv run pytest
```

## Git Commits
- Do NOT add Claude co-author info in the commits you create
- Prefer short and simple commit messages
