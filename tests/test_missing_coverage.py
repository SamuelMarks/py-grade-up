"""Module containing coverage tests."""

import sys
from unittest.mock import patch

import pytest

from py_gradeup.cli import main
from py_gradeup.models import AuditResult, FixResult, RevertResult
from py_gradeup.sdk import PyGradeup


def test_cli_audit_diff(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.audit") as mock_audit, patch(
        "py_gradeup.core._get_target_files"
    ) as mock_get_target_files:
        mock_get_target_files.return_value = []
        mock_audit.return_value = AuditResult(
            current_version="3.8",
            target_version="3.9",
            backup_name=None,
            files_to_upgrade=["a.py"],
            dependency_updates={},
            proposed_diffs=["diff line 1\n", "diff line 2\n"],
            ci_files_to_update=[],
            cls_files_to_update=[],
            docker_files_to_update=[],
        )
        with patch("sys.argv", ["py-gradeup", "audit", "--diff", "."]):
            main()
        out, _ = capsys.readouterr()
        assert "diff line 1" in out


def test_cli_audit_dependencies(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.audit") as mock_audit, patch(
        "py_gradeup.core._get_target_files"
    ) as mock_get_target_files, patch("os.path.exists", return_value=True), patch(
        "py_gradeup.core._should_modify", return_value=True
    ):
        mock_get_target_files.return_value = ["reqs.txt"]
        mock_audit.return_value = AuditResult(
            current_version="3.8",
            target_version="3.8",
            backup_name=None,
            files_to_upgrade=[],
            dependency_updates={"reqs.txt": {"requests": "requests>=2.0.0"}},
            proposed_diffs=[],
            ci_files_to_update=[],
            cls_files_to_update=[],
            docker_files_to_update=[],
        )
        with patch("sys.argv", ["py-gradeup", "audit", "."]):
            main()
        out, _ = capsys.readouterr()
        assert "- requests: requests>=2.0.0" in out


def test_cli_fix_dependencies(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.fix") as mock_fix, patch(
        "py_gradeup.core._get_target_files"
    ) as mock_get_target_files, patch("os.path.exists", return_value=True), patch(
        "py_gradeup.core._should_modify", return_value=True
    ):
        mock_get_target_files.return_value = ["reqs.txt"]
        mock_fix.return_value = FixResult(
            current_version="3.8",
            target_version="3.8",
            backup_path=None,
            files_upgraded=[],
            dependency_updates={"reqs.txt": {"requests": "requests>=2.0.0"}},
            ci_files_updated=[],
            cls_files_updated=[],
            docker_files_updated=[],
            tests_passed=None,
        )
        with patch("sys.argv", ["py-gradeup", "fix", "."]):
            main()
        out, _ = capsys.readouterr()
        assert "- requests: requests>=2.0.0" in out


def test_cli_fix_tests_failed(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.fix") as mock_fix, patch(
        "py_gradeup.core._get_target_files"
    ) as mock_get_target_files:
        mock_get_target_files.return_value = []
        mock_fix.return_value = FixResult(
            current_version="3.8",
            target_version="3.8",
            backup_path=None,
            files_upgraded=[],
            dependency_updates={},
            ci_files_updated=[],
            cls_files_updated=[],
            docker_files_updated=[],
            tests_passed=False,
        )
        with patch("sys.argv", ["py-gradeup", "fix", "--run-tests", "."]):
            main()
        out, _ = capsys.readouterr()
        assert "Verifying upgrades by running tests..." in out


