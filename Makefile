# Prefer pyenv-local 3.11 (.python-version). Override: make install-dev PYTHON=/path/to/python3.11
SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PYTEST := $(VENV_BIN)/pytest
DOCKER_COMPOSE ?= docker compose
DOCKER_COMPOSE_FILE ?= docker/docker-compose.yml

# GitHub repository ruleset helpers (scripts/ does the real work).
RULESET_ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
RULESET_SCRIPTS := $(RULESET_ROOT_DIR)/scripts
RULESET_REPO ?=
RULESET_BRANCH ?= main
RULESET_VISIBILITY ?= public
RULESET_CREATE_FLAGS ?=

.PHONY: help venv install-dev install-pi test test-cov coverage-html docker-build docker-test clean \
	ruleset-help ruleset-create ruleset-apply ruleset-check

help:
	@echo "Targets:"
	@echo "  make install-dev    Create .venv and pip install -e \".[dev]\""
	@echo "  make install-pi     Run ./install.sh (Raspberry Pi deploy via app/install.sh)"
	@echo "  make test           Run pytest on host"
	@echo "  make test-cov       Run pytest with coverage (app/lib, terminal report)"
	@echo "  make coverage-html  Same as test-cov, plus htmlcov/ report"
	@echo "  make docker-build   Build the Python 3.11 dev image"
	@echo "  make docker-test    Run pytest (with coverage) inside Docker"
	@echo "  make clean          Remove venv, caches, and coverage artifacts"
	@echo ""
	@echo "Requires Python 3.11 (see .python-version). Example:"
	@echo "  make install-dev PYTHON=$$HOME/.pyenv/versions/3.11.9/bin/python3.11"
	@echo ""
	@echo "Docker (no local venv needed):"
	@echo "  make docker-build && make docker-test"
	@echo ""
	@$(MAKE) --no-print-directory ruleset-help

venv:
	@PYVER=$$($(PYTHON) -c 'import sys; print("%d.%d" % sys.version_info[:2])'); \
	case "$$PYVER" in \
		3.11) ;; \
		*) echo "ERROR: need Python 3.11 (got $$PYVER from: $(PYTHON))" >&2; exit 1 ;; \
	esac
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip

install-dev: venv
	$(VENV_BIN)/pip install -e ".[dev]"

install-pi:
	./install.sh

test: $(PYTEST)
	$(PYTEST) -q

test-cov: $(PYTEST)
	$(PYTEST) -q --cov=app.lib --cov-report=term-missing --cov-config=.coveragerc

coverage-html: $(PYTEST)
	$(PYTEST) -q --cov=app.lib --cov-report=term-missing --cov-report=html --cov-config=.coveragerc
	@echo "HTML report: htmlcov/index.html"

docker-build:
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) build

docker-test: docker-build
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) run --rm dev \
		sh -c "pip install -q -e '.[dev]' && pytest -q --cov=app.lib --cov-report=term-missing --cov-config=.coveragerc"

$(PYTEST):
	@echo "Missing $(PYTEST). Run: make install-dev" >&2
	@exit 1

clean:
	rm -rf $(VENV) .pytest_cache htmlcov .coverage coverage.xml *.egg-info build dist
	find . -type d -name __pycache__ -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true

ruleset-help:
	@printf '%s\n' \
		'GitHub ruleset targets:' \
		'' \
		'  make ruleset-create RULESET_REPO=OWNER/NAME [RULESET_VISIBILITY=public] [RULESET_CREATE_FLAGS="--clone"]' \
		'      Create a GitHub repo and apply rulesets.' \
		'' \
		'  make ruleset-apply RULESET_REPO=OWNER/NAME' \
		'      Apply/update rulesets on an existing repo.' \
		'' \
		'  make ruleset-check RULESET_REPO=OWNER/NAME [RULESET_BRANCH=main]' \
		'      List rulesets and check which rules apply to RULESET_BRANCH.' \
		'' \
		'Notes:' \
		'  - GitHub Free (org): rulesets work on public repos only.' \
		'  - Requires gh (repo admin) and jq.'

ruleset-create:
	@if [[ -z "$(RULESET_REPO)" ]]; then \
		echo "error: RULESET_REPO=OWNER/NAME is required" >&2; \
		echo "example: make ruleset-create RULESET_REPO=my-org/new-app" >&2; \
		exit 1; \
	fi
	@$(RULESET_SCRIPTS)/create-repo-with-rulesets.sh "$(RULESET_REPO)" "--$(RULESET_VISIBILITY)" $(RULESET_CREATE_FLAGS)

ruleset-apply:
	@if [[ -z "$(RULESET_REPO)" ]]; then \
		echo "error: RULESET_REPO=OWNER/NAME is required" >&2; \
		echo "example: make ruleset-apply RULESET_REPO=my-org/existing-app" >&2; \
		exit 1; \
	fi
	@$(RULESET_SCRIPTS)/apply-rulesets.sh --repo "$(RULESET_REPO)"

ruleset-check:
	@if [[ -z "$(RULESET_REPO)" ]]; then \
		echo "error: RULESET_REPO=OWNER/NAME is required" >&2; \
		echo "example: make ruleset-check RULESET_REPO=my-org/existing-app RULESET_BRANCH=main" >&2; \
		exit 1; \
	fi
	@echo "== ruleset list =="
	@gh ruleset list -R "$(RULESET_REPO)"
	@echo
	@echo "== ruleset check $(RULESET_BRANCH) =="
	@gh ruleset check "$(RULESET_BRANCH)" -R "$(RULESET_REPO)"
