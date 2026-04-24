VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTHON_DEPS_STAMP := $(VENV)/.deps-installed

.PHONY: install-python migrate

$(PYTHON_DEPS_STAMP): packages/python-common/pyproject.toml apps/api/requirements.txt requirements-dev.txt
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ./packages/python-common -r ./apps/api/requirements.txt -r ./requirements-dev.txt
	touch $(PYTHON_DEPS_STAMP)

install-python: $(PYTHON_DEPS_STAMP)

migrate: install-python
	cd apps/api && PYTHONPATH=. ../../$(VENV)/bin/alembic upgrade head
