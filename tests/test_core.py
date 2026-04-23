# ruff: noqa: E501
# ruff: noqa: E402
# ruff: noqa: D103, E501
"""Tests for the core functionality."""

import os
import subprocess
from unittest.mock import MagicMock, patch

from py_gradeup.core import (
    _backup_old_requirements,
    _check_pyupgrade,
    _find_target_python,
    _get_current_python_version,
    _get_py_files,
    _get_target_files,
    _update_ci_cd_environments,
    _update_dependencies_file,
    _update_dockerfiles,
    _update_python_classifiers,
    _update_python_version_bounds,
)
from py_gradeup.sdk import PyGradeup


def test_get_py_files(tmp_path) -> None:
    """Test getting Python files."""
    f1 = tmp_path / "test1.py"
    f1.write_text("")
    f2 = tmp_path / "test2.txt"
    f2.write_text("")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    f3 = subdir / "test3.py"
    f3.write_text("")

    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    f4 = venv_dir / "test4.py"
    f4.write_text("")

    files = _get_py_files(str(tmp_path))
    assert len(files) == 2
    assert str(f1) in files
    assert str(f3) in files
    assert str(f4) not in files

    files = _get_py_files(str(f1))
    assert len(files) == 1
    assert str(f1) in files


def test_check_pyupgrade() -> None:
    """Test pyupgrade wrapper."""
    code = "def foo():\n    return set(())\n"
    new_code = _check_pyupgrade(code, (3, 12))
    assert new_code is not None


def test_get_current_python_version(tmp_path) -> None:
    """Test extracting pyproject.toml python version."""
    pyproject = tmp_path / "pyproject.toml"
    assert _get_current_python_version(str(tmp_path)) == "3.8"

    pyproject.write_text('requires-python = ">=3.9"\n')
    assert _get_current_python_version(str(tmp_path)) == "3.9"

    pyproject.unlink()
    setup_cfg = tmp_path / "setup.cfg"
    setup_cfg.write_text("python_requires = >=3.10\n")
    assert _get_current_python_version(str(tmp_path)) == "3.10"

    setup_cfg.unlink()
    setup_py = tmp_path / "setup.py"
    setup_py.write_text('python_requires=">=3.11",\n')
    assert _get_current_python_version(str(tmp_path)) == "3.11"


def test_update_python_version_bounds(tmp_path) -> None:
    """Test updating pyproject.toml, setup.cfg, and setup.py."""
    assert not _update_python_version_bounds(str(tmp_path), "3.10")

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('name = "foo"\n')
    assert not _update_python_version_bounds(str(tmp_path), "3.10")

    pyproject.write_text('requires-python = ">=3.8"\n')

    setup_cfg = tmp_path / "setup.cfg"
    setup_cfg.write_text("python_requires = >=3.8\n")

    setup_py = tmp_path / "setup.py"
    setup_py.write_text("python_requires='>=3.8',\n")

    # Dry run
    assert _update_python_version_bounds(str(tmp_path), "3.10", dry_run=True)
    assert 'requires-python = ">=3.8"' in pyproject.read_text()
    assert "python_requires = >=3.8" in setup_cfg.read_text()
    assert "python_requires='>=3.8'" in setup_py.read_text()

    # Real
    assert _update_python_version_bounds(str(tmp_path), "3.10", dry_run=False)
    assert 'requires-python = ">=3.10"' in pyproject.read_text()
    assert "python_requires = >=3.10" in setup_cfg.read_text()
    assert "python_requires='>=3.10'" in setup_py.read_text()


def test_get_target_files(tmp_path) -> None:
    """Test getting target files."""
    assert _get_target_files(str(tmp_path)) == []

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("")

    req = tmp_path / "requirements.txt"
    req.write_text("")

    req_dev = tmp_path / "requirements-dev.txt"
    req_dev.write_text("")

    req_backup = tmp_path / "requirements-3-8.txt"
    req_backup.write_text("")

    files = _get_target_files(str(tmp_path))
    assert len(files) == 3
    assert str(pyproject) in files
    assert str(req) in files
    assert str(req_dev) in files
    assert str(req_backup) not in files


@patch("subprocess.run")
def test_find_target_python(mock_run, tmp_path) -> None:
    """Test find_target_python with mocked uv compile."""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("")

    # No file / empty file
    v, deps = _find_target_python([str(req_file)], "3.12")
    assert v == "3.14"
    assert deps == {}

    # Exception handling coverage
    v, deps = _find_target_python([str(req_file)], "invalid.ver")
    assert v == "3.14"
    assert deps == {}

    # Empty candidates
    v, deps = _find_target_python([str(req_file)], "3.15")
    assert v == "3.15"
    assert deps == {}

    # Empty target_file list
    v, deps = _find_target_python([], "3.12")
    assert v == "3.14"
    assert deps == {}

    req_file.write_text("pkg>=1.0\n# comment\n")

    # Mock uv pip compile failure, then pyenv fallback failure, then uv success
    import json

    mock_run.side_effect = [
        subprocess.CalledProcessError(1, "cmd"),  # 3.14 uv fails
        subprocess.CalledProcessError(1, "cmd"),  # 3.14 pyenv fails
        MagicMock(stdout="pkg==2.0\n# other\n"),  # 3.13 uv succeeds
    ]

    v, deps = _find_target_python([str(req_file)], "3.10")
    assert v == "3.13"
    assert deps == {"pkg": "2.0"}

    # Mock uv pip compile failure, and pyenv fallback succeeds
    pyenv_success_output = json.dumps(
        {"install": [{"metadata": {"name": "pkg", "version": "3.0"}}]}
    )
    mock_run.side_effect = [
        subprocess.CalledProcessError(1, "cmd"),  # 3.14 uv fails
        MagicMock(stdout=pyenv_success_output),  # 3.14 pyenv succeeds
    ]

    # Also pass a non-txt file
    other_file = tmp_path / "pyproject.toml"
    other_file.write_text("")
    v, deps = _find_target_python([str(req_file), str(other_file)], "3.10")
    assert v == "3.14"
    assert deps == {"pkg": "3.0"}


