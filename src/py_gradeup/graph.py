"""Dependency graph visualization."""

from __future__ import annotations

import re
import tempfile


def _prepare_compile_targets(
    target_files: list[str], tmp_paths: list[str]
) -> list[str]:
    """Convert supported target files into a list of valid requirements for uv."""
    compile_targets = []

    for fpath in target_files:
        if fpath.endswith(".txt"):
            with open(fpath, encoding="utf-8") as f:
                lines = f.readlines()

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".in"
            ) as tmp:
                tmp_paths.append(tmp.name)
                for line in lines:
                    m = re.match(r"^([a-zA-Z0-9\-_]+)[>=]=([0-9\.]+)", line.strip())
                    if m:
                        tmp.write(f"{m.group(1)}>={m.group(2)}\n")
                    else:
                        tmp.write(line)

            compile_targets.append(tmp.name)
        elif fpath.endswith(".lock"):
            if fpath.endswith("Pipfile.lock"):
                import json

                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                with tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".in"
                ) as tmp:
                    tmp_paths.append(tmp.name)
                    for section in ["default", "develop"]:
                        for pkg, info in data.get(section, {}).items():
                            version = info.get("version", "").lstrip("=")
                            if version:
                                tmp.write(f"{pkg}=={version}\n")

                compile_targets.append(tmp.name)
            else:
                with open(fpath, encoding="utf-8") as f:
                    content_f = f.read()
                with tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".in"
                ) as tmp:
                    tmp_paths.append(tmp.name)
                    for match in re.finditer(
                        r"name\s*=\s*[\"\']([^\"\']+)[\"\'].*?version\s*=\s*[\"\']([^\"\']+)[\"\']",  # noqa: E501
                        content_f,
                        re.DOTALL,
                    ):
                        if "[[package]]" not in match.group(0)[10:]:
                            tmp.write(f"{match.group(1)}=={match.group(2)}\n")

                compile_targets.append(tmp.name)
        elif fpath.endswith(".yml") or fpath.endswith(".yaml"):
            with open(fpath, encoding="utf-8") as f:
                content_f = f.read()
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".in"
            ) as tmp:
                tmp_paths.append(tmp.name)
                for match in re.finditer(
                    r"-\s*([a-zA-Z0-9\-_]+)[>=]=?([0-9\.]+)", content_f
                ):
                    if match.group(1).lower() != "python":
                        tmp.write(f"{match.group(1)}>={match.group(2)}\n")

            compile_targets.append(tmp.name)
        elif fpath.endswith("Pipfile"):
            with open(fpath, encoding="utf-8") as f:
                content_f = f.read()
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".in"
            ) as tmp:
                tmp_paths.append(tmp.name)
                for match in re.finditer(
                    r"^([a-zA-Z0-9\-_]+)\s*=\s*[\"\'][>=]=?([0-9\.]+)[\"\']",
                    content_f,
                    re.MULTILINE,
                ):
                    tmp.write(f"{match.group(1)}>={match.group(2)}\n")

            compile_targets.append(tmp.name)
        else:
            compile_targets.append(fpath)

    return compile_targets
