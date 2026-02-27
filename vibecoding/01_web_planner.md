# 01 — Web-Based Parameter Planner

## What Was Implemented

A local web UI (`behave plan`) that lets QA engineers visually browse feature files, see which steps have `@param` decorators, and edit parameter values through type-appropriate widgets. Changes are saved immediately to YAML plan files via a REST API.

## Subcommand

```bash
behave plan --features-dir demo/features --plans-dir demo/plans/conservative
```

Dispatched early in `behave/__main__.py:main()` before `Configuration()` is created, since the planner has its own argparse.

## ParamDef Extension

Added `choices: Optional[list] = None` field to `ParamDef` in `param_decorator.py`. The `@param` decorator accepts `choices=` and `validate_value()` rejects values not in the list. This powers the EnumSelect dropdown widget.

## Backend Architecture (behave/planner/)

| Module | Purpose |
|--------|---------|
| `__init__.py` | `run_plan()` entry point with argparse for `--features-dir`, `--plans-dir`, `--host`, `--port`, `--no-browser` |
| `discovery.py` | `FeatureDiscovery` — creates a `Configuration(load_config=False)` to avoid `behave.ini` interference, runs `Runner.setup_paths()` + `load_step_definitions()`, parses features, exposes step param metadata |
| `serializers.py` | Converts Feature/Scenario/Step model objects + ParamDef metadata to JSON dicts |
| `yaml_io.py` | Reads/writes/scaffolds YAML plan files; `write_param_value()` does surgical single-param updates |
| `api.py` | `PlannerAPIHandler(BaseHTTPRequestHandler)` with REST routing: GET feature tree, GET feature detail, GET plan, PUT param value |
| `server.py` | `HTTPServer` setup, static file serving from elm/static + elm/dist, browser auto-open |

### REST API

| Method | Path | Response |
|--------|------|----------|
| GET | `/api/features` | Feature file tree for sidebar |
| GET | `/api/features/{path}` | Full feature with scenarios, steps, param defs |
| GET | `/api/plans/{path}` | Current YAML plan values |
| PUT | `/api/params/{feature}/{scenario}/{step_idx}/{param}` | Update one param, validates via `validate_value()` |

### Key Design Decision: `load_config=False`

`FeatureDiscovery` passes `load_config=False` to `Configuration()`. Without this, `behave.ini` in the project root overrides `config.paths` to empty, causing the runner to load step definitions from the wrong directory (behave's own test steps instead of the target project's steps).

## Frontend Architecture (behave/planner/elm/)

Elm 0.19.1 SPA with Tailwind CSS via CDN. Two-panel layout: sidebar (feature tree) + main panel (Gherkin rendering with expandable param editors).

| Module | Purpose |
|--------|---------|
| `Main.elm` | `Browser.element` app shell, Model/Msg/update/view |
| `Types.elm` | All types + JSON decoders. `FeatureTreeNode` is a proper `type` (not alias) to allow recursion |
| `Api.elm` | HTTP requests to backend |
| `FeatureTree.elm` | Sidebar file tree with selection highlighting |
| `FeatureView.elm` | Gherkin rendering; parameterized steps show `[+]` expand button |
| `ParamEditor.elm` | Widget dispatch based on `paramType` and `choices` |
| `Widgets/FloatSlider.elm` | Range slider + numeric input |
| `Widgets/IntInput.elm` | Integer input |
| `Widgets/StringInput.elm` | Text input |
| `Widgets/BoolToggle.elm` | Toggle switch |
| `Widgets/EnumSelect.elm` | Dropdown from `choices` list |

Build: `cd behave/planner/elm && elm make src/Main.elm --output=dist/elm.js`

## Demo Updates

Added "Generate with full options" scenario to `demo/features/llm.feature` to exercise every widget type:

- `model` (str + choices) → EnumSelect
- `system_prompt` (str) → StringInput
- `temperature` (float) → FloatSlider
- `max_tokens` (int) → IntInput
- `block_unsafe`, `log_prompts` (bool) → BoolToggle
- `safety_level` (str + choices) → EnumSelect

Both `conservative` and `creative` plan YAMLs updated.

## Files Modified

- `behave/__main__.py` — subcommand dispatch (~10 lines added)
- `behave/param_decorator.py` — `choices` field on ParamDef, validation in `validate_value()`
- `tests/unit/test_param_decorator.py` — tests for choices
- `demo/features/llm.feature` — new scenario
- `demo/features/steps/llm_steps.py` — new steps with str/bool/choices params
- `demo/plans/conservative/llm.yml` — new scenario values
- `demo/plans/creative/llm.yml` — new scenario values

## Files Created

- `behave/planner/__init__.py`
- `behave/planner/discovery.py`
- `behave/planner/serializers.py`
- `behave/planner/yaml_io.py`
- `behave/planner/api.py`
- `behave/planner/server.py`
- `behave/planner/elm/elm.json`
- `behave/planner/elm/static/index.html`
- `behave/planner/elm/src/Main.elm`
- `behave/planner/elm/src/Types.elm`
- `behave/planner/elm/src/Api.elm`
- `behave/planner/elm/src/FeatureTree.elm`
- `behave/planner/elm/src/FeatureView.elm`
- `behave/planner/elm/src/ParamEditor.elm`
- `behave/planner/elm/src/Widgets/FloatSlider.elm`
- `behave/planner/elm/src/Widgets/IntInput.elm`
- `behave/planner/elm/src/Widgets/StringInput.elm`
- `behave/planner/elm/src/Widgets/BoolToggle.elm`
- `behave/planner/elm/src/Widgets/EnumSelect.elm`