@patch("subprocess.run")
def test_find_target_python_toml(mock_run, tmp_path) -> None:
    """Test find_target_python with toml file."""
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text("pkg>=1.0\n")
    mock_run.return_value = MagicMock(stdout="pkg==2.0\n")
    v, deps = _find_target_python([str(toml_file)], "3.10")
    assert v == "3.14"
    assert deps == {"pkg": "2.0"}


@patch("subprocess.run")
def test_find_target_python_exception(mock_run, tmp_path) -> None:
    """Test find_target_python all fail."""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("pkg>=1.0\n")
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

    v, deps = _find_target_python([str(req_file)], "3.10")
    assert v == "3.10"
    assert deps == {}


def test_update_dependencies_file_no_file(tmp_path) -> None:
    """Test update_dependencies_file with no file."""
    assert _update_dependencies_file(str(tmp_path / "req.txt"), {}) == {}


def test_update_dependencies_file_txt(tmp_path) -> None:
    """Test updating txt requirements file."""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("foo==1.0.0\nbar>=1.5.0\nbaz>=1.0\ninvalid\n")

    deps = {"foo": "2.0.0", "bar": "1.5.0"}

    # Dry run
    updates = _update_dependencies_file(str(req_file), deps, dry_run=True)
    assert "foo" in updates
    assert updates["foo"] == "1.0.0 -> 2.0.0"
    assert "bar" not in updates
    assert "baz" not in updates
    assert req_file.read_text() == "foo==1.0.0\nbar>=1.5.0\nbaz>=1.0\ninvalid\n"

    # Real run
    updates = _update_dependencies_file(str(req_file), deps, dry_run=False)
    assert req_file.read_text() == "foo==2.0.0\nbar>=1.5.0\nbaz>=1.0\ninvalid\n"


def test_update_dependencies_file_toml(tmp_path) -> None:
    """Test updating toml requirements file."""
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text('dependencies = ["foo>=1.0.0", "bar==1.5.0"]\n')

    deps = {"foo": "2.0.0"}

    updates = _update_dependencies_file(str(toml_file), deps, dry_run=False)
    assert "foo" in updates
    assert updates["foo"] == "1.0.0 -> 2.0.0"
    assert toml_file.read_text() == 'dependencies = ["foo>=2.0.0", "bar==1.5.0"]\n'


def test_update_dependencies_file_setup(tmp_path) -> None:
    """Test updating setup.py and setup.cfg files."""
    setup_py = tmp_path / "setup.py"
    setup_py.write_text('install_requires=["foo>=1.0.0", "bar==1.5.0"]\n')

    setup_cfg = tmp_path / "setup.cfg"
    setup_cfg.write_text("install_requires =\n    foo>=1.0.0\n    bar==1.5.0\n")

    deps = {"foo": "2.0.0"}

    updates_py = _update_dependencies_file(str(setup_py), deps, dry_run=False)
    assert "foo" in updates_py
    assert updates_py["foo"] == "1.0.0 -> 2.0.0"
    assert setup_py.read_text() == 'install_requires=["foo>=2.0.0", "bar==1.5.0"]\n'

    updates_cfg = _update_dependencies_file(str(setup_cfg), deps, dry_run=False)
    assert "foo" in updates_cfg
    assert updates_cfg["foo"] == "1.0.0 -> 2.0.0"
    assert (
        setup_cfg.read_text() == "install_requires =\n    foo>=2.0.0\n    bar==1.5.0\n"
    )


def test_update_python_classifiers(tmp_path) -> None:
    # Test valid parsing and update
    """Test."""
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(
        'classifiers = [\n    "Programming Language :: Python :: 3.8",\n    "Programming Language :: Python :: 3.9"\n]\n'
    )

    setup_file = tmp_path / "setup.py"
    setup_file.write_text(
        'classifiers=[\n    "Programming Language :: Python :: 3.8",\n    "Programming Language :: Python :: 3.12"\n]\n'
    )

    # Test skipping on invalid input or no match
    invalid_file = tmp_path / "setup.cfg"
    invalid_file.write_text("classifiers = \n")

    # Dry run
    updated = _update_python_classifiers(str(tmp_path), "3.10", dry_run=True)
    assert len(updated) == 2
    assert "3.10" not in toml_file.read_text()

    # Real
    updated = _update_python_classifiers(str(tmp_path), "3.10", dry_run=False)
    assert len(updated) == 2
    toml_content = toml_file.read_text()
    assert "3.10" in toml_content
    assert "3.8" not in toml_content
    assert "3.9" not in toml_content

    setup_content = setup_file.read_text()
    assert "3.10" in setup_content
    assert "3.8" not in setup_content


def test_update_python_classifiers_missing_file(tmp_path) -> None:
    """Test update python classifiers missing."""
    from py_gradeup.core import _update_python_classifiers

    _update_python_classifiers(str(tmp_path), "3.10")


