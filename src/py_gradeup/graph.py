# ruff: noqa: E501, SIM115
"""Dependency graph visualization."""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import tempfile

from py_gradeup.core import _get_target_files


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
                    r"name\s*=\s*[\"\']([^\"\']+)[\"\'].*?version\s*=\s*[\"\']([^\"\']+)[\"\']",
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
                r"^([a-zA-Z0-9\-_]+)\s*=\s*[\"\'][>=]=?([0-9\.]+)[\"\']",
                content_f,
                re.MULTILINE,
            ):
                tmp.write(f"{match.group(1)}>={match.group(2)}\n")
            tmp.close()
            compile_targets.append(tmp.name)
        else:
            compile_targets.append(fpath)

    return compile_targets


def visualize_graph(path: str) -> None:
    """Visualize sub-dependencies and conflict trees using uv."""
    print(f"Generating dependency graph for {path}...")
    target_files = _get_target_files(path)

    if not target_files:
        print("No dependency files found to visualize.")
        return

    tmp_paths = []
    try:
        compile_targets = _prepare_compile_targets(target_files, tmp_paths)
        if not compile_targets:
            print("No valid packages found in dependency files.")
            return

        with tempfile.TemporaryDirectory() as venv_dir:
            print("Resolving dependencies... (this may take a moment)")
            try:
                # 1. Create venv
                subprocess.run(
                    ["uv", "venv", venv_dir], check=True, capture_output=True, text=True
                )

                # 2. Install requirements to test conflicts
                cmd = ["uv", "pip", "install", "-p", venv_dir]
                for target in compile_targets:
                    cmd.extend(["-r", target])

                subprocess.run(cmd, check=True, capture_output=True, text=True)

                # 3. Print tree
                print("\nDependency Tree:")
                tree_res = subprocess.run(
                    ["uv", "pip", "tree", "-p", venv_dir],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                print(tree_res.stdout)

            except subprocess.CalledProcessError as e:
                # uv pip install failed, likely due to a conflict
                if "No solution found" in e.stderr or "conflict" in e.stderr.lower():
                    print("\n[!] Dependency Conflict Detected:\n")
                    print(e.stderr)
                else:
                    print(f"\n[!] Resolution Error:\n{e.stderr or e.stdout}")

    finally:
        for t in tmp_paths:
            if os.path.exists(t):
                with contextlib.suppress(Exception):
                    os.remove(t)
