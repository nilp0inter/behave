"""
Provides YAML-based parameter configuration for step parameters
declared with the ``@param`` decorator.

The YAML files mirror the feature file structure and supply concrete values
for degrees-of-freedom declared by step decorators.

YAML structure example::

    feature: "Login functionality"
    background:
      steps:
        - step: "the system is initialized"
          params:
            log_level: "debug"
    scenarios:
      - scenario: "User logs in with AI assistance"
        steps:
          - step: "the LLM is configured"
            params:
              temperature: 0.7
              max_tokens: 1024
          - step: "the user exists"
"""

import os

import yaml

from behave.param_decorator import get_step_params, validate_value


class ParamConfigError(Exception):
    """Raised when parameter configuration has validation errors."""
    pass


class StepParams:
    """Attribute-access namespace for step parameter values.

    Provides attribute-style access to parameter values injected from YAML config.
    """

    def __init__(self, data=None):
        object.__setattr__(self, "_data", data or {})

    def __getattr__(self, name):
        data = object.__getattribute__(self, "_data")
        if name in data:
            return data[name]
        raise AttributeError(
            "Step has no parameter '{name}'".format(name=name)
        )

    def __setattr__(self, name, value):
        raise AttributeError("StepParams is read-only; use _set() internally")

    def _set(self, name, value):
        self._data[name] = value

    def _clear(self):
        self._data.clear()

    def _as_dict(self):
        return dict(self._data)

    def __repr__(self):
        return "StepParams({0})".format(self._data)

    def __bool__(self):
        return bool(self._data)


