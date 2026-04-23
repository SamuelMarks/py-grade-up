"""Data models for py-gradeup operations."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AuditResult:
    """Represents the results of an audit operation.

    Attributes:
        current_version: The currently detected Python version.
        target_version: The target Python version to upgrade to.
        backup_name: The name of the backup file created for requirements.
        files_to_upgrade: A list of file paths that require syntax upgrades.
        proposed_diffs: A list of unified diff strings showing proposed syntax changes.
        dependency_updates: A mapping of dependency file paths to their updates.
        ci_files_to_update: A list of CI/CD file paths requiring Python version updates.
        cls_files_to_update: A list of files needing classifier updates.
        docker_files_to_update: A list of Dockerfiles needing base image updates.
    """

    current_version: str
    target_version: str
    backup_name: Optional[str]
    files_to_upgrade: List[str] = field(default_factory=list)
    proposed_diffs: List[str] = field(default_factory=list)
    # Mapping of file_path -> {pkg_name: diff_str}
    dependency_updates: Dict[str, Dict[str, str]] = field(default_factory=dict)
    ci_files_to_update: List[str] = field(default_factory=list)
    cls_files_to_update: List[str] = field(default_factory=list)
    docker_files_to_update: List[str] = field(default_factory=list)


@dataclass
class FixResult:
    """Represents the results of a fix operation.

    Attributes:
        current_version: The currently detected Python version before the fix.
        target_version: The target Python version upgraded to.
        backup_path: The path to the backup file created for dependencies.
        files_upgraded: A list of file paths where syntax was upgraded.
        dependency_updates: A mapping of dependency file paths to their updates.
        ci_files_updated: A list of CI/CD file paths that were updated.
        cls_files_updated: A list of files where classifiers were updated.
        docker_files_updated: A list of Dockerfiles where base images were updated.
        tests_passed: Boolean indicating whether tests passed after fix,
            or None if skipped.
    """

    current_version: str
    target_version: str
    backup_path: Optional[str]
    files_upgraded: List[str] = field(default_factory=list)
    dependency_updates: Dict[str, Dict[str, str]] = field(default_factory=dict)
    ci_files_updated: List[str] = field(default_factory=list)
    cls_files_updated: List[str] = field(default_factory=list)
    docker_files_updated: List[str] = field(default_factory=list)
    tests_passed: Optional[bool] = None


@dataclass
class RevertResult:
    """Represents the results of a revert operation.

    Attributes:
        git_restored: Whether files were successfully restored via Git.
        git_error: Error message from Git, if any.
        dependencies_restored_from: The backup file from which dependencies
            were restored.
    """

    git_restored: bool
    git_error: Optional[str] = None
    dependencies_restored_from: Optional[str] = None


@dataclass
class TestResult:
    """Represents the results of a multi-environment test operation.

    Attributes:
        results: A mapping of environment names to boolean pass status.
        all_passed: True if tests passed in all tested environments.
        output: Combined output from test runners.
    """

    __test__ = False
    results: Dict[str, bool] = field(default_factory=dict)
    all_passed: bool = False
    output: str = ""


@dataclass
class SecurityResult:
    """Represents the results of a security audit operation.

    Attributes:
        vulnerabilities_found: True if any vulnerabilities were found in dependencies.
        vulnerabilities: A mapping of dependency strings to their vulnerability details.
    """

    vulnerabilities_found: bool
    vulnerabilities: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)


@dataclass
class GraphResult:
    """Represents the results of a dependency graph operation.

    Attributes:
        tree: The raw dependency tree output, if successful.
        conflict_error: The resolution error output, if conflicts exist.
    """

    tree: Optional[str] = None
    conflict_error: Optional[str] = None


@dataclass
class BisectResult:
    """Represents the results of a dependency bisect operation.

    Attributes:
        culprit: The package name that introduced the test failure, if found.
        old_version: The version of the culprit before the upgrade.
        new_version: The version of the culprit after the upgrade.
    """

    culprit: Optional[str] = None
    old_version: Optional[str] = None
    new_version: Optional[str] = None


@dataclass
class ResolveResult:
    """Represents the results of a conflict resolution operation.

    Attributes:
        success: True if a resolution suggestion was found.
        suggestions: A list of string constraints suggested to fix the graph conflicts.
        error: An error message if resolution suggestion failed.
    """

    success: bool
    suggestions: List[str] = field(default_factory=list)
    error: Optional[str] = None
