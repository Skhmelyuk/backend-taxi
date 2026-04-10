.PHONY: help build up down restart logs shell migrate test seed seed-driver seed-all-drivers seed-clear

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
	@echo "  make seed        - Створити тестові дані (пасажири + 2 тест-драйвери + поїздки)"
	@echo "  make seed-clear  - Очистити і перестворити тестові дані"
	@echo "  make seed-driver EMAILS=a@b.com,c@d.com RIDES=30  - Додати поїздки існуючим драйверам"
	@echo "  make seed-all-drivers RIDES=30                     - Додати поїздки всім драйверам"

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

RIDES ?= 30
EMAILS ?=

seed:
	docker compose exec api python manage.py create_test_data --rides $(RIDES)

seed-clear:
	docker compose exec api python manage.py create_test_data --clear --rides $(RIDES)

seed-driver:
	@if [ -z "$(EMAILS)" ]; then echo "Вкажіть EMAILS=email1@x.com,email2@x.com"; exit 1; fi
	docker compose exec api python manage.py create_test_data --driver "$(EMAILS)" --rides $(RIDES)

seed-all-drivers:
	docker compose exec api python manage.py create_test_data --all-drivers --rides $(RIDES)