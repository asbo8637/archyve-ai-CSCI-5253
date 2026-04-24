VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTHON_DEPS_STAMP := $(VENV)/.deps-installed

.PHONY: install install-python install-web up down logs dev-web dev-api dev-worker migrate test

install: install-web install-python

install-web:
	npm install

$(PYTHON_DEPS_STAMP): packages/python-common/pyproject.toml apps/api/requirements.txt apps/worker/requirements.txt requirements-dev.txt
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ./packages/python-common -r ./apps/api/requirements.txt -r ./apps/worker/requirements.txt -r ./requirements-dev.txt
	touch $(PYTHON_DEPS_STAMP)

install-python: $(PYTHON_DEPS_STAMP)

up:
	docker compose build api worker
	docker compose run --rm api alembic upgrade head
	docker compose up -d api worker

down:
	docker compose down

logs:
	docker compose logs -f api worker

migrate: install-python
	cd apps/api && PYTHONPATH=. ../../$(VENV)/bin/alembic upgrade head

dev-api: install-python
	PYTHONPATH=apps/api $(VENV)/bin/uvicorn api_app.main:app --reload --host 0.0.0.0 --port 8000

dev-worker: install-python
	PYTHONPATH=apps/worker $(PYTHON) -m worker_app.main

dev-web:
	npm run dev:web

test: install-python
	$(VENV)/bin/pytest