def test_cli_revert_git_error(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.revert") as mock_revert:
        mock_revert.return_value = RevertResult(
            git_restored=False,
            git_error="Some strange error",
            dependencies_restored_from=None,
        )
        with patch("sys.argv", ["py-gradeup", "revert", "."]):
            main()
        _, err = capsys.readouterr()
        assert "Git restore failed: Some strange error" in err


def test_cli_security_no_target_files(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.security"), patch(
        "py_gradeup.core._get_target_files"
    ) as mock_get_target_files:
        mock_get_target_files.return_value = []
        with patch("sys.argv", ["py-gradeup", "security", "."]):
            assert main() == 0
        out, _ = capsys.readouterr()
        assert "No dependency files found to scan" in out


def test_cli_graph_no_target_files(capsys):
    """Test function."""
    with patch("py_gradeup.core._get_target_files") as mock_get_target_files:
        mock_get_target_files.return_value = []
        with patch("sys.argv", ["py-gradeup", "graph", "."]):
            assert main() == 0
        out, _ = capsys.readouterr()
        assert "No dependency files found to visualize" in out


def test_cli_main_block():
    """Test function."""
    with patch("sys.argv", ["py-gradeup", "audit", "."]), patch(
        "py_gradeup.cli.main", return_value=0
    ):
        with pytest.raises(SystemExit) as exc, open("src/py_gradeup/cli.py") as f:
            exec(f.read(), {"__name__": "__main__", "sys": sys})
        assert exc.value.code == 0


def test_sdk_fix_single_part_version():
    """Test function."""
    sdk = PyGradeup(path=".")
    with patch("py_gradeup.sdk._get_current_python_version", return_value="3.8"), patch(
        "py_gradeup.sdk._get_target_files", return_value=[]
    ), patch("py_gradeup.sdk._find_target_python", return_value=("3", {})), patch(
        "py_gradeup.sdk._get_py_files", return_value=[]
    ), patch("py_gradeup.core._update_python_version_bounds", return_value=False):
        res = sdk.fix()
        assert res.target_version == "3"


def test_sdk_fix_docker_files():
    """Test function."""
    sdk = PyGradeup(path=".")
    with patch("py_gradeup.sdk._get_current_python_version", return_value="3.8"), patch(
        "py_gradeup.sdk._get_target_files", return_value=[]
    ), patch("py_gradeup.sdk._find_target_python", return_value=("3.9", {})), patch(
        "py_gradeup.sdk._get_py_files", return_value=[]
    ), patch("py_gradeup.core._update_python_version_bounds", return_value=True), patch(
        "py_gradeup.sdk._update_ci_cd_environments", return_value=[]
    ), patch("py_gradeup.sdk._update_python_classifiers", return_value=[]), patch(
        "py_gradeup.sdk._update_dockerfiles", return_value=["Dockerfile"]
    ):
        with patch("subprocess.run"):
            res = sdk.fix(commit=True)
        assert "Dockerfile" in res.docker_files_updated


def test_sdk_fix_exception_in_pyupgrade():
    """Test function."""
    sdk = PyGradeup(path=".")
    with patch("py_gradeup.sdk._get_current_python_version", return_value="3.8"), patch(
        "py_gradeup.sdk._get_target_files", return_value=[]
    ), patch("py_gradeup.sdk._find_target_python", return_value=("3.9", {})), patch(
        "py_gradeup.sdk._get_py_files", return_value=["test.py"]
    ), patch("py_gradeup.sdk._should_modify", return_value=True), patch(
        "py_gradeup.core._update_python_version_bounds", return_value=False
    ), patch("builtins.open") as mock_open:
        mock_open.side_effect = Exception("Read error")
        res = sdk.fix()
        assert len(res.files_upgraded) == 0


def test_sdk_fix_any_deps_bumped():
    """Test function."""
    sdk = PyGradeup(path=".")
    with patch("py_gradeup.sdk._get_current_python_version", return_value="3.8"), patch(
        "py_gradeup.sdk._get_target_files", return_value=["reqs.txt"]
    ), patch("py_gradeup.sdk._find_target_python", return_value=("3.9", {})), patch(
        "os.path.exists", return_value=True
    ), patch("py_gradeup.sdk._should_modify", return_value=True), patch(
        "py_gradeup.sdk._update_dependencies_file", return_value={"r": "r>=2.0"}
    ), patch("py_gradeup.sdk._get_py_files", return_value=[]), patch(
        "py_gradeup.core._update_python_version_bounds", return_value=False
    ):
        with patch("subprocess.run"):
            res = sdk.fix(commit=True)
        assert res.dependency_updates == {"reqs.txt": {"r": "r>=2.0"}}


def test_cli_revert_git_not_found(capsys):
    """Test function."""
    with patch("py_gradeup.sdk.PyGradeup.revert") as mock_revert:
        mock_revert.return_value = RevertResult(
            git_restored=False,
            git_error="Git not found. Please install git.",
            dependencies_restored_from=None,
        )
        with patch("sys.argv", ["py-gradeup", "revert", "."]):
            main()
        _, err = capsys.readouterr()
        assert "Git not found. Cannot automatically revert files." in err
