"""Tests for workspace support."""

from py_gradeup.sdk import PyGradeup


def test_workspace_full(tmp_path):
    """Test."""
    # Create a workspace
    # Root
    (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.8"\n')
    (tmp_path / "tox.ini").write_text("[tox]\nenvlist = py38\n")

    # Subdir
    sub = tmp_path / "subpkg"
    sub.mkdir()
    (sub / "pyproject.toml").write_text('requires-python = ">=3.8"\n')
    (sub / "Dockerfile").write_text("FROM python:3.8\n")
    (sub / ".gitlab-ci.yml").write_text("image: python:3.8\n")
    (sub / "setup.py").write_text("python_requires='>=3.8',\n")

    # Ignored dir
    venv = tmp_path / "venv"
    venv.mkdir()
    (venv / "pyproject.toml").write_text('requires-python = ">=3.8"\n')

    # SDK with workspace
    gradeup = PyGradeup(str(tmp_path), workspace=True)
    res = gradeup.audit()
    assert len(res.files_to_upgrade) == 0
    assert "3.14" in res.target_version or "3.8" in res.target_version

    # Fix
    gradeup.fix(run_tests=False)

    # Check changes
    assert "3." in (sub / "pyproject.toml").read_text()
    assert "3." in (sub / "Dockerfile").read_text()
    assert "3." in (sub / ".gitlab-ci.yml").read_text()
    assert "3." in (sub / "setup.py").read_text()


def test_workspace_files(tmp_path):
    """Test."""
    from py_gradeup.core import (
        _get_target_files,
        _update_ci_cd_environments,
        _update_dockerfiles,
        _update_python_classifiers,
        _update_python_version_bounds,
    )

    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "requirements.txt").write_text("pkg==1.0")
    (sub / "setup.cfg").write_text("python_requires = >=3.8\n")
    (sub / "Pipfile").write_text('python_version = "3.8"\n')
    (sub / "environment.yml").write_text("- python >= 3.8\n")
    (sub / "app.Dockerfile").write_text("FROM python:3.8")

    # ci cd
    (sub / "noxfile.py").write_text('python_versions=["3.8"]\n')
    (sub / ".gitlab-ci.yml").write_text("image: python:3.8\n")
    (sub / "tox.ini").write_text("[tox]\nenvlist = py38\n")
    (sub / ".pre-commit-config.yaml").write_text("language_version: python3.8\n")

    # Python classifiers
    c = 'classifiers = [\n    "Programming Language :: Python :: 3.8"\n]\n'
    (sub / "pyproject.toml").write_text(c)

    targets = _get_target_files(str(tmp_path), workspace=True)
    assert len(targets) > 0

    _update_dockerfiles(str(tmp_path), "3.10", workspace=True)
    assert "3.10" in (sub / "app.Dockerfile").read_text()

    _update_ci_cd_environments(str(tmp_path), "3.10", workspace=True)
    assert "3.10" in (sub / "noxfile.py").read_text()
    assert "3.10" in (sub / ".gitlab-ci.yml").read_text()
    assert "py310" in (sub / "tox.ini").read_text()
    assert "3.10" in (sub / ".pre-commit-config.yaml").read_text()

    _update_python_classifiers(str(tmp_path), "3.10", workspace=True)
    assert "3.10" in (sub / "pyproject.toml").read_text()

    _update_python_version_bounds(str(tmp_path), "3.10", workspace=True)
    assert "3.10" in (sub / "setup.cfg").read_text()
    assert "3.10" in (sub / "Pipfile").read_text()
    assert "3.10" in (sub / "environment.yml").read_text()


def test_workspace_tox_continue(tmp_path):
    """Test."""
    from py_gradeup.core import _update_ci_cd_environments

    # Workspace=False, tox.ini does not exist
    _update_ci_cd_environments(str(tmp_path), "3.10", workspace=False)


def test_workspace_tox_continue2(tmp_path):
    """Test."""
    from py_gradeup.core import _update_ci_cd_environments

    tox_file = tmp_path / "tox.ini"
    tox_file.write_text("[tox]\n")
    # tox.ini exists, but only=["Dockerfile"] so it skips
    _update_ci_cd_environments(
        str(tmp_path), "3.10", workspace=False, only=["Dockerfile"]
    )
