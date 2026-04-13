.PHONY: help build up down restart logs shell migrate test seed seed-rides seed-all-drivers seed-clear check-drivers

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
	@echo "  make seed        - Створити тестових пасажирів та поїздки для існуючих драйверів"
	@echo "  make seed-clear  - Очистити тестові дані і перестворити пасажирів"
	@echo "  make seed-rides RIDES=50              - Додати поїздки існуючим драйверам"
	@echo "  make seed-all-drivers RIDES=30        - Додати поїздки всім драйверам"
	@echo "  make check-drivers                    - Перевірити кількість активних драйверів"

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

seed-rides:
	docker compose exec api python manage.py create_test_data --rides $(RIDES)

seed-all-drivers:
	docker compose exec api python manage.py create_test_data --all-drivers --rides $(RIDES)

check-drivers:
	@docker compose exec api python manage.py shell -c "from apps.drivers.models import Driver; print(f'Драйверів у системі: {Driver.objects.filter(status=2).count()}')"

recent-rides:
	docker compose exec api python /app/add_recent_rides.py