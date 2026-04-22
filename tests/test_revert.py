"""Test module."""
# ruff: noqa: D100
# ruff: noqa: D103, E501
from unittest.mock import MagicMock, patch

from py_gradeup.core import revert_project


@patch("subprocess.run")
def test_revert_project_git_success(mock_run, tmp_path, capsys):
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res

    revert_project(str(tmp_path))
    captured = capsys.readouterr()
    assert "Reverted file modifications via git" in captured.out


@patch("subprocess.run")
def test_revert_project_git_fail(mock_run, tmp_path, capsys):
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stderr = "error"
    mock_run.return_value = mock_res

    revert_project(str(tmp_path))
    captured = capsys.readouterr()
    assert "Git restore failed: error" in captured.err


@patch("subprocess.run")
def test_revert_project_git_not_found(mock_run, tmp_path, capsys):
    """Test."""
    mock_run.side_effect = FileNotFoundError()

    revert_project(str(tmp_path))
    captured = capsys.readouterr()
    assert "Git not found." in captured.err


@patch("subprocess.run")
def test_revert_project_restore_backup(mock_run, tmp_path, capsys):
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res

    req_bak = tmp_path / "requirements-3-8.txt"
    req_bak.write_text("backup")
    req = tmp_path / "requirements.txt"
    req.write_text("new")

    revert_project(str(tmp_path))
    captured = capsys.readouterr()
    assert "Restored dependencies from requirements-3-8.txt" in captured.out
    assert req.read_text() == "backup"


@patch("subprocess.run")
@patch("shutil.copy2")
def test_revert_project_restore_backup_error(mock_copy, mock_run, tmp_path, capsys):
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res

    mock_copy.side_effect = Exception("error")

    req_bak = tmp_path / "requirements-3-8.txt"
    req_bak.write_text("backup")

    revert_project(str(tmp_path))
    captured = capsys.readouterr()
    assert "Failed to restore backup requirements-3-8.txt: error" in captured.err


@patch("subprocess.run")
def test_revert_project_no_backups(mock_run, tmp_path, capsys):
    """Test."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res

    revert_project(str(tmp_path))
    captured = capsys.readouterr()
    assert "No dependency backups found." in captured.out
