"""Feature & step parameter discovery for the planner UI.

Parses feature files, loads step definitions, and exposes parameter
metadata declared via ``@param`` decorators.
"""

import os
from behave.configuration import Configuration
from behave.runner import Runner
from behave.runner_util import collect_feature_locations, parse_features
from behave.step_registry import registry as the_step_registry
from behave.param_decorator import get_step_params


class FeatureDiscovery:
    """Discovers features, step definitions, and their parameter metadata.

    :param features_dir: Path to the directory containing ``.feature`` files.
    """

    def __init__(self, features_dir):
        self.features_dir = os.path.abspath(features_dir)
        self.features = []
        self.step_registry = None

    def discover(self):
        """Parse feature files and load step definitions."""
        config = Configuration(
            command_args=[self.features_dir, "--dry-run"],
            load_config=False,
        )
        runner = Runner(config)
        with runner.path_manager:
            runner.setup_paths()
            runner.load_step_definitions()

        self.step_registry = the_step_registry

        feature_locations = list(collect_feature_locations([self.features_dir]))
        self.features = parse_features(feature_locations, language=config.lang)

    def get_step_params(self, step):
        """Return list of ParamDef for a step, or empty list."""
        if self.step_registry is None:
            return []
        match = self.step_registry.find_match(step)
        if match:
            return get_step_params(match.func)
        return []

    def get_feature_tree(self):
        """Build a tree structure of feature files for the sidebar."""
        tree = {}
        for feature in self.features:
            relpath = os.path.relpath(feature.filename, self.features_dir)
            parts = relpath.split(os.sep)
            _insert_into_tree(tree, parts, relpath)

        return _tree_dict_to_list(tree)

    def get_feature_by_path(self, relpath):
        """Find a feature by its path relative to features_dir."""
        for feature in self.features:
            feature_relpath = os.path.relpath(feature.filename, self.features_dir)
            if feature_relpath == relpath:
                return feature
        return None


def _insert_into_tree(tree, parts, full_path):
    """Insert a file path into a nested dict tree structure."""
    if len(parts) == 1:
        tree[parts[0]] = {"_path": full_path, "_type": "file"}
    else:
        if parts[0] not in tree:
            tree[parts[0]] = {"_type": "directory", "_path": parts[0]}
        _insert_into_tree(tree[parts[0]], parts[1:], full_path)


def _tree_dict_to_list(tree):
    """Convert the nested dict tree to the JSON-ready list format."""
    result = []
    for name, value in sorted(tree.items()):
        if name.startswith("_"):
            continue
        if value.get("_type") == "file":
            result.append({
                "type": "file",
                "name": name,
                "path": value["_path"],
            })
        else:
            children = _tree_dict_to_list(value)
            result.append({
                "type": "directory",
                "name": name,
                "path": value.get("_path", name),
                "children": children,
            })
    return result
