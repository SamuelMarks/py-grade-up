from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AuditResult:
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
    git_restored: bool
    git_error: Optional[str] = None
    dependencies_restored_from: Optional[str] = None


@dataclass
class TestResult:
    results: Dict[str, bool] = field(default_factory=dict)
    all_passed: bool = False
    output: str = ""


@dataclass
class SecurityResult:
    vulnerabilities_found: bool
    vulnerabilities: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)


@dataclass
class GraphResult:
    tree: Optional[str] = None
    conflict_error: Optional[str] = None
