# ruff: noqa: E501
"""Command-line interface for py-gradeup."""

import argparse
import sys
from typing import Optional, Sequence

from py_gradeup.core import audit_project, fix_project, revert_project
from py_gradeup.graph import visualize_graph
from py_gradeup.security import audit_security


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Execute the main CLI logic.

    Args:
        argv: Optional sequence of command-line arguments.

    Returns:
        Integer exit code.
    """
    parser = argparse.ArgumentParser(description="Upgrade Python projects.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser(
        "audit", help="Audit the project for upgrades."
    )
    audit_parser.add_argument("path", help="Path to the project to audit.")
    audit_parser.add_argument(
        "--diff",
        action="store_true",
        help="Output unified diffs of proposed syntax changes",
    )

    fix_parser = subparsers.add_parser("fix", help="Fix and upgrade the project.")
    fix_parser.add_argument("path", help="Path to the project to fix.")
    fix_parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Prompt before applying each file's changes",
    )
    fix_parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run tests (tox, nox, or pytest) after upgrading",
    )
    fix_parser.add_argument(
        "--commit",
        action="store_true",
        help="Automatically commit the applied changes",
    )
    fix_parser.add_argument(
        "--recreate-venv",
        action="store_true",
        help="Destroy and rebuild local .venv using the new target version",
    )
    fix_parser.add_argument(
        "--versioned-venv",
        action="store_true",
        help="Create a versioned virtual environment (e.g. .venv-uv-3-12) instead of .venv",
    )

    revert_parser = subparsers.add_parser(
        "revert", help="Revert the project to its previous state."
    )
    revert_parser.add_argument("path", help="Path to the project to revert.")

    security_parser = subparsers.add_parser(
        "security", help="Scan the project dependencies for security vulnerabilities."
    )
    security_parser.add_argument("path", help="Path to the project to scan.")

    test_parser = subparsers.add_parser(
        "test", help="Test the project against a matrix of Python versions using uv and pyenv."
    )
    test_parser.add_argument("path", help="Path to the project to test.")
    test_parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel execution of the test matrix.",
    )

    graph_parser = subparsers.add_parser(
        "graph", help="Visualize dependency graph and conflict trees."
    )
    graph_parser.add_argument("path", help="Path to the project to graph.")

    args = parser.parse_args(argv)

    if args.command == "audit":
        audit_project(args.path, show_diff=args.diff)
    elif args.command == "fix":
        fix_project(
            args.path,
            run_tests=args.run_tests,
            interactive=args.interactive,
            commit=args.commit,
            recreate_venv=args.recreate_venv,
            versioned_venv=args.versioned_venv,
        )
    elif args.command == "revert":
        revert_project(args.path)
    elif args.command == "security":
        found = audit_security(args.path)
        if found:
            return 1
    elif args.command == "test":
        from py_gradeup.core import test_matrix
        passed = test_matrix(args.path, parallel=not args.no_parallel)
        if not passed:
            return 1
    elif args.command == "graph":
        visualize_graph(args.path)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