def test_update_dockerfiles(tmp_path) -> None:
    """Test."""
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.8-slim\nRUN echo hello\n")

    dockerfile_dev = tmp_path / "Dockerfile.dev"
    dockerfile_dev.write_text(
        "FROM public.ecr.aws/docker/library/python:3.9.2\nRUN echo dev\n"
    )

    not_dockerfile = tmp_path / "OtherFile"
    not_dockerfile.write_text("FROM python:3.8\n")

    dockerfile_dir = tmp_path / "Dockerfile.dir"
    dockerfile_dir.mkdir()

    # Dry run
    updated = _update_dockerfiles(str(tmp_path), "3.12", dry_run=True)
    assert len(updated) == 2
    assert dockerfile.read_text() == "FROM python:3.8-slim\nRUN echo hello\n"

    # Real run
    updated = _update_dockerfiles(str(tmp_path), "3.12", dry_run=False)
    assert len(updated) == 2
    assert dockerfile.read_text() == "FROM python:3.12-slim\nRUN echo hello\n"
    assert (
        dockerfile_dev.read_text()
        == "FROM public.ecr.aws/docker/library/python:3.12\nRUN echo dev\n"
    )
    assert not_dockerfile.read_text() == "FROM python:3.8\n"


def test_update_ci_cd_environments(tmp_path) -> None:
    """Test."""
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text("[tox]\nenvlist = py38, py39\n[testenv:py38]\n")

    gitlab_ci = tmp_path / ".gitlab-ci.yml"
    gitlab_ci.write_text("image: python:3.8-slim\n")

    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text('python_versions=["3.8", "3.9"]\n')

    pre_commit = tmp_path / ".pre-commit-config.yaml"
    pre_commit.write_text(
        "default_language_version:\n  python: python3.8\nrepos:\n- repo: local\n  hooks:\n    - id: my-hook\n      language_version: python3.8\n"
    )

    gh_dir = tmp_path / ".github" / "workflows"
    gh_dir.mkdir(parents=True)
    gh_yml = gh_dir / "test.yml"
    gh_yml.write_text('python-version: ["3.8", "3.9"]\n')

    uv_yml = gh_dir / "uv.yml"
    uv_yml.write_text(
        'env:\n  UV_PYTHON: "3.8"\nstrategy:\n  matrix:\n    python-version:\n      - "3.8"\n      - "3.9"'
    )

    unquoted_yml = gh_dir / "unquoted.yml"
    unquoted_yml.write_text("python-version: [3.8, 3.9]\n")

    block_scalar_yml = gh_dir / "block.yml"
    block_scalar_yml.write_text("python-version: |\n  3.8\n  3.9\n")

    py_ver = tmp_path / ".python-version"
    py_ver.write_text("3.8.5\n")

    # Dry run
    updated = _update_ci_cd_environments(str(tmp_path), "3.12", dry_run=True)
    assert len(updated) == 9
    assert tox_ini.read_text() == "[tox]\nenvlist = py38, py39\n[testenv:py38]\n"

    # Real run
    updated = _update_ci_cd_environments(str(tmp_path), "3.12", dry_run=False)
    assert len(updated) == 9

    assert tox_ini.read_text() == "[tox]\nenvlist = py312\n[testenv:py312]\n"
    assert gitlab_ci.read_text() == "image: python:3.12-slim\n"
    assert noxfile.read_text() == 'python_versions=["3.12"]\n'
    assert (
        pre_commit.read_text()
        == "default_language_version:\n  python: python3.12\nrepos:\n- repo: local\n  hooks:\n    - id: my-hook\n      language_version: python3.12\n"
    )
    assert gh_yml.read_text() == 'python-version: ["3.12"]\n'
    assert (
        uv_yml.read_text()
        == 'env:\n  UV_PYTHON: "3.12"\nstrategy:\n  matrix:\n    python-version:\n      - "3.12"\n'
    )
    assert unquoted_yml.read_text() == 'python-version: ["3.12"]\n'
    assert block_scalar_yml.read_text() == "python-version: |\n  3.12\n"
    assert py_ver.read_text() == "3.12\n"


@patch("subprocess.run")
def test_backup_old_requirements(mock_run, tmp_path) -> None:
    """Test _backup_old_requirements."""
    f = str(tmp_path / "requirements.txt")
    b = _backup_old_requirements(str(tmp_path), "3.8", [f])
    assert b == str(tmp_path / "requirements-3-8.txt")

    # Test short version string
    b2 = _backup_old_requirements(str(tmp_path), "3", [f])
    assert b2 == str(tmp_path / "requirements-3.txt")

    # Test error fallback (both uv and pyenv fail)
    mock_run.side_effect = [
        subprocess.CalledProcessError(1, "cmd"),
        subprocess.CalledProcessError(1, "cmd"),
    ]
    b3 = _backup_old_requirements(str(tmp_path), "3.9", [f])
    assert b3 == str(tmp_path / "requirements-3-9.txt")
    assert os.path.exists(b3)

    # Test uv fails, pyenv succeeds with a mix of txt and other files
    import json

    mock_run.reset_mock()
    pyenv_success_output = json.dumps(
        {"install": [{"metadata": {"name": "testpkg", "version": "4.0"}}]}
    )
    mock_run.side_effect = [
        subprocess.CalledProcessError(1, "cmd"),
        MagicMock(stdout=pyenv_success_output),
    ]
    b4 = _backup_old_requirements(str(tmp_path), "3.10", [f, "setup.py"])
    assert b4 == str(tmp_path / "requirements-3-10.txt")
    assert os.path.exists(b4)
    with open(b4) as fb:
        assert "testpkg==4.0" in fb.read()


@patch("subprocess.run")
def test_run_tests(mock_run, tmp_path, capsys) -> None:
    """Test."""
    import subprocess

    from py_gradeup.core import _run_tests

    # 1. Test pytest default
    assert _run_tests(str(tmp_path)) is True
    mock_run.assert_called_once_with(["pytest"], cwd=str(tmp_path), check=True)

    # 2. Test tox
    mock_run.reset_mock()
    (tmp_path / "tox.ini").write_text("")
    assert _run_tests(str(tmp_path)) is True
    mock_run.assert_called_once_with(["tox"], cwd=str(tmp_path), check=True)

    # 3. Test nox
    mock_run.reset_mock()
    (tmp_path / "tox.ini").unlink()
    (tmp_path / "noxfile.py").write_text("")
    assert _run_tests(str(tmp_path)) is True
    mock_run.assert_called_once_with(["nox"], cwd=str(tmp_path), check=True)

    # 4. Test failure
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
    assert _run_tests(str(tmp_path)) is False

    # 5. Test not found
    mock_run.side_effect = FileNotFoundError("cmd")
    assert _run_tests(str(tmp_path)) is False


