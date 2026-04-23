# ruff: noqa: E501, SIM102, SIM115
"""Core logic for py-gradeup auditing and fixing."""

from __future__ import annotations

import difflib
import os
import re
import subprocess
import sys
import tempfile

try:
    from pyupgrade._main import (  # type: ignore[import-untyped]
        Settings,
        _fix_plugins,
        _fix_tokens,
    )
except ImportError:
    # fallback for tests if pyupgrade isn't fully available
    Settings = None

    def _fix_plugins(text: str, settings: object | None) -> str:
        """Run pyupgrade plugins."""
        return text

    def _fix_tokens(text: str) -> str:
        """Run pyupgrade token fixers."""
        return text


def _prompt_diff(file_path: str, old_content: str, new_content: str) -> bool:
    """Show diff and prompt user to accept changes."""
    diff = list(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{os.path.basename(file_path)}",
            tofile=f"b/{os.path.basename(file_path)}",
        )
    )
    if not diff:
        return False
    sys.stdout.writelines(diff)
    while True:
        sys.stdout.write(f"Apply changes to {file_path}? [y/N]: ")
        sys.stdout.flush()
        try:
            ans = input().strip().lower()
        except EOFError:
            return False
        if ans in ("y", "yes"):
            return True
        elif ans in ("n", "no", ""):
            return False


def _get_py_files(path: str) -> list[str]:
    """Get all Python files in the given path."""
    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        return [path]
    for root, dirs, files in os.walk(path):
        # Exclude hidden directories like .venv, .git, etc.
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files


def _check_pyupgrade(content: str, target_py_version: tuple[int, int]) -> str:
    """Run pyupgrade on the given content."""
    if Settings is None:
        return content
    settings = Settings(
        min_version=target_py_version,
        keep_percent_format=False,
        keep_mock=False,
        keep_runtime_typing=False,
    )
    new_content = _fix_plugins(content, settings=settings)
    new_content = _fix_tokens(new_content)
    return new_content


def _get_current_python_version(path: str) -> str:
    """Extract current python version from build config files."""
    pyproject_path = os.path.join(path, "pyproject.toml")
    if os.path.exists(pyproject_path):
        with open(pyproject_path, encoding="utf-8") as f:
            for line in f:
                match = re.match(r'^requires-python\s*=\s*">=(3\.\d+)"', line.strip())
                if match:
                    return match.group(1)

    setup_cfg_path = os.path.join(path, "setup.cfg")
    if os.path.exists(setup_cfg_path):
        with open(setup_cfg_path, encoding="utf-8") as f:
            for line in f:
                match = re.match(r"^python_requires\s*=\s*>=(3\.\d+)", line.strip())
                if match:
                    return match.group(1)

    setup_py_path = os.path.join(path, "setup.py")
    if os.path.exists(setup_py_path):
        with open(setup_py_path, encoding="utf-8") as f:
            for line in f:
                match = re.search(r'python_requires\s*=\s*[\'"]>=(3\.\d+)[\'"]', line)
                if match:
                    return match.group(1)

    pipfile_path = os.path.join(path, "Pipfile")
    if os.path.exists(pipfile_path):
        with open(pipfile_path, encoding="utf-8") as f:
            for line in f:
                match = re.match(
                    r'^python_version\s*=\s*[\'"](3\.\d+)[\'"]', line.strip()
                )
                if match:
                    return match.group(1)

    for env_file in ["environment.yml", "environment.yaml"]:
        env_path = os.path.join(path, env_file)
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    match = re.search(r"-\s*python\s*[>=]=?\s*(3\.\d+)", line)
                    if match:
                        return match.group(1)

    return "3.8"  # default


def _should_modify(filepath: str, only_types: list[str] | None) -> bool:
    """Check if a file should be modified based on the only flag."""
    if not only_types:
        return True

    filepath_lower = filepath.lower()
    for t in only_types:
        t = t.lower().strip()
        if t == "python" and filepath_lower.endswith(".py"):
            return True
        if t == "toml" and filepath_lower.endswith(".toml"):
            return True
        if t == "ghactions" and ".github/workflows" in filepath_lower.replace(
            "\\", "/"
        ):
            return True
        if t == "docker" and "dockerfile" in os.path.basename(filepath_lower):
            return True
        if t in ("yaml", "yml") and (
            filepath_lower.endswith(".yaml") or filepath_lower.endswith(".yml")
        ):
            return True
        if filepath_lower.endswith(f".{t}"):
            return True
    return False


