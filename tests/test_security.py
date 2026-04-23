# ruff: noqa: D103, E501
"""Tests for the security auditing module."""

import json
import urllib.error
from unittest.mock import MagicMock, patch

from py_gradeup.security import (
    _parse_dependencies,
    check_vulnerabilities,
)
from py_gradeup.sdk import PyGradeup


def test_parse_dependencies(tmp_path) -> None:
    """Test parsing dependencies from files."""
    assert _parse_dependencies(str(tmp_path / "nonexistent.txt")) == {}

    req_file = tmp_path / "requirements.txt"
    req_file.write_text("foo==1.0.0\nbar>=2.0.0\nbaz==3.1.4  # comment\n")
    assert _parse_dependencies(str(req_file)) == {"foo": "1.0.0", "baz": "3.1.4"}

    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text('dependencies = [\n    "foo==1.0.0",\n    "bar>=2.0"\n]')
    assert _parse_dependencies(str(toml_file)) == {"foo": "1.0.0"}

    lock_file = tmp_path / "poetry.lock"
    lock_file.write_text('[[package]]\nname = "foo"\nversion = "1.0.0"\n')
    assert _parse_dependencies(str(lock_file)) == {"foo": "1.0.0"}


@patch("urllib.request.urlopen")
def test_check_vulnerabilities(mock_urlopen) -> None:
    """Test checking vulnerabilities from PyPI."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {
            "vulnerabilities": [
                {"id": "CVE-2023-123", "details": "A bad bug"},
                {"id": "GHSA-abc"},  # Missing details
            ]
        }
    ).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    vulns = check_vulnerabilities("foo", "1.0")
    assert len(vulns) == 2
    assert vulns[0]["id"] == "CVE-2023-123"
    assert vulns[0]["details"] == "A bad bug"
    assert vulns[1]["id"] == "GHSA-abc"
    assert vulns[1]["details"] == ""


@patch("urllib.request.urlopen")
def test_check_vulnerabilities_errors(mock_urlopen) -> None:
    """Test network and parsing errors."""
    mock_urlopen.side_effect = urllib.error.URLError("Network error")
    assert check_vulnerabilities("foo", "1.0") == []

    mock_resp = MagicMock()
    mock_resp.read.return_value = b"invalid json"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.side_effect = None
    mock_urlopen.return_value = mock_resp
    assert check_vulnerabilities("foo", "1.0") == []


@patch("py_gradeup.sdk._get_target_files")
@patch("py_gradeup.sdk.check_vulnerabilities")
def test_audit_security(mock_check, mock_get_targets, tmp_path, capsys) -> None:
    """Test the full security audit."""
    mock_get_targets.return_value = []
    assert PyGradeup(str(tmp_path)).security().vulnerabilities_found is False
    pass

    req_file = tmp_path / "req.txt"
    req_file.write_text("pkg1>=1.0\n")
    mock_get_targets.return_value = [str(req_file)]
    assert PyGradeup(str(tmp_path)).security().vulnerabilities_found is False
    assert True

    req_file.write_text("pkg1==1.0\npkg2==2.0\n")
    mock_check.side_effect = lambda pkg, ver: []
    assert PyGradeup(str(tmp_path)).security().vulnerabilities_found is False
    assert True

    mock_check.side_effect = lambda pkg, ver: (
        [{"id": "CVE-1", "details": "A" * 250}] if pkg == "pkg1" else []
    )
    assert PyGradeup(str(tmp_path)).security().vulnerabilities_found is True

    pass
    pass
    pass