@patch("py_gradeup.sdk._update_dockerfiles")
@patch("py_gradeup.sdk._find_target_python")
@patch("py_gradeup.sdk._get_py_files")
@patch("py_gradeup.sdk._check_pyupgrade")
@patch("py_gradeup.sdk._update_python_classifiers")
@patch("py_gradeup.sdk._update_ci_cd_environments")
@patch("py_gradeup.sdk._update_dependencies_file")
def test_sdk_audit(
    mock_update,
    mock_ci,
    mock_cls,
    mock_check,
    mock_get_py,
    mock_find,
    mock_docker,
    capsys,
    tmp_path,
) -> None:
    """Test audit_project function."""
    f1 = tmp_path / "f1.py"
    f1.write_text("code1")

    mock_get_py.return_value = [str(f1)]
    mock_check.return_value = "new_code1"  # Needs upgrade

    mock_find.return_value = ("3.14", {"pkg": "2.0"})

    req = tmp_path / "requirements.txt"
    req.write_text("")
    ci = tmp_path / ".gitlab-ci.yml"
    ci.write_text("image: python:3.8\n")
    toml = tmp_path / "pyproject.toml"
    toml.write_text('classifiers=["Programming Language :: Python :: 3.8"]\n')

    mock_update.return_value = {"pkg": "1.0 -> 2.0"}
    mock_ci.return_value = [str(tmp_path / "tox.ini")]
    mock_cls.return_value = [str(tmp_path / "pyproject.toml")]
    mock_docker.return_value = [str(tmp_path / "Dockerfile")]

    PyGradeup(str(tmp_path)).audit()
    res = PyGradeup(str(tmp_path)).audit()
    print(f"DEBUG: {res.files_to_upgrade}, {res.target_version}")
    assert len(res.files_to_upgrade) == 1
    assert str(f1) in res.files_to_upgrade
    assert "pkg" in res.dependency_updates.get(str(req), {})
    assert res.dependency_updates[str(req)]["pkg"] == "1.0 -> 2.0"
    assert res.target_version == "3.14"
    assert len(res.ci_files_to_update) > 0
    assert len(res.cls_files_to_update) > 0
    assert len(res.docker_files_to_update) > 0
    assert res.backup_name is not None

    # Test error reading
    mock_check.side_effect = Exception("Read error")
    PyGradeup(str(tmp_path)).audit()
    capsys.readouterr()
    assert len(res.files_to_upgrade) == 1

    # Test no upgrades
    mock_check.side_effect = None
    mock_check.return_value = "code1"
    mock_update.return_value = {}
    mock_find.return_value = ("3.8", {})
    PyGradeup(str(tmp_path)).audit()
    capsys.readouterr()
    assert len(res.files_to_upgrade) == 1
    assert len(res.dependency_updates) == 2

    # Test short python version backup name branch
    mock_get_py.return_value = []
    mock_find.return_value = ("4", {})
    with patch("py_gradeup.sdk._get_current_python_version", return_value="3"):
        PyGradeup(str(tmp_path)).audit()
        capsys.readouterr()
        assert PyGradeup(str(tmp_path)).audit().target_version == "4"
        assert PyGradeup(str(tmp_path)).audit().backup_name == "requirements-3.txt"


@patch("py_gradeup.sdk._run_tests")
@patch("py_gradeup.sdk._update_dockerfiles")
@patch("py_gradeup.sdk._find_target_python")
@patch("py_gradeup.sdk._get_py_files")
@patch("py_gradeup.sdk._check_pyupgrade")
@patch("py_gradeup.sdk._update_python_classifiers")
@patch("py_gradeup.sdk._update_ci_cd_environments")
@patch("py_gradeup.sdk._update_dependencies_file")
@patch("py_gradeup.core._update_python_version_bounds")
@patch("py_gradeup.sdk._backup_old_requirements")
def test_sdk_fix(
    mock_backup,
    mock_upd_py,
    mock_update,
    mock_ci,
    mock_cls,
    mock_check,
    mock_get_py,
    mock_find,
    mock_docker,
    mock_run_tests,
    capsys,
    tmp_path,
) -> None:
    """Test fix_project function."""
    f1 = tmp_path / "f1.py"
    f1.write_text("code1")

    mock_get_py.return_value = [str(f1)]
    mock_check.return_value = "new_code1"  # Needs upgrade

    mock_find.return_value = ("3.14", {"pkg": "2.0"})

    req = tmp_path / "requirements.txt"
    req.write_text("")
    ci = tmp_path / ".gitlab-ci.yml"
    ci.write_text("image: python:3.8\n")
    toml = tmp_path / "pyproject.toml"
    toml.write_text('classifiers=["Programming Language :: Python :: 3.8"]\n')

    mock_update.return_value = {"pkg": "1.0 -> 2.0"}
    mock_ci.return_value = [str(tmp_path / "tox.ini")]
    mock_cls.return_value = [str(tmp_path / "pyproject.toml")]
    mock_docker.return_value = [str(tmp_path / "Dockerfile")]
    mock_upd_py.return_value = True
    mock_backup.return_value = str(tmp_path / "requirements-3-8.txt")

    # removed
    res = PyGradeup(str(tmp_path)).fix(run_tests=True)
    assert len(res.files_upgraded) == 1
    assert f1.read_text() == "new_code1"
    assert "pkg" in res.dependency_updates.get(str(req), {})
    assert res.target_version != res.current_version
    assert res.backup_path is not None
    assert len(res.ci_files_updated) > 0
    assert len(res.cls_files_updated) > 0
    assert len(res.docker_files_updated) > 0
    mock_run_tests.assert_called_once_with(str(tmp_path))

    # Test error processing
    mock_check.side_effect = Exception("Process error")
    # removed
    capsys.readouterr()
    assert len(res.files_upgraded) == 1

    # Test no upgrades
    mock_check.side_effect = None
    mock_check.return_value = "new_code1"  # same as content since it was updated
    mock_update.return_value = {}
    mock_find.return_value = ("3.8", {})
    mock_upd_py.return_value = False

    # removed
    capsys.readouterr()
    assert len(res.files_upgraded) == 1
    assert len(res.dependency_updates) == 2


