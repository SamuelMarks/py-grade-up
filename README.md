# py-gradeup

[![License](https://img.shields.io/badge/license-Apache--2.0%20OR%20MIT-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![Doc Coverage](https://img.shields.io/badge/doc%20coverage-100%25-green)
![Test Coverage](https://img.shields.io/badge/test%20coverage-100%25-green)
[![CI](https://github.com/username/py-gradeup/actions/workflows/ci.yml/badge.svg)](https://github.com/username/py-gradeup/actions/workflows/ci.yml)

`py-gradeup` is a powerful, deterministic command-line utility designed to automatically upgrade Python projects to their highest compatible Python version. It seamlessly integrates AST-safe syntax refactoring with reproducible dependency resolution.

## Why py-gradeup?

Maintaining older Python projects often involves a tedious two-step process: rewriting deprecated syntax to match newer Python idioms and ensuring your dependency tree actually supports the new target version. `py-gradeup` automates both.

It leverages [pyupgrade](https://github.com/asottile/pyupgrade) for AST transformations and [uv](https://github.com/astral-sh/uv) by Astral for lightning-fast, deterministic dependency resolution.

## Key Features

- **Automated Syntax Upgrades**: Directly transforms your `.py` source files to utilize modern Python constructs safely.
- **Intelligent Dependency Bumping**: Uses `uv pip compile` to determine the highest possible Python version your current dependency tree can support.
- **Deterministic Resolution**: Never guesses versions. It empirically tests resolution graphs across Python versions (3.8 up to 3.14).
- **Extensive Format Support**: Natively understands and updates `requirements.txt`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile`, `environment.yml`, and various lock files (Poetry, PDM, uv).
- **Safe Auditing**: Provides a purely diagnostic `audit` command to show you exactly what _would_ change without modifying your files.
- **Security Auditing**: Scans dependency versions for known vulnerabilities using PyPI data.
- **Dependency Graphing**: Visualizes sub-dependencies and detects conflict trees to aid troubleshooting.
- **Automatic Backups & Revert**: Gracefully backs up your old dependencies (e.g., `requirements-3-8.txt`) and allows you to easily revert changes.

## Installation

You can install `py-gradeup` directly from source or via pip once distributed:

```bash
pip install py-gradeup
```

_Note: `py-gradeup` requires `uv` to be installed and accessible in your environment for dependency resolution._

## Quick Start

`py-gradeup` provides several commands to manage your project's upgrade lifecycle: `audit`, `fix`, `revert`, `security`, `test`, and `graph`.

To see what changes can be made to your project without applying them:

```bash
py-gradeup audit /path/to/your/project
```

To apply the upgrades and bump dependencies:

```bash
py-gradeup fix /path/to/your/project
```

To verify changes against a matrix of Python versions automatically:

```bash
py-gradeup test /path/to/your/project
```

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
