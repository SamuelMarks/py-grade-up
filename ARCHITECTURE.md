# Architecture

This document outlines the internal architecture of `py-gradeup` and how it coordinates various external tools to provide a unified, deterministic upgrade path for Python projects.

## High-Level Overview

`py-gradeup` is split into three primary layers:

1. **CLI Layer (`src/py_gradeup/cli.py`)**: Handles argument parsing, subcommand delegation (`audit`, `fix`, `revert`, `security`, `test`, `graph`, `resolve`, `bisect`), and user input validation, rendering output nicely to the terminal.
2. **SDK Layer (`src/py_gradeup/sdk.py`, `models.py`)**: Provides a unified, programmatic object-oriented interface (`PyGradeup`) that orchestrates the underlying tools and returns typed data models (`AuditResult`, `FixResult`, etc.) instead of printing to stdout. This makes it ideal for custom automation.
3. **Core Logic (`src/py_gradeup/core.py`, `graph.py`, `security.py`)**: Implements the actual file discovery, AST refactoring, dependency resolution protocols, graph visualization, and security auditing.

### 1. Python Version Discovery

The tool first determines the project's _current_ minimum Python version by inspecting `requires-python` inside `pyproject.toml`. If none is found, it defaults to `3.8`.

To find the highest _target_ Python version, `py-gradeup` leverages [uv](https://docs.astral.sh/uv/concepts/resolution/#reproducible-resolutions).
It dynamically generates isolated `.in` requirement files containing your existing strict lower bounds (e.g., `requests>=2.20.0`), extracting dependencies from a wide range of formats (`requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`, lock files, etc.).

It then iterates from Python `3.14` downward, invoking:

```bash
uv pip compile <target_file> --resolution lowest-direct --python-version <candidate>
```

The first `<candidate>` version that resolves successfully without conflict represents the maximum achievable upgrade without breaking the dependency tree. The `lowest-direct` flag ensures we only bump dependencies precisely as much as is necessary to support the new Python version.

### 2. AST-Safe Code Refactoring

Instead of relying on fragile regex for Python code upgrades, `py-gradeup` hooks directly into `pyupgrade`'s internal engine (`_fix_plugins`, `_fix_tokens`).

- During an **audit**, `py-gradeup` passes the source code of all discovered `.py` files through the engine purely in-memory and compares the output to the original string.
- During a **fix**, the updated AST string is written back to the disk.

This process explicitly targets the _newly discovered_ Python version bounds, enabling `pyupgrade` to apply aggressive modernizations (e.g., Python 3.12 syntax) if `uv` determined the ecosystem supports it.

### 3. Safe Dependency Bumping

Once the target resolution is finalized by `uv`, `py-gradeup` uses safe regex substitutions to update the project configurations natively:

- **`requirements.txt`**: Matches `(^|\s)package(>=)version` and replaces the version literal with the exact pinned minimal version `uv` requires for the new Python environment.
- **`pyproject.toml`**: Safely mutates inline list definitions (e.g., `dependencies = ["package>=version"]`) using quotes-aware regex patterns.

### 4. Automatic Environment Backup

If the target Python version established by `uv` is strictly greater than the current minimum Python version (e.g., bumping from `3.8` to `3.12`), `py-gradeup` will freeze the dependencies valid for the _old_ environment before mutating the primary configuration.

It accomplishes this by forcing a `uv pip compile` against the _current_ python version, writing the results to `requirements-{MAJOR}-{MINOR}.txt` (e.g., `requirements-3-8.txt`). This allows teams to maintain legacy support branches trivially.

### 5. Workspace Crawling

`_get_py_files` recursively searches for `.py` target files. To protect local environments, it is explicitly programmed to ignore dot-prefixed hidden directories (like `.venv/`, `.git/`, `.tox/`, etc.). This prevents `pyupgrade` from modifying third-party library code installed in local virtual environments.

### 6. Dependency Graphing

The `graph` command orchestrates `uv pip tree` inside a temporary virtual environment to display the full resolution graph of your dependencies and highlight conflicts.

### 7. Security Auditing

The `security` command parses all discovered dependencies and queries the PyPI JSON API to report known vulnerabilities based on the exact pinned versions.

### 8. State Reversion

The `revert` command facilitates rolling back `py-gradeup` modifications by utilizing git (if available) to restore source code and recovering the backed-up `requirements-{MAJOR}-{MINOR}.txt` files to reset your dependency tree.


### 9. Matrix Test Orchestration

The `test` command orchestrates integration testing dynamically:
- **Range Resolution:** Determines the minimum supported Python version from configuration and builds a matrix incrementally up to the latest known released version (e.g., 3.8 up to 3.14).
- **Framework Discovery:** Probes the workspace for `pytest` footprints (like `pytest.ini` or definitions in `requirements-dev.txt`). If found, it natively bootstraps `pytest`; otherwise, it gracefully falls back to the standard library `unittest` runner.
- **Concurrency:** Utilizing Python's `concurrent.futures.ThreadPoolExecutor`, it dispatches isolated test runs simultaneously using both `uv` and `pyenv` virtual environments. Logs are aggregated and synchronized safely upon thread completion, minimizing I/O bottlenecks.

### 10. Automated Bisection

The `bisect` command helps developers track down test regressions caused by dependency version bumps. It takes an old known-good `requirements.txt` and a new failing `requirements.txt`, then iteratively executes a binary search against the changing packages, reinstalling specific package subsets into a temporary `uv` virtual environment and running the user-provided test command until it pinpoints the exact package upgrade that caused the failure.

### 11. Conflict Resolution Suggestions

The `resolve` command works alongside `graph` to actively parse `uv pip compile` failure outputs when a dependency tree cannot be resolved. It analyzes the conflicting edges and calculates explicit version pinning (`package==version`) suggestions that satisfy the intersection of constraints, saving developers hours of manual dependency tree untangling.
