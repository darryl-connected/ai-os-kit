"""Local vault paths and the small, non-secret context file format."""

import re
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
PROFILE = "context/about-me.md"
CONNECTIONS = "connections.md"
DESTINATION = "Meeting destination"


class KitError(Exception):
    """An actionable message safe to show on the CLI."""


def field_values(text: str, field: str) -> list[str]:
    prefix = rf"^[ \t]*(?:[-*] )?(?:\*\*)?{re.escape(field)}(?:\*\*)?:(?:\*\*)?[ \t]*([^\r\n]*)"
    return [value.strip() for value in re.findall(prefix, text, re.MULTILINE | re.IGNORECASE) if value.strip()]


def read_context(root: Path, name: str) -> str:
    path = vault_path(root, name)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def vault_path(root: Path, name: str) -> Path:
    """Resolve a vault-relative path without following links below the root."""
    relative = Path(name)
    if relative.anchor or not relative.parts or any(part == ".." for part in relative.parts):
        raise KitError("Use a path relative to the vault, without '..'.")
    path = root.resolve()
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise KitError("A vault path is a symlink. Choose a regular local path.")
    return path


def meeting_destination(root: Path, value: str) -> Path:
    if not re.fullmatch(r"projects/[a-z0-9]+(?:[-_][a-z0-9]+)*/meetings", value):
        raise KitError("Meeting destination must be projects/<project-slug>/meetings with a real project slug.")
    return vault_path(root, value)


def meeting_destinations(root: Path) -> list[Path]:
    values = field_values(read_context(root, CONNECTIONS), DESTINATION)
    return [meeting_destination(root, value) for value in dict.fromkeys(values)]


def inbox(root: Path) -> Path:
    return vault_path(root, "inbox")


def processed(root: Path) -> Path:
    return vault_path(root, "inbox/processed")


def write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as file:
        file.write(content)