def _update_python_version_bounds(
    path: str,
    target_py: str,
    dry_run: bool = False,
    only: list[str] | None = None,
    workspace: bool = False,
) -> bool:
    """Update requires-python in pyproject.toml, setup.cfg, and setup.py."""
    import os
    import re

    updated = False

    def do_for_dir(p: str) -> None:
        """Process directory."""
        nonlocal updated
        pyproject_path = os.path.join(p, "pyproject.toml")
        if os.path.exists(pyproject_path) and _should_modify(pyproject_path, only):
            with open(pyproject_path, encoding="utf-8") as f:
                content_f = f.read()
            new_content, count = re.subn(
                r'(requires-python\s*=\s*">=)(3\.\d+)(")',
                rf"\g<1>{target_py}\g<3>",
                content_f,
            )
            if count > 0 and new_content != content_f:
                updated = True
                if not dry_run:
                    with open(pyproject_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

        setup_cfg_path = os.path.join(p, "setup.cfg")
        if os.path.exists(setup_cfg_path) and _should_modify(setup_cfg_path, only):
            with open(setup_cfg_path, encoding="utf-8") as f:
                content_f = f.read()
            new_content, count = re.subn(
                r"(python_requires\s*=\s*>=)(3\.\d+)", rf"\g<1>{target_py}", content_f
            )
            if count > 0 and new_content != content_f:
                updated = True
                if not dry_run:
                    with open(setup_cfg_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

        setup_py_path = os.path.join(p, "setup.py")
        if os.path.exists(setup_py_path) and _should_modify(setup_py_path, only):
            with open(setup_py_path, encoding="utf-8") as f:
                content_f = f.read()
            new_content, count = re.subn(
                r'(python_requires\s*=\s*[\'"]>=)(3\.\d+)([\'"])',
                rf"\g<1>{target_py}\g<3>",
                content_f,
            )
            if count > 0 and new_content != content_f:
                updated = True
                if not dry_run:
                    with open(setup_py_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

        pipfile_path = os.path.join(p, "Pipfile")
        if os.path.exists(pipfile_path) and _should_modify(pipfile_path, only):
            with open(pipfile_path, encoding="utf-8") as f:
                content_f = f.read()
            new_content, count = re.subn(
                r'(python_version\s*=\s*[\'"])(3\.\d+)([\'"])',
                rf"\g<1>{target_py}\g<3>",
                content_f,
            )
            if count > 0 and new_content != content_f:
                updated = True
                if not dry_run:
                    with open(pipfile_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

        for env_file in ["environment.yml", "environment.yaml"]:
            env_path = os.path.join(p, env_file)
            if os.path.exists(env_path) and _should_modify(env_path, only):
                with open(env_path, encoding="utf-8") as f:
                    content_f = f.read()
                new_content, count = re.subn(
                    r"(-\s*python\s*[>=]=?\s*)(3\.\d+)", rf"\g<1>{target_py}", content_f
                )
                if count > 0 and new_content != content_f:
                    updated = True
                    if not dry_run:
                        with open(env_path, "w", encoding="utf-8") as f:
                            f.write(new_content)

    if workspace:
        for root, dirs, _files in os.walk(path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in ("venv", "env", "node_modules", "dist", "build", "__pycache__")
            ]
            do_for_dir(root)
    else:
        do_for_dir(path)

    return updated


def _get_target_files(path: str, workspace: bool = False) -> list[str]:
    """Find the target files for dependency resolution."""
    target_files = []
    if os.path.exists(path) and os.path.isdir(path):
        if workspace:
            for root, dirs, files in os.walk(path):
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d
                    not in (
                        "venv",
                        "env",
                        "node_modules",
                        "dist",
                        "build",
                        "__pycache__",
                    )
                ]
                for f in files:
                    if f in (
                        "pyproject.toml",
                        "setup.py",
                        "setup.cfg",
                        "poetry.lock",
                        "pdm.lock",
                        "uv.lock",
                        "Pipfile",
                        "Pipfile.lock",
                        "environment.yml",
                        "environment.yaml",
                    ):
                        target_files.append(os.path.join(root, f))
                    elif "requirements" in f and f.endswith(".txt"):
                        if not re.match(r"^requirements-\d+(-\d+)?\.txt$", f):
                            target_files.append(os.path.join(root, f))
                    elif "Dockerfile" in f or f.endswith(".Dockerfile"):
                        target_files.append(os.path.join(root, f))
        else:
            for f in os.listdir(path):
                if f in (
                    "pyproject.toml",
                    "setup.py",
                    "setup.cfg",
                    "poetry.lock",
                    "pdm.lock",
                    "uv.lock",
                    "Pipfile",
                    "Pipfile.lock",
                    "environment.yml",
                    "environment.yaml",
                ):
                    target_files.append(os.path.join(path, f))
                elif "requirements" in f and f.endswith(".txt"):
                    if not re.match(r"^requirements-\d+(-\d+)?\.txt$", f):
                        target_files.append(os.path.join(path, f))
                elif "Dockerfile" in f or f.endswith(".Dockerfile"):
                    target_files.append(os.path.join(path, f))
    return target_files


def _prepare_compile_targets(
    target_files: list[str], tmp_paths: list[str]
) -> list[str]:
    """Convert supported target files into a list of valid requirements for uv."""
    compile_targets = []

    for fpath in target_files:
        if fpath.endswith(".txt"):
            with open(fpath, encoding="utf-8") as f:
                lines = f.readlines()

            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".in")
            tmp_paths.append(tmp.name)
            for line in lines:
                m = re.match(r"^([a-zA-Z0-9\-_]+)[>=]=([0-9\.]+)", line.strip())
                if m:
                    tmp.write(f"{m.group(1)}>={m.group(2)}\n")
                else:
                    tmp.write(line)
            tmp.close()
            compile_targets.append(tmp.name)
        elif fpath.endswith(".lock"):
            if fpath.endswith("Pipfile.lock"):
                import json

                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".in")
                tmp_paths.append(tmp.name)
                for section in ["default", "develop"]:
                    for pkg, info in data.get(section, {}).items():
                        version = info.get("version", "").lstrip("=")
                        if version:
                            tmp.write(f"{pkg}=={version}\n")
                tmp.close()
                compile_targets.append(tmp.name)
            else:
                with open(fpath, encoding="utf-8") as f:
                    content_f = f.read()
                tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".in")
                tmp_paths.append(tmp.name)
                for match in re.finditer(
                    r"name\s*=\s*[\"']([^\"']+)[\"'].*?version\s*=\s*[\"']([^\"']+)[\"']",
                    content_f,
                    re.DOTALL,
                ):
                    if "[[package]]" not in match.group(0)[10:]:
                        tmp.write(f"{match.group(1)}=={match.group(2)}\n")
                tmp.close()
                compile_targets.append(tmp.name)
        elif fpath.endswith(".yml") or fpath.endswith(".yaml"):
            with open(fpath, encoding="utf-8") as f:
                content_f = f.read()
            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".in")
            tmp_paths.append(tmp.name)
            for match in re.finditer(
                r"-\s*([a-zA-Z0-9\-_]+)[>=]=?([0-9\.]+)", content_f
            ):
                if match.group(1).lower() != "python":
                    tmp.write(f"{match.group(1)}>={match.group(2)}\n")
            tmp.close()
            compile_targets.append(tmp.name)
        elif fpath.endswith("Pipfile"):
            with open(fpath, encoding="utf-8") as f:
                content_f = f.read()
            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".in")
            tmp_paths.append(tmp.name)
            for match in re.finditer(
                r"^([a-zA-Z0-9\-_]+)\s*=\s*[\"'][>=]=?([0-9\.]+)[\"']",
                content_f,
                re.MULTILINE,
            ):
                tmp.write(f"{match.group(1)}>={match.group(2)}\n")
            tmp.close()
            compile_targets.append(tmp.name)
        else:
            compile_targets.append(fpath)

    return compile_targets


