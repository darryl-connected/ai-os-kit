#!/usr/bin/env python3
"""
fathom-fetch.py — On-demand fetch of the latest unprocessed Fathom meeting.

Pulls the most recent meeting from your Fathom account, checks if it's already
been processed (file exists in inbox/processed/ or projects/.../meetings/),
and if not, drops it as a markdown file into inbox/ for /process-inbox to handle.

Run: python scripts/fathom-fetch.py

Setup:
    1. Generate API key in Fathom → Settings → API
    2. Add to .env at vault root: FATHOM_API_KEY=your_key_here
    3. pip install requests python-dotenv

Phase: 1 (manual, on-demand). Advance cadence only after manual validation
across several meetings.
"""

import os
import re
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# --- Config ---
VAULT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(VAULT_ROOT / ".env")

API_KEY = os.getenv("FATHOM_API_KEY")
if not API_KEY:
    sys.exit("FATHOM_API_KEY not set. Add it to .env at vault root and try again.")

BASE_URL = "https://api.fathom.ai/external/v1"
HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json",
}
INBOX_DIR = VAULT_ROOT / "inbox"
PROCESSED_DIR = VAULT_ROOT / "inbox" / "processed"
MEETINGS_DIR = VAULT_ROOT / "projects" / "<your-project>" / "meetings"  # user-customize per project

MEETINGS_TO_CHECK = 10  # how far back to look for unprocessed

# --- API params: ask Fathom to include the full content in the list response
API_PARAMS = {
    "limit": MEETINGS_TO_CHECK,
    "include_transcript": "true",
    "include_summary": "true",
    "include_action_items": "true",
    "include_crm_matches": "false",
}


