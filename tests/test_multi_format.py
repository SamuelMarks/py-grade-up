"""Test module."""
# ruff: noqa: D100, F841
# ruff: noqa: D103, E501
import json
from unittest.mock import MagicMock, patch

from py_gradeup.core import (
    _find_target_python,
    _get_current_python_version,
    _get_target_files,
    _update_dependencies_file,
    _update_python_version_bounds,
)


def test_pipfile_version(tmp_path):
    """Test."""
    pf = tmp_path / "Pipfile"
    pf.write_text('python_version = "3.8"\n')
    assert _get_current_python_version(str(tmp_path)) == "3.8"


def test_env_yml_version(tmp_path):
    """Test."""
    env = tmp_path / "environment.yml"
    env.write_text("dependencies:\n  - python>=3.9\n")
    assert _get_current_python_version(str(tmp_path)) == "3.9"


def test_update_pipfile_bounds(tmp_path):
    """Test."""
    pf = tmp_path / "Pipfile"
    pf.write_text('python_version = "3.8"\n')
    _update_python_version_bounds(str(tmp_path), "3.10", dry_run=False)
    assert 'python_version = "3.10"' in pf.read_text()


def test_update_env_yml_bounds(tmp_path):
    """Test."""
    env = tmp_path / "environment.yaml"
    env.write_text("dependencies:\n  - python>=3.8\n")
    _update_python_version_bounds(str(tmp_path), "3.10", dry_run=False)
    assert "python>=3.10" in env.read_text()


def test_get_target_files_multi(tmp_path):
    """Test."""
    (tmp_path / "Pipfile").write_text("")
    (tmp_path / "uv.lock").write_text("")
    (tmp_path / "environment.yml").write_text("")
    targets = _get_target_files(str(tmp_path))
    assert len(targets) == 3


@patch("subprocess.run")
def test_find_target_python_pipfile_lock(mock_run, tmp_path):
    """Test."""
    lock = tmp_path / "Pipfile.lock"
    lock.write_text(json.dumps({"default": {"requests": {"version": "==2.31.0"}}}))
    mock_run.return_value = MagicMock(stdout="requests==2.32.0\n")
    v, deps = _find_target_python([str(lock)], "3.8")
    assert deps == {"requests": "2.32.0"}


def test_update_dependencies_pipfile(tmp_path):
    """Test."""
    pf = tmp_path / "Pipfile"
    pf.write_text('requests = "==2.31.0"\n')
    updates = _update_dependencies_file(str(pf), {"requests": "2.32.0"})
    assert 'requests = "==2.32.0"' in pf.read_text()


def test_update_dependencies_pipfile_lock(tmp_path):
    """Test."""
    lock = tmp_path / "Pipfile.lock"
    lock.write_text('{\n  "requests": {\n    "version": "==2.31.0"\n  }\n}')
    updates = _update_dependencies_file(str(lock), {"requests": "2.32.0"})
    assert '"version": "==2.32.0"' in lock.read_text()


def test_update_dependencies_env_yml(tmp_path):
    """Test."""
    env = tmp_path / "environment.yml"
    env.write_text("dependencies:\n  - requests>=2.31.0\n")
    updates = _update_dependencies_file(str(env), {"requests": "2.32.0"})
    assert "- requests>=2.32.0" in env.read_text()


@patch("subprocess.run")
def test_find_target_python_uv_lock(mock_run, tmp_path):
    """Test."""
    lock = tmp_path / "uv.lock"
    lock.write_text(
        '[[package]]\nname = "foo"\nversion = "1.0"\n[[package]]\nname="bar"\nversion="2.0"\n'
    )
    mock_run.return_value = MagicMock(stdout="foo==1.0\nbar==2.0\n")
    v, deps = _find_target_python([str(lock)], "3.8")
    assert deps == {"foo": "1.0", "bar": "2.0"}


@patch("subprocess.run")
def test_find_target_python_pipfile(mock_run, tmp_path):
    """Test."""
    pf = tmp_path / "Pipfile"
    pf.write_text('requests = "==2.31.0"\nfoo = ">=1.0"\n')
    mock_run.return_value = MagicMock(stdout="requests==2.31.0\nfoo==1.0\n")
    v, deps = _find_target_python([str(pf)], "3.8")
    assert deps == {"requests": "2.31.0", "foo": "1.0"}


@patch("subprocess.run")
def test_find_target_python_env_yml(mock_run, tmp_path):
    """Test."""
    env = tmp_path / "environment.yml"
    env.write_text("dependencies:\n  - python>=3.8\n  - requests>=2.31.0\n")
    mock_run.return_value = MagicMock(stdout="requests==2.31.0\n")
    v, deps = _find_target_python([str(env)], "3.8")
    assert deps == {"requests": "2.31.0"}