def _find_target_python(
    target_files: list[str], current_ver: str
) -> tuple[str, dict[str, str]]:
    """Use uv (or pyenv fallback) to find the highest workable python version."""
    import json

    candidates = ["3.14", "3.13", "3.12", "3.11", "3.10", "3.9", "3.8"]

    try:
        c_parts = tuple(map(int, current_ver.split(".")))
        candidates = [c for c in candidates if tuple(map(int, c.split("."))) > c_parts]
    except Exception:
        pass

    if not candidates:
        return current_ver, {}

    if not target_files:
        return candidates[0] if candidates else current_ver, {}

    tmp_paths: list[str] = []
    compile_targets = []

    try:
        compile_targets = _prepare_compile_targets(target_files, tmp_paths)

        for candidate in candidates:
            # 1) Try uv
            cmd = [
                "uv",
                "pip",
                "compile",
                "--resolution",
                "lowest-direct",
                "--python-version",
                candidate,
            ] + compile_targets
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                deps = {}
                for line in result.stdout.splitlines():
                    m = re.match(r"^([a-zA-Z0-9\-_]+)==([0-9\.\w]+)", line)
                    if m:
                        deps[m.group(1).lower()] = m.group(2)
                return candidate, deps
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            # 2) Fallback to pyenv python3 -m pip install --dry-run
            env = os.environ.copy()
            env["PYENV_VERSION"] = candidate
            pip_args = []
            for ct in compile_targets:
                if ct.endswith(".in") or ct.endswith(".txt"):
                    pip_args.extend(["-r", ct])
                else:
                    pip_args.append(ct)
            cmd_pyenv = [
                "python3",
                "-m",
                "pip",
                "install",
                "--ignore-installed",
                "--dry-run",
                "--report",
                "-",
            ] + pip_args

            try:
                result_pyenv = subprocess.run(
                    cmd_pyenv, env=env, capture_output=True, text=True, check=True
                )
                report = json.loads(result_pyenv.stdout)
                deps = {}
                for item in report.get("install", []):
                    meta = item.get("metadata", {})
                    name = meta.get("name")
                    version = meta.get("version")
                    if name and version:
                        deps[name.lower()] = version
                return candidate, deps
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                json.JSONDecodeError,
            ):
                continue
    finally:
        for tmp_path in tmp_paths:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return current_ver, {}


