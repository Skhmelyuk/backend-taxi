.PHONY: help build up down restart logs shell migrate test

help:
	@echo "Taxi Platform Commands:"
	@echo "  make build       - Зібрати Docker образи"
	@echo "  make up          - Запустити контейнери в фоні"
	@echo "  make down        - Зупинити та видалити контейнери"
	@echo "  make restart     - Перезапустити сервіси"
	@echo "  make logs        - Переглянути логи API"
	@echo "  make shell       - Відкрити Django shell"
	@echo "  make migrate     - Виконати міграції бази даних"
	@echo "  make test        - Запустити тести (pytest)"
	@echo "  make initial     - Повний setup (міграції + суперюзер)"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f api

shell:
	docker compose exec api python manage.py shell

migrate:
	docker compose exec api python manage.py migrate

test:
	docker compose exec api pytest

initial:
	docker compose exec api python manage.py initial_setup

superuser:
	docker compose exec api python manage.py createsuperuser

clean:
	docker compose down -v
	docker system prune -f