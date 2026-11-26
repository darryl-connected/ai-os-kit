#!/usr/bin/env python3
"""Fetch a bounded window of recent Fathom recordings for meeting intake."""

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kit_context import VAULT, KitError, inbox, meeting_destinations, processed, write_new
from kit_http import credential, request_json

BASE_URL = "https://api.fathom.ai/external/v1/meetings"
URL = re.compile(r"https?://[^\s<>\[\]()\"'`]+")
Meeting = dict[str, Any]


def fetch_meetings_with_limit(limit: int, root: Path = VAULT, *, include_content: bool = True) -> list[Meeting]:
    if type(limit) is not int or limit < 1:
        raise KitError("Scan limit must be a positive integer.")
    key = credential(root, "FATHOM_API_KEY")
    params = {field: str(include_content).lower() for field in
              ("include_transcript", "include_summary", "include_action_items")}
    meetings: list[Meeting] = []
    seen: set[str] = set()
    while len(meetings) < limit:
        result = request_json("Fathom", "GET", BASE_URL, {"X-Api-Key": key}, params=dict(params))
        if isinstance(result, dict):
            page = next((result[key] for key in ("items", "meetings", "data") if key in result), None)
            cursor = result.get("next_cursor")
        else:
            page, cursor = result, None
        if not isinstance(page, list) or not all(isinstance(item, dict) for item in page):
            raise KitError("Fathom returned an invalid meeting list.")
        meetings.extend(page[:limit - len(meetings)])
        if cursor in (None, ""):
            break
        if not isinstance(cursor, str):
            raise KitError("Fathom returned an invalid pagination cursor.")
        if cursor in seen:
            raise KitError("Fathom returned a repeating pagination cursor.")
        seen.add(cursor)
        params["cursor"] = cursor
    return meetings


def recording_url(meeting: Meeting) -> str:
    url = meeting.get("share_url")
    return url if isinstance(url, str) and URL.fullmatch(url) else ""


def known_recordings(root: Path) -> set[str]:
    known: set[str] = set()
    for directory in (inbox(root), processed(root), *meeting_destinations(root)):
        for path in directory.glob("*.md"):
            if path.is_file() and not path.is_symlink():
                known.update(URL.findall(path.read_text(encoding="utf-8", errors="replace")))
    return known


def recording_start(meeting: Meeting) -> datetime:
    start = meeting.get("recording_start_time")
    if isinstance(start, str):
        try:
            parsed = datetime.fromisoformat(start)
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except (ValueError, OverflowError):
            pass
    return datetime.min.replace(tzinfo=UTC)


def write_to_inbox(meeting: Meeting, root: Path = VAULT) -> Path:
    url = recording_url(meeting)
    if not url:
        raise KitError("Fathom recording has no usable share URL.")
    start = recording_start(meeting)
    date = "undated" if start.year == 1 else start.date().isoformat()
    title = str(meeting.get("title") or meeting.get("meeting_title") or "Untitled meeting")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:64].rstrip("-") or "untitled"
    identity = hashlib.sha256(url.encode()).hexdigest()[:20]
    path = inbox(root) / f"{date} - {slug} - {identity}.md"

    summary = (meeting.get("default_summary") or {}).get("markdown_formatted") or "(no summary provided)"
    actions = [f"- {item.get('description') or '(unspecified action)'}"
               + (f" [WATCH]({item['recording_playback_url']})" if item.get("recording_playback_url") else "")
               for item in meeting.get("action_items") or []]
    turns = [f"[@{turn.get('timestamp') or '?'}] - **{(turn.get('speaker') or {}).get('display_name') or 'Unknown'}**\n"
             f"{turn.get('text') or ''}" for turn in meeting.get("transcript") or []]
    attendees = [name for invitee in meeting.get("calendar_invitees") or []
                 if (name := invitee.get("matched_speaker_display_name") or invitee.get("name"))]
    data = ["---", "type: meeting-raw", "status: active", f"date: {date}", f"recording: {json.dumps(url)}",
            f"fathom_id: {json.dumps(meeting.get('recording_id'))}", f"attendees: {json.dumps(attendees)}", "---", "",
            f"# {' '.join(title.split())}", "", f"[VIEW RECORDING]({url})", "", str(summary), "",
            "## Action Items", "", "\n".join(actions) or "(no action items provided)", "",
            "## Transcript", "", "\n\n".join(turns) or "(no transcript provided)", ""]
    write_new(path, "\n".join(data).encode("utf-8"))
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=VAULT, help="Vault root (defaults to this kit folder)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--backfill", action="store_true", help="Save unfiled recordings within this scan only")
    mode.add_argument("--check", action="store_true", help="Validate access to the recent feed; write no files")
    parser.add_argument("--limit", type=int, help="Scan depth (default: 10, or 30 with --backfill, 1 with --check)")
    parser.add_argument("--share-url", help="Only use this exact recording if it is in the scanned window")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except KitError as error:
        print(error, file=sys.stderr)
    except (OSError, UnicodeError):
        print("Cannot read or write local meeting files. Check permissions and existing destinations.", file=sys.stderr)
    except (AttributeError, KeyError, TypeError):
        print("Fathom returned an unexpected recording format.", file=sys.stderr)
    return 1


def run(args: argparse.Namespace) -> int:
    limit = args.limit if args.limit is not None else (1 if args.check else 30 if args.backfill else 10)
    if args.share_url and not URL.fullmatch(args.share_url):
        raise KitError("Use a complete recording share URL.")
    meetings = fetch_meetings_with_limit(limit, args.vault, include_content=not args.check)
    if args.share_url:
        meetings = [meeting for meeting in meetings if recording_url(meeting) == args.share_url]
        if not meetings:
            raise KitError("Requested recording was not found in the scan window.")
    if args.check:
        print("Fathom scoped read succeeded (recent feed). No files written.")
        return 0
    known = known_recordings(args.vault)
    written = 0
    for meeting in sorted(meetings, key=recording_start, reverse=True):
        url = recording_url(meeting)
        if not url:
            print("Skipped a recording without a usable share URL.", file=sys.stderr)
            continue
        if url in known:
            continue
        path = write_to_inbox(meeting, args.vault)
        known.add(url)
        print(f"Saved: {path.relative_to(args.vault.resolve()).as_posix()}")
        written += 1
        if not args.backfill:
            break
    if written:
        print("Next: run meeting-intake for reviewed filing.")
    else:
        print("No unfiled recordings in the scanned window.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
