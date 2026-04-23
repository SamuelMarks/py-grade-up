"""Module containing additional missing coverage tests."""

# ruff: noqa

import json
import os
from unittest.mock import patch

import pytest

import py_gradeup.core as core
import py_gradeup.graph as graph
from py_gradeup.cli import main
from py_gradeup.models import (
    AuditResult,
    FixResult,
    GraphResult,
    RevertResult,
    SecurityResult,
)
from py_gradeup.sdk import PyGradeup


def test_core_recreate_venv_missing_dir(tmp_path):
    """Test function."""
    with __import__("unittest").mock.patch("subprocess.run"):
        core._recreate_venv(str(tmp_path), "3.8", versioned=True)

def test_cli_audit_skip_file(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.audit") as mock_audit, patch("py_gradeup.core._get_target_files") as mock_get_target_files, patch("os.path.exists", return_value=True), patch("py_gradeup.core._should_modify", return_value=False):
        mock_get_target_files.return_value = ["reqs.txt"]
        mock_audit.return_value = AuditResult("3.8", "3.8", None, [], {"reqs.txt": {"requests": "requests>=2.0.0"}}, [], [], [], [])
        with patch("sys.argv", ["py-gradeup", "audit", "."]):
            main()

def test_cli_fix_skip_file(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.fix") as mock_fix, patch("py_gradeup.core._get_target_files") as mock_get_target_files, patch("os.path.exists", return_value=True), patch("py_gradeup.core._should_modify", return_value=False):
        mock_get_target_files.return_value = ["reqs.txt"]
        mock_fix.return_value = FixResult("3.8", "3.8", None, [], {"reqs.txt": {"requests": "requests>=2.0.0"}}, [], [], [], None)
        with patch("sys.argv", ["py-gradeup", "fix", "."]):
            main()

def test_cli_fix_tests_passed_none(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.fix") as mock_fix, patch("py_gradeup.core._get_target_files") as mock_get_target_files:
        mock_get_target_files.return_value = []
        mock_fix.return_value = FixResult("3.8", "3.8", None, [], {}, [], [], [], None)
        with patch("sys.argv", ["py-gradeup", "fix", "--run-tests", "."]):
            main()

def test_cli_revert_no_error(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.revert") as mock_revert:
        mock_revert.return_value = RevertResult(False, None, None)
        with patch("sys.argv", ["py-gradeup", "revert", "."]):
            main()

def test_cli_security_none_details(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.security") as mock_sec, patch("py_gradeup.core._get_target_files") as mock_get_target_files, patch("os.path.exists", return_value=True), patch("py_gradeup.security._parse_dependencies", return_value={"pkg==1.0": "1.0"}):
        mock_get_target_files.return_value = ["reqs.txt"]
        mock_sec.return_value = SecurityResult(True, {"pkg==1.0": [{"id": "CVE-1", "details": ""}]})
        with patch("sys.argv", ["py-gradeup", "security", "."]):
            main()

def test_cli_graph_empty_tree_not_none(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.graph") as mock_graph, patch("py_gradeup.core._get_target_files") as mock_get_target_files:
        mock_get_target_files.return_value = ["reqs.txt"]
        mock_graph.return_value = GraphResult(tree="", conflict_error=None)
        with patch("sys.argv", ["py-gradeup", "graph", "."]):
            main()

def test_cli_command_is_none(capsys):
    """Test function."""
    class DummyArgs:
        """Docstring."""
        command = None
        path = "."
    with patch("argparse.ArgumentParser.parse_args", return_value=DummyArgs()):
        main()

def test_cli_command_unknown_exception(capsys):
    """Test function."""
    with patch("sys.argv", ["py-gradeup", "unknown", "."]):
        with pytest.raises(SystemExit):
            main()

def test_cli_command_bisect(capsys):
    """Test function."""
    class DummyArgs:
        """Docstring."""
        command = "bisect"
        path = "."
    with patch("argparse.ArgumentParser.parse_args", return_value=DummyArgs()):
        main()

def test_graph_prepare_compile_targets_empty_version(tmp_path):
    """Test function."""
    lock_file = tmp_path / "Pipfile.lock"
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({"default": {"pkg1": {"version": ""}}}, f)
    graph._prepare_compile_targets([str(lock_file)], [])

def test_graph_prepare_compile_targets_package_match(tmp_path):
    """Test function."""
    lock_file = tmp_path / "poetry.lock"
    with open(lock_file, "w", encoding="utf-8") as f:
        f.write("[[package]]\nname = \"pkg1\"\n# [[package]]\nversion = \"1.0.0\"")
    graph._prepare_compile_targets([str(lock_file)], [])

def test_sdk_audit_skip_file(tmp_path):
    """Test function."""
    pg = PyGradeup(str(tmp_path))
    (tmp_path / "reqs.txt").touch()
    with patch("py_gradeup.sdk._should_modify", return_value=False), patch("py_gradeup.sdk._get_target_files", return_value=[str(tmp_path / "reqs.txt")]), patch("py_gradeup.sdk._get_py_files", return_value=[]):
        assert not pg.audit().dependency_updates

def test_sdk_fix_skip_file(tmp_path):
    """Test function."""
    pg = PyGradeup(str(tmp_path))
    (tmp_path / "reqs.txt").touch()
    with patch("py_gradeup.sdk._should_modify", return_value=False), patch("py_gradeup.sdk._get_target_files", return_value=[str(tmp_path / "reqs.txt")]), patch("py_gradeup.sdk._get_py_files", return_value=[]):
        assert not pg.fix().dependency_updates

def test_sdk_fix_commit_no_version_change(tmp_path):
    """Test function."""
    pg = PyGradeup(str(tmp_path))
    with patch("py_gradeup.sdk._get_current_python_version", return_value="3.8"), patch("py_gradeup.sdk._find_target_python", return_value=("3.8", {})), patch("py_gradeup.sdk._get_target_files", return_value=[]), patch("py_gradeup.sdk._get_py_files", return_value=[]), patch("py_gradeup.core._update_python_version_bounds", return_value=False), patch("subprocess.run"):
        pg.fix(commit=True)

def test_sdk_revert_path_not_exists(tmp_path):
    """Test function."""
    pg = PyGradeup("/does/not/exist/12345")
    with patch("subprocess.run") as mock_run:
        mock_result = __import__("unittest").mock.MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        pg.revert()

def test_sdk_test_no_pytest_in_pyproject(tmp_path):
    """Test function."""
    (tmp_path / "pyproject.toml").write_text("some random content")
    pg = PyGradeup(str(tmp_path))
    with patch("subprocess.run") as mock_run:
        mock_result = __import__("unittest").mock.MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        pg.test()

def test_sdk_test_no_pytest_in_reqs_dev(tmp_path):
    """Test function."""
    (tmp_path / "requirements-dev.txt").write_text("requests==2.0.0")
    pg = PyGradeup(str(tmp_path))
    with patch("subprocess.run") as mock_run:
        mock_result = __import__("unittest").mock.MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        pg.test()

def test_sdk_find_target_python_cleanup(tmp_path):
    """Test function."""
    pg = PyGradeup(str(tmp_path))
    with patch("py_gradeup.sdk._get_current_python_version", return_value="3.8"), patch("py_gradeup.core._prepare_compile_targets", return_value=["/does/not/exist/999"]):
        (tmp_path / "fake.txt").touch()
        with patch("py_gradeup.sdk._get_target_files", return_value=[str(tmp_path / "fake.txt")]):
            pg.audit()

def test_sdk_graph_cleanup_not_exists(tmp_path):
    """Test function."""
    (tmp_path / "requirements.txt").write_text("requests==2.0.0\n")
    pg = PyGradeup(str(tmp_path))
    def side_effect(*args, **kwargs):
        """Docstring."""
        import contextlib
        import glob
        import tempfile
        for f in glob.glob(os.path.join(tempfile.gettempdir(), "*.in")):
            with contextlib.suppress(Exception):
                os.remove(f)
        mock_result = __import__("unittest").mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "tree"
        return mock_result
    with patch("subprocess.run", side_effect=side_effect):
        pg.graph()

def test_core_empty_config_files(tmp_path):
    """Test function."""
    (tmp_path / "setup.cfg").touch()
    (tmp_path / "setup.py").touch()
    (tmp_path / "Pipfile").touch()
    (tmp_path / "environment.yml").touch()
    (tmp_path / "setup.cfg").write_text("random line\n")
    (tmp_path / "setup.py").write_text("random line\n")
    (tmp_path / "Pipfile").write_text("random line\n")
    (tmp_path / "environment.yml").write_text("random line\n")
    assert core._get_current_python_version(str(tmp_path)) == "3.8"

def test_core_update_bounds_no_match(tmp_path):
    """Test function."""
    (tmp_path / "setup.cfg").write_text("random line\n")
    (tmp_path / "setup.py").write_text("random line\n")
    (tmp_path / "Pipfile").write_text("random line\n")
    (tmp_path / "environment.yml").write_text("random line\n")
    assert core._update_python_version_bounds(str(tmp_path), "3.9") is False

def test_core_update_bounds_dry_run(tmp_path):
    """Test function."""
    (tmp_path / "Pipfile").write_text("python_version = \"3.8\"\n")
    (tmp_path / "environment.yml").write_text("- python >= 3.8\n")
    assert core._update_python_version_bounds(str(tmp_path), "3.9", dry_run=True) is True

def test_core_get_target_files_no_workspace(tmp_path):
    """Test function."""
    (tmp_path / "requirements.txt").touch()
    assert len(core._get_target_files(str(tmp_path), workspace=False)) == 1

def test_core_get_target_files_not_exists():
    """Test function."""
    assert core._get_target_files("/does/not/exist/dir") == []

def test_core_get_targets_requirements_regex(tmp_path):
    """Test function."""
    (tmp_path / "requirements-123.txt").touch()
    assert core._get_target_files(str(tmp_path), workspace=True) == []

def test_core_prepare_compile_targets_empty_version(tmp_path):
    """Test function."""
    lock_file = tmp_path / "Pipfile.lock"
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({"default": {"pkg1": {"version": ""}}}, f)
    core._prepare_compile_targets([str(lock_file)], [])

def test_core_prepare_compile_targets_package_match(tmp_path):
    """Test function."""
    lock_file = tmp_path / "poetry.lock"
    with open(lock_file, "w", encoding="utf-8") as f:
        f.write("[[package]]\nname = \"pkg1\"\n# [[package]]\nversion = \"1.0.0\"")
    core._prepare_compile_targets([str(lock_file)], [])

def test_core_update_python_classifiers_no_change(tmp_path):
    """Test function."""
    (tmp_path / "setup.py").write_text("Programming Language :: Python :: 3.8\n")
    core._update_python_classifiers(str(tmp_path), "3.8")

def test_core_update_dockerfiles_no_change(tmp_path):
    """Test function."""
    (tmp_path / "Dockerfile").write_text("FROM python:3.8\n")
    core._update_dockerfiles(str(tmp_path), "3.8")

def test_core_update_ci_cd_tox_branches(tmp_path):
    """Test function."""
    f = tmp_path / "tox.ini"
    f.write_text("envlist py38\n")
    core._update_ci_cd_environments(str(tmp_path), "3.9")
    f.write_text("envlist = py38\n")
    core._update_ci_cd_environments(str(tmp_path), "3.8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.txt").touch()
    core._update_ci_cd_environments(str(tmp_path), "3.9")
    (tmp_path / ".python-version").write_text("3.8\n")
    core._update_ci_cd_environments(str(tmp_path), "3.8")

def test_core_recreate_venv_no_dir(tmp_path):
    """Test function."""
    with __import__("unittest").mock.patch("subprocess.run"):
        core._recreate_venv(str(tmp_path), "3.8", versioned=True)

def test_core_run_test_env_unknown_backend(tmp_path):
    """Test function."""
    assert core._run_test_env(str(tmp_path), "3.8", "unknown", "pytest")[1] is False

def test_core_find_target_python_missing_name(tmp_path):
    """Test function."""
    mock_result = __import__("unittest").mock.MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"install": [{"metadata": {"name": "pkg1"}}, {"metadata": {"version": "1.0"}}, {"metadata": {}}]})
    def side_effect(cmd, **kwargs):
        """Docstring."""
        if "uv" in cmd: raise FileNotFoundError("no uv")
        return mock_result
    with patch("subprocess.run", side_effect=side_effect), patch("py_gradeup.core._prepare_compile_targets", return_value=["fake.in"]):
        core._find_target_python(["fake.txt"], "3.8")

def test_core_backup_old_requirements_missing_name(tmp_path):
    """Test function."""
    mock_result = __import__("unittest").mock.MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"install": [{"metadata": {"name": "pkg1"}}, {"metadata": {"version": "1.0"}}]})
    def side_effect(cmd, **kwargs):
        """Docstring."""
        if "uv" in cmd: raise FileNotFoundError("no uv")
        return mock_result
    with patch("subprocess.run", side_effect=side_effect), patch("py_gradeup.core._prepare_compile_targets", return_value=["fake.in"]):
        core._backup_old_requirements(str(tmp_path), "3.8", ["req.txt"])

def test_core_update_dockerfiles_false_branch(tmp_path):
    """Test function."""
    (tmp_path / "not-docker.txt").touch()
    (tmp_path / "Dockerfile.dev").touch()
    core._update_dockerfiles(str(tmp_path), "3.9")

def test_core_recreate_venv_missing_dir2(tmp_path):
    """Test function."""
    with __import__("unittest").mock.patch("subprocess.run"):
        core._recreate_venv(str(tmp_path), "3.8", versioned=True)

def test_core_find_target_python_cleanup_not_exists(tmp_path):
    """Test function."""
    def mock_prepare(files, tmp_paths):
        """Docstring."""
        tmp_paths.append("/does/not/exist/999")
        return ["fake.in"]
    mock_result = __import__("unittest").mock.MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '{"install": []}'
    with patch("subprocess.run", return_value=mock_result), patch("py_gradeup.core._prepare_compile_targets", side_effect=mock_prepare):
        core._find_target_python(["fake.txt"], "3.8")

def test_core_update_dockerfiles_not_exists(tmp_path):
    """Test function."""
    core._update_dockerfiles("/does/not/exist/1234", "3.9")

def test_core_recreate_venv_missing_dir_pyenv(tmp_path):
    """Test function."""
    def side_effect(cmd, **kwargs):
        """Docstring."""
        if "uv" in cmd: raise FileNotFoundError("no uv")
        mock_result = __import__("unittest").mock.MagicMock()
        mock_result.returncode = 0
        return mock_result
    with __import__("unittest").mock.patch("subprocess.run", side_effect=side_effect):
        core._recreate_venv(str(tmp_path), "3.8", versioned=True)
