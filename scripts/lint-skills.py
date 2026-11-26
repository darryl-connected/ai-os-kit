#!/usr/bin/env python3
"""Validate local SKILL.md files with the actual Pi loader and kit style rules."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from kit_context import VAULT, KitError

LOADER = """
import { pathToFileURL } from 'node:url';
const [loader, cwd, agentDir, ...skillPaths] = process.argv.slice(1);
const {loadSkills} = await import(pathToFileURL(loader));
const result = loadSkills({cwd, agentDir, skillPaths, includeDefaults: false});
console.log(JSON.stringify(result));
"""


def pi_dist() -> Path:
    if configured := os.getenv("PI_DIST"):
        candidates = [Path(configured)]
    elif executable := shutil.which("pi"):
        candidates = list(Path(executable).resolve().parents)[:3]
    else:
        candidates = []
    for path in candidates:
        if (path / "core/skills.js").is_file():
            return path.resolve()
    raise KitError("Pi's local loader not found. Set PI_DIST to its dist directory (containing core/skills.js).")


def lint(directory: Path, skill: str | None, as_json: bool, strict: bool) -> int:
    files = [directory / skill / "SKILL.md"] if skill else sorted(directory.glob("*/SKILL.md"))
    if not files or any(not file.is_file() for file in files):
        raise KitError("No matching SKILL.md files. Use --skills-dir for your harness or the kit source.")
    with TemporaryDirectory(prefix="kit-skill-lint-") as isolated:
        env = {"PATH": os.defpath, "HOME": isolated, "USERPROFILE": isolated,
               "PI_CODING_AGENT_DIR": isolated}
        if "SystemRoot" in os.environ:
            env["SystemRoot"] = os.environ["SystemRoot"]
        node = shutil.which("node")
        if not node:
            raise KitError("Node.js is required to run Pi's skill loader.")
        result = subprocess.run(
            [node, "--input-type=module", "-e", LOADER, str(pi_dist() / "core/skills.js"), isolated, isolated,
             *(str(file.resolve()) for file in files)],
            env=env, cwd=isolated, capture_output=True, text=True, check=True, timeout=30,
        )
    loaded = json.loads(result.stdout)
    diagnostics = loaded["diagnostics"]
    matched = {Path(data["filePath"]).resolve(): data["name"] for data in loaded["skills"]}
    errors = []
    for file in files:
        block = re.match(r"\A---\n(.*?)\n---(?:\n|$)", file.read_text(encoding="utf-8"), re.S)
        if not block or not re.search(r"^description:[ \t]*'(?:[^'\n]|'')+'[ \t]*$", block[1], re.M):
            errors.append(f"{file}: description must be a single-quoted, non-empty scalar in frontmatter")
        if matched.get(file.resolve()) != file.parent.name:
            errors.append(f"{file}: Pi did not load the expected skill name {file.parent.name!r}")
    warnings = [f"{item.get('path', '')}: {item['message']}" for item in diagnostics if item["type"] != "error"]
    errors.extend(f"{item.get('path', '')}: {item['message']}" for item in diagnostics if item["type"] == "error")
    if as_json:
        print(json.dumps({"loader": "Pi", "loaded": sorted(matched.values()), "errors": errors, "warnings": warnings}))
    else:
        print(f"Pi loaded: {', '.join(sorted(matched.values()))}")
        for issue in errors + warnings:
            print(issue, file=sys.stderr)
    return int(bool(errors or (strict and warnings)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, default=Path(".pi/skills"), help="Directory relative to kit root")
    parser.add_argument("--skill", help="Only validate this skill directory")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Pi warnings fail the check")
    args = parser.parse_args()
    try:
        return lint(VAULT / args.skills_dir, args.skill, args.json, args.strict)
    except KitError as error:
        print(error, file=sys.stderr)
    except subprocess.CalledProcessError as error:
        print(f"Pi skill loader exited {error.returncode}: {error.stderr}", file=sys.stderr)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        print("Could not validate local skills using Pi's loader.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