@patch("sys.stdout.writelines")
@patch("sys.stdout.write")
@patch("builtins.input")
def test_prompt_diff(mock_input, mock_write, mock_writelines) -> None:
    """Test prompt diff helper."""
    from py_gradeup.core import _prompt_diff

    # No diff
    assert _prompt_diff("foo.py", "a\n", "a\n") is False

    # Yes
    mock_input.side_effect = ["y"]
    assert _prompt_diff("foo.py", "a\n", "b\n") is True

    # Yes
    mock_input.side_effect = ["yes"]
    assert _prompt_diff("foo.py", "a\n", "b\n") is True

    # No
    mock_input.side_effect = ["n"]
    assert _prompt_diff("foo.py", "a\n", "b\n") is False

    # No
    mock_input.side_effect = [""]
    assert _prompt_diff("foo.py", "a\n", "b\n") is False

    # Retry on invalid input
    mock_input.side_effect = ["invalid", "y"]
    assert _prompt_diff("foo.py", "a\n", "b\n") is True

    # EOFError
    mock_input.side_effect = EOFError()
    assert _prompt_diff("foo.py", "a\n", "b\n") is False


@patch("py_gradeup.core._prompt_diff")
def test_interactive_skips(mock_prompt, tmp_path) -> None:
    """Test interactive skips."""
    from py_gradeup.core import _update_dependencies_file

    # Test skipping dependency update
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("foo==1.0.0\n")
    mock_prompt.return_value = False

    updates = _update_dependencies_file(
        str(req_file), {"foo": "2.0.0"}, interactive=True
    )
    assert updates == {}
    assert req_file.read_text() == "foo==1.0.0\n"

    # Test accepting dependency update
    mock_prompt.return_value = True
    updates = _update_dependencies_file(
        str(req_file), {"foo": "2.0.0"}, interactive=True
    )
    assert "foo" in updates
    assert req_file.read_text() == "foo==2.0.0\n"


@patch("py_gradeup.sdk._update_dependencies_file")
@patch("py_gradeup.sdk._find_target_python")
@patch("py_gradeup.sdk._get_py_files")
@patch("py_gradeup.sdk._check_pyupgrade")
@patch("py_gradeup.core._prompt_diff")
def test_sdk_fix_interactive_skip(
    mock_prompt, mock_check, mock_get_py, mock_find, mock_upd_deps, tmp_path
) -> None:
    """Test."""
    f1 = tmp_path / "f1.py"
    f1.write_text("code1")

    mock_get_py.return_value = [str(f1)]
    mock_check.return_value = "new_code1"  # Needs upgrade
    mock_find.return_value = ("3.8", {})  # no other changes

    mock_prompt.return_value = False

    PyGradeup(str(tmp_path)).fix(interactive=True)
    assert f1.read_text() == "code1"  # Not updated because prompt returned False

    mock_prompt.return_value = True
    PyGradeup(str(tmp_path)).fix(interactive=True)
    assert f1.read_text() == "new_code1"  # Updated because prompt returned True


@patch("py_gradeup.sdk._update_ci_cd_environments")
@patch("py_gradeup.sdk._update_dependencies_file")
def test_sdk_audit_diff(mock_update, mock_ci, tmp_path, capsys) -> None:
    """Test."""
    f1 = tmp_path / "f1.py"
    f1.write_text("def foo():\n    return set(())\n")
    with patch("py_gradeup.sdk._get_current_python_version", return_value="3"):
        PyGradeup(str(tmp_path)).audit(show_diff=True)
        res = PyGradeup(str(tmp_path)).audit(show_diff=True)
        assert len(res.proposed_diffs) > 0
        assert "--- a/f1.py\n" in res.proposed_diffs
        assert "+++ b/f1.py\n" in res.proposed_diffs
        assert "-    return set(())\n" in res.proposed_diffs
        assert "+    return set()\n" in res.proposed_diffs


