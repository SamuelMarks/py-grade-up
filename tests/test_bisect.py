"""Tests for the bisect functionality."""

import os
from unittest.mock import MagicMock, patch

from py_gradeup.sdk import PyGradeup


def test_bisect_empty_changed_deps(tmp_path):
    """Test bisect when there are no changed dependencies."""
    old_file = tmp_path / "old.txt"
    new_file = tmp_path / "new.txt"

    old_file.write_text("pytest==1.0.0\n")
    new_file.write_text("pytest==1.0.0\n")

    pg = PyGradeup(str(tmp_path))
    res = pg.bisect("old.txt", "new.txt", "pytest")
    assert res.culprit is None


@patch("subprocess.run")
def test_bisect_success(mock_run, tmp_path):
    """Test a successful bisect operation."""
    old_file = tmp_path / "old.txt"
    new_file = tmp_path / "new.txt"

    old_file.write_text("A==1.0.0\nB==1.0.0\nC==1.0.0\n")
    new_file.write_text("A==2.0.0\nB==2.0.0\nC==2.0.0\n")

    pg = PyGradeup(str(tmp_path))

    def side_effect(cmd, **kwargs):
        """Mock side effect for subprocess.run."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        # Check if it's the test command
        if cmd == ["pytest"]:
            env_dir = kwargs.get("env", {}).get("VIRTUAL_ENV", "")
            req_path = os.path.join(env_dir, "test_reqs.txt")
            if True:
                with open(req_path, encoding="utf-8") as f:
                    content = f.read()
                    if "c==2.0.0" in content.lower():
                        mock_result.returncode = 1

        return mock_result

    mock_run.side_effect = side_effect

    res = pg.bisect("old.txt", "new.txt", "pytest")
    assert res.culprit == "c"
    assert res.old_version == "1.0.0"
    assert res.new_version == "2.0.0"


@patch("subprocess.run")
def test_bisect_all_pass(mock_run, tmp_path):
    """Test bisect where all dependencies pass the test."""
    old_file = tmp_path / "old.txt"
    new_file = tmp_path / "new.txt"

    old_file.write_text("A==1.0.0\n")
    new_file.write_text("A==2.0.0\n")

    pg = PyGradeup(str(tmp_path))

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    res = pg.bisect("old.txt", "new.txt", "pytest")
    assert res.culprit is None


@patch("subprocess.run")
def test_bisect_install_fail(mock_run, tmp_path):
    """Test bisect where dependency installation fails."""
    old_file = tmp_path / "old.txt"
    new_file = tmp_path / "new.txt"

    old_file.write_text("A==1.0.0\n")
    new_file.write_text("A==2.0.0\n")

    pg = PyGradeup(str(tmp_path))

    def side_effect(cmd, **kwargs):
        """Mock side effect for subprocess.run."""
        mock_result = MagicMock()
        if "install" in cmd:
            mock_result.returncode = 1
        else:
            mock_result.returncode = 0
        return mock_result

    mock_run.side_effect = side_effect

    res = pg.bisect("old.txt", "new.txt", "pytest")
    assert res.culprit == "a"


@patch("subprocess.run")
def test_bisect_venv_fallback(mock_run, tmp_path):
    """Test bisect falls back to python -m venv if uv is missing."""
    old_file = tmp_path / "old.txt"
    new_file = tmp_path / "new.txt"

    old_file.write_text("A==1.0.0\n")
    new_file.write_text("A==2.0.0\n")

    pg = PyGradeup(str(tmp_path))

    def side_effect(cmd, **kwargs):
        """Mock side effect for subprocess.run."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        if cmd[0] == "uv":
            raise FileNotFoundError("uv not found")
        return mock_result

    mock_run.side_effect = side_effect

    res = pg.bisect("old.txt", "new.txt", "pytest")
    assert res.culprit is None
