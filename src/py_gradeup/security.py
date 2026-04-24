"""Security auditing for dependencies."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request


def _parse_dependencies(file_path: str) -> dict[str, str]:
    """Parse dependencies and their versions from a file."""
    deps: dict[str, str] = {}
    if not os.path.exists(file_path):
        return deps

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    if (
        file_path.endswith(".toml")
        or file_path.endswith("setup.py")
        or file_path.endswith("setup.cfg")
    ):
        pattern = r'(["\']|^|\s)([a-zA-Z0-9\-_]+)(==)([0-9\.]+)(["\']|$|\s)'
        for match in re.finditer(pattern, content, flags=re.MULTILINE):
            deps[match.group(2).lower()] = match.group(4)
    elif file_path.endswith(".lock"):
        pattern = r'name\s*=\s*["\']([a-zA-Z0-9\-_]+)["\']\s*\n\s*version\s*=\s*["\']([0-9\.]+)["\']'  # noqa: E501
        for match in re.finditer(pattern, content):
            deps[match.group(1).lower()] = match.group(2)
    elif "Dockerfile" in os.path.basename(file_path) or file_path.endswith(
        ".Dockerfile"
    ):
        for line in content.splitlines():
            if "pip install" in line or "pip3 install" in line:
                for match in re.finditer(r"\b([a-zA-Z0-9\-_]+)==([0-9\.]+)\b", line):
                    deps[match.group(1).lower()] = match.group(2)
    else:
        # standard requirements.txt
        for line in content.splitlines():
            line = line.split("#")[0].strip()
            match_req = re.match(r"^([a-zA-Z0-9\-_]+)==([0-9\.]+)$", line)
            if match_req:
                deps[match_req.group(1).lower()] = match_req.group(2)

    return deps


def check_vulnerabilities(pkg_name: str, version: str) -> list[dict[str, str]]:
    """Check PyPI for known vulnerabilities of a specific package version."""
    url = f"https://pypi.org/pypi/{pkg_name}/{version}/json"
    req = urllib.request.Request(
        url, headers={"User-Agent": "py-gradeup-security-auditor"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            vulns = data.get("vulnerabilities", [])
            # PyPI vulnerabilities format typically has 'id' and 'details'
            return [
                {"id": v.get("id", "Unknown"), "details": v.get("details", "")}
                for v in vulns
            ]
    except (urllib.error.URLError, json.JSONDecodeError):
        # Ignore network errors or missing packages for the purpose of the audit
        return []
