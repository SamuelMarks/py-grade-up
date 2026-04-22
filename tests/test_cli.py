# ruff: noqa: E402
# ruff: noqa: D103, E501
"""Tests for the command-line interface."""

from unittest.mock import patch

import pytest

from py_gradeup.cli import main


@patch("py_gradeup.cli.audit_project")
def test_audit_command(mock_audit, capsys) -> None:
    """Test the audit subcommand."""
    exit_code = main(["audit", "."])
    assert exit_code == 0
    mock_audit.assert_called_once_with(".", show_diff=False)


@patch("py_gradeup.cli.fix_project")
def test_fix_command(mock_fix, capsys) -> None:
    """Test the fix subcommand."""
    exit_code = main(["fix", "."])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        ".", run_tests=False, interactive=False, commit=False, recreate_venv=False, versioned_venv=False
    )

    mock_fix.reset_mock()
    exit_code = main(["fix", ".", "--run-tests"])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        ".", run_tests=True, interactive=False, commit=False, recreate_venv=False, versioned_venv=False
    )

    mock_fix.reset_mock()
    exit_code = main(["fix", ".", "-i"])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        ".", run_tests=False, interactive=True, commit=False, recreate_venv=False, versioned_venv=False
    )

    mock_fix.reset_mock()
    exit_code = main(["fix", ".", "--recreate-venv"])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        ".", run_tests=False, interactive=False, commit=False, recreate_venv=True, versioned_venv=False
    )


def test_main_no_args() -> None:
    """Test main with no arguments raises SystemExit."""
    with pytest.raises(SystemExit):
        main([])


@patch("sys.argv", ["py-gradeup", "audit", "."])
@patch("py_gradeup.cli.audit_project")
def test_main_sys_argv(mock_audit) -> None:
    """Test main using sys.argv implicitly."""
    exit_code = main()
    assert exit_code == 0
    mock_audit.assert_called_once_with(".", show_diff=False)


@patch("py_gradeup.cli.audit_project")
def test_audit_command_diff(mock_audit, capsys) -> None:
    """Test the audit subcommand with diff."""
    exit_code = main(["audit", ".", "--diff"])
    assert exit_code == 0
    mock_audit.assert_called_once_with(".", show_diff=True)


@patch("py_gradeup.cli.fix_project")
def test_fix_command_commit(mock_fix, capsys) -> None:
    """Test the fix subcommand with commit."""
    exit_code = main(["fix", ".", "--commit"])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        ".", run_tests=False, interactive=False, commit=True, recreate_venv=False, versioned_venv=False
    )


@patch("py_gradeup.cli.revert_project")
def test_revert_command(mock_revert, capsys) -> None:
    """Test the revert subcommand."""
    exit_code = main(["revert", "."])
    assert exit_code == 0
    mock_revert.assert_called_once_with(".")


@patch("py_gradeup.cli.audit_security")
def test_security_command(mock_security, capsys) -> None:
    """Test the security subcommand."""
    mock_security.return_value = False
    exit_code = main(["security", "."])
    assert exit_code == 0
    mock_security.assert_called_once_with(".")

    mock_security.reset_mock()
    mock_security.return_value = True
    exit_code = main(["security", "."])
    assert exit_code == 1
    mock_security.assert_called_once_with(".")


@patch("py_gradeup.cli.visualize_graph")
def test_graph_command(mock_graph, capsys) -> None:
    """Test the graph subcommand."""
    exit_code = main(["graph", "."])
    assert exit_code == 0
    mock_graph.assert_called_once_with(".")
from unittest.mock import patch


@patch("py_gradeup.core.test_matrix")
def test_test_command(mock_test_matrix, capsys) -> None:
    """Test."""
    mock_test_matrix.return_value = True
    exit_code = main(["test", "."])
    assert exit_code == 0
    mock_test_matrix.assert_called_once_with(".", parallel=True)

@patch("py_gradeup.core.test_matrix")
def test_test_command_fail(mock_test_matrix, capsys) -> None:
    """Test."""
    mock_test_matrix.return_value = False
    exit_code = main(["test", "."])
    assert exit_code == 1
    mock_test_matrix.assert_called_once_with(".", parallel=True)
