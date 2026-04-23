# Usage Guide

`py-gradeup` requires two things to operate efficiently:

1. `uv` installed in the current environment (`pip install uv`).
2. A valid target Python project directory containing dependency files (e.g., `requirements.txt`, `pyproject.toml`, etc.).

The tool features six subcommands: `audit`, `fix`, `revert`, `security`, `test`, and `graph`, as well as orthogonal integration scripts.

---

## `audit` Command

The `audit` command is a read-only, diagnostic operation. It simulates the upgrade process entirely in memory and outputs what _would_ happen to the target project.

```bash
py-gradeup audit <path_to_project> [--diff]
```

**Options:**

- `--diff`: Output unified diffs of proposed syntax changes.

**What it does:**

1. Crawls `<path_to_project>` recursively, skipping hidden folders (like `.venv`).
2. Simulates dependency resolution incrementally across Python versions to identify the highest compatible Python version target.
3. Simulates an AST refactoring pass against all `.py` files.
4. Outputs the exact files and dependencies that require modification to support the new environment.

**Example Output:**

```
$ py-gradeup audit src/
Auditing project at src/
Current Python version: 3.8
Target Python version: 3.12

Would backup old requirements to requirements-3-8.txt

Files that would be upgraded:
  - src/app/main.py
  - src/app/utils.py

Checking dependencies in requirements.txt...
Dependencies that would be bumped:
  - requests: 2.20.0 -> 2.31.0
  - urllib3: 1.25 -> 1.26.17

pyproject.toml requires-python would be updated.
```

---

## `fix` Command

The `fix` command destructively applies the changes discovered during the `audit` phase directly to disk. **It is highly recommended that you run this in a version-controlled repository with a clean working tree.**

```bash
py-gradeup fix <path_to_project> [-i] [--run-tests] [--commit] [--recreate-venv] [--versioned-venv]
```

**Options:**

- `-i, --interactive`: Prompt before applying each file's changes.
- `--run-tests`: Run tests (tox, nox, or pytest) after upgrading.
- `--commit`: Automatically commit the applied changes.
- `--recreate-venv`: Destroy and rebuild local `.venv` using the new target version.
- `--versioned-venv`: Create a versioned virtual environment (e.g. `.venv-uv-3-12`) instead of `.venv`.

**What it does:**

1. Re-runs the Python version discovery constraints.
2. (If upgrading the Python version) Compiles a `requirements-{MAJOR}-{MINOR}.txt` backup of the legacy environment.
3. Mutates all outdated `.py` files using `pyupgrade`.
4. Overwrites minimum dependency versions in `requirements.txt` and `pyproject.toml`.
5. Mutates `requires-python` in `pyproject.toml`.
6. (If requested) Destroys the existing `.venv` and creates a new one using the newly targeted Python version (via `uv` or `pyenv`).

**Example Output:**

```
$ py-gradeup fix src/
Fixing project at src/
Backed up old requirements to requirements-3-8.txt
Upgraded src/app/main.py
Upgraded src/app/utils.py

Upgraded 2 Python files.

Updating dependencies in requirements.txt...
Bumped dependencies:
  - requests: 2.20.0 -> 2.31.0
  - urllib3: 1.25 -> 1.26.17
Updated pyproject.toml requires-python to >= 3.12
```

---

## `revert` Command

The `revert` command rolls back the project to its previous state before a fix was applied.

```bash
py-gradeup revert <path_to_project>
```

---

## `security` Command

The `security` command scans the project dependencies for security vulnerabilities by cross-referencing pinned dependency versions against the PyPI vulnerability database.

```bash
py-gradeup security <path_to_project>
```


---

## `test` Command

The `test` command runs your project's test suite against a matrix of Python versions, automatically resolving the lowest and highest compatible bounds. It isolates the runs within temporary `uv` or `pyenv` virtual environments.

```bash
py-gradeup test <path_to_project> [--no-parallel]
```

**Options:**

- `--no-parallel`: Disable concurrent execution and run the test matrix serially.

**What it does:**

1. Determines the bottom/minimum Python version bound from your project configurations (e.g. `requires-python` in `pyproject.toml`).
2. Iterates incrementally up to the highest available released Python version.
3. Automatically discovers your test framework by probing for `pytest.ini`, `conftest.py`, or explicit references in `requirements-dev.txt` / `pyproject.toml`.
4. If `pytest` is found, it uses it; otherwise, it defaults to the built-in `python -m unittest discover`.
5. Executes the discovered test suite in parallel using a `ThreadPoolExecutor` across all versions using both `uv` and `pyenv` backends, outputting a clear `PASSED` or `FAILED` summary.

---

## `graph` Command

The `graph` command visualizes the dependency graph and conflict trees for your project, helping to identify why a dependency resolution might be failing.

```bash
py-gradeup graph <path_to_project>
```

## Supported Configurations

`py-gradeup` is designed to be highly interoperable and parses dependencies configured across the most popular standards automatically:

### 1. `requirements.txt`

Standard PIP definition strings.

```txt
# py-gradeup will find and mutate bounds:
django>=4.0.0
pytest==7.0.0
```

### 2. `pyproject.toml`

Standard PEP-621 definitions, and specific PEP-508 array lists.

```toml
[project]
requires-python = ">=3.8"
dependencies = [
    "pydantic>=1.8.0",
]
```

### 3. Other Supported Formats

`py-gradeup` also natively scans and extracts dependencies from:

- `setup.py` & `setup.cfg`
- `Pipfile` & `Pipfile.lock`
- Lock files (`poetry.lock`, `pdm.lock`, `uv.lock`)
- Conda Environments (`environment.yml`, `environment.yaml`)

---

## Integration Pipelines

`py-gradeup` includes integration pipelines designed to confirm that modernized code can be successfully containerized. These orthogonal scripts bridge the application-layer upgrades of `py-gradeup` with the infrastructure scaffolding capabilities of neighboring tools like `mkconf`.

### Running the Pipeline

You can run the integration pipeline against a target Python project using the provided shell or batch scripts:

**Linux / macOS:**
```bash
./scripts/pipeline.sh /path/to/target_project
```

**Windows:**
```cmd
scripts\pipeline.bat C:\path\to\target_project
```

### Pipeline Workflow

The pipeline executes the following sequence:
1. **Modernization:** Invokes `py-gradeup fix` on the target directory to upgrade syntax and dependency constraints.
2. **Scaffolding:** Locates the `mkconf` binary (assumed to be in a neighboring directory `../mkconf`) and runs it against the updated target project to generate fresh `Dockerfile`s and Makefiles.
3. **Verification:** Validates the entire modernization process by immediately running `docker build` against the scaffolded environment (preferring `debian.Dockerfile` if available). This confirms the upgraded application successfully boots in a containerized environment.
