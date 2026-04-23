# ruff: noqa: D103, E501
"""Test lock file operations."""

from unittest.mock import MagicMock, patch

from py_gradeup.core import (
    _find_target_python,
    _get_target_files,
    _update_dependencies_file,
)


def test_get_target_files_lock(tmp_path) -> None:
    """Test getting target files."""
    (tmp_path / "poetry.lock").write_text("")
    (tmp_path / "pdm.lock").write_text("")
    targets = _get_target_files(str(tmp_path))
    assert any("poetry.lock" in t for t in targets)
    assert any("pdm.lock" in t for t in targets)


@patch("subprocess.run")
def test_find_target_python_lock(mock_run, tmp_path) -> None:
    """Test finding target python lock."""
    lock_file = tmp_path / "poetry.lock"
    lock_file.write_text('[[package]]\nname = "certifi"\nversion = "2023.7.22"')

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "certifi==2024.1.1\n"
    mock_run.return_value = mock_res

    target, deps = _find_target_python([str(lock_file)], "3.8")
    assert target != "3.8"
    assert "certifi" in deps


def test_update_dependencies_file_lock(tmp_path) -> None:
    """Test updating lock deps."""
    lock_file = tmp_path / "poetry.lock"
    lock_file.write_text('[[package]]\nname = "certifi"\nversion = "2023.7.22"\n')

    updates = _update_dependencies_file(str(lock_file), {"certifi": "2024.1.1"})
    assert "certifi" in updates
    assert (
        lock_file.read_text() == '[[package]]\nname = "certifi"\nversion = "2024.1.1"\n'
    )