# --- API calls ---
def fetch_meetings():
    """Fetch recent meetings with full content (transcript, summary, action items)."""
    resp = requests.get(
        f"{BASE_URL}/meetings",
        headers=HEADERS,
        params=API_PARAMS,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("items") or data.get("meetings") or data.get("data") or []


# --- Idempotency check ---
def already_processed(meeting):
    """Check if a meeting has already landed in inbox/processed/ or meetings/.

    Match by share_url (which is the most stable identifier and is already
    in your frontmatter as `recording:`).
    """
    share_url = meeting.get("share_url") or ""
    if not share_url:
        return False  # can't dedupe without a stable key

    for folder in (PROCESSED_DIR, MEETINGS_DIR, INBOX_DIR):
        if not folder.exists():
            continue
        for f in folder.glob("*.md"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                if share_url in content:
                    return True
            except Exception:
                continue
    return False


# --- Helpers ---
def calc_duration_minutes(meeting):
    """Calculate meeting duration in minutes from start/end timestamps."""
    start = meeting.get("recording_start_time")
    end = meeting.get("recording_end_time")
    if not (start and end):
        return None
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return int((e - s).total_seconds() // 60)
    except Exception:
        return None


def format_attendees(meeting):
    """Build attendees list from calendar_invitees, excluding external + noreply."""
    invitees = meeting.get("calendar_invitees") or []
    names = []
    seen = set()
    for inv in invitees:
        if not isinstance(inv, dict):
            continue
        name = inv.get("matched_speaker_display_name") or inv.get("name") or ""
        # Skip email-as-name patterns and noreply addresses
        if "@" in name or "noreply" in name.lower():
            # try to use a clean name from email if it's the only thing
            email = inv.get("email") or ""
            local = email.split("@")[0] if email else ""
            name = local.replace(".", " ").replace("_", " ").title() if local else ""
        name = name.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names


def format_transcript(turns):
    """Format transcript list-of-turns into the standard transcript format.

    Output matches: [@HH:MM:SS] - **Speaker Name** text
    """
    if not turns:
        return "(no transcript provided by Fathom)"
    lines = []
    last_speaker = None
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        ts = turn.get("timestamp") or "00:00:00"
        speaker_obj = turn.get("speaker") or {}
        speaker = speaker_obj.get("display_name") or "Unknown"
        text = (turn.get("text") or "").strip()
        # Collapse consecutive same-speaker turns into a single line per the Fathom transcript style
        if speaker == last_speaker:
            lines.append(f"  {text}")
        else:
            lines.append("")
            lines.append(f"[@{ts}] - **{speaker}**")
            lines.append(text)
            last_speaker = speaker
    return "\n".join(lines).strip()


def format_action_items(items):
    """Format action items list into the standard format with WATCH links."""
    if not items:
        return "_No action items captured by Fathom._"
    lines = []
    for item in items:
        if not isinstance(item, dict):
            continue
        desc = item.get("description") or ""
        url = item.get("recording_playback_url") or ""
        if not desc:
            continue
        if url:
            lines.append(f"- **{desc}** - [WATCH]({url})")
        else:
            lines.append(f"- {desc}")
    if not lines:
        return "_No action items captured by Fathom._"
    return "\n".join(lines)


# --- File writer ---
def write_to_inbox(meeting):
    """Write the meeting as a markdown file into inbox/.

    Structure mirrors your manually-processed meeting files:
    frontmatter + VIEW RECORDING + Fathom's default_summary.markdown_formatted
    (covers Meeting Purpose, Key Takeaways, Topics, Next Steps) + Action Items
    + Transcript.
    """
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    start = meeting.get("recording_start_time") or ""
    date = start[:10] if start else datetime.now().date().isoformat()
    title = meeting.get("title") or meeting.get("meeting_title") or "Untitled meeting"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "untitled"
    filename = f"{date} - {slug}.md"
    path = INBOX_DIR / filename

    attendees = format_attendees(meeting)
    share_url = meeting.get("share_url") or ""
    duration_min = calc_duration_minutes(meeting)
    summary_md = (
        (meeting.get("default_summary") or {}).get("markdown_formatted")
        or "(no summary provided by Fathom)"
    )

    # --- Frontmatter ---
    fm_lines = [
        "---",
        "type: meeting-raw",
        "status: active",
        f"date: {date}",
        "topic: []",
        "priority:",
    ]
    if share_url:
        fm_lines.append(f"recording: {share_url}")
    if attendees:
        fm_lines.append(f"attendees: {json.dumps(attendees)}")
    if meeting.get("recording_id"):
        fm_lines.append(f"fathom_id: {meeting.get('recording_id')}")
    fm_lines.append("---")
    fm_lines.append("")

    # --- Body ---
    body = []
    if share_url:
        mins = f" - {duration_min} mins" if duration_min else ""
        body.append(f"[**VIEW RECORDING{mins}**]({share_url})")
        body.append("")

    # Fathom's summary block (Meeting Purpose → Next Steps)
    body.append(summary_md.rstrip())
    body.append("")

    # Action Items (separately, with WATCH links)
    body.append("## Action Items")
    body.append("")
    body.append(format_action_items(meeting.get("action_items") or []))
    body.append("")

    # Transcript
    body.append("## Transcript")
    body.append("")
    body.append(format_transcript(meeting.get("transcript") or []))
    body.append("")

    path.write_text("\n".join(fm_lines + body), encoding="utf-8")
    return path


# --- Main ---
def fetch_meetings_with_limit(limit):
    """Fetch recent meetings using a custom limit (overrides module default)."""
    resp = requests.get(
        f"{BASE_URL}/meetings",
        headers=HEADERS,
        params={**API_PARAMS, "limit": limit},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("items") or data.get("meetings") or data.get("data") or []


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Fathom meeting notes into inbox/ for /process-inbox to file."
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Fetch ALL unprocessed meetings (default: fetch only the newest unprocessed).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Override scan depth (default: 10, or 30 with --backfill).",
    )
    args = parser.parse_args()

    if args.limit:
        limit = args.limit
    elif args.backfill:
        limit = 30
    else:
        limit = MEETINGS_TO_CHECK

    print(f"[{datetime.now().isoformat()}] Fetching recent Fathom meetings (limit={limit}, backfill={args.backfill})...")
    try:
        meetings = fetch_meetings_with_limit(limit)
    except requests.HTTPError as e:
        sys.exit(f"HTTP error from Fathom: {e.response.status_code} — {e.response.text[:500]}")
    except requests.RequestException as e:
        sys.exit(f"Network error: {e}")

    if not meetings:
        print("No meetings returned from API.")
        return

    # Sort newest first by recording_start_time
    meetings_sorted = sorted(
        meetings,
        key=lambda m: m.get("recording_start_time") or "",
        reverse=True,
    )

    if args.backfill:
        # Walk ALL meetings, write each unprocessed one. Don't stop at first processed.
        # Use case: a meeting was missed earlier and the default heuristic skipped it.
        written = []
        skipped = 0
        for m in meetings_sorted:
            if already_processed(m):
                skipped += 1
                continue
            try:
                path = write_to_inbox(m)
                written.append((m.get("title", "Untitled"), path))
            except Exception as e:
                title = m.get("title", "?")
                print(f"  FAILED to write '{title}': {e}")
        print()
        print(f"Backfill complete: {len(written)} written, {skipped} skipped (already processed), {len(meetings_sorted)} total scanned.")
        if written:
            print("Written to inbox/:")
            for title, p in written:
                print(f"  {p.relative_to(VAULT_ROOT)}")
            print()
            print("Next: run /process-inbox to file them.")
    else:
        # Default: walk newest→oldest, stop at first processed, write just the newest unprocessed.
        # This prevents the script from backfilling old meetings when the recent
        # ones are all already done — "latest unprocessed since last processed".
        target = None
        for m in meetings_sorted:
            if already_processed(m):
                break
            target = m
        if not target:
            print(f"All {len(meetings)} recent meetings already processed. Nothing to do.")
            return
        out = write_to_inbox(target)
        print(f"Written: {out.relative_to(VAULT_ROOT)}")
        print("Next: run /process-inbox to file it.")


if __name__ == "__main__":
    main()