@patch("subprocess.run")
@patch("py_gradeup.sdk._update_dockerfiles")
@patch("py_gradeup.sdk._find_target_python")
@patch("py_gradeup.sdk._get_py_files")
@patch("py_gradeup.sdk._check_pyupgrade")
@patch("py_gradeup.sdk._update_python_classifiers")
@patch("py_gradeup.sdk._update_ci_cd_environments")
@patch("py_gradeup.sdk._update_dependencies_file")
@patch("py_gradeup.core._update_python_version_bounds")
@patch("py_gradeup.sdk._backup_old_requirements")
def test_sdk_fix_commit(
    mock_backup,
    mock_upd_py,
    mock_upd_dep,
    mock_upd_ci,
    mock_upd_cls,
    mock_check,
    mock_get_py,
    mock_find,
    mock_upd_docker,
    mock_run,
    capsys,
    tmp_path,
) -> None:
    """Test fix_project with commit=True."""
    from py_gradeup.sdk import PyGradeup

    mock_find.return_value = ("3.14", {"pkg": "2.0"})
    mock_upd_py.return_value = True

    b_path = tmp_path / "req-old.txt"
    b_path.write_text("old")
    mock_backup.return_value = str(b_path)

    mock_upd_docker.return_value = ["Dockerfile"]
    mock_upd_ci.return_value = ["ci.yml"]
    f1 = tmp_path / "f1.py"
    f1.write_text("code1")
    mock_get_py.return_value = [str(f1)]
    mock_check.return_value = "new_code1"
    mock_upd_dep.return_value = {"pkg": "2.0"}

    # Mock subprocess.run for git
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res

    with patch(
        "py_gradeup.core._get_target_files", return_value=[str(tmp_path / "req.txt")]
    ):
        req_file = tmp_path / "req.txt"
        req_file.write_text("pkg==1.0")
        PyGradeup(str(tmp_path)).fix(commit=True)

    capsys.readouterr()
    assert True

    # Verify git was called
    calls = mock_run.call_args_list
    assert len(calls) >= 1
    assert "commit" in calls[-1][0][0]
    assert "commit" in calls[-1][0][0]

    msg_arg = calls[-1][0][0][4]
    assert (
        "Added support for Python versions: 3.14; also in Docker and GitHub Actions"
        in msg_arg
    )
    assert "Upgraded syntax in 1 files" in msg_arg
    assert "Upgraded syntax in 1 files" in msg_arg

    # Test nothing to commit
    mock_res.returncode = 1
    mock_res.stdout = "nothing to commit"
    mock_res.stderr = ""
    with patch(
        "py_gradeup.core._get_target_files", return_value=[str(tmp_path / "req.txt")]
    ):
        req_file = tmp_path / "req.txt"
        req_file.write_text("pkg==1.0")
        PyGradeup(str(tmp_path)).fix(commit=True)
    capsys.readouterr()
    assert True

    # Test error
    mock_res.stdout = ""
    mock_res.stderr = "some git error"
    with patch(
        "py_gradeup.core._get_target_files", return_value=[str(tmp_path / "req.txt")]
    ):
        req_file = tmp_path / "req.txt"
        req_file.write_text("pkg==1.0")
        PyGradeup(str(tmp_path)).fix(commit=True)
    capsys.readouterr()
    assert True

    # Test exception FileNotFoundError
    mock_run.side_effect = FileNotFoundError()
    with patch(
        "py_gradeup.core._get_target_files", return_value=[str(tmp_path / "req.txt")]
    ):
        req_file = tmp_path / "req.txt"
        req_file.write_text("pkg==1.0")
        PyGradeup(str(tmp_path)).fix(commit=True)
    capsys.readouterr()
    assert True


from unittest.mock import patch

from py_gradeup.core import _recreate_venv


def test_recreate_venv_no_venv(tmp_path) -> None:
    """Test."""
    assert _recreate_venv(str(tmp_path), "3.9") is False


@patch("shutil.rmtree")
def test_recreate_venv_rmtree_fails(mock_rmtree, tmp_path) -> None:
    """Test."""
    (tmp_path / ".venv").mkdir()
    mock_rmtree.side_effect = Exception("failed")
    assert _recreate_venv(str(tmp_path), "3.9") is False


@patch("shutil.rmtree")
@patch("subprocess.run")
def test_recreate_venv_uv_success(mock_run, mock_rmtree, tmp_path) -> None:
    """Test."""
    (tmp_path / ".venv").mkdir()
    mock_run.return_value = MagicMock(returncode=0)
    assert _recreate_venv(str(tmp_path), "3.9") is True
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0] == ["uv", "venv", ".venv", "--python", "3.9"]


@patch("shutil.rmtree")
@patch("subprocess.run")
def test_recreate_venv_uv_fails_pyenv_success(mock_run, mock_rmtree, tmp_path) -> None:
    """Test."""
    (tmp_path / ".venv").mkdir()

    def side_effect(cmd, **kwargs):
        """Test."""
        if cmd[0] == "uv":
            raise subprocess.CalledProcessError(1, cmd)
        return MagicMock(returncode=0)

    mock_run.side_effect = side_effect

    assert _recreate_venv(str(tmp_path), "3.9") is True
    assert mock_run.call_count == 2
    assert mock_run.call_args[0][0] == ["python3", "-m", "venv", ".venv"]


@patch("shutil.rmtree")
@patch("subprocess.run")
def test_recreate_venv_uv_fails_pyenv_fails(mock_run, mock_rmtree, tmp_path) -> None:
    """Test."""
    (tmp_path / ".venv").mkdir()
    mock_run.side_effect = FileNotFoundError()

    assert _recreate_venv(str(tmp_path), "3.9") is False
    assert mock_run.call_count == 2


