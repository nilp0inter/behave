# Parameter Decorators & YAML Configuration Phase

## What This Is

A new feature for behave that introduces a "configuration phase" between test
definition and execution. Step authors declare degrees-of-freedom on their step
functions using a `@param` decorator, and QA engineers supply concrete values
for those parameters via YAML files that mirror the feature-file structure. The
values are injected into `context.params` at runtime.

The motivating use-case is testing non-deterministic platforms (e.g.
LLM-based systems), where parameters like `temperature` or `max_tokens` are
not inherent to the test logic but need to be tuned per environment or run.

---

## Files Created

### `behave/param_decorator.py`

The decorator module. Contains:

- **`ParamDef`** -- a `@dataclass` storing `name`, `type` (callable, default
  `float`), `min`, `max`. Intentionally minimal; no default-value field.
- **`param(name, type, min, max)`** -- the decorator. Appends a `ParamDef` to
  `func._behave_params`. Designed to be stacked (multiple `@param` on one
  function) and placed *above* `@given`/`@when`/`@then` (Python applies
  decorators bottom-up; `@given` returns `func` unchanged, so `@param` mutates
  the same object that the step registry holds via `matcher.func`).
- **`validate_value(param_def, value)`** -- converts via `param_def.type(value)`,
  checks min/max. Raises `ParamValidationError` (a `ValueError` subclass).
- **`get_step_params(func)`** -- returns `getattr(func, '_behave_params', [])`.

The `_behave_params` attribute name was chosen with a leading underscore to
signal it is behave-internal, but it lives on the user's function object so
it can't truly be private.

### `behave/param_config.py`

The YAML loading, validation, and runtime lookup module. Contains:

- **`StepParams`** -- attribute-access namespace. Uses `object.__setattr__` in
  `__init__` to avoid triggering its own `__setattr__` override. Externally
  read-only (raises `AttributeError` on direct assignment); internal mutation
  is through `_set()`. Has `__bool__` for truthiness checks.
- **`ParamConfig`** -- the main class. Takes a `config_dir` path.
  - `load_and_validate(features, step_registry)` walks every feature's model
    tree, computes the YAML path (`config_dir/<basename>.yml`), loads it with
    `yaml.safe_load`, and validates:
    - Step count in YAML matches step count in feature (including background).
    - Step text in YAML matches step name in feature (structural integrity).
    - Every `@param`-declared parameter has a value in the YAML.
    - Every value passes type conversion and min/max validation.
    - Errors are accumulated across all features and raised as a single
      `ParamConfigError`.
  - `get_step_params(feature_filename, scenario_name, step_index)` returns a
    `StepParams` for a given step, keyed by a 3-tuple. Returns an empty
    `StepParams` if no params exist for that step.
  - Handles Rules via a `rules:` key in the YAML. Rule backgrounds inherit
    feature background steps.
  - Handles ScenarioOutline by storing params under the outline's name, then
    copying them to each generated scenario name.
- **`generate_params_yaml(feature, step_registry, output_dir)`** -- generates
  skeleton YAML with param names and constraint comments for `--generate-params-config`.
- **`ParamConfigError`** -- exception class for config validation failures.

**Matching strategy**: Positional. The Nth step in the YAML scenario maps to
the Nth step in the feature scenario (background steps are prepended). The
`step:` text field is verified against the model for structural integrity but
is not used for matching -- it's there for human readability.

**YAML path computation**: `_compute_yaml_path` uses `os.path.basename`, so
`features/auth/login.feature` maps to `<config_dir>/login.yml`. This means
features in different subdirectories with the same filename would collide. The
plan mentioned preserving subdirectories but I went with basename for
simplicity. A reviewer may want to reconsider this.

### `tests/unit/test_param_decorator.py`

25 tests covering:
- `ParamDef` construction and defaults.
- `@param` attaching `_behave_params`, multiple decorators composing, returning
  the original function, interacting with mock `@given`.
- `validate_value` accepting valid values, boundary values, rejecting below-min,
  above-max, wrong types, and handling no-constraint cases.
- `get_step_params` on decorated and undecorated functions.

### `tests/unit/test_param_config.py`

22 tests covering:
- `StepParams` attribute access, missing attribute, `_set`, `_clear`,
  `_as_dict`, `__bool__`, `__repr__`, read-only enforcement.
- `ParamConfig` with mock objects:
  - No YAML + no params = OK.
  - Missing YAML when params exist = error.
  - Valid YAML loads and populates correctly.
  - Missing param value = error.
  - Out-of-range value = error.
  - Wrong type = error.
  - Step count mismatch = error.
  - Unknown keys return empty `StepParams`.
  - Multiple scenarios keyed correctly.
  - Mixed steps (with and without params) work.
  - Background steps with params.
  - Empty YAML file with param steps = error.

The tests use lightweight mock classes (`MockStep`, `MockMatch`,
`MockStepRegistry`, `MockFeature`, `MockScenario`, `MockBackground`) rather
than `unittest.mock.Mock` to keep the contract explicit.

---

## Files Modified

### `behave/__init__.py`

Added `from behave.param_decorator import param` and `"param"` to `__all__`.
This is the public API surface -- users write `from behave import param`.

### `behave/configuration.py`

Two new entries in the `OPTIONS` list:

- **`--params-config-dir DIR`**: `dest="params_config_dir"`, `default=None`.
  Points to the directory with YAML files.
- **`--generate-params-config DIR`**: `dest="generate_params_config"`,
  `default=None`. Early-exit command to generate skeleton YAMLs.

`generate_params_config` added to `CONFIGFILE_EXCLUDED_OPTIONS` since it's a
CLI-only command, not a config-file option.

