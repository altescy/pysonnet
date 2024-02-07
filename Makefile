PWD      := $(shell pwd)
PYTHON   := poetry run python
PYTEST   := poetry run pytest
PYSEN    := poetry run pysen
MODULE   := pysonnet

.PHONY: all
all: format lint test

.PHONY: test
test:
	PYTHONPATH=$(PWD) $(PYTEST)

.PHONY: lint
lint:
	PYTHONPATH=$(PWD) $(PYSEN) run lint

.PHONY: format
format:
	PYTHONPATH=$(PWD) $(PYSEN) run format

.PHONY: clean
clean: clean-pyc clean-build

.PHONY: clean-pyc
clean-pyc:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-build
clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf pip-wheel-metadata/
