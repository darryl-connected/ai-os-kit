#!/usr/bin/env python3
"""Install the Pi kit without replacing vault files or changing user settings."""

import argparse
import shutil
import sys
from pathlib import Path

from kit_context import VAULT, KitError, vault_path
from kit_files import DISTRIBUTION, SKILLS


def copy_if_missing(source: Path, target: Path, name: str, relative: str, conflicts: list[str]) -> None:
    origin = vault_path(source, name)
    try:
        destination = vault_path(target, relative)
    except KitError:
        conflicts.append(relative)
        return
    if destination == origin:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with origin.open("rb") as incoming, destination.open("xb") as new_file:
            shutil.copyfileobj(incoming, new_file)
    except FileExistsError:
        # Existing user files are authoritative; do not read their contents to compare.
        conflicts.append(relative)


def install(source: Path, target: Path) -> None:
    plan = [(name, name) for name in DISTRIBUTION]
    plan.extend((f"skills/{skill}/SKILL.md", f".pi/skills/{skill}/SKILL.md") for skill in SKILLS)
    if any(not vault_path(source, name).is_file() for name, _ in plan):
        raise KitError("Kit is incomplete. Extract a complete lean archive before installing.")
    conflicts: list[str] = []
    for name, relative in plan:
        copy_if_missing(source, target, name, relative, conflicts)
    print(f"Pi: default skills are {', '.join(SKILLS)}.")
    if conflicts:
        print("Preserved existing paths (or skipped symlinks). Review these against the new archive before use:")
        for path in conflicts:
            print(f"  {path}")
    for name in ("audit", "gameplan", "level-up", "push-to-drive"):
        legacy = target / ".pi/skills" / name
        if legacy.exists() or legacy.is_symlink():
            print(f"Legacy skill left in place: .pi/skills/{name}. Review manually if still enabled.")
    print("No credentials or global settings changed. See docs/SYNC.md for manual migration.")
    print("Open the vault in Pi and run /skill:onboard for one useful first task.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=VAULT, help="Target vault (defaults to this kit folder)")
    args = parser.parse_args()
    try:
        install(VAULT, args.vault.resolve())
    except KitError as error:
        print(error, file=sys.stderr)
        return 1
    except OSError:
        print("Cannot install kit files. Check vault paths and permissions.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