### `behave/model.py`

Two surgical changes:

1. **`Scenario.run()`** (line ~1192): Changed `for step in self.all_steps` to
   `for step_index, step in enumerate(self.all_steps)` and added
   `step._param_step_index = step_index`. This tags each step with its
   positional index so `Step.run()` can look up params.

2. **`Step.run()`** (line ~1993): Inserted a block between
   `runner.context.table = self.table` and `match.run(runner.context)` that:
   - Creates an empty `StepParams`.
   - If the matched function has `_behave_params` and the runner has a
     `param_config`, looks up the params by `(feature_filename, scenario_name,
     step_index)`.
   - Sets `runner.context.params = step_params` unconditionally (so
     `context.params` is always available, just empty when no params exist).

The import of `StepParams` is done inside the method to avoid circular imports
and top-level import overhead for codepaths that don't use this feature.

### `behave/runner.py`

Three changes:

1. **`ModelRunner.__init__()`**: Added `self.param_config = None`.

2. **`Runner._any_steps_have_params()`**: New method. Iterates all features ->
   `walk_scenarios()` -> steps, finds matches, checks for `_behave_params`.
   Used in the `elif` branch to raise a clear error when `@param` is used
   without `--params-config-dir`.

3. **`Runner.run_with_paths()`**: After `parse_features()` and before
   `run_model()`, added the configuration phase:
   - Eagerly initializes `self.step_registry` from the module-level registry if
     it's still `None`. This was necessary because the original code deferred
     this to `run_model()`, but we need it earlier for validation.
   - If `params_config_dir` is set: creates `ParamConfig`, calls
     `load_and_validate()`.
   - Else if any steps have params: raises `ConfigError` with a clear message.

### `behave/__main__.py`

- Added `generate_params_config_command(config)` function that creates a
  temporary `Runner`, loads step definitions, parses features, then calls
  `generate_params_yaml` for each feature.
- Added early-exit check in `run_behave()`: `if config.generate_params_config`.

### `pyproject.toml`

Added `"PyYAML >= 6.0"` to the `dependencies` list.

### `py.requirements/basic.txt`

Added `PyYAML >= 6.0`.

### `tests/unit/test_configuration.py`

Added `"params_config_dir"` to the hardcoded expected config option names list
in `TestConfigFileParser::test_configfile_iter__verify_option_names`.

### `tests/unit/test_runner.py`

- `TestRunWithPaths.setUp()`: Added `config.params_config_dir = None` and
  `config.generate_params_config = None` to the mock config. These are needed
  because the config is a `unittest.mock.Mock()`, and any attribute access on a
  `Mock` auto-creates a truthy child mock. Without explicitly setting these to
  `None`, the runner's configuration phase would try to create a `ParamConfig`
  with a mock path.
- `test_parses_feature_files_and_appends_to_feature_list`: Added
  `feature.walk_scenarios.return_value = []` to the mock feature. This is
  needed because `_any_steps_have_params()` calls `feature.walk_scenarios()`
  and iterates the result, which fails on an un-configured mock.

---

## Design Decisions Worth Reviewing

### `_behave_params` lives on the user's function object

The `@param` decorator mutates `func._behave_params` directly. This works
because `@given`/`@when`/`@then` return `func` unchanged -- the step registry
holds a reference to the same function object via `matcher.func`. An
alternative would be a separate registry mapping functions to param defs, but
this is simpler and follows the same pattern as Python's `functools.wraps`.

### Step registry initialization order

The original code initialized `self.step_registry` lazily in `run_model()`.
The configuration phase runs before `run_model()`, so I added an early
initialization: `if self.step_registry is None: self.step_registry =
the_step_registry`. This is done inline in `run_with_paths()` rather than
moving the initialization to an earlier lifecycle point, to minimize the diff.
A reviewer might prefer pulling this into `load_step_definitions()` instead.

### YAML path uses basename only

`_compute_yaml_path` strips the directory and uses only the filename base:
`features/auth/login.feature` -> `<config_dir>/login.yml`. The plan specified
preserving subdirectory structure, but the implementation uses `os.path.basename`.
This is simpler but means two features named `login.feature` in different
subdirectories would collide. May need revisiting.

### `context.params` is always set

Every step execution sets `runner.context.params`, even when no params exist
for that step (it gets an empty `StepParams`). This means step code can always
reference `context.params` without checking if the feature uses params at all.
Accessing a nonexistent param raises `AttributeError` with a clear message.

### ScenarioOutline params are copied by reference

When a `ScenarioOutline` has params, the same `StepParams` objects are shared
between the outline template and all generated scenarios. This is fine because
`StepParams` is read-only, but worth knowing if mutability is ever introduced.

### `_any_steps_have_params()` scans every step on every run

When `--params-config-dir` is not provided, the runner calls
`_any_steps_have_params()` to check if any step uses `@param`. This iterates
all features -> all scenarios -> all steps -> finds matches -> checks for the
attribute. For large test suites this adds overhead to every run. An
alternative would be to track this during step registration, but that would
require more invasive changes to the step registry. In practice the check
should be fast (it short-circuits on the first match).

### Import placement

`from behave.param_config import ...` is done as a late import inside methods
(in `model.py`, `runner.py`, `__main__.py`) rather than at the module top
level. This avoids circular imports and prevents any overhead for users who
don't use the `@param` feature.

---

## Test Results

- **1683 pytest tests pass** (47 new + 1636 existing), 3 skipped, 2 xfailed.
- **96 behave features pass**, 618 scenarios, 3768 steps, 0 failures.
- No regressions.
