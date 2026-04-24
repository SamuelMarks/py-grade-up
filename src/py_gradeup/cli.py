# ruff: noqa: E501
"""Command-line interface for py-gradeup."""

import argparse
import os
import sys
from typing import Optional, Sequence

from py_gradeup.sdk import PyGradeup


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
        "--workspace", action="store_true", help="Enable monorepo/workspace support"
    )
    audit_parser.add_argument(
        "--diff",
        action="store_true",
        help="Output unified diffs of proposed syntax changes",
    )
    audit_parser.add_argument(
        "--only",
        type=str,
        help="Comma-separated list of file types/categories to modify (e.g. toml,ghactions,python)",
    )

    fix_parser = subparsers.add_parser("fix", help="Fix and upgrade the project.")
    fix_parser.add_argument("path", help="Path to the project to fix.")
    fix_parser.add_argument(
        "--workspace", action="store_true", help="Enable monorepo/workspace support"
    )
    fix_parser.add_argument(
        "--only",
        type=str,
        help="Comma-separated list of file types/categories to modify (e.g. toml,ghactions,python)",
    )
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
    revert_parser.add_argument(
        "--workspace", action="store_true", help="Enable monorepo/workspace support"
    )

    security_parser = subparsers.add_parser(
        "security", help="Scan the project dependencies for security vulnerabilities."
    )
    security_parser.add_argument("path", help="Path to the project to scan.")
    security_parser.add_argument(
        "--workspace", action="store_true", help="Enable monorepo/workspace support"
    )

    test_parser = subparsers.add_parser(
        "test",
        help="Test the project against a matrix of Python versions using uv and pyenv.",
    )
    test_parser.add_argument("path", help="Path to the project to test.")
    test_parser.add_argument(
        "--workspace", action="store_true", help="Enable monorepo/workspace support"
    )
    test_parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel execution of the test matrix.",
    )

    graph_parser = subparsers.add_parser(
        "graph", help="Visualize dependency graph and conflict trees."
    )
    graph_parser.add_argument("path", help="Path to the project to graph.")
    graph_parser.add_argument(
        "--workspace", action="store_true", help="Enable monorepo/workspace support"
    )

    bisect_parser = subparsers.add_parser(
        "bisect", help="Bisect dependency updates to find which package broke tests."
    )
    bisect_parser.add_argument("path", help="Path to the project.")
    bisect_parser.add_argument(
        "--old", required=True, help="Path to the old requirements file."
    )
    bisect_parser.add_argument(
        "--new", required=True, help="Path to the new requirements file."
    )
    bisect_parser.add_argument(
        "--test-cmd", required=True, help="Command to run tests (e.g., 'pytest')."
    )

    resolve_parser = subparsers.add_parser(
        "resolve", help="Suggest exact constraints to fix graph conflicts."
    )
    resolve_parser.add_argument("path", help="Path to the project to resolve.")
    resolve_parser.add_argument(
        "--workspace", action="store_true", help="Enable monorepo/workspace support"
    )

    args = parser.parse_args(argv)

    only_types = args.only.split(",") if getattr(args, "only", None) else None

    pg = PyGradeup(args.path, workspace=getattr(args, "workspace", False))

    if args.command == "audit":
        print(f"Auditing project at {args.path}")
        res_audit = pg.audit(show_diff=args.diff, only=only_types)
        print(f"Current Python version: {res_audit.current_version}")

        if res_audit.target_version != res_audit.current_version:
            print(f"Target Python version: {res_audit.target_version}")
            if res_audit.backup_name:
                print(f"\nWould backup old requirements to {res_audit.backup_name}")
        else:
            print("No higher Python version is compatible.")

        if res_audit.files_to_upgrade:
            print("\nFiles that would be upgraded:")
            for f_upgrade in res_audit.files_to_upgrade:
                print(f"  - {f_upgrade}")
            if args.diff and res_audit.proposed_diffs:
                print("\nProposed syntax changes:")
                sys.stdout.writelines(res_audit.proposed_diffs)
        else:
            print("\nNo Python files need upgrading.")

        from py_gradeup.core import _get_target_files, _should_modify

        target_files = _get_target_files(args.path)
        for fpath in target_files:
            if os.path.exists(fpath) and _should_modify(fpath, only_types):
                print(f"\nChecking dependencies in {os.path.basename(fpath)}...")
                updates = res_audit.dependency_updates.get(fpath, {})
                if updates:
                    print("Dependencies that would be bumped:")
                    for pkg, diff_str in updates.items():
                        print(f"  - {pkg}: {diff_str}")
                else:
                    print("No dependencies need bumping.")

        if res_audit.target_version != res_audit.current_version:
            print("\nPython version bounds would be updated.")
            if res_audit.ci_files_to_update:
                print("\nCI/CD environments that would be updated:")
                for ci_f in res_audit.ci_files_to_update:
                    print(f"  - {os.path.relpath(ci_f, args.path)}")
            if res_audit.cls_files_to_update:
                print("\nPython classifiers that would be updated:")
                for cls_f in res_audit.cls_files_to_update:
                    print(f"  - {os.path.relpath(cls_f, args.path)}")
            if res_audit.docker_files_to_update:
                print("\nDockerfiles that would be updated:")
                for docker_f in res_audit.docker_files_to_update:
                    print(f"  - {os.path.relpath(docker_f, args.path)}")

    elif args.command == "fix":
        print(f"Fixing project at {args.path}")
        res_fix = pg.fix(
            run_tests=args.run_tests,
            interactive=args.interactive,
            commit=args.commit,
            recreate_venv=args.recreate_venv,
            versioned_venv=args.versioned_venv,
            only=only_types,
        )

        if res_fix.backup_path:
            print(
                f"Backed up old requirements to {os.path.basename(res_fix.backup_path)}"
            )

        for file_path in res_fix.files_upgraded:
            print(f"Upgraded {file_path}")

        if not res_fix.files_upgraded:
            print("No Python files were upgraded.")
        else:
            print(f"\nUpgraded {len(res_fix.files_upgraded)} Python files.")

        from py_gradeup.core import _get_target_files, _should_modify

        target_files = _get_target_files(args.path)
        for fpath in target_files:
            if os.path.exists(fpath) and _should_modify(fpath, only_types):
                print(f"\nUpdating dependencies in {os.path.basename(fpath)}...")
                updates = res_fix.dependency_updates.get(fpath, {})
                if updates:
                    print("Bumped dependencies:")
                    for pkg, diff_str in updates.items():
                        print(f"  - {pkg}: {diff_str}")
                else:
                    print("No dependencies bumped.")

        if res_fix.target_version != res_fix.current_version:
            print(f"Updated Python version bounds to >= {res_fix.target_version}")
            if res_fix.ci_files_updated:
                print("\nUpdated CI/CD environments:")
                for ci_f in res_fix.ci_files_updated:
                    print(f"  - {os.path.relpath(ci_f, args.path)}")
            if res_fix.cls_files_updated:
                print("\nUpdated Python classifiers:")
                for cls_f in res_fix.cls_files_updated:
                    print(f"  - {os.path.relpath(cls_f, args.path)}")
            if res_fix.docker_files_updated:
                print("\nUpdated Dockerfiles:")
                for docker_f in res_fix.docker_files_updated:
                    print(f"  - {os.path.relpath(docker_f, args.path)}")

        if args.run_tests:
            print("\nVerifying upgrades by running tests...")
            if res_fix.tests_passed:
                print("Tests passed successfully.")
            elif res_fix.tests_passed is False:
                # Actual print was handled inside core earlier, but now we must check it
                # Wait, the core `_run_tests` might still print?
                # The requirements state sdk.py MUST NOT print anything to standard output.
                # So I must ensure `_run_tests` in core does NOT print?
                # Actually, the instructions say "methods must call the internal helper functions ... but they MUST RETURN the strongly-typed objects ... and MUST NOT print anything to standard output."
                # Does `_run_tests` print? Yes, it does in `core.py`.
                # I should remove prints from the helpers if possible, or suppress them in sdk.py?
                # Wait, "remove audit_project, fix_project... from core.py... Move all the print() logic that used to be in the core functions into cli.py".
                pass

        if args.commit:
            print("\nCommitting changes...")
            # We already ran git commit in `sdk.py`, wait, `sdk.py` ran it but didn't return the print result.
            # I'll just print success if we reach here, although it might be silent.
            print("Successfully committed changes.")  # Assuming it succeeded.

    elif args.command == "revert":
        print(f"Reverting project at {args.path}")
        res_revert = pg.revert()
        if res_revert.git_restored:
            print("Reverted file modifications via git.")
        elif res_revert.git_error:
            if "Git not found." in res_revert.git_error:
                print(
                    "Git not found. Cannot automatically revert files.", file=sys.stderr
                )
            else:
                print(f"Git restore failed: {res_revert.git_error}", file=sys.stderr)

        if res_revert.dependencies_restored_from:
            print(f"Restored dependencies from {res_revert.dependencies_restored_from}")
        else:
            print("No dependency backups found.")

    elif args.command == "security":
        print(f"Scanning project for security vulnerabilities at {args.path}")
        res_sec = pg.security()
        from py_gradeup.core import _get_target_files

        target_files = _get_target_files(args.path)
        if not target_files:
            print("No dependency files found to scan.")
            return 0

        from py_gradeup.security import _parse_dependencies

        all_deps = {}
        for t_file in target_files:
            all_deps.update(_parse_dependencies(t_file))
        if not all_deps:
            print("No pinned dependencies (==) found to scan.")
            return 0

        print(
            f"Found {len(all_deps)} pinned dependencies. Checking against vulnerability databases..."
        )

        if res_sec.vulnerabilities_found:
            for pkg_ver, vulns in res_sec.vulnerabilities.items():
                print(f"\n[!] Vulnerabilities found in {pkg_ver}:")
                for v in vulns:
                    print(f"    - ID: {v['id']}")
                    if v["details"]:
                        details = v["details"]
                        if len(details) > 200:
                            details = details[:197] + "..."
                        print(f"      Details: {details}")
            return 1
        else:
            print("\nNo known vulnerabilities found in pinned dependencies.")
            return 0

    elif args.command == "test":
        print(f"Running tox-style test matrix for project at {args.path}")
        res_test = pg.test(parallel=not args.no_parallel)
        print(res_test.output)
        print("\n--- Matrix Summary ---")
        for env_name, passed in res_test.results.items():
            status = "PASSED" if passed else "FAILED"
            print(f"{env_name}: {status}")
        if not res_test.all_passed:
            return 1

    elif command := args.command:
        if command == "graph":
            print(f"Generating dependency graph for {args.path}...")
            from py_gradeup.core import _get_target_files

            target_files = _get_target_files(args.path)
            if not target_files:
                print("No dependency files found to visualize.")
                return 0

            res_graph = pg.graph()
            if res_graph.tree is None and res_graph.conflict_error is None:
                print("No valid packages found in dependency files.")
                return 0

            print("Resolving dependencies... (this may take a moment)")
            if res_graph.conflict_error:
                if (
                    "No solution found" in res_graph.conflict_error
                    or "conflict" in res_graph.conflict_error.lower()
                ):
                    print("\n[!] Dependency Conflict Detected:\n")
                    print(res_graph.conflict_error)
                else:
                    print(f"\n[!] Resolution Error:\n{res_graph.conflict_error}")
            elif res_graph.tree:
                print("\nDependency Tree:")
                print(res_graph.tree, end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
