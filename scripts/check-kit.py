#!/usr/bin/env python3
"""Run the source checkout's offline verification commands."""

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from kit_context import VAULT
from kit_files import RUNTIME, SKILLS

PYTHON = sys.executable
SOURCE = [f"scripts/{name}" for name in RUNTIME] + ["scripts/build-kit.py", "scripts/check-kit.py"]


def run(argv: Sequence[str]) -> None:
    subprocess.run(argv, check=True, cwd=VAULT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=("typecheck", "lint", "unit", "build", "acceptance"))
    args = parser.parse_args()
    try:
        if args.check == "typecheck":
            run([PYTHON, "-m", "mypy", "--strict", "--cache-dir", os.devnull, *SOURCE])
        elif args.check == "lint":
            run([PYTHON, "-m", "ruff", "check", "--no-cache", *SOURCE, "tests"])
            run(["bash", "-n", "harnesses/pi/install.sh"])
            for skill in SKILLS:
                run([PYTHON, "scripts/lint-skills.py", "--skills-dir", "skills", "--skill", skill, "--strict"])
        elif args.check in ("unit", "acceptance"):
            pattern = "test_*.py" if args.check == "unit" else "acceptance_*.py"
            run([PYTHON, "-m", "unittest", "discover", "-v", "-s", "tests", "-p", pattern])
        else:
            output = Path(os.environ.get("KIT_BUILD_OUTPUT", str(VAULT / "dist/ai-os-kit.zip")))
            run([PYTHON, "scripts/build-kit.py", "--output", str(output)])
    except subprocess.CalledProcessError as error:
        return error.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
