"""HTTP server for the planner web UI."""

import os
import webbrowser
from http.server import HTTPServer

from behave.planner.api import PlannerAPIHandler
from behave.planner.discovery import FeatureDiscovery


def serve(features_dir, plans_dir, host="localhost", port=8525, open_browser=True):
    """Start the planner web server.

    :param features_dir: Path to the features directory.
    :param plans_dir: Path to the plans directory.
    :param host: Host to bind to.
    :param port: Port to bind to.
    :param open_browser: Whether to open the browser on start.
    """
    # Discover features and step definitions
    print("Discovering features in: {}".format(os.path.abspath(features_dir)))
    discovery = FeatureDiscovery(features_dir)
    discovery.discover()
    print("Found {} feature(s)".format(len(discovery.features)))

    # Ensure plans dir exists
    os.makedirs(plans_dir, exist_ok=True)

    # Set up handler class attributes
    package_dir = os.path.dirname(os.path.abspath(__file__))
    elm_dir = os.path.join(package_dir, "elm")

    PlannerAPIHandler.discovery = discovery
    PlannerAPIHandler.plans_dir = os.path.abspath(plans_dir)
    PlannerAPIHandler.static_dir = os.path.join(elm_dir, "static")
    PlannerAPIHandler.dist_dir = os.path.join(elm_dir, "dist")

    # Check if Elm app is built
    elm_js = os.path.join(PlannerAPIHandler.dist_dir, "elm.js")
    if not os.path.isfile(elm_js):
        print("WARNING: Elm app not built. The UI will not load.")
        print("  Run: cd behave/planner/elm && elm make src/Main.elm --output=dist/elm.js")

    server = HTTPServer((host, port), PlannerAPIHandler)
    url = "http://{}:{}".format(host, port)
    print("Planner server running at {}".format(url))

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down planner server.")
        server.server_close()