def _backup_old_requirements(
    path: str, current_ver: str, target_files: list[str]
) -> str:
    """Create a backup of the old requirements using uv or pyenv fallback."""
    import json

    parts = current_ver.split(".")
    if len(parts) >= 2:
        backup_name = f"requirements-{parts[0]}-{parts[1]}.txt"
    else:
        backup_name = f"requirements-{current_ver}.txt"

    backup_path = os.path.join(path, backup_name)

    cmd = [
        "uv",
        "pip",
        "compile",
        "--python-version",
        current_ver,
        "-o",
        backup_path,
    ] + target_files
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return backup_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    env = os.environ.copy()
    env["PYENV_VERSION"] = current_ver
    pip_args = []
    for tf in target_files:
        if tf.endswith(".txt") or tf.endswith(".in"):
            pip_args.extend(["-r", tf])
        else:
            pip_args.append(tf)

    cmd_pyenv = [
        "python3",
        "-m",
        "pip",
        "install",
        "--ignore-installed",
        "--dry-run",
        "--report",
        "-",
    ] + pip_args

    try:
        res = subprocess.run(
            cmd_pyenv, env=env, capture_output=True, text=True, check=True
        )
        report = json.loads(res.stdout)
        with open(backup_path, "w", encoding="utf-8") as f:
            for item in report.get("install", []):
                meta = item.get("metadata", {})
                name = meta.get("name")
                version = meta.get("version")
                if name and version:
                    f.write(f"{name}=={version}\n")
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(f"# Failed to compile for {current_ver}\n")

    return backup_path


