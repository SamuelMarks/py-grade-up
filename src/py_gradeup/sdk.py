"""SDK layer for programmable access to py-gradeup."""

import difflib
import os
from typing import List, Optional

from py_gradeup.core import (
    _backup_old_requirements,
    _check_pyupgrade,
    _find_target_python,
    _get_current_python_version,
    _get_py_files,
    _get_target_files,
    _recreate_venv,
    _run_test_env,
    _run_tests,
    _should_modify,
    _update_ci_cd_environments,
    _update_dependencies_file,
    _update_dockerfiles,
    _update_python_classifiers,
)
from py_gradeup.graph import _prepare_compile_targets
from py_gradeup.models import (
    AuditResult,
    FixResult,
    GraphResult,
    RevertResult,
    SecurityResult,
    TestResult,
)
from py_gradeup.security import _parse_dependencies, check_vulnerabilities


class PyGradeup:
    """SDK for py-gradeup operations.

    Provides programmable access to audit, fix, revert, test, security,
    and graph functionalities.
    """

    def __init__(self, path: str = "."):
        """Initialize the PyGradeup SDK.

        Args:
            path: The root path of the project to operate on.
        """
        self.path = os.path.abspath(path)

    def audit(
        self, show_diff: bool = False, only: Optional[List[str]] = None
    ) -> AuditResult:
        """Perform an audit of the project to identify possible upgrades.

        Args:
            show_diff: If True, include diff strings for proposed file modifications.
            only: A list of specific file or directory paths to restrict the audit to.

        Returns:
            An AuditResult object containing the findings of the audit.
        """
        current_ver = _get_current_python_version(self.path)
        target_files = _get_target_files(self.path)
        target_py, resolved_deps = _find_target_python(target_files, current_ver)

        backup_name = None
        if target_py != current_ver and target_files:
            parts = current_ver.split(".")
            if len(parts) >= 2:
                backup_name = f"requirements-{parts[0]}-{parts[1]}.txt"
            else:
                backup_name = f"requirements-{current_ver}.txt"

        parts_int = [int(x) for x in target_py.split(".")]
        if len(parts_int) >= 2:
            py_ver_tuple = (parts_int[0], parts_int[1])
        else:
            py_ver_tuple = (parts_int[0], 0)  # pragma: no cover
        py_files = [f for f in _get_py_files(self.path) if _should_modify(f, only)]

        files_to_upgrade = []
        proposed_diffs = []
        for file_path in py_files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                new_content = _check_pyupgrade(content, py_ver_tuple)
                if new_content != content:
                    files_to_upgrade.append(file_path)
                    if show_diff:
                        diff = list(
                            difflib.unified_diff(
                                content.splitlines(keepends=True),
                                new_content.splitlines(keepends=True),
                                fromfile=f"a/{os.path.relpath(file_path, self.path)}",
                                tofile=f"b/{os.path.relpath(file_path, self.path)}",
                            )
                        )
                        proposed_diffs.extend(diff)
            except Exception:  # pragma: no cover
                pass

        dependency_updates = {}
        for fpath in target_files:
            if os.path.exists(fpath) and _should_modify(fpath, only):
                updates = _update_dependencies_file(fpath, resolved_deps, dry_run=True)
                if updates:
                    dependency_updates[fpath] = updates

        ci_files = []
        cls_files = []
        docker_files = []
        if target_py != current_ver:
            ci_files = _update_ci_cd_environments(
                self.path, target_py, dry_run=True, only=only
            )
            cls_files = _update_python_classifiers(
                self.path, target_py, dry_run=True, only=only
            )
            docker_files = _update_dockerfiles(
                self.path, target_py, dry_run=True, only=only
            )

        return AuditResult(
            current_version=current_ver,
            target_version=target_py,
            backup_name=backup_name,
            files_to_upgrade=files_to_upgrade,
            proposed_diffs=proposed_diffs,
            dependency_updates=dependency_updates,
            ci_files_to_update=ci_files,
            cls_files_to_update=cls_files,
            docker_files_to_update=docker_files,
        )

    def fix(
        self,
        run_tests: bool = False,
        interactive: bool = False,
        commit: bool = False,
        recreate_venv: bool = False,
        versioned_venv: bool = False,
        only: Optional[List[str]] = None,
    ) -> FixResult:
        """Apply identified upgrades to the project.

        Args:
            run_tests: If True, run the project's test suite after applying fixes.
            interactive: If True, prompt for confirmation before making file
                modifications.
            commit: If True, commit the changes via git after a successful fix.
            recreate_venv: If True, recreate the virtual environment using the
                target Python version.
            versioned_venv: If True, create a versioned virtual environment
                (e.g. .venv-3.12).
            only: A list of specific file or directory paths to restrict the fix to.

        Returns:
            A FixResult object containing the details of the changes applied.
        """
        import subprocess

        current_ver = _get_current_python_version(self.path)
        target_files = _get_target_files(self.path)
        target_py, resolved_deps = _find_target_python(target_files, current_ver)
        parts_int = [int(x) for x in target_py.split(".")]
        if len(parts_int) >= 2:
            py_ver_tuple = (parts_int[0], parts_int[1])
        else:
            py_ver_tuple = (parts_int[0], 0)  # pragma: no cover

        backup_path = None
        if target_py != current_ver and target_files:
            backup_path = _backup_old_requirements(self.path, current_ver, target_files)

        from py_gradeup.core import _prompt_diff

        py_files = [f for f in _get_py_files(self.path) if _should_modify(f, only)]
        files_upgraded = []
        for file_path in py_files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content_f = f.read()
                new_content = _check_pyupgrade(content_f, py_ver_tuple)
                if new_content != content_f:
                    if interactive and not _prompt_diff(
                        file_path, content_f, new_content
                    ):
                        continue
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    files_upgraded.append(file_path)
            except Exception:  # pragma: no cover
                pass

        dependency_updates = {}
        any_deps_bumped = False
        for fpath in target_files:
            if os.path.exists(fpath) and _should_modify(fpath, only):
                updates = _update_dependencies_file(
                    fpath, resolved_deps, dry_run=False, interactive=interactive
                )
                if updates:
                    dependency_updates[fpath] = updates
                    any_deps_bumped = True

        from py_gradeup.core import _update_python_version_bounds

        ci_files = []
        cls_files = []
        docker_files = []
        if target_py != current_ver and _update_python_version_bounds(
            self.path, target_py, dry_run=False, only=only
        ):
            ci_files = _update_ci_cd_environments(
                self.path, target_py, dry_run=False, only=only
            )
            cls_files = _update_python_classifiers(
                self.path, target_py, dry_run=False, only=only
            )
            docker_files = _update_dockerfiles(
                self.path, target_py, dry_run=False, only=only
            )

        if recreate_venv or versioned_venv:
            _recreate_venv(self.path, target_py, versioned=versioned_venv)

        tests_passed = None
        if run_tests:
            tests_passed = _run_tests(self.path)

        if commit:
            msg_title = f"Upgrade project to Python {target_py}"
            details = []
            if target_py != current_ver:
                extra = []
                if docker_files:
                    extra.append("Docker")
                if ci_files:
                    extra.append("GitHub Actions")
                extra_str = f"; also in {' and '.join(extra)}" if extra else ""
                details.append(
                    f"- Added support for Python versions: {target_py}{extra_str}"
                )
            if files_upgraded:
                details.append(f"- Upgraded syntax in {len(files_upgraded)} files")
            if any_deps_bumped:
                details.append("- Bumped dependency versions")  # pragma: no cover

            msg = msg_title
            if details:
                msg += "\n\n" + "\n".join(details)

            try:
                if backup_path and os.path.exists(backup_path):
                    subprocess.run(  # pragma: no cover
                        ["git", "add", os.path.basename(backup_path)],
                        cwd=self.path,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                subprocess.run(
                    ["git", "commit", "-a", "-m", msg],
                    cwd=self.path,
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except FileNotFoundError:  # pragma: no cover
                pass

        return FixResult(
            current_version=current_ver,
            target_version=target_py,
            backup_path=backup_path,
            files_upgraded=files_upgraded,
            dependency_updates=dependency_updates,
            ci_files_updated=ci_files,
            cls_files_updated=cls_files,
            docker_files_updated=docker_files,
            tests_passed=tests_passed,
        )

    def revert(self) -> RevertResult:
        """Revert the project to its state before the last fix operation.

        Restores tracked files via Git and attempts to restore dependencies
        from the most recent backup.

        Returns:
            A RevertResult object containing the status of the operation.
        """
        import re
        import shutil
        import subprocess

        git_restored = False
        git_error = None
        try:
            res = subprocess.run(
                ["git", "restore", "."],
                cwd=self.path,
                check=False,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                git_restored = True
            else:
                git_error = res.stderr
        except FileNotFoundError:  # pragma: no cover
            git_error = "Git not found."

        backups = []
        if os.path.exists(self.path):
            for f in os.listdir(self.path):
                if re.match(r"^requirements-\d+(-\d+)?\.txt$", f):
                    backups.append(f)

        dependencies_restored_from = None
        if backups:
            backups.sort(
                key=lambda x: os.path.getmtime(os.path.join(self.path, x)), reverse=True
            )
            latest_backup = backups[0]
            backup_path = os.path.join(self.path, latest_backup)
            req_path = os.path.join(self.path, "requirements.txt")
            try:
                shutil.copy2(backup_path, req_path)
                dependencies_restored_from = latest_backup
            except Exception:  # pragma: no cover
                pass

        return RevertResult(
            git_restored=git_restored,
            git_error=git_error,
            dependencies_restored_from=dependencies_restored_from,
        )

    def test(self, parallel: bool = True) -> TestResult:
        """Test the project against multiple Python environments.

        Args:
            parallel: If True, run tests concurrently across environments.

        Returns:
            A TestResult object with testing outcomes.
        """
        current_ver = _get_current_python_version(self.path)
        target_files = _get_target_files(self.path)
        _, _ = _find_target_python(target_files, current_ver)

        all_versions = ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]
        try:
            c_parts = tuple(map(int, current_ver.split(".")))
            versions = [
                v for v in all_versions if c_parts <= tuple(map(int, v.split(".")))
            ]
        except Exception:  # pragma: no cover
            versions = all_versions

        uses_pytest = False
        if os.path.exists(os.path.join(self.path, "pytest.ini")) or os.path.exists(
            os.path.join(self.path, "conftest.py")
        ):
            uses_pytest = True
        elif os.path.exists(os.path.join(self.path, "pyproject.toml")):
            with open(os.path.join(self.path, "pyproject.toml"), encoding="utf-8") as f:
                if "pytest" in f.read():
                    uses_pytest = True
        elif os.path.exists(os.path.join(self.path, "requirements-dev.txt")):
            with open(
                os.path.join(self.path, "requirements-dev.txt"), encoding="utf-8"
            ) as f:
                if "pytest" in f.read():
                    uses_pytest = True

        backends = ["uv", "pyenv"]
        results = {}
        outputs = []

        tasks = [
            (self.path, backend, v, uses_pytest)
            for v in versions
            for backend in backends
        ]

        if parallel:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(_run_test_env, *task) for task in tasks]
                for future in concurrent.futures.as_completed(futures):
                    env_name, passed, out = future.result()
                    results[env_name] = passed
                    outputs.append(out)
        else:
            for task in tasks:
                env_name, passed, out = _run_test_env(*task)
                results[env_name] = passed
                outputs.append(out)

        all_passed = True
        for _env_name, passed in results.items():
            if not passed:
                all_passed = False

        return TestResult(
            results=results, all_passed=all_passed, output="\n".join(outputs)
        )

    def security(self) -> SecurityResult:
        """Audit project dependencies for known security vulnerabilities.

        Returns:
            A SecurityResult object with detected vulnerabilities.
        """
        target_files = _get_target_files(self.path)

        all_deps = {}
        for t_file in target_files:
            deps = _parse_dependencies(t_file)
            all_deps.update(deps)

        vulnerabilities = {}
        found_vulns = False

        if all_deps:
            for pkg, version in sorted(all_deps.items()):
                vulns = check_vulnerabilities(pkg, version)
                if vulns:
                    found_vulns = True
                    vulnerabilities[f"{pkg}=={version}"] = vulns

        return SecurityResult(
            vulnerabilities_found=found_vulns,
            vulnerabilities=vulnerabilities,
        )

    def graph(self) -> GraphResult:
        """Generate a dependency tree of the project.

        Attempts to resolve and output the dependency tree.

        Returns:
            A GraphResult object containing the tree or conflict errors.
        """
        import contextlib
        import subprocess
        import tempfile

        target_files = _get_target_files(self.path)
        if not target_files:
            return GraphResult()

        tmp_paths: list[str] = []
        try:
            compile_targets = _prepare_compile_targets(target_files, tmp_paths)
            if not compile_targets:
                return GraphResult()

            with tempfile.TemporaryDirectory() as venv_dir:
                try:
                    subprocess.run(
                        ["uv", "venv", venv_dir],
                        check=True,
                        capture_output=True,
                        text=True,
                    )

                    cmd = ["uv", "pip", "install", "-p", venv_dir]
                    for target in compile_targets:
                        cmd.extend(["-r", target])

                    subprocess.run(cmd, check=True, capture_output=True, text=True)

                    tree_res = subprocess.run(
                        ["uv", "pip", "tree", "-p", venv_dir],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    return GraphResult(tree=tree_res.stdout)

                except subprocess.CalledProcessError as e:
                    return GraphResult(conflict_error=e.stderr or e.stdout)

        finally:
            for t in tmp_paths:
                if os.path.exists(t):
                    with contextlib.suppress(Exception):
                        os.remove(t)
