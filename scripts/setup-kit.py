#!/usr/bin/env python3
"""Identify missing onboarding inputs and save only new, reviewed context."""

import argparse
import json
import sys
from pathlib import Path

from kit_context import (
    CONNECTIONS,
    DESTINATION,
    PROFILE,
    VAULT,
    KitError,
    field_values,
    meeting_destination,
    read_context,
    vault_path,
)


def single_line(value: str) -> str:
    value = value.strip()
    if not value or any(ord(c) < 32 for c in value):
        raise argparse.ArgumentTypeError("use a non-empty single line")
    return value


def add_fields(root: Path, name: str, label: str, fields: list[tuple[str, str]]) -> None:
    if not fields:
        return
    path = vault_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    heading = "\n" if path.exists() else f"# {label}\n"
    with path.open("ab") as file:
        file.write((heading + "\n" + "".join(f"- {key}: {value}\n" for key, value in fields)).encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=VAULT, help="Vault root (defaults to this kit folder)")
    parser.add_argument("--sources", choices=("supplied", "fathom", "clickup", "both"), default="both",
                        help="Only ask about connectors relevant to the first task")
    parser.add_argument("--role", type=single_line)
    parser.add_argument("--team", type=single_line)
    parser.add_argument("--project", type=single_line)
    parser.add_argument("--task", type=single_line, help="First task for this run; never saved")
    parser.add_argument("--fathom-scope", type=single_line, help="Confirmed meeting or approved recent feed")
    parser.add_argument("--clickup-scope", type=single_line, help="Confirmed workspace, space and list names or IDs")
    parser.add_argument("--meeting-destination", type=single_line, action="append", default=[],
                        help="Add a local projects/<project-slug>/meetings destination; repeatable")
    parser.add_argument("--material", type=Path, help="Supplied UTF-8 notes for a local first-task brief")
    parser.add_argument("--save", action="store_true", help="Append reviewed new fields; never replace existing ones")
    args = parser.parse_args(argv)
    try:
        return setup(args)
    except KitError as error:
        print(error, file=sys.stderr)
    except (OSError, UnicodeError):
        print("Cannot read or save local setup material. Check file paths, permissions and UTF-8 encoding.",
              file=sys.stderr)
    return 1


def setup(args: argparse.Namespace) -> int:
    profile = read_context(args.vault, PROFILE)
    scope = read_context(args.vault, CONNECTIONS)
    missing = []
    additions: dict[str, list[tuple[str, str]]] = {PROFILE: [], CONNECTIONS: []}
    for key in ("Role", "Team", "Project"):
        provided = getattr(args, key.lower())
        if not field_values(profile, key):
            if provided:
                additions[PROFILE].append((key, provided))
            else:
                missing.append(key)
    if not args.task:
        missing.append("First task")
    for service, provided in (("Fathom", args.fathom_scope), ("ClickUp", args.clickup_scope)):
        key = f"{service} scope"
        if not field_values(scope, key):
            if provided:
                additions[CONNECTIONS].append((key, provided))
            elif args.sources in ("both", service.lower()):
                missing.append(key)
    destinations = field_values(scope, DESTINATION)
    for value in dict.fromkeys(args.meeting_destination):
        meeting_destination(args.vault, value)
        if value not in destinations:
            additions[CONNECTIONS].append((DESTINATION, value))
    material = args.material.read_text(encoding="utf-8") if args.material else None
    if material is not None and not args.task:
        raise KitError("Provide --task to make a first-task brief from --material.")
    if args.save:
        add_fields(args.vault, PROFILE, "Profile", additions[PROFILE])
        add_fields(args.vault, CONNECTIONS, "Connections", additions[CONNECTIONS])
    result: dict[str, object] = {"missing": missing, "live_sources_checked": []}
    if material is not None:
        result["brief"] = {
            "task": args.task,
            "source_status": "No live sources checked. This brief uses supplied material only.",
            "supplied_material": material,
            "outline": ["Desired outcome", "Constraints and evidence", "Next steps", "Unresolved questions"],
        }
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