def _update_dependencies_file(
    file_path: str,
    resolved_deps: dict[str, str],
    dry_run: bool = False,
    interactive: bool = False,
) -> dict[str, str]:
    """Update dependencies in a given file (.txt, .toml, setup.py, setup.cfg)."""
    if not os.path.exists(file_path):
        return {}

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    updates = {}

    if (
        file_path.endswith(".toml")
        or file_path.endswith("setup.py")
        or file_path.endswith("Pipfile")
    ):
        pattern = r"([\"\']|^|\n)([a-zA-Z0-9\-_]+)([\"\']?\s*[=:]\s*[\"\']?[>=]=?|[>=]=?)([0-9\.]+)([\"\']?)"
    elif file_path.endswith(".lock"):
        if file_path.endswith("Pipfile.lock"):
            pattern = r"([\"\'])([a-zA-Z0-9\-_]+)([\"\']\s*:\s*\{\s*[\"\']version[\"\']\s*:\s*[\"\']={1,2})([0-9\.]+)([\"\'])"
        else:
            pattern = r"(name\s*=\s*[\"\'])([a-zA-Z0-9\-_]+)([\"\']\s*\n\s*version\s*=\s*[\"\'])([0-9\.]+)([\"\'])"
    elif file_path.endswith(".yml") or file_path.endswith(".yaml"):
        pattern = r"(-\s*)([a-zA-Z0-9\-_]+)([>=]=?)([0-9\.]+)($|\s)"
    else:
        pattern = r"(^|\s)([a-zA-Z0-9\-_]+)([>=]=)([0-9\.]+)($|\s)"

    def replacer(match: re.Match) -> str:
        """Replace dependency version in file."""
        prefix = match.group(1)
        pkg = match.group(2)
        op = match.group(3)
        curr_ver = match.group(4)
        suffix = match.group(5)

        new_ver = resolved_deps.get(pkg.lower())
        if new_ver and new_ver != curr_ver:
            updates[pkg] = f"{curr_ver} -> {new_ver}"
            return f"{prefix}{pkg}{op}{new_ver}{suffix}"
        return match.group(0)

    new_content = re.sub(pattern, replacer, content, flags=re.MULTILINE)

    if not dry_run and updates and new_content != content:
        if interactive and not _prompt_diff(file_path, content, new_content):
            return {}  # Return empty updates since we skipped
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    return updates


def _update_python_classifiers(
    path: str,
    target_py: str,
    dry_run: bool = False,
    only: list[str] | None = None,
    workspace: bool = False,
) -> list[str]:
    """Clean up and bump Python classifiers in config files."""
    updated_files = []
    target_major, target_minor = map(int, target_py.split("."))

    files_to_check = []
    if workspace:
        for root, dirs, files in os.walk(path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in ("venv", "env", "node_modules", "dist", "build", "__pycache__")
            ]
            for filename in ["pyproject.toml", "setup.cfg", "setup.py"]:
                if filename in files:
                    files_to_check.append(os.path.join(root, filename))
    else:
        for filename in ["pyproject.toml", "setup.cfg", "setup.py"]:
            files_to_check.append(os.path.join(path, filename))

    for fpath in files_to_check:
        if not os.path.exists(fpath) or not _should_modify(fpath, only):
            continue

        with open(fpath, encoding="utf-8") as f:
            content = f.read()

        existing_vers = []
        for m in re.finditer(r"Programming Language :: Python :: (3\.\d+)", content):
            existing_vers.append(m.group(1))

        if not existing_vers:
            continue

        target_in_list = target_py in existing_vers
        added_target = target_in_list

        def repl(m: re.Match) -> str:
            """Replace old Python versions with target Python version."""
            nonlocal added_target
            ver_str = m.group(1)
            full_match = m.group(0)

            major, minor = map(int, ver_str.split("."))
            if (major, minor) < (target_major, target_minor):
                if not added_target:
                    added_target = True
                    return full_match.replace(ver_str, target_py)
                else:
                    return ""
            return full_match

        new_content = re.sub(
            r'^[ \t]*["\']?Programming Language :: Python :: (3\.\d+)["\']?,?[ \t]*(?:\r?\n|$)',
            repl,
            content,
            flags=re.MULTILINE,
        )

        if new_content != content:
            if not dry_run:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
            updated_files.append(fpath)

    return updated_files


