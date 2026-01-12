# Makefile for managing the application with Docker Compose

.PHONY: up down build logs clean shell-db shell-app

# Start all services (App, DB, Redis, Celery)
up:
	docker compose up --build

# Stop all services
down:
	docker compose down

# Stop all services and remove volumes (cleans DB and Redis data)
clean:
	docker compose down -v
	@echo "All data volumes removed."

# View logs
logs:
	docker compose logs -f

# Access Postgres shell
shell-db:
	docker compose exec db psql -U postgres -d realestate

# Access App shell
shell-app:
	docker compose exec app /bin/bash