class ParamConfig:
    """Manages loading, validation, and lookup of YAML parameter configs.

    :param config_dir: Directory containing YAML parameter config files.
    """

    def __init__(self, config_dir):
        self.config_dir = config_dir
        # Keyed by (feature_filename, scenario_name, step_index) -> StepParams
        self._params = {}

    def load_and_validate(self, features, step_registry):
        """Load YAML configs for all features and validate them.

        :param features:      List of parsed Feature model objects.
        :param step_registry: StepRegistry for finding step definitions.
        :raises ParamConfigError: If any validation errors are found.
        """
        errors = []
        for feature in features:
            try:
                self._load_feature(feature, step_registry)
            except ParamConfigError as e:
                errors.append(str(e))

        if errors:
            raise ParamConfigError(
                "Parameter configuration errors:\n" + "\n".join(errors)
            )

    def get_step_params(self, feature_filename, scenario_name, step_index):
        """Return a StepParams object for a given step.

        :param feature_filename: The feature file path.
        :param scenario_name:    The scenario name.
        :param step_index:       The step index within the scenario (including background).
        :returns: StepParams with values, or empty StepParams.
        """
        key = (feature_filename, scenario_name, step_index)
        return self._params.get(key, StepParams())

    def _compute_yaml_path(self, feature_filename):
        """Compute YAML config path from feature filename.

        Strips the feature file's base directory and replaces .feature with .yml.
        """
        # Strip the .feature extension and add .yml
        base = feature_filename
        if base.endswith(".feature"):
            base = base[: -len(".feature")]
        return os.path.join(self.config_dir, os.path.basename(base) + ".yml")

    def _feature_has_params(self, feature, step_registry):
        """Check if any step in the feature has @param decorators."""
        for scenario in self._iter_scenarios(feature):
            for step in self._iter_all_steps(scenario, feature):
                match = step_registry.find_match(step)
                if match and get_step_params(match.func):
                    return True
        return False

    def _iter_scenarios(self, feature):
        """Iterate over all scenarios in a feature, including those in rules."""
        for scenario in feature.scenarios:
            yield scenario
        for rule in feature.rules:
            for scenario in rule.scenarios:
                yield scenario

    def _iter_all_steps(self, scenario, feature):
        """Iterate all steps for a scenario, including background steps."""
        # Background steps come first
        bg = getattr(scenario, "background", None) or feature.background
        if bg:
            yield from bg.all_steps
        yield from scenario.steps

    def _load_feature(self, feature, step_registry):
        """Load and validate YAML config for a single feature."""
        yaml_path = self._compute_yaml_path(feature.filename)
        has_params = self._feature_has_params(feature, step_registry)

        if not os.path.exists(yaml_path):
            if has_params:
                raise ParamConfigError(
                    "Feature '{name}' ({filename}) has steps with @param decorators "
                    "but no YAML config file found at: {yaml_path}".format(
                        name=feature.name,
                        filename=feature.filename,
                        yaml_path=yaml_path,
                    )
                )
            return  # No params, no YAML needed

        with open(yaml_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if config_data is None:
            if has_params:
                raise ParamConfigError(
                    "YAML config file is empty: {yaml_path}".format(
                        yaml_path=yaml_path
                    )
                )
            return

        errors = []

        # Process background steps
        bg_config = config_data.get("background", {})
        bg_steps_config = bg_config.get("steps", []) if bg_config else []

        # Process scenarios (top-level)
        scenarios_config = config_data.get("scenarios", [])
        self._validate_scenarios(
            feature, feature.scenarios, scenarios_config,
            step_registry, bg_steps_config, errors
        )

        # Process rules
        rules_config = config_data.get("rules", [])
        for rule in feature.rules:
            rule_config = self._find_rule_config(rule, rules_config)
            if rule_config is None:
                # Check if any step in rule scenarios has params
                for scenario in rule.scenarios:
                    for step in self._iter_all_steps(scenario, feature):
                        match = step_registry.find_match(step)
                        if match and get_step_params(match.func):
                            errors.append(
                                "Rule '{name}' has steps with @param decorators "
                                "but no rule entry in YAML config: {yaml_path}".format(
                                    name=rule.name, yaml_path=yaml_path
                                )
                            )
                            break
                continue

            rule_scenarios_config = rule_config.get("scenarios", [])
            rule_bg_config = rule_config.get("background", {})
            rule_bg_steps = rule_bg_config.get("steps", []) if rule_bg_config else []
            # Rule background inherits feature background
            combined_bg_steps = bg_steps_config + rule_bg_steps
            self._validate_scenarios(
                feature, rule.scenarios, rule_scenarios_config,
                step_registry, combined_bg_steps, errors
            )

        if errors:
            raise ParamConfigError("\n".join(errors))

    def _find_rule_config(self, rule, rules_config):
        """Find the YAML config entry for a rule by name."""
        for rule_cfg in rules_config:
            if rule_cfg.get("rule") == rule.name:
                return rule_cfg
        return None

    def _validate_scenarios(self, feature, scenarios, scenarios_config,
                            step_registry, bg_steps_config, errors):
        """Validate scenario configs against model scenarios."""
        from behave.model import ScenarioOutline

        scenario_config_map = {}
        for sc_cfg in scenarios_config:
            sc_name = sc_cfg.get("scenario", "")
            scenario_config_map[sc_name] = sc_cfg

        for scenario in scenarios:
            if isinstance(scenario, ScenarioOutline):
                scenario_name = scenario.name
            else:
                scenario_name = scenario.name

            sc_cfg = scenario_config_map.get(scenario_name)
            if sc_cfg is None:
                # Check if scenario has param steps
                for step in self._iter_all_steps(scenario, feature):
                    match = step_registry.find_match(step)
                    if match and get_step_params(match.func):
                        errors.append(
                            "Scenario '{name}' has steps with @param decorators "
                            "but no scenario entry in YAML config".format(
                                name=scenario_name
                            )
                        )
                        break
                continue

            sc_steps_config = sc_cfg.get("steps", [])

            # Build the full list of steps (background + scenario)
            all_model_steps = list(self._iter_all_steps(scenario, feature))
            all_yaml_steps = bg_steps_config + sc_steps_config

            # Validate step count match
            if len(all_yaml_steps) != len(all_model_steps):
                errors.append(
                    "Scenario '{name}': YAML has {yaml_count} steps "
                    "(including background) but feature has {model_count} steps".format(
                        name=scenario_name,
                        yaml_count=len(all_yaml_steps),
                        model_count=len(all_model_steps),
                    )
                )
                continue

            # Validate each step
            for idx, (model_step, yaml_step) in enumerate(
                zip(all_model_steps, all_yaml_steps)
            ):
                # Verify step text matches (structural check)
                yaml_step_text = yaml_step.get("step", "")
                if yaml_step_text and yaml_step_text != model_step.name:
                    errors.append(
                        "Scenario '{scenario}', step {idx}: YAML step text "
                        "'{yaml_text}' does not match feature step '{model_text}'".format(
                            scenario=scenario_name,
                            idx=idx,
                            yaml_text=yaml_step_text,
                            model_text=model_step.name,
                        )
                    )
                    continue

                match = step_registry.find_match(model_step)
                if not match:
                    continue

                param_defs = get_step_params(match.func)
                if not param_defs:
                    continue

                yaml_params = yaml_step.get("params", {})
                if yaml_params is None:
                    yaml_params = {}

                # Validate all declared params have values
                for pdef in param_defs:
                    if pdef.name not in yaml_params:
                        errors.append(
                            "Scenario '{scenario}', step {idx} ('{step}'): "
                            "missing parameter '{param}'".format(
                                scenario=scenario_name,
                                idx=idx,
                                step=model_step.name,
                                param=pdef.name,
                            )
                        )
                        continue

                    raw_value = yaml_params[pdef.name]
                    try:
                        converted = validate_value(pdef, raw_value)
                    except Exception as e:
                        errors.append(
                            "Scenario '{scenario}', step {idx} ('{step}'): {error}".format(
                                scenario=scenario_name,
                                idx=idx,
                                step=model_step.name,
                                error=e,
                            )
                        )
                        continue

                    # Store the validated value
                    key = (feature.filename, scenario_name, idx)
                    if key not in self._params:
                        self._params[key] = StepParams()
                    self._params[key]._set(pdef.name, converted)

            # For ScenarioOutline: apply same params to all generated scenarios
            if isinstance(scenario, ScenarioOutline):
                for gen_scenario in scenario.scenarios:
                    for idx in range(len(all_model_steps)):
                        src_key = (feature.filename, scenario_name, idx)
                        if src_key in self._params:
                            dst_key = (feature.filename, gen_scenario.name, idx)
                            self._params[dst_key] = self._params[src_key]


def generate_params_yaml(feature, step_registry, output_dir):
    """Generate a skeleton YAML config file for a feature.

    :param feature:        Parsed Feature model object.
    :param step_registry:  StepRegistry for finding step definitions.
    :param output_dir:     Directory to write generated YAML files.
    """
    from behave.model import ScenarioOutline

    lines = []
    lines.append("# Auto-generated parameter config for: {0}".format(
        os.path.basename(feature.filename)
    ))
    lines.append("# Fill in parameter values before running tests.")
    lines.append('feature: "{0}"'.format(feature.name))

    # Background
    if feature.background:
        bg_lines = _generate_steps_yaml(
            feature.background.all_steps, step_registry, indent=4
        )
        if bg_lines:
            lines.append("background:")
            lines.append("  steps:")
            lines.extend(bg_lines)

    # Scenarios
    scenario_lines = []
    for scenario in feature.scenarios:
        sc_lines = _generate_scenario_yaml(scenario, feature, step_registry)
        scenario_lines.extend(sc_lines)
    if scenario_lines:
        lines.append("scenarios:")
        lines.extend(scenario_lines)

    # Rules
    for rule in feature.rules:
        rule_lines = []
        rule_lines.append('  - rule: "{0}"'.format(rule.name))
        rule_scenario_lines = []
        for scenario in rule.scenarios:
            sc_lines = _generate_scenario_yaml(scenario, feature, step_registry)
            rule_scenario_lines.extend(sc_lines)
        if rule_scenario_lines:
            rule_lines.append("    scenarios:")
            for sl in rule_scenario_lines:
                rule_lines.append("  " + sl)

        if len(rule_lines) > 1:
            if not any(l.startswith("rules:") for l in lines):
                lines.append("rules:")
            lines.extend(rule_lines)

    # Write file
    base = os.path.basename(feature.filename)
    if base.endswith(".feature"):
        base = base[: -len(".feature")]
    yaml_filename = base + ".yml"
    output_path = os.path.join(output_dir, yaml_filename)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return output_path


def _generate_scenario_yaml(scenario, feature, step_registry):
    """Generate YAML lines for a single scenario."""
    lines = []
    lines.append('  - scenario: "{0}"'.format(scenario.name))

    all_steps = []
    bg = getattr(scenario, "background", None) or feature.background
    if bg:
        all_steps.extend(bg.all_steps)
    all_steps.extend(scenario.steps)

    step_lines = _generate_steps_yaml(all_steps, step_registry, indent=6)
    if step_lines:
        lines.append("    steps:")
        lines.extend(step_lines)
    return lines


def _generate_steps_yaml(steps, step_registry, indent=6):
    """Generate YAML lines for a list of steps."""
    prefix = " " * indent
    lines = []
    has_any_params = False
    step_entries = []

    for step in steps:
        entry_lines = []
        entry_lines.append('{prefix}- step: "{text}"'.format(
            prefix=prefix, text=step.name
        ))
        match = step_registry.find_match(step)
        if match:
            param_defs = get_step_params(match.func)
            if param_defs:
                has_any_params = True
                entry_lines.append("{prefix}  params:".format(prefix=prefix))
                for pdef in param_defs:
                    comment_parts = ["type: {0}".format(pdef.type.__name__)]
                    if pdef.min is not None:
                        comment_parts.append("min: {0}".format(pdef.min))
                    if pdef.max is not None:
                        comment_parts.append("max: {0}".format(pdef.max))
                    comment = ", ".join(comment_parts)
                    entry_lines.append(
                        "{prefix}    {name}:   # {comment}".format(
                            prefix=prefix, name=pdef.name, comment=comment
                        )
                    )
        step_entries.append(entry_lines)

    if not has_any_params:
        return []

    for entry in step_entries:
        lines.extend(entry)
    return lines