def _update_dockerfiles(
    path: str,
    target_py: str,
    dry_run: bool = False,
    only: list[str] | None = None,
    workspace: bool = False,
) -> list[str]:
    """Update Python versions in Dockerfiles."""
    updated_files = []

    files_to_check = []
    if workspace:
        for root, dirs, files in os.walk(path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in ("venv", "env", "node_modules", "dist", "build", "__pycache__")
            ]
            for filename in files:
                if filename.startswith("Dockerfile") or filename.endswith(
                    ".Dockerfile"
                ):
                    files_to_check.append(os.path.join(root, filename))
    else:
        if os.path.exists(path) and os.path.isdir(path):
            for filename in os.listdir(path):
                if filename.startswith("Dockerfile") or filename.endswith(
                    ".Dockerfile"
                ):
                    files_to_check.append(os.path.join(path, filename))

    for fpath in files_to_check:
        if True:
            if not os.path.isfile(fpath) or not _should_modify(fpath, only):
                continue

            with open(fpath, encoding="utf-8") as f:
                content = f.read()

            new_content = re.sub(
                r"^(FROM\s+(?:.*python|python)(?:[^:]*:))3\.\d+(?:\.\d+)?([\w\.-]*)$",
                rf"\g<1>{target_py}\g<2>",
                content,
                flags=re.MULTILINE | re.IGNORECASE,
            )

            if new_content != content:
                if not dry_run:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                updated_files.append(fpath)

    return updated_files


