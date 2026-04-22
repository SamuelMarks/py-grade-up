"""Test module."""
# ruff: noqa: D100, SIM115
# ruff: noqa: D103, E501
import subprocess
from unittest.mock import MagicMock, patch

from py_gradeup.graph import _prepare_compile_targets, visualize_graph


def test_prepare_compile_targets_empty():
    """Test."""
    assert _prepare_compile_targets([], []) == []


def test_prepare_compile_targets_txt(tmp_path):
    """Test."""
    f = tmp_path / "req.txt"
    f.write_text("pkg1>=1.0\n")
    tmps = []
    res = _prepare_compile_targets([str(f)], tmps)
    assert len(res) == 1
    assert "pkg1>=1.0" in open(res[0]).read()


@patch("py_gradeup.graph._get_target_files")
def test_visualize_graph_no_files(mock_get, capsys, tmp_path):
    """Test."""
    mock_get.return_value = []
    visualize_graph(str(tmp_path))
    assert "No dependency files found" in capsys.readouterr().out


@patch("py_gradeup.graph._get_target_files")
@patch("py_gradeup.graph._prepare_compile_targets")
def test_visualize_graph_no_targets(mock_prep, mock_get, capsys, tmp_path):
    """Test."""
    mock_get.return_value = ["fake.txt"]
    mock_prep.return_value = []
    visualize_graph(str(tmp_path))
    assert "No valid packages found" in capsys.readouterr().out


@patch("py_gradeup.graph._get_target_files")
@patch("subprocess.run")
def test_visualize_graph_success(mock_run, mock_get, capsys, tmp_path):
    """Test."""
    f = tmp_path / "req.txt"
    f.write_text("pkg1==1.0\n")
    mock_get.return_value = [str(f)]

    mock_run.return_value = MagicMock(stdout="Fake Tree Output", stderr="")

    visualize_graph(str(tmp_path))

    out = capsys.readouterr().out
    assert "Dependency Tree:" in out
    assert "Fake Tree Output" in out


@patch("py_gradeup.graph._get_target_files")
@patch("subprocess.run")
def test_visualize_graph_conflict(mock_run, mock_get, capsys, tmp_path):
    """Test."""
    f = tmp_path / "req.txt"
    f.write_text("pkg1==1.0\n")
    mock_get.return_value = [str(f)]

    mock_run.side_effect = subprocess.CalledProcessError(
        1, "cmd", stderr="No solution found for foo", output=""
    )

    visualize_graph(str(tmp_path))

    out = capsys.readouterr().out
    assert "Dependency Conflict Detected" in out
    assert "No solution found" in out


@patch("py_gradeup.graph._get_target_files")
@patch("subprocess.run")
def test_visualize_graph_other_error(mock_run, mock_get, capsys, tmp_path):
    """Test."""
    f = tmp_path / "req.txt"
    f.write_text("pkg1==1.0\n")
    mock_get.return_value = [str(f)]

    mock_run.side_effect = subprocess.CalledProcessError(
        1, "cmd", stderr="Some other random network error", output=""
    )

    visualize_graph(str(tmp_path))

    out = capsys.readouterr().out
    assert "Resolution Error" in out
    assert "random network error" in out


def test_prepare_compile_targets_all_formats(tmp_path):
    """Test."""
    tmps = []

    pf = tmp_path / "Pipfile"
    pf.write_text('requests = "==2.31.0"\nfoo = ">=1.0"\n')

    env = tmp_path / "environment.yml"
    env.write_text("dependencies:\n  - python>=3.8\n  - requests>=2.31.0\n")

    plock = tmp_path / "Pipfile.lock"
    plock.write_text('{"default": {"requests": {"version": "==2.31.0"}}}')

    ptoml = tmp_path / "pylock.toml"
    ptoml.write_text('[[package]]\nname = "foo"\nversion = "1.0"\n')

    other = tmp_path / "setup.py"
    other.write_text("")

    res = _prepare_compile_targets(
        [str(pf), str(env), str(plock), str(ptoml), str(other)], tmps
    )
    assert len(res) == 5


def test_prepare_compile_targets_poetry_lock(tmp_path):
    """Test."""
    tmps = []
    f = tmp_path / "poetry.lock"
    f.write_text(
        '[[package]]\nname = "foo"\nversion = "1.0"\n[[package]]\nname="bar"\nversion="2.0"\n'
    )
    res = _prepare_compile_targets([str(f)], tmps)
    assert len(res) == 1
    assert "foo==1.0" in open(res[0]).read()


def test_prepare_compile_targets_txt_fallback(tmp_path):
    """Test."""
    tmps = []
    f = tmp_path / "req.txt"
    f.write_text("foo\n")
    res = _prepare_compile_targets([str(f)], tmps)
    assert "foo" in open(res[0]).read()


@patch("os.remove")
@patch("py_gradeup.graph._get_target_files")
@patch("subprocess.run")
def test_visualize_graph_remove_exception(

    mock_run, mock_get, mock_remove, capsys, tmp_path
):
    """Test."""
    f = tmp_path / "req.txt"
    f.write_text("pkg1==1.0\n")
    mock_get.return_value = [str(f)]
    mock_run.return_value = MagicMock(stdout="Fake Tree Output", stderr="")
    mock_remove.side_effect = Exception("Remove error")
    visualize_graph(str(tmp_path))
