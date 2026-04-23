# ruff: noqa: E402
# ruff: noqa: D103, E501
"""Tests for the command-line interface."""

from unittest.mock import patch, MagicMock

import pytest

from py_gradeup.cli import main


@patch("py_gradeup.cli.PyGradeup.audit")
def test_audit_command(mock_audit, capsys) -> None:
    """Test the audit subcommand."""
    exit_code = main(["audit", "."])
    assert exit_code == 0
    mock_audit.assert_called_once_with(show_diff=False, only=None)


@patch("py_gradeup.cli.PyGradeup.fix")
def test_fix_command(mock_fix, capsys) -> None:
    """Test the fix subcommand."""
    exit_code = main(["fix", "."])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        run_tests=False,
        interactive=False,
        commit=False,
        recreate_venv=False,
        versioned_venv=False,
        only=None,
    )

    mock_fix.reset_mock()
    exit_code = main(["fix", ".", "--run-tests"])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        run_tests=True,
        interactive=False,
        commit=False,
        recreate_venv=False,
        versioned_venv=False,
        only=None,
    )

    mock_fix.reset_mock()
    exit_code = main(["fix", ".", "-i"])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        run_tests=False,
        interactive=True,
        commit=False,
        recreate_venv=False,
        versioned_venv=False,
        only=None,
    )

    mock_fix.reset_mock()
    exit_code = main(["fix", ".", "--recreate-venv"])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        run_tests=False,
        interactive=False,
        commit=False,
        recreate_venv=True,
        versioned_venv=False,
        only=None,
    )


def test_main_no_args() -> None:
    """Test main with no arguments raises SystemExit."""
    with pytest.raises(SystemExit):
        main([])


@patch("sys.argv", ["py-gradeup", "audit", "."])
@patch("py_gradeup.cli.PyGradeup.audit")
def test_main_sys_argv(mock_audit) -> None:
    """Test main using sys.argv implicitly."""
    exit_code = main()
    assert exit_code == 0
    mock_audit.assert_called_once_with(show_diff=False, only=None)


@patch("py_gradeup.cli.PyGradeup.audit")
def test_audit_command_diff(mock_audit, capsys) -> None:
    """Test the audit subcommand with diff."""
    exit_code = main(["audit", ".", "--diff"])
    assert exit_code == 0
    mock_audit.assert_called_once_with(show_diff=True, only=None)


@patch("py_gradeup.cli.PyGradeup.fix")
def test_fix_command_commit(mock_fix, capsys) -> None:
    """Test the fix subcommand with commit."""
    exit_code = main(["fix", ".", "--commit"])
    assert exit_code == 0
    mock_fix.assert_called_once_with(
        run_tests=False,
        interactive=False,
        commit=True,
        recreate_venv=False,
        versioned_venv=False,
        only=None,
    )


@patch("py_gradeup.cli.PyGradeup.revert")
def test_revert_command(mock_revert, capsys) -> None:
    mock_revert.return_value = MagicMock(
        git_restored=False, git_error="err", dependencies_restored_from=None
    )
    main(["revert", "."])

    mock_revert.return_value = MagicMock(
        git_restored=True, git_error=None, dependencies_restored_from="back.txt"
    )
    """Test the revert subcommand."""
    exit_code = main(["revert", "."])
    assert exit_code == 0
    assert mock_revert.call_count == 2


@patch("py_gradeup.cli.PyGradeup.security")
@patch("py_gradeup.core._get_target_files")
@patch("py_gradeup.security._parse_dependencies")
def test_security_command(mock_parse, mock_get_targets, mock_security, capsys) -> None:
    """Test the security subcommand."""
    mock_get_targets.return_value = ["req.txt"]
    mock_parse.return_value = {"pkg": "1.0"}
    from unittest.mock import MagicMock

    mock_security.return_value = MagicMock(
        vulnerabilities_found=False, vulnerabilities={}
    )
    exit_code = main(["security", "."])
    assert exit_code == 0
    mock_security.assert_called_once_with()

    mock_security.reset_mock()
    mock_security.return_value = MagicMock(
        vulnerabilities_found=True,
        vulnerabilities={"pkg==1.0": [{"id": "CVE-123", "details": "bad"}]},
    )
    exit_code = main(["security", "."])
    assert exit_code == 1
    mock_security.assert_called_once_with()


@patch("py_gradeup.cli.PyGradeup.graph")
def test_graph_command(mock_graph, capsys) -> None:
    """Test the graph subcommand."""
    exit_code = main(["graph", "."])
    assert exit_code == 0
    mock_graph.assert_called_once_with()


from unittest.mock import patch, MagicMock


@patch("py_gradeup.cli.PyGradeup.test")
def test_test_command(mock_test, capsys) -> None:
    """Test."""
    from unittest.mock import MagicMock

    mock_test.return_value = MagicMock(all_passed=True, output="yay")
    exit_code = main(["test", "."])
    assert exit_code == 0
    mock_test.assert_called_once_with(parallel=True)


@patch("py_gradeup.cli.PyGradeup.test")
def test_test_command_fail(mock_test, capsys) -> None:
    """Test."""
    from unittest.mock import MagicMock

    mock_test.return_value = MagicMock(all_passed=False, output="nay")
    exit_code = main(["test", "."])
    assert exit_code == 1
    mock_test.assert_called_once_with(parallel=True)
