"""YAML read/write operations for parameter plan files."""

import os
import yaml


def feature_path_to_yaml_path(feature_relpath, plans_dir):
    """Convert a feature-relative path to the corresponding YAML plan path.

    :param feature_relpath: Path relative to features_dir, e.g. "subdir/foo.feature"
    :param plans_dir: Directory containing plan YAML files.
    :returns: Absolute path to the YAML plan file.
    """
    base = feature_relpath
    if base.endswith(".feature"):
        base = base[:-len(".feature")]
    return os.path.join(plans_dir, base + ".yml")


def read_plan_yaml(yaml_path):
    """Read and parse a YAML plan file.

    :param yaml_path: Path to the YAML file.
    :returns: Parsed dict, or None if file doesn't exist.
    """
    if not os.path.exists(yaml_path):
        return None
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_param_value(yaml_path, feature, scenario_name, step_index,
                      param_name, value, discovery):
    """Update a single parameter value in a YAML plan file.

    Creates the file (with scaffold) if it doesn't exist.

    :param yaml_path: Path to the YAML file.
    :param feature: Feature model object.
    :param scenario_name: Name of the scenario.
    :param step_index: Index of the step (including background steps).
    :param param_name: Name of the parameter to update.
    :param value: New value for the parameter.
    :param discovery: FeatureDiscovery instance.
    """
    data = read_plan_yaml(yaml_path)
    if data is None:
        data = scaffold_yaml(feature, discovery)

    scenarios = data.get("scenarios", [])
    for sc in scenarios:
        if sc.get("scenario") == scenario_name:
            steps = sc.get("steps", [])
            if step_index < len(steps):
                step_entry = steps[step_index]
                if "params" not in step_entry:
                    step_entry["params"] = {}
                step_entry["params"][param_name] = value
            break
    else:
        # Scenario not found in YAML — create it
        sc_entry = _scaffold_scenario_entry(feature, scenario_name, discovery)
        if sc_entry:
            steps = sc_entry.get("steps", [])
            if step_index < len(steps):
                if "params" not in steps[step_index]:
                    steps[step_index]["params"] = {}
                steps[step_index]["params"][param_name] = value
            scenarios.append(sc_entry)
            data["scenarios"] = scenarios

    os.makedirs(os.path.dirname(yaml_path) or ".", exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def scaffold_yaml(feature, discovery):
    """Build an initial YAML structure dict from a Feature model.

    :param feature: Feature model object.
    :param discovery: FeatureDiscovery instance.
    :returns: dict suitable for yaml.dump().
    """
    data = {"feature": feature.name, "scenarios": []}

    for scenario in feature.scenarios:
        sc_entry = _scaffold_scenario_entry(feature, scenario.name, discovery)
        if sc_entry:
            data["scenarios"].append(sc_entry)

    return data


def _scaffold_scenario_entry(feature, scenario_name, discovery):
    """Build a scaffold dict for a single scenario."""
    scenario = None
    for sc in feature.scenarios:
        if sc.name == scenario_name:
            scenario = sc
            break
    if scenario is None:
        return None

    steps = []
    bg = getattr(scenario, "background", None) or feature.background
    if bg:
        for step in bg.all_steps:
            steps.append(step)
    for step in scenario.steps:
        steps.append(step)

    step_entries = []
    for step in steps:
        entry = {"step": step.name}
        param_defs = discovery.get_step_params(step)
        if param_defs:
            entry["params"] = {pd.name: None for pd in param_defs}
        step_entries.append(entry)

    return {"scenario": scenario_name, "steps": step_entries}
