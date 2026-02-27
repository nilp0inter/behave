"""REST API request handlers for the planner web server."""

import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import unquote

from behave.param_decorator import validate_value, ParamValidationError
from behave.planner.serializers import serialize_feature_tree, serialize_feature
from behave.planner.yaml_io import (
    feature_path_to_yaml_path,
    read_plan_yaml,
    write_param_value,
)


class PlannerAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler with REST API routing for the planner.

    Class attributes are set by the server before starting:
      - discovery: FeatureDiscovery instance
      - plans_dir: Path to the plans directory
      - static_dir: Path to the static files directory
      - dist_dir: Path to the Elm dist directory
    """
    discovery = None
    plans_dir = None
    static_dir = None
    dist_dir = None

    MIME_TYPES = {
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".ico": "image/x-icon",
    }

    def do_GET(self):
        path = unquote(self.path)

        if path == "/api/features":
            self._handle_feature_tree()
        elif path.startswith("/api/features/"):
            feature_path = path[len("/api/features/"):]
            self._handle_feature_detail(feature_path)
        elif path.startswith("/api/plans/"):
            feature_path = path[len("/api/plans/"):]
            self._handle_plan_detail(feature_path)
        elif path == "/" or path == "/index.html":
            self._serve_static("index.html")
        elif path == "/elm.js":
            self._serve_dist("elm.js")
        else:
            # Try static files
            static_path = path.lstrip("/")
            if static_path:
                self._serve_static(static_path)
            else:
                self._send_error(404, "Not found")

    def do_PUT(self):
        path = unquote(self.path)

        if path.startswith("/api/params/"):
            remainder = path[len("/api/params/"):]
            self._handle_param_update(remainder)
        else:
            self._send_error(404, "Not found")

    def _handle_feature_tree(self):
        data = serialize_feature_tree(self.discovery)
        self._send_json(200, data)

    def _handle_feature_detail(self, feature_path):
        feature = self.discovery.get_feature_by_path(feature_path)
        if feature is None:
            self._send_error(404, "Feature not found: {}".format(feature_path))
            return
        data = serialize_feature(feature, self.discovery)
        self._send_json(200, data)

    def _handle_plan_detail(self, feature_path):
        yaml_path = feature_path_to_yaml_path(feature_path, self.plans_dir)
        plan_data = read_plan_yaml(yaml_path)
        if plan_data is None:
            self._send_json(200, {"exists": False, "data": None})
        else:
            self._send_json(200, {"exists": True, "data": plan_data})

    def _handle_param_update(self, remainder):
        # Parse: feature_path/scenario_name/step_idx/param_name
        parts = remainder.rsplit("/", 2)
        if len(parts) != 3:
            self._send_error(400, "Invalid path format. Expected: feature_path/scenario/step_idx/param")
            return

        feature_and_scenario = parts[0]
        step_idx_str = parts[1]
        param_name = parts[2]

        # Split feature_path from scenario name — scenario is last segment before step_idx
        fs_parts = feature_and_scenario.rsplit("/", 1)
        if len(fs_parts) != 2:
            self._send_error(400, "Invalid path format. Expected: feature_path/scenario/step_idx/param")
            return

        feature_path = fs_parts[0]
        scenario_name = fs_parts[1]

        try:
            step_idx = int(step_idx_str)
        except ValueError:
            self._send_error(400, "step_idx must be an integer")
            return

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_error(400, "Request body required")
            return

        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON")
            return

        if "value" not in payload:
            self._send_error(400, "Missing 'value' field")
            return

        raw_value = payload["value"]

        # Find the feature and validate
        feature = self.discovery.get_feature_by_path(feature_path)
        if feature is None:
            self._send_error(404, "Feature not found: {}".format(feature_path))
            return

        # Find the param def for validation
        param_def = self._find_param_def(feature, scenario_name, step_idx, param_name)
        if param_def is None:
            self._send_error(404, "Parameter '{}' not found on step {} in scenario '{}'".format(
                param_name, step_idx, scenario_name
            ))
            return

        # Validate the value
        try:
            validated = validate_value(param_def, raw_value)
        except ParamValidationError as e:
            self._send_json(200, {"status": "error", "message": str(e)})
            return

        # Write to YAML
        yaml_path = feature_path_to_yaml_path(feature_path, self.plans_dir)
        write_param_value(yaml_path, feature, scenario_name, step_idx,
                          param_name, validated, self.discovery)

        self._send_json(200, {"status": "ok", "value": validated})

    def _find_param_def(self, feature, scenario_name, step_idx, param_name):
        """Find a ParamDef by navigating the feature model."""
        for scenario in feature.scenarios:
            if scenario.name == scenario_name:
                all_steps = []
                bg = getattr(scenario, "background", None) or feature.background
                if bg:
                    all_steps.extend(bg.all_steps)
                all_steps.extend(scenario.steps)

                if step_idx >= len(all_steps):
                    return None

                step = all_steps[step_idx]
                param_defs = self.discovery.get_step_params(step)
                for pd in param_defs:
                    if pd.name == param_name:
                        return pd
                return None
        return None

    def _serve_static(self, filename):
        filepath = os.path.join(self.static_dir, filename)
        if not os.path.isfile(filepath):
            self._send_error(404, "Not found: {}".format(filename))
            return
        self._serve_file(filepath)

    def _serve_dist(self, filename):
        filepath = os.path.join(self.dist_dir, filename)
        if not os.path.isfile(filepath):
            self._send_error(404, "Elm app not built. Run: cd behave/planner/elm && elm make src/Main.elm --output=dist/elm.js")
            return
        self._serve_file(filepath)

    def _serve_file(self, filepath):
        ext = os.path.splitext(filepath)[1]
        content_type = self.MIME_TYPES.get(ext, "application/octet-stream")
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status, message):
        self._send_json(status, {"error": message})

    def log_message(self, format, *args):
        """Quieter logging — only show non-200 responses."""
        status = args[1] if len(args) > 1 else ""
        if str(status).startswith("2"):
            return
        BaseHTTPRequestHandler.log_message(self, format, *args)
