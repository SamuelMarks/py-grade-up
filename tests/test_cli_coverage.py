"""Module containing coverage tests."""

from unittest.mock import patch

from py_gradeup.cli import main
from py_gradeup.models import (
    AuditResult,
    FixResult,
    GraphResult,
    MatrixResult,
    RevertResult,
    SecurityResult,
)


@patch("py_gradeup.cli.PyGradeup")
def test_cli_coverage_audit(mock_sdk, capsys):
    """Test function."""
    mock_instance = mock_sdk.return_value
    mock_instance.audit.return_value = AuditResult(
        current_version="3.8",
        target_version="3.11",
        backup_name="backup.txt",
        files_to_upgrade=["a.py"],
        proposed_diffs=["diff"],
        dependency_updates={"req.txt": {"pkg": "1->2"}},
        docker_files_to_update=["Dockerfile"],
        ci_files_to_update=[".github/workflows/ci.yml"],
        cls_files_to_update=["setup.py"],
    )
    main(["audit", ".", "--diff"])

    mock_instance.audit.return_value = AuditResult(
        current_version="3.8",
        target_version="3.11",
        backup_name=None,
        files_to_upgrade=[],
        proposed_diffs=[],
        dependency_updates={},
        docker_files_to_update=[],
        ci_files_to_update=[],
        cls_files_to_update=[],
    )
    main(["audit", "."])


@patch("py_gradeup.cli.PyGradeup")
def test_cli_coverage_fix(mock_sdk, capsys):
    """Test function."""
    mock_instance = mock_sdk.return_value
    mock_instance.fix.return_value = FixResult(
        current_version="3.8",
        target_version="3.11",
        backup_path="backup.txt",
        files_upgraded=["a.py"],
        dependency_updates={"req.txt": {"pkg": "1->2"}},
        docker_files_updated=["Dockerfile"],
        ci_files_updated=[".github/workflows/ci.yml"],
        cls_files_updated=["setup.py"],
        tests_passed=True,
    )
    main(["fix", "."])

    mock_instance.fix.return_value = FixResult(
        current_version="3.8",
        target_version="3.11",
        backup_path=None,
        files_upgraded=[],
        dependency_updates={},
        docker_files_updated=[],
        ci_files_updated=[],
        cls_files_updated=[],
        tests_passed=False,
    )
    main(["fix", "."])

    mock_instance.fix.return_value = FixResult(
        current_version="3.8",
        target_version="3.11",
        backup_path=None,
        files_upgraded=[],
        dependency_updates={},
        docker_files_updated=[],
        ci_files_updated=[],
        cls_files_updated=[],
        tests_passed=None,
    )
    main(["fix", "."])


@patch("py_gradeup.cli.PyGradeup")
def test_cli_coverage_revert(mock_sdk, capsys):
    """Test function."""
    mock_instance = mock_sdk.return_value
    mock_instance.revert.return_value = RevertResult(
        git_restored=True, git_error=None, dependencies_restored_from="req.txt"
    )
    main(["revert", "."])

    mock_instance.revert.return_value = RevertResult(
        git_restored=False, git_error="error", dependencies_restored_from=None
    )
    main(["revert", "."])


@patch("py_gradeup.cli.PyGradeup")
def test_cli_coverage_security(mock_sdk, capsys):
    """Test function."""
    mock_instance = mock_sdk.return_value
    mock_instance.security.return_value = SecurityResult(
        vulnerabilities_found=True,
        vulnerabilities={"pkg==1.0": [{"id": "CVE-1", "details": "d" * 200}]},
    )
    main(["security", "."])

    mock_instance.security.return_value = SecurityResult(
        vulnerabilities_found=False, vulnerabilities={}
    )
    main(["security", "."])


@patch("py_gradeup.cli.PyGradeup")
def test_cli_coverage_test(mock_sdk, capsys):
    """Test function."""
    mock_instance = mock_sdk.return_value
    mock_instance.test.return_value = MatrixResult(
        all_passed=False, output="out", results={"env1": True, "env2": False}
    )
    main(["test", "."])


@patch("py_gradeup.cli.PyGradeup")
def test_cli_coverage_graph(mock_sdk, capsys):
    """Test function."""
    mock_instance = mock_sdk.return_value
    mock_instance.graph.return_value = GraphResult(
        tree="tree", conflict_error="conflict"
    )
    main(["graph", "."])

    mock_instance.graph.return_value = GraphResult(tree=None, conflict_error=None)
    main(["graph", "."])
