"""Web-based parameter planner for behave.

Provides a local web UI for QA engineers to visually navigate feature files,
see which steps are parameterized, and edit parameter values through
type-appropriate widgets. Changes are saved to YAML plan files via a REST API.

Usage::

    behave plan --features-dir features --plans-dir plans/conservative
"""

import argparse

from behave.planner.server import serve


def run_plan(args):
    """Entry point for the ``behave plan`` subcommand.

    :param args: Command-line arguments (after "plan").
    """
    parser = argparse.ArgumentParser(
        prog="behave plan",
        description="Launch the web-based parameter planner UI.",
    )
    parser.add_argument(
        "--features-dir",
        default="features",
        help="Path to features directory (default: features)",
    )
    parser.add_argument(
        "--plans-dir",
        required=True,
        help="Path to plans directory for YAML config files",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8525,
        help="Port to bind to (default: 8525)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser on start",
    )

    opts = parser.parse_args(args)
    return serve(
        features_dir=opts.features_dir,
        plans_dir=opts.plans_dir,
        host=opts.host,
        port=opts.port,
        open_browser=not opts.no_browser,
    )
