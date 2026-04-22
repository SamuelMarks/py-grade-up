# ruff: noqa: E501
"""Security auditing for dependencies."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from py_gradeup.core import _get_target_files


def _parse_dependencies(file_path: str) -> dict[str, str]:
    """Parse dependencies and their versions from a file."""
    deps = {}
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
        pattern = r'name\s*=\s*["\']([a-zA-Z0-9\-_]+)["\']\s*\n\s*version\s*=\s*["\']([0-9\.]+)["\']'
        for match in re.finditer(pattern, content):
            deps[match.group(1).lower()] = match.group(2)
    else:
        # standard requirements.txt
        for line in content.splitlines():
            line = line.split("#")[0].strip()
            match = re.match(r"^([a-zA-Z0-9\-_]+)==([0-9\.]+)$", line)
            if match:
                deps[match.group(1).lower()] = match.group(2)

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


def audit_security(path: str) -> bool:
    """
    Audit the project dependencies for security vulnerabilities.

    Args:
        path: Path to the project directory.

    Returns:
        True if vulnerabilities were found, False otherwise.
    """
    print(f"Scanning project for security vulnerabilities at {path}")
    target_files = _get_target_files(path)

    if not target_files:
        print("No dependency files found to scan.")
        return False

    all_deps = {}
    for t_file in target_files:
        deps = _parse_dependencies(t_file)
        all_deps.update(deps)

    if not all_deps:
        print("No pinned dependencies (==) found to scan.")
        return False

    print(
        f"Found {len(all_deps)} pinned dependencies. Checking against vulnerability databases..."
    )

    found_vulns = False
    for pkg, version in sorted(all_deps.items()):
        vulns = check_vulnerabilities(pkg, version)
        if vulns:
            found_vulns = True
            print(f"\\n[!] Vulnerabilities found in {pkg}=={version}:")
            for v in vulns:
                print(f"    - ID: {v['id']}")
                if v["details"]:
                    # truncate details if too long
                    details = v["details"]
                    if len(details) > 200:
                        details = details[:197] + "..."
                    print(f"      Details: {details}")

    if not found_vulns:
        print("\\nNo known vulnerabilities found in pinned dependencies.")

    return found_vulns
