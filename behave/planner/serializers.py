"""JSON serialization for behave model objects used by the planner API."""

from behave.model import ScenarioOutline


def serialize_feature_tree(discovery):
    """Serialize the feature tree for the sidebar.

    :param discovery: FeatureDiscovery instance.
    :returns: dict with "tree" key.
    """
    return {"tree": discovery.get_feature_tree()}


def serialize_feature(feature, discovery):
    """Serialize a full feature with scenarios, steps, and param metadata.

    :param feature: Parsed Feature model object.
    :param discovery: FeatureDiscovery instance.
    :returns: dict suitable for JSON encoding.
    """
    result = {
        "name": feature.name,
        "filename": feature.filename,
        "description": list(feature.description) if feature.description else [],
        "tags": [str(t) for t in feature.tags] if feature.tags else [],
        "background": None,
        "scenarios": [],
        "rules": [],
    }

    if feature.background:
        bg_steps = _serialize_steps(feature.background.all_steps, discovery, start_index=0)
        result["background"] = {"steps": bg_steps}

    bg_count = len(feature.background.all_steps) if feature.background else 0

    for scenario in feature.scenarios:
        result["scenarios"].append(
            _serialize_scenario(scenario, feature, discovery, bg_count)
        )

    for rule in feature.rules:
        rule_data = {
            "name": rule.name,
            "tags": [str(t) for t in rule.tags] if rule.tags else [],
            "scenarios": [],
        }
        for scenario in rule.scenarios:
            rule_data["scenarios"].append(
                _serialize_scenario(scenario, feature, discovery, bg_count)
            )
        result["rules"].append(rule_data)

    return result


def _serialize_scenario(scenario, feature, discovery, bg_step_count):
    """Serialize a single scenario."""
    steps = []
    idx = 0

    bg = getattr(scenario, "background", None) or feature.background
    if bg:
        for step in bg.all_steps:
            steps.append(_serialize_step(step, discovery, idx))
            idx += 1

    for step in scenario.steps:
        steps.append(_serialize_step(step, discovery, idx))
        idx += 1

    return {
        "name": scenario.name,
        "tags": [str(t) for t in scenario.tags] if scenario.tags else [],
        "steps": steps,
    }


def _serialize_steps(steps, discovery, start_index=0):
    """Serialize a list of steps."""
    result = []
    for i, step in enumerate(steps):
        result.append(_serialize_step(step, discovery, start_index + i))
    return result


def _serialize_step(step, discovery, index):
    """Serialize a single step with its parameter metadata."""
    param_defs = discovery.get_step_params(step)
    params = [_serialize_param_def(pd) for pd in param_defs]

    return {
        "keyword": step.keyword.strip(),
        "name": step.name,
        "stepType": step.step_type,
        "index": index,
        "hasParams": len(params) > 0,
        "params": params,
    }


def _serialize_param_def(param_def):
    """Serialize a ParamDef to a JSON-ready dict."""
    type_name = param_def.type.__name__ if hasattr(param_def.type, "__name__") else str(param_def.type)

    result = {
        "name": param_def.name,
        "type": type_name,
        "min": param_def.min,
        "max": param_def.max,
        "choices": param_def.choices,
    }
    return result
