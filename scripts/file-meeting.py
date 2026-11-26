#!/usr/bin/env python3
"""Preview or file a reviewed meeting summary and retain the original capture."""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

from kit_context import VAULT, KitError, field_values, meeting_destination, vault_path, write_new


def store_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise KitError("A filing path already contains different content. Nothing there was overwritten.")
    else:
        write_new(path, data)


def file_meeting(args: argparse.Namespace) -> int:
    root = args.vault.resolve()
    capture = vault_path(root, args.capture)
    if capture.parent != root / "inbox" or capture.suffix != ".md" or capture.name.lower() == "readme.md":
        raise KitError("Choose one original Markdown capture directly in inbox/.")
    archived = vault_path(root, f"inbox/processed/{capture.name}")
    destination = meeting_destination(root, args.destination)
    summary = vault_path(root, f"{args.destination}/{capture.name}")
    draft = vault_path(root, args.draft)
    if draft in (capture, archived, summary):
        raise KitError("Choose a separate draft summary file.")
    body = draft.read_text(encoding="utf-8").strip()
    if not body or re.search(r"(?im)^\s*#{1,6}\s+transcript\b|\[@\d{2}:\d{2}:\d{2}\]", body):
        raise KitError("Use a short reviewed summary without an inline transcript.")
    original = capture.read_bytes()
    if not original:
        raise KitError("The original capture is empty.")
    recording = args.recording
    if not recording:
        first_block = original.decode("utf-8").splitlines()
        if first_block and first_block[0] == "---" and "---" in first_block[1:]:
            frontmatter = first_block[1:first_block.index("---", 1)]
            urls = field_values("\n".join(frontmatter), "recording")
            if urls:
                recording = urls[0].strip("\"'")
    if recording and not re.fullmatch(r"https?://[^\s<>\[\]()\"'`]+", recording):
        raise KitError("Recording must be a complete HTTP(S) URL.")
    source_link = "../../../" + quote(archived.relative_to(root).as_posix())
    note = (
        f"---\ntype: meeting\nstatus: active\ndate: {args.date.isoformat()}\n"
        + (f"recording: {json.dumps(recording)}\n" if recording else "")
        + f"---\n\n[Full original capture]({source_link})\n\n{body}\n"
    )
    print(f"Original: {capture.relative_to(root).as_posix()} -> {archived.relative_to(root).as_posix()}")
    print(f"Summary: {destination.relative_to(root).as_posix()}/{summary.name}\n\n{note}")
    if not args.apply:
        print("Preview only; no files changed.")
        return 0
    for path, expected in ((archived, original), (summary, note.encode("utf-8"))):
        if path.exists() and path.read_bytes() != expected:
            raise KitError("A filing path already contains different content. Nothing there was overwritten.")
    store_once(archived, original)
    store_once(summary, note.encode("utf-8"))
    if archived.read_bytes() != original or capture.read_bytes() != original:
        raise KitError("Capture changed during filing. The inbox original was not removed.")
    capture.unlink()
    print("Filed the summary and retained the full original. No remote writes.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=VAULT, help="Vault root (defaults to this kit folder)")
    parser.add_argument("--capture", required=True, help="Vault-relative inbox Markdown path")
    parser.add_argument("--draft", required=True, help="Separate, vault-relative reviewed summary draft (UTF-8)")
    parser.add_argument("--destination", required=True, help="Approved projects/<project-slug>/meetings directory")
    parser.add_argument("--date", type=date.fromisoformat, required=True, help="Confirmed meeting date (YYYY-MM-DD)")
    parser.add_argument("--recording", help="Approved recording link if not in the capture frontmatter")
    parser.add_argument("--apply", action="store_true", help="File locally only after approval of this preview")
    try:
        return file_meeting(parser.parse_args(argv))
    except KitError as error:
        print(error, file=sys.stderr)
    except (OSError, UnicodeError):
        print("Cannot file local meeting files. Check paths, permissions and UTF-8 encoding.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
