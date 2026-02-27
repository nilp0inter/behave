# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**behave** is a BDD (Behavior-Driven Development) framework for Python using Gherkin syntax. Tests are written as `.feature` files in natural language, backed by Python step implementations. Current version is 1.4.0.dev0, targeting Python 3.10+.

## Common Commands

### Running Tests

```bash
# Unit tests (pytest)
pytest                                          # all unit tests
pytest tests/unit/test_model.py                 # single file
pytest tests/unit/test_model.py::TestFeature::test_constructor -v  # single test

# BDD feature tests (behave self-tests)
behave --format=progress features/              # main feature tests
behave --format=progress issue.features/        # issue regression tests
behave --format=progress tools/test-features/   # tool tests

# All tests together
just test-all
```

### Using the justfile (requires `just`)

```bash
just init              # install all dependencies (uses uv pip)
just test [TESTS]      # run pytest
just behave [FILES]    # run behave features
just behave-all        # run all feature test suites
just test-all          # pytest + behave-all
just coverage          # full coverage report
just cleanup           # clean build artifacts
```

### Tox

```bash
tox -e py312           # test with specific Python version
tox -e docs            # build Sphinx documentation
```

### Linting

```bash
ruff check .           # lint (line-length: 100)
pylint behave/         # static analysis
```

## Architecture

### Execution Flow

1. **Entry point** (`behave/__main__.py`): CLI parses args into `Configuration`, calls `run_behave()`
2. **Configuration** (`configuration.py`): Merges CLI args with config files (behave.ini, setup.cfg, tox.ini, pyproject.toml)
3. **Runner** (`runner.py`): Orchestrates execution — loads step modules, parses features, runs scenarios through hooks
4. **Parser** (`parser.py`): Parses `.feature` files (Gherkin v5/v6) into model objects, supports i18n
5. **Model** (`model.py`, `model_core.py`): `Feature` → `Rule` → `Scenario`/`ScenarioOutline` → `Step` hierarchy
6. **Step matching** (`matchers.py`, `step_registry.py`): Links step text to Python functions via `@given`/`@when`/`@then` decorators. Supports `parse`, `re`, and `cfexpr` (cucumber expressions) matchers
7. **Formatters** (`formatter/`): Output plugins (progress, pretty, json, etc.)
8. **Reporters** (`reporter/`): Post-run reporting (junit, summary)

### Context Object

`runner.Context` is passed to all steps and hooks. It uses a layer-based namespace (root → feature → scenario) that automatically pushes/pops as execution progresses.

### Hook System

Hooks are defined in `features/environment.py`: `before_all`, `after_all`, `before_feature`, `after_feature`, `before_scenario`, `after_scenario`, `before_step`, `after_step`, `before_tag`, `after_tag`.

### Key Large Files

- `model.py` (~2200 lines): All BDD model classes
- `configuration.py` (~1200 lines): Config loading/merging
- `runner.py` (~1100 lines): Test execution engine
- `parser.py` (~900 lines): Gherkin parser
- `capture.py` (~800 lines): stdout/stderr/log capture

## Test Structure

- `tests/unit/` — pytest unit tests
- `tests/functional/` — functional tests
- `tests/api/` — public API tests
- `tests/issues/` — issue-specific regression tests
- `features/` — behave self-tests (BDD tests for behave itself)
- `issue.features/` — issue reproduction features
- `tools/test-features/` — tool testing features

Pytest config is in `pytest.ini` (testpaths: `tests`, markers: `smoke`, `slow`).

## Code Style

- Line length: 100 (configured in `.ruff.toml` and `pyproject.toml`)
- Indent: 4 spaces
- Target: Python 3.12 for ruff
- Double quotes for strings (ruff format config)

## CI

GitHub Actions (`.github/workflows/test.yml`) runs on push to main and PRs: pytest + behave across Python 3.10–3.14 and PyPy-3.10 on Ubuntu. Dependencies installed via `uv pip`.

## Mission: Non-Deterministic Testing Support

We are modifying behave to support testing non-deterministic platforms (e.g. LLM-based systems). The core idea is a **configuration phase** between test definition and execution: step authors declare degrees-of-freedom via a `@param` decorator, and QA engineers supply concrete values through YAML files that mirror the feature-file structure. Values are injected into `context.params` at runtime.

### Implemented So Far

- **`@param` decorator** (`behave/param_decorator.py`): Declares configurable parameters on step functions with name, type, min/max constraints.
- **YAML parameter configs** (`behave/param_config.py`): Loads, validates, and injects parameter values from YAML files that structurally mirror `.feature` files.
- **CLI integration**: `--params-config-dir` to point at YAML configs, `--generate-params-config` to scaffold them.
- **Runtime injection**: `context.params` is set on every step, providing attribute-access to parameter values.

### What's Next

This is the foundation layer. Future work may include: multiple config profiles (e.g. `--params-profile fast`), parameter sweep / grid execution, statistical pass/fail criteria for non-deterministic steps, and integration with reporting to track parameter-outcome correlations.

## Coding Procedure

After each coding session:

1. **Update "Lessons Learned"** (below) with any new corrections, patterns, or insights from the session.
2. **Write `vibecoding/NN_<feature_name>.md`** documenting what was implemented, all files touched, design decisions, and anything a reviewer should know. `NN` is a zero-padded sequence number.

## Lessons Learned

- **Never defend against tests in production code.** When existing tests break because they use `Mock()` objects that lack new attributes or methods, fix the test mocks to properly reflect the new interface. Do not add `try/except`, `isinstance` guards, or other defensive patterns to the production code to work around mock limitations. The production code should be written for correctness; the tests must keep up.
- **Mock config objects auto-create truthy attributes.** `unittest.mock.Mock()` returns a truthy child mock for any attribute access. When adding new config options (like `params_config_dir`), existing tests that use `Mock()` for config need explicit `config.new_option = None` to prevent the runner from treating the mock as a real value.
- **`step_registry` is lazily initialized.** In behave's `Runner`, `self.step_registry` starts as `None` and is only set from the module-level registry inside `run_model()`. Any code that needs the registry before `run_model()` (like the configuration phase) must initialize it explicitly.