def _update_ci_cd_environments(
    path: str,
    target_py: str,
    dry_run: bool = False,
    only: list[str] | None = None,
    workspace: bool = False,
) -> list[str]:
    """Update Python version matrices in CI/CD files."""
    updated_files = []

    tox_paths = []
    if workspace:
        for root, dirs, files in os.walk(path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in ("venv", "env", "node_modules", "dist", "build", "__pycache__")
            ]
            if "tox.ini" in files:
                tox_paths.append(os.path.join(root, "tox.ini"))
    else:
        tox_paths.append(os.path.join(path, "tox.ini"))

    for tox_path in tox_paths:
        if not os.path.exists(tox_path) or not _should_modify(tox_path, only):
            continue
        with open(tox_path, encoding="utf-8") as f:
            content = f.read()

        target_env = f"py{target_py.replace('.', '')}"
        lines = []
        changed = False
        for line in content.splitlines():
            if line.strip().startswith("envlist"):
                new_line = re.sub(r"\bpy3\d+\b", target_env, line)
                if "=" in new_line:
                    prefix, envs_str = new_line.split("=", 1)
                    envs = [e.strip() for e in envs_str.split(",")]
                    envs = list(dict.fromkeys(envs))
                    new_line = prefix + "= " + ", ".join(envs)
                if new_line != line:
                    changed = True
                lines.append(new_line)
            else:
                new_line = re.sub(r"\bpy3\d+\b", target_env, line)
                if new_line != line:
                    changed = True
                lines.append(new_line)

        if changed:
            new_content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")
            if not dry_run:
                with open(tox_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
            updated_files.append(tox_path)

    ci_files = []

    def gather_ci(p: str) -> None:
        """Gather CI files in directory."""
        gitlab_ci = os.path.join(p, ".gitlab-ci.yml")
        if os.path.exists(gitlab_ci):
            ci_files.append(gitlab_ci)
        noxfile = os.path.join(p, "noxfile.py")
        if os.path.exists(noxfile):
            ci_files.append(noxfile)
        pre_commit = os.path.join(p, ".pre-commit-config.yaml")
        if os.path.exists(pre_commit):
            ci_files.append(pre_commit)

    if workspace:
        for root, dirs, _files in os.walk(path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in ("venv", "env", "node_modules", "dist", "build", "__pycache__")
            ]
            gather_ci(root)
    else:
        gather_ci(path)

    # Always check root .github
    gh_dir = os.path.join(path, ".github", "workflows")
    if os.path.exists(gh_dir) and os.path.isdir(gh_dir):
        for filename in os.listdir(gh_dir):
            if filename.endswith(".yml") or filename.endswith(".yaml"):
                ci_files.append(os.path.join(gh_dir, filename))

    py_ver = os.path.join(path, ".python-version")
    if os.path.exists(py_ver):
        ci_files.append(py_ver)

    for ci_file in ci_files:
        if not _should_modify(ci_file, only):
            continue

        with open(ci_file, encoding="utf-8") as f:
            content = f.read()

        new_content = re.sub(
            r'\[\s*(?:[\'"]?3\.\d+[\'"]?\s*,\s*)*[\'"]?3\.\d+[\'"]?\s*\]',
            f'["{target_py}"]',
            content,
        )
        new_content = re.sub(
            r'(python-version\s*:\s*|UV_PYTHON\s*:\s*|python\s*:\s*(?:python)?|image\s*:\s*python:|python_versions\s*=\s*|python\s*=\s*|language_version\s*:\s*python)([\'"]?)3\.\d+([\'"]?)',
            rf"\g<1>\g<2>{target_py}\g<3>",
            new_content,
        )
        keys_pattern = r"python-version|UV_PYTHON|python|python_versions"
        new_content = re.sub(
            rf'({keys_pattern})\s*:\s*\n([ \t]*-\s*[\'"]?)3\.\d+([\'"]?(?:\s*\n|$))(?:[ \t]*-\s*[\'"]?3\.\d+[\'"]?(?:\s*\n|$))*',
            rf"\g<1>:\n\g<2>{target_py}\g<3>",
            new_content,
        )
        new_content = re.sub(
            rf'({keys_pattern})\s*:\s*\|\s*\n(?:[ \t]+[\'"]?3\.\d+[\'"]?\s*\n)*([ \t]+[\'"]?)3\.\d+([\'"]?(?:\s*\n|$))',
            rf"\g<1>: |\n\g<2>{target_py}\g<3>",
            new_content,
        )

        if new_content != content:
            if not dry_run:
                with open(ci_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
            updated_files.append(ci_file)

    python_version_file = os.path.join(path, ".python-version")
    if os.path.exists(python_version_file) and _should_modify(
        python_version_file, only
    ):
        with open(python_version_file, encoding="utf-8") as f:
            content = f.read()

        new_content = re.sub(r"^3\.\d+(?:\.\d+)?", target_py, content)
        if new_content != content:
            if not dry_run:
                with open(python_version_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
            updated_files.append(python_version_file)

    return updated_files


def _run_tests(path: str) -> bool:
    """
    Run tests in the project to verify changes.

    Args:
        path: The path to the project directory.

    Returns:
        True if tests passed or runner not found but no crash, False if tests failed.
    """
    tox_path = os.path.join(path, "tox.ini")
    nox_path = os.path.join(path, "noxfile.py")

    if os.path.exists(tox_path):
        cmd = ["tox"]
    elif os.path.exists(nox_path):
        cmd = ["nox"]
    else:
        cmd = ["pytest"]

    try:
        subprocess.run(cmd, cwd=path, check=True)

        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def _recreate_venv(path: str, target_py: str, versioned: bool = False) -> bool:
    """
    Destroy and rebuild local .venv using the newly targeted version.

    Args:
        path: The path to the project directory.
        target_py: The target Python version.
        versioned: Whether to create a versioned virtual environment (e.g. .venv-uv-3-12).

    Returns:
        True if successful, False otherwise.
    """
    import shutil

    if not versioned:
        venv_path = os.path.join(path, ".venv")
        if not os.path.exists(venv_path):
            return False

        try:
            shutil.rmtree(venv_path)
        except Exception:
            return False

    version_suffix = target_py.replace(".", "-")

    # Try uv first
    venv_dir_uv = f".venv-uv-{version_suffix}" if versioned else ".venv"
    venv_path_uv = os.path.join(path, venv_dir_uv)

    if versioned:
        if os.path.exists(venv_path_uv):
            try:
                shutil.rmtree(venv_path_uv)
            except Exception:
                return False

    cmd_uv = ["uv", "venv", venv_dir_uv, "--python", target_py]
    try:
        subprocess.run(cmd_uv, cwd=path, capture_output=True, text=True, check=True)

        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try pyenv fallback
    venv_dir_pyenv = f".venv-pyenv-{version_suffix}" if versioned else ".venv"
    venv_path_pyenv = os.path.join(path, venv_dir_pyenv)

    if versioned:
        if os.path.exists(venv_path_pyenv):
            try:
                shutil.rmtree(venv_path_pyenv)
            except Exception:
                return False

    env = os.environ.copy()
    env["PYENV_VERSION"] = target_py
    cmd_pyenv = ["python3", "-m", "venv", venv_dir_pyenv]
    try:
        subprocess.run(
            cmd_pyenv, env=env, cwd=path, capture_output=True, text=True, check=True
        )

        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _run_test_env(
    path: str, backend: str, v: str, uses_pytest: bool
) -> tuple[str, bool, str]:
    """Helper."""
    import os
    import shutil
    import subprocess

    env_name = f"{backend}-{v}"
    output_lines = [f"\n--- Testing environment: {env_name} ---"]
    venv_dir = f".venv-{backend}-{v.replace('.', '-')}"
    venv_path = os.path.join(path, venv_dir)

    if os.path.exists(venv_path):
        try:
            shutil.rmtree(venv_path)
        except Exception as e:
            output_lines.append(f"Failed to remove existing {venv_dir}: {e}")
            return env_name, False, "\n".join(output_lines)

    # Create environment
    success = False
    if backend == "uv":
        cmd_uv = ["uv", "venv", venv_dir, "--python", v]
        try:
            subprocess.run(cmd_uv, cwd=path, capture_output=True, text=True, check=True)
            success = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            output_lines.append(f"Backend uv not available or failed for {v}.")
    elif backend == "pyenv":
        env = os.environ.copy()
        env["PYENV_VERSION"] = v
        cmd_pyenv = ["python3", "-m", "venv", venv_dir]
        try:
            subprocess.run(
                cmd_pyenv, env=env, cwd=path, capture_output=True, text=True, check=True
            )
            success = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            output_lines.append(f"Backend pyenv not available or failed for {v}.")

    if not success:
        return env_name, False, "\n".join(output_lines)

    # Run tests
    output_lines.append(f"Running tests in {venv_dir}...")
    pip_bin = os.path.join(venv_path, "bin", "pip")
    pytest_bin = os.path.join(venv_path, "bin", "pytest")

    from typing import Any

    if backend == "uv":
        env_kwargs: dict[str, Any] = {"env": {"VIRTUAL_ENV": venv_path}}
    else:
        env_kwargs = {}

    try:
        if uses_pytest:
            cmd_install_pytest = (
                ["uv", "pip", "install", "pytest"]
                if backend == "uv"
                else [pip_bin, "install", "pytest"]
            )
            subprocess.run(
                cmd_install_pytest,
                cwd=path,
                capture_output=True,
                text=True,
                check=True,
                **env_kwargs,
            )
        if os.path.exists(os.path.join(path, "requirements.txt")):
            if backend == "uv":
                subprocess.run(
                    ["uv", "pip", "install", "-r", "requirements.txt"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    check=True,
                    **env_kwargs,
                )
            else:
                subprocess.run(
                    [pip_bin, "install", "-r", "requirements.txt"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    check=True,
                )

        # Install current project if pyproject.toml exists
        if os.path.exists(os.path.join(path, "pyproject.toml")) or os.path.exists(
            os.path.join(path, "setup.py")
        ):
            if backend == "uv":
                subprocess.run(
                    ["uv", "pip", "install", "-e", "."],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    check=True,
                    **env_kwargs,
                )
            else:
                subprocess.run(
                    [pip_bin, "install", "-e", "."],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    check=True,
                )

        if uses_pytest:
            cmd_test = [pytest_bin]
        else:
            python_bin = os.path.join(venv_path, "bin", "python3")
            cmd_test = [python_bin, "-m", "unittest", "discover"]

        res = subprocess.run(cmd_test, cwd=path, capture_output=True, text=True)
        if res.returncode == 0:
            output_lines.append(f"[{env_name}] PASSED")
            return env_name, True, "\n".join(output_lines)
        else:
            output_lines.append(f"[{env_name}] FAILED")
            output_lines.append(res.stdout)
            return env_name, False, "\n".join(output_lines)
    except Exception as e:
        output_lines.append(f"[{env_name}] ERROR: {e}")
        return env_name, False, "\n".join(output_lines)
