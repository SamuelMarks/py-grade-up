"""End-to-End tests for py-gradeup."""

import os
import subprocess
from pathlib import Path

from py_gradeup.cli import main


def test_e2e_fix_and_audit(tmp_path: Path) -> None:
    """Test the complete audit and fix lifecycle."""
    # 1. Setup a dummy project
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        "[project]\n"
        'name = "dummy"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.8"\n'
        "dependencies = [\n"
        '    "requests==2.20.0",\n'
        "]\n"
    )

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    main_py = src_dir / "main.py"
    main_py.write_text(
        'def test() -> None:\n    x = set([])\n    print("Hello {0}".format("world"))\n'
    )

    # 2. Run Audit
    exit_code = main(["audit", str(tmp_path)])
    assert exit_code == 0

    # Ensure files weren't mutated yet
    assert "set([])" in main_py.read_text()
    assert ">=3.8" in pyproject_toml.read_text()

    # 3. Setup git since revert or backup might interact with it
    env = os.environ.copy()
    env.pop("GIT_INDEX_FILE", None)
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    env["GIT_AUTHOR_NAME"] = "test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    subprocess.run(
        ["git", "init"], cwd=str(tmp_path), check=True, capture_output=True, env=env
    )
    subprocess.run(
        ["git", "add", "."], cwd=str(tmp_path), check=True, capture_output=True, env=env
    )

    # 4. Run Fix
    exit_code = main(["fix", str(tmp_path)])
    assert exit_code == 0

    # 5. Assert mutations
    content = main_py.read_text()
    assert "set()" in content  # pyupgrade set([]) -> set()
    assert "{0}" not in content  # pyupgrade format -> {} or f-string

    toml_content = pyproject_toml.read_text()
    assert 'requires-python = ">=' in toml_content
    assert ">=3.8" not in toml_content  # It should bump to highest (e.g. 3.14)


def test_e2e_revert(tmp_path: Path) -> None:
    """Test the revert command reverts files properly."""
    # 1. Setup a dummy project
    pyproject_toml = tmp_path / "pyproject.toml"
    original_toml = (
        '[project]\nname = "dummy"\nversion = "0.1.0"\nrequires-python = ">=3.8"\n'
    )
    pyproject_toml.write_text(original_toml)

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    main_py = src_dir / "main.py"
    original_py = "def test() -> None:\n    x = set([])\n"
    main_py.write_text(original_py)

    # 2. Setup git
    env = os.environ.copy()
    env.pop("GIT_INDEX_FILE", None)
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    env["GIT_AUTHOR_NAME"] = "test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    subprocess.run(
        ["git", "init"], cwd=str(tmp_path), check=True, capture_output=True, env=env
    )
    subprocess.run(
        ["git", "add", "."], cwd=str(tmp_path), check=True, capture_output=True, env=env
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        env=env,
    )

    # 3. Fix
    exit_code = main(["fix", str(tmp_path)])
    assert exit_code == 0
    assert "set()" in main_py.read_text()

    # 4. Revert
    exit_code = main(["revert", str(tmp_path)])
    assert exit_code == 0

    # 5. Assert reverted
    assert "set([])" in main_py.read_text()
    assert original_toml == pyproject_toml.read_text()


def test_e2e_security(tmp_path: Path) -> None:
    """Test the security scan on a dummy requirements file."""
    # Test security command on a known vulnerable package
    req_txt = tmp_path / "requirements.txt"
    # urllib3 1.25.8 has vulnerabilities
    req_txt.write_text("urllib3==1.25.8\n")

    # Run security scan
    exit_code = main(["security", str(tmp_path)])
    # exit_code might be 1 if vulnerabilities are found
    assert exit_code == 1


def test_e2e_graph(tmp_path: Path) -> None:
    """Test the graph command visually prints dependency trees."""
    req_txt = tmp_path / "requirements.txt"
    req_txt.write_text("requests==2.20.0\n")

    exit_code = main(["graph", str(tmp_path)])
    assert exit_code == 0
