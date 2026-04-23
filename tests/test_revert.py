"""Test module."""

# ruff: noqa: D100
# ruff: noqa: D103, E501
from unittest.mock import MagicMock, patch

from py_gradeup.sdk import PyGradeup


@patch("subprocess.run")
def test_revert_project_git_success(mock_run, tmp_path, capsys) -> None:
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res

    res = PyGradeup(str(tmp_path)).revert()
    captured = capsys.readouterr()
    assert res.git_restored is True


@patch("subprocess.run")
def test_revert_project_git_fail(mock_run, tmp_path, capsys) -> None:
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stderr = "error"
    mock_run.return_value = mock_res

    res = PyGradeup(str(tmp_path)).revert()
    captured = capsys.readouterr()
    assert str(res.git_error) == "error"


@patch("subprocess.run")
def test_revert_project_git_not_found(mock_run, tmp_path, capsys) -> None:
    """Test."""
    mock_run.side_effect = FileNotFoundError()

    res = PyGradeup(str(tmp_path)).revert()
    captured = capsys.readouterr()
    assert "Git not found" in str(res.git_error)


@patch("subprocess.run")
def test_revert_project_restore_backup(mock_run, tmp_path, capsys) -> None:
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res

    req_bak = tmp_path / "requirements-3-8.txt"
    req_bak.write_text("backup")
    req = tmp_path / "requirements.txt"
    req.write_text("new")

    res = PyGradeup(str(tmp_path)).revert()
    captured = capsys.readouterr()
    assert res.dependencies_restored_from == "requirements-3-8.txt"
    assert req.read_text() == "backup"


@patch("subprocess.run")
@patch("shutil.copy2")
def test_revert_project_restore_backup_error(
    mock_copy, mock_run, tmp_path, capsys
) -> None:
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res

    mock_copy.side_effect = Exception("error")

    req_bak = tmp_path / "requirements-3-8.txt"
    req_bak.write_text("backup")

    res = PyGradeup(str(tmp_path)).revert()
    captured = capsys.readouterr()
    assert res.dependencies_restored_from is None


@patch("subprocess.run")
def test_revert_project_no_backups(mock_run, tmp_path, capsys) -> None:
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res

    res = PyGradeup(str(tmp_path)).revert()
    captured = capsys.readouterr()
    assert res.dependencies_restored_from is None
