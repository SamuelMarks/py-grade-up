# py-gradeup

[![License](https://img.shields.io/badge/license-Apache--2.0%20OR%20MIT-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![Doc Coverage](https://img.shields.io/badge/doc%20coverage-100.0%25-green)
![Test Coverage](https://img.shields.io/badge/test%20coverage-100%25-green)
[![CI](https://github.com/SamuelMarks/py-grade-up/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/py-grade-up/actions/workflows/ci.yml)

`py-gradeup` is a powerful, deterministic utility designed to automatically upgrade Python projects to their highest compatible Python version. It seamlessly integrates AST-safe syntax refactoring with reproducible dependency resolution. It can be utilized as a standalone Command-Line Interface (CLI) or integrated programmatically via its Python SDK.

## Why py-gradeup?

Maintaining older Python projects often involves a tedious two-step process: rewriting deprecated syntax to match newer Python idioms and ensuring your dependency tree actually supports the new target version. `py-gradeup` automates both.

It leverages [pyupgrade](https://github.com/asottile/pyupgrade) for AST transformations and [uv](https://github.com/astral-sh/uv) by Astral for lightning-fast, deterministic dependency resolution.

## Key Features

- **Automated Syntax Upgrades**: Directly transforms your `.py` source files to utilize modern Python constructs safely.
- **Intelligent Dependency Bumping**: Uses `uv pip compile` to determine the highest possible Python version your current dependency tree can support.
- **Deterministic Resolution**: Never guesses versions. It empirically tests resolution graphs across Python versions (3.8 up to 3.14).
- **Extensive Format Support**: Natively understands and updates `requirements.txt`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile`, `environment.yml`, and various lock files (Poetry, PDM, uv).
- **Monorepo/Workspace Support**: Operate gracefully across nested package architectures using the `--workspace` flag.
- **Containerization Ready**: Includes orthogonal integration scripts to seamlessly verify your upgrades with container scaffolding tools like [mkconf](https://github.com/SamuelMarks/mkconf).
- **Safe Auditing**: Provides a purely diagnostic `audit` command to show you exactly what _would_ change without modifying your files.
- **Security Auditing**: Scans dependency versions for known vulnerabilities using PyPI data.
- **Dependency Graphing & Resolution**: Visualizes sub-dependencies, detects conflict trees, and can automatically `resolve` strict constraints to fix conflicts.
- **Automated Bisection**: Uses `bisect` to pinpoint exactly which dependency version bump broke your test suite.
- **Automatic Backups & Revert**: Gracefully backs up your old dependencies (e.g., `requirements-3-8.txt`) and allows you to easily revert changes.
- **CLI & SDK**: First-class support for both command-line operation and Python script integration.

## Installation

You can install `py-gradeup` directly from PyPI (once distributed) or from source via pip:

```bash
pip install py-gradeup
```

*Note: `py-gradeup` requires `uv` to be installed and accessible in your environment for fast dependency resolution. You can install it via `pip install uv`.*

## Usage: CLI

`py-gradeup` provides several subcommands to manage your project's upgrade lifecycle. To run them, point the CLI to your target project directory:

### `audit` (Read-only)
See what changes can be made to your project without applying them. Simulates the entire process in memory.
```bash
py-gradeup audit /path/to/your/project [--diff] [--workspace] [--only <types>]
```

### `fix` (Destructive)
Apply the upgrades and bump dependencies directly to disk. **It is highly recommended to run this in a version-controlled repository with a clean working tree.**
```bash
py-gradeup fix /path/to/your/project [-i] [--run-tests] [--commit] [--recreate-venv] [--versioned-venv] [--workspace] [--only <types>]
```

### `test`
Verify changes against a matrix of Python versions automatically using `uv` or `pyenv` virtual environments.
```bash
py-gradeup test /path/to/your/project [--no-parallel] [--workspace]
```

### `security`
Scan the project's dependency versions for known security vulnerabilities using PyPI data.
```bash
py-gradeup security /path/to/your/project [--workspace]
```

### `graph`
Visualize the dependency graph and conflict trees for your project, helping to identify why a dependency resolution might be failing.
```bash
py-gradeup graph /path/to/your/project [--workspace]
```

### `resolve`
Suggest exact constraints to fix graph conflicts automatically.
```bash
py-gradeup resolve /path/to/your/project [--workspace]
```

### `bisect`
Bisect dependency updates to find which package broke tests.
```bash
py-gradeup bisect /path/to/your/project --old <old_reqs> --new <new_reqs> --test-cmd <cmd>
```

### `revert`
Roll back the project to its previous state before a fix was applied (restores Git tracked files and old dependencies).
```bash
py-gradeup revert /path/to/your/project [--workspace]
```

## Usage: SDK

For programmatic workflows or custom automation, you can interact directly with the Python SDK:

```python
from py_gradeup.sdk import PyGradeup

# Initialize the SDK pointing to your target project directory
gradeup = PyGradeup("/path/to/your/project")

# 1. Audit the project
audit_result = gradeup.audit(show_diff=True)
print(f"Target Python Version: {audit_result.target_version}")
print(f"Files to upgrade: {audit_result.files_to_upgrade}")

# 2. Fix the project (Apply upgrades)
fix_result = gradeup.fix(run_tests=True, recreate_venv=True)
print(f"Upgraded {len(fix_result.files_upgraded)} files.")
if fix_result.tests_passed:
    print("Project successfully upgraded and passed tests!")

# 3. Security Scan
sec_result = gradeup.security()
if sec_result.vulnerabilities_found:
    print("Vulnerabilities detected:")
    for pkg_ver, vulns in sec_result.vulnerabilities.items():
        print(f"  {pkg_ver}: {len(vulns)} issues")

# 4. Run cross-version test matrix
test_result = gradeup.test(parallel=True)
if test_result.all_passed:
    print("All compatibility tests passed!")

# 5. Dependency Graph
graph_result = gradeup.graph()
if graph_result.tree:
    print(graph_result.tree)

# Optional: Revert changes
# gradeup.revert()
```

## Integration Pipelines

`py-gradeup` includes orthogonal integration scripts (`scripts/pipeline.sh` and `scripts/pipeline.bat`) that demonstrate how to pair automated modernizations with external container scaffolding tools. These scripts allow you to upgrade a project and instantly verify that its newly generated Dockerfiles build successfully.

## Documentation

For more detailed information, please refer to the following documentation:

- [Usage Guide](USAGE.md) - Detailed breakdown of CLI commands and expected outputs.
- [Architecture](ARCHITECTURE.md) - Deep dive into how `py-gradeup` safely modifies code and resolves dependencies.

## Development & Contributing

This project strictly enforces **100% Test Coverage** and **100% Documentation Coverage**.
We utilize `ruff` for linting and formatting. Ensure you run the pre-commit checks before submitting patches.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt -e .
./.git/hooks/pre-commit
```

---

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or <https://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or <https://opensource.org/licenses/MIT>)

at your option.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in the work by you, as defined in the Apache-2.0 license, shall be
dual licensed as above, without any additional terms or conditions.