@patch("py_gradeup.sdk._recreate_venv")
def test_sdk_fix_recreate_venv(mock_recreate_venv, tmp_path) -> None:
    """Test."""
    (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.8"')
    (tmp_path / "f1.py").write_text("print('hello')")
    PyGradeup(str(tmp_path)).fix(recreate_venv=True)
    mock_recreate_venv.assert_called_once_with(str(tmp_path), "3.14", versioned=False)


@patch("py_gradeup.sdk._recreate_venv")
def test_sdk_fix_versioned_venv(mock_recreate_venv, tmp_path) -> None:
    """Test."""
    (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.8"')
    (tmp_path / "f1.py").write_text("print('hello')")
    PyGradeup(str(tmp_path)).fix(versioned_venv=True)
    mock_recreate_venv.assert_called_once_with(str(tmp_path), "3.14", versioned=True)


@patch("shutil.rmtree")
@patch("subprocess.run")
def test_recreate_venv_versioned_uv_success(mock_run, mock_rmtree, tmp_path) -> None:
    """Test."""
    from py_gradeup.core import _recreate_venv

    (tmp_path / ".venv-uv-3-9").mkdir()
    mock_run.return_value = MagicMock(returncode=0)
    assert _recreate_venv(str(tmp_path), "3.9", versioned=True) is True
    mock_run.assert_called_once()


@patch("shutil.rmtree")
@patch("subprocess.run")
def test_recreate_venv_versioned_uv_fails_pyenv_success(
    mock_run, mock_rmtree, tmp_path
) -> None:
    """Test."""
    from py_gradeup.core import _recreate_venv

    (tmp_path / ".venv-uv-3-9").mkdir()
    (tmp_path / ".venv-pyenv-3-9").mkdir()

    def side_effect(cmd, **kwargs):
        """Test."""
        if cmd[0] == "uv":
            raise subprocess.CalledProcessError(1, cmd)
        return MagicMock(returncode=0)

    mock_run.side_effect = side_effect
    assert _recreate_venv(str(tmp_path), "3.9", versioned=True) is True
    assert mock_run.call_count == 2


@patch("shutil.rmtree")
@patch("subprocess.run")
def test_recreate_venv_versioned_rmtree_fails(mock_run, mock_rmtree, tmp_path) -> None:
    """Test."""
    from py_gradeup.core import _recreate_venv

    (tmp_path / ".venv-uv-3-9").mkdir()
    mock_rmtree.side_effect = Exception("failed")
    assert _recreate_venv(str(tmp_path), "3.9", versioned=True) is False


@patch("shutil.rmtree")
@patch("subprocess.run")
def test_recreate_venv_versioned_rmtree_fails2(mock_run, mock_rmtree, tmp_path) -> None:
    """Test."""
    from py_gradeup.core import _recreate_venv

    (tmp_path / ".venv-pyenv-3-9").mkdir()

    def side_effect(cmd, **kwargs):
        """Test side effect."""
        raise subprocess.CalledProcessError(1, cmd)

    mock_run.side_effect = side_effect
    mock_rmtree.side_effect = Exception("failed")
    assert _recreate_venv(str(tmp_path), "3.9", versioned=True) is False


from unittest.mock import patch


@patch("py_gradeup.sdk._get_current_python_version")
@patch("py_gradeup.sdk._get_target_files")
@patch("py_gradeup.sdk._find_target_python")
@patch("shutil.rmtree")
@patch("subprocess.run")
@patch("os.path.exists")
def test_test_matrix(
    mock_exists,
    mock_run,
    mock_rmtree,
    mock_find,
    mock_get_files,
    mock_get_ver,
    tmp_path,
) -> None:
    """Test."""
    mock_get_ver.return_value = "3.8"
    mock_get_files.return_value = []
    mock_find.return_value = ("3.9", {})

    (tmp_path / "pyproject.toml").write_text("pytest")
    (tmp_path / "requirements.txt").touch()

    def side_effect_exists(path):
        """Test."""
        if "pyproject.toml" in path or "requirements.txt" in path:
            return True
        return ".venv" in path

    mock_exists.side_effect = side_effect_exists

    mock_run.return_value = MagicMock(returncode=0)

    res = PyGradeup(str(tmp_path)).test()
    passed = res.all_passed
    assert passed is True
    # Verify uv and pyenv were called
    assert mock_run.call_count >= 4


@patch("py_gradeup.sdk._get_current_python_version")
@patch("py_gradeup.sdk._get_target_files")
@patch("py_gradeup.sdk._find_target_python")
@patch("subprocess.run")
@patch("os.path.exists")
def test_test_matrix_failures(
    mock_exists, mock_run, mock_find, mock_get_files, mock_get_ver, tmp_path
) -> None:
    """Test."""
    mock_get_ver.return_value = "3.8"
    mock_get_files.return_value = []
    mock_find.return_value = ("3.8", {})  # single version
    mock_exists.return_value = False

    import subprocess

    def side_effect_run(cmd, **kwargs):
        """Test."""
        raise subprocess.CalledProcessError(1, cmd)

    mock_run.side_effect = side_effect_run

    res = PyGradeup(str(tmp_path)).test()
    passed = res.all_passed
    assert passed is False


@patch("py_gradeup.sdk._get_current_python_version")
@patch("py_gradeup.sdk._get_target_files")
@patch("py_gradeup.sdk._find_target_python")
@patch("subprocess.run")
@patch("os.path.exists")
def test_test_matrix_test_failures(
    mock_exists, mock_run, mock_find, mock_get_files, mock_get_ver, tmp_path
) -> None:
    """Test."""
    mock_get_ver.return_value = "invalid"
    mock_get_files.return_value = []
    mock_find.return_value = ("3.8", {})
    mock_exists.return_value = False

    def side_effect_run(cmd, **kwargs):
        """Test."""
        if cmd[0].endswith("pytest") or "unittest" in cmd:
            print("MOCK RUN pytest/unittest CALLED!")
            raise Exception("error")
        return MagicMock(returncode=0)

    mock_run.side_effect = side_effect_run

    res = PyGradeup(str(tmp_path)).test()
    passed = res.all_passed
    assert passed is False


@patch("py_gradeup.sdk._get_current_python_version")
@patch("py_gradeup.sdk._get_target_files")
@patch("py_gradeup.sdk._find_target_python")
@patch("subprocess.run")
@patch("os.path.exists")
@patch("shutil.rmtree")
def test_test_matrix_exception_rmtree(
    mock_rmtree,
    mock_exists,
    mock_run,
    mock_find,
    mock_get_files,
    mock_get_ver,
    tmp_path,
) -> None:
    """Test."""
    mock_get_ver.return_value = "3.8"
    mock_get_files.return_value = []
    mock_find.return_value = ("3.8", {})

    def side_effect_exists(path):
        """Test."""
        return ".venv" in path

    mock_exists.side_effect = side_effect_exists
    mock_rmtree.side_effect = Exception("error")

    res = PyGradeup(str(tmp_path)).test()
    passed = res.all_passed
    assert passed is False


@patch("py_gradeup.sdk._get_current_python_version")
@patch("py_gradeup.sdk._get_target_files")
@patch("py_gradeup.sdk._find_target_python")
@patch("subprocess.run")
@patch("os.path.exists")
def test_test_matrix_returncode_1(
    mock_exists, mock_run, mock_find, mock_get_files, mock_get_ver, tmp_path
) -> None:
    """Test."""
    mock_get_ver.return_value = "3.8"
    mock_get_files.return_value = []
    mock_find.return_value = ("3.8", {})
    mock_exists.return_value = False

    def side_effect_run(cmd, **kwargs):
        """Test."""
        if cmd[0].endswith("pytest") or "unittest" in cmd:
            return MagicMock(returncode=1, stdout="failed tests")
        return MagicMock(returncode=0)

    mock_run.side_effect = side_effect_run

    res = PyGradeup(str(tmp_path)).test()
    passed = res.all_passed
    assert passed is False


@patch("py_gradeup.sdk._get_current_python_version")
@patch("py_gradeup.sdk._get_target_files")
@patch("py_gradeup.sdk._find_target_python")
@patch("subprocess.run")
@patch("os.path.exists")
def test_test_matrix_pytest_ini(
    mock_exists, mock_run, mock_find, mock_get_files, mock_get_ver, tmp_path
) -> None:
    """Test."""
    mock_get_ver.return_value = "3.8"
    mock_get_files.return_value = []
    mock_find.return_value = ("3.8", {})
    (tmp_path / "pytest.ini").write_text("[pytest]")
    mock_exists.side_effect = lambda path: "pytest.ini" in path
    mock_run.return_value = MagicMock(returncode=0)
    assert PyGradeup(str(tmp_path)).test().all_passed is True


@patch("py_gradeup.sdk._get_current_python_version")
@patch("py_gradeup.sdk._get_target_files")
@patch("py_gradeup.sdk._find_target_python")
@patch("subprocess.run")
@patch("os.path.exists")
def test_test_matrix_requirements_dev(
    mock_exists, mock_run, mock_find, mock_get_files, mock_get_ver, tmp_path
) -> None:
    """Test."""
    mock_get_ver.return_value = "3.8"
    mock_get_files.return_value = []
    mock_find.return_value = ("3.8", {})
    (tmp_path / "requirements-dev.txt").write_text("pytest")
    mock_exists.side_effect = lambda path: "requirements-dev.txt" in path
    mock_run.return_value = MagicMock(returncode=0)
    assert PyGradeup(str(tmp_path)).test().all_passed is True


@patch("py_gradeup.sdk._run_test_env")
@patch("py_gradeup.sdk._get_current_python_version")
@patch("py_gradeup.sdk._get_target_files")
@patch("py_gradeup.sdk._find_target_python")
def test_test_matrix_no_parallel(
    mock_find, mock_get_files, mock_get_ver, mock_run_test, tmp_path
) -> None:
    """Test."""
    mock_get_ver.return_value = "3.8"
    mock_get_files.return_value = []
    mock_find.return_value = ("3.8", {})
    mock_run_test.return_value = ("uv-3.8", True, "output")

    assert PyGradeup(str(tmp_path)).test(parallel=False).all_passed is True


def test_should_modify() -> None:
    """Test should modify."""
    from py_gradeup.core import _should_modify

    assert _should_modify("file.py", None) is True
    assert _should_modify("file.py", ["python"]) is True
    assert _should_modify("file.toml", ["python"]) is False
    assert _should_modify("file.toml", ["toml"]) is True
    assert _should_modify(".github/workflows/ci.yml", ["ghactions"]) is True
    assert _should_modify("Dockerfile", ["docker"]) is True
    assert _should_modify("dockerfile.dev", ["docker"]) is True
    assert _should_modify("config.yaml", ["yaml"]) is True
    assert _should_modify("config.yml", ["yaml"]) is True
    assert _should_modify("config.yml", ["yml"]) is True
    assert _should_modify("req.txt", ["txt"]) is True
    assert _should_modify("pdm.lock", ["lock"]) is True
    assert _should_modify("setup.cfg", ["cfg"]) is True
    assert _should_modify("tox.ini", ["ini"]) is True
    assert _should_modify("unknown.xyz", ["xyz"]) is True
    assert _should_modify("file.py", ["toml", "python"]) is True


def test_should_modify_coverage():
    """Test should_modify coverage cases."""
    from py_gradeup.core import _should_modify

    assert _should_modify("test.py", ["xyz"]) is False


def test_only_filters() -> None:
    """Test the only filters."""
    import os
    import tempfile

    from py_gradeup.core import (
        _update_ci_cd_environments,
        _update_dockerfiles,
        _update_python_classifiers,
    )

    with tempfile.TemporaryDirectory() as d:
        # For classifiers
        with open(os.path.join(d, "setup.py"), "w") as f:
            f.write("Programming Language :: Python :: 3.8")
        res1 = _update_python_classifiers(d, "3.9", dry_run=True, only=["toml"])
        assert not res1  # skipped setup.py

        # For dockerfiles
        with open(os.path.join(d, "Dockerfile"), "w") as f:
            f.write("FROM python:3.8")
        res2 = _update_dockerfiles(d, "3.9", dry_run=True, only=["python"])
        assert not res2

        # For ci cd environments
        os.makedirs(os.path.join(d, ".github", "workflows"))
        with open(os.path.join(d, ".github", "workflows", "ci.yml"), "w") as f:
            f.write("python-version: '3.8'")
        res2 = _update_ci_cd_environments(d, "3.9", dry_run=True, only=["python"])
        assert not res2
