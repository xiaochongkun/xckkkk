.PHONY: all format lint test tests test_watch integration_tests docker_tests help extended_tests test_uv lint_uv format_uv sync_uv install_uv integration_tests_uv spell_check_uv spell_fix_uv test_watch_uv test_profile_uv

# Default target executed when no arguments are given to make.
all: help

# Define a variable for the test file path.
TEST_FILE ?= tests/unit_tests/

test:
	python -m pytest $(TEST_FILE)

test_watch:
	python -m ptw --snapshot-update --now . -- -vv tests/unit_tests

test_profile:
	python -m pytest -vv tests/unit_tests/ --profile-svg

extended_tests:
	python -m pytest --only-extended $(TEST_FILE)


######################
# LINTING AND FORMATTING
######################

# Define a variable for Python and notebook files.
PYTHON_FILES=src/
MYPY_CACHE=.mypy_cache
lint format: PYTHON_FILES=.
lint_diff format_diff: PYTHON_FILES=$(shell git diff --name-only --diff-filter=d main | grep -E '\.py$$|\.ipynb$$')
lint_package: PYTHON_FILES=src
lint_tests: PYTHON_FILES=tests
lint_tests: MYPY_CACHE=.mypy_cache_test

lint lint_diff lint_package lint_tests:
	python -m ruff check .
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff format $(PYTHON_FILES) --diff
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff check --select I $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || python -m mypy --strict $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || mkdir -p $(MYPY_CACHE) && python -m mypy --strict $(PYTHON_FILES) --cache-dir $(MYPY_CACHE)

format format_diff:
	ruff format $(PYTHON_FILES)
	ruff check --select I --fix $(PYTHON_FILES)

spell_check:
	codespell --toml pyproject.toml

spell_fix:
	codespell --toml pyproject.toml -w

######################
# UV COMMANDS
######################

# UV environment management
sync_uv:
	$$HOME/.local/bin/uv sync

install_uv:
	$$HOME/.local/bin/uv install

# UV test commands
test_uv:
	$$HOME/.local/bin/uv run pytest $(TEST_FILE)

test_watch_uv:
	$$HOME/.local/bin/uv run ptw --snapshot-update --now . -- -vv tests/unit_tests

test_profile_uv:
	$$HOME/.local/bin/uv run pytest -vv tests/unit_tests/ --profile-svg

integration_tests_uv:
	$$HOME/.local/bin/uv run pytest tests/integration_tests/

# UV lint and format commands  
lint_uv:
	$$HOME/.local/bin/uv run ruff check .
	$$HOME/.local/bin/uv run ruff format . --diff
	$$HOME/.local/bin/uv run ruff check --select I .
	$$HOME/.local/bin/uv run mypy --strict src/

format_uv:
	$$HOME/.local/bin/uv run ruff format .
	$$HOME/.local/bin/uv run ruff check --select I --fix .

spell_check_uv:
	$$HOME/.local/bin/uv run codespell --toml pyproject.toml

spell_fix_uv:
	$$HOME/.local/bin/uv run codespell --toml pyproject.toml -w

######################
# HELP
######################

help:
	@echo '----'
	@echo 'Standard commands:'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo 'test                         - run unit tests'
	@echo 'tests                        - run unit tests'
	@echo 'test TEST_FILE=<test_file>   - run all tests in file'
	@echo 'test_watch                   - run unit tests in watch mode'
	@echo '----'
	@echo 'UV commands:'
	@echo 'sync_uv                      - sync dependencies with uv'
	@echo 'install_uv                   - install dependencies with uv'
	@echo 'test_uv                      - run unit tests with uv'
	@echo 'test_watch_uv                - run unit tests in watch mode with uv'
	@echo 'integration_tests_uv         - run integration tests with uv'
	@echo 'test_profile_uv              - run unit tests with profiling with uv'
	@echo 'lint_uv                      - run linters with uv'
	@echo 'format_uv                    - run code formatters with uv'
	@echo 'spell_check_uv               - run spell check with uv'
	@echo 'spell_fix_uv                 - run spell fix with uv'

