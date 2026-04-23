"""Tests for Dockerfile parsing and updating."""

from py_gradeup.core import (
    _get_target_files,
    _prepare_compile_targets,
    _update_dependencies_file,
)
from py_gradeup.security import _parse_dependencies


def test_dockerfile_get_target_files(tmp_path):
    """Test _get_target_files for Dockerfiles."""
    d = tmp_path / "Dockerfile"
    d.write_text("FROM python:3.9")

    d2 = tmp_path / "app.Dockerfile"
    d2.write_text("FROM python:3.9")

    targets = _get_target_files(str(tmp_path))
    assert str(d) in targets
    assert str(d2) in targets


def test_dockerfile_prepare_compile_targets(tmp_path):
    """Test _prepare_compile_targets for Dockerfiles."""
    d = tmp_path / "Dockerfile"
    d.write_text(
        "RUN pip install requests==2.25.1 flask>=1.1.2\nENV X=1\n"
        "RUN pip3 install django==3.2"
    )

    tmp_paths = []
    targets = _prepare_compile_targets([str(d)], tmp_paths)

    assert len(targets) == 1
    with open(targets[0]) as f:
        content = f.read()
        assert "requests==2.25.1" in content
        assert "flask>=1.1.2" in content
        assert "django==3.2" in content


def test_dockerfile_update_dependencies_file(tmp_path):
    """Test _update_dependencies_file for Dockerfiles."""
    d = tmp_path / "Dockerfile"
    d.write_text(
        "RUN pip install requests==2.25.1\nENV pkg==1.0\nRUN pip3 install flask>=1.1.2"
    )

    resolved = {"requests": "2.26.0", "flask": "2.0.0"}
    updates = _update_dependencies_file(str(d), resolved)

    assert "requests" in updates
    assert updates["requests"] == "2.25.1 -> 2.26.0"

    assert "flask" in updates
    assert updates["flask"] == "1.1.2 -> 2.0.0"

    content = d.read_text()
    assert "RUN pip install requests==2.26.0" in content
    assert "ENV pkg==1.0" in content
    assert "RUN pip3 install flask>=2.0.0" in content


def test_dockerfile_parse_dependencies(tmp_path):
    """Test _parse_dependencies for Dockerfiles."""
    d = tmp_path / "Dockerfile"
    d.write_text(
        "RUN pip install requests==2.25.1\nENV pkg==1.0\nRUN pip3 install flask==1.1.2"
    )

    deps = _parse_dependencies(str(d))
    assert deps.get("requests") == "2.25.1"
    assert deps.get("flask") == "1.1.2"
    assert "pkg" not in deps


def test_dockerfile_update_dependencies_file_no_update(tmp_path):
    """Test _update_dependencies_file when no updates occur."""
    d = tmp_path / "Dockerfile"
    d.write_text("RUN pip install unchanged==1.0.0")

    # either not in resolved, or version is same
    resolved = {"unchanged": "1.0.0", "other": "2.0"}
    updates = _update_dependencies_file(str(d), resolved)

    assert not updates
    assert d.read_text() == "RUN pip install unchanged==1.0.0"
