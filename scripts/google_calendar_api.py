"""
google_calendar_api.py — Google Calendar API wrapper (read + write with --yes gate).

Functions: me, calendars, events, event, create, update, delete.

Setup:
    1. Enable Calendar API in Google Cloud Console (same project as Drive/Gmail)
    2. Re-run python scripts/google_auth.py to refresh token with calendar scope
    3. pip install google-auth google-auth-oauthlib google-api-python-client (already installed)

Run examples:
    python scripts/google_calendar_api.py me
    python scripts/google_calendar_api.py calendars
    python scripts/google_calendar_api.py events --days 7
    python scripts/google_calendar_api.py events --days 30 --max 50
    python scripts/google_calendar_api.py event --id <event_id>
    python scripts/google_calendar_api.py create --summary "QA sync" --start 2026-06-19T15:00 --end 2026-06-19T16:00 --yes
    python scripts/google_calendar_api.py update --id <event_id> --summary "New title" --yes
    python scripts/google_calendar_api.py delete --id <event_id> --yes

Auth:
    Personal OAuth token, shared with Gmail and Drive (see google_auth.py).
    Scope: https://www.googleapis.com/auth/calendar (full read/write).

Write gate:
    All write commands (create, update, delete) require --yes flag.
    Without --yes, the script prints a preview and prompts for confirmation (y/N).
    Auto-aborts on no input. Mirrors the ClickUp write-gate convention.

Time helpers:
    --days N lists events from now to now+N days
    --start/--end accept ISO 8601 (e.g. 2026-06-19T15:00 or with TZ offset)
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from google_auth import get_calendar_service

# Windows UTF-8: set PYTHONIOENCODING=utf-8 in your shell before running this script.
# The io.TextIOWrapper approach (re-wrapping sys.stdout.buffer) can conflict with the
# Google auth library on Windows and cause "I/O operation on closed file" errors.

# Load .env from vault root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PRIMARY = "primary"


def _confirm_or_exit(action_desc, yes_flag):
    """Two-layer write gate. Mirrors clickup_api.py pattern."""
    if yes_flag:
        return
    print(f"\nAbout to: {action_desc}")
    print("Pass --yes to skip this prompt, or pipe 'y' to confirm.")
    try:
        resp = input("Proceed? [y/N] ")
    except EOFError:
        resp = ""
    if resp.strip().lower() != "y":
        print("Aborted.")
        sys.exit(0)


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(s):
    """Parse ISO 8601 datetime. Accepts naive (treated as local) or TZ-aware."""
    if not s:
        return None
    # Replace space with T for leniency
    s = s.replace(" ", "T")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        raise ValueError(f"Could not parse datetime: {s}. Use ISO 8601 (e.g. 2026-06-19T15:00 or 2026-06-19T15:00:00+08:00).")
    if dt.tzinfo is None:
        # Treat as local timezone
        dt = dt.astimezone()
    return dt.isoformat()


def me():
    """Get the user's primary calendar info."""
    service = get_calendar_service()
    calendar = service.calendars().get(calendarId=PRIMARY).execute()
    return calendar


def list_calendars():
    """List all calendars the user has access to."""
    service = get_calendar_service()
    items = []
    page_token = None
    while True:
        kwargs = {"maxResults": 250}
        if page_token:
            kwargs["pageToken"] = page_token
        result = service.calendarList().list(**kwargs).execute()
        items.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return items


def list_events(calendar_id=PRIMARY, days=7, max_results=50, query=None, time_min=None, time_max=None):
    """List events on a calendar. Defaults to next 7 days on primary."""
    service = get_calendar_service()
    if time_min is None:
        time_min = _iso_now()
    if time_max is None:
        time_max = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    params = {
        "calendarId": calendar_id,
        "timeMin": time_min,
        "timeMax": time_max,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if query:
        params["q"] = query
    items = []
    page_token = None
    while True:
        if page_token:
            params["pageToken"] = page_token
        result = service.events().list(**params).execute()
        items.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return items


def get_event(event_id, calendar_id=PRIMARY):
    """Get a single event by ID."""
    service = get_calendar_service()
    return service.events().get(calendarId=calendar_id, eventId=event_id).execute()


def create_event(calendar_id, summary, start, end, description=None, location=None, attendees=None, yes=False):
    """Create a calendar event. Requires --yes."""
    desc = f"Create event '{summary}' on calendar '{calendar_id}' from {start} to {end}"
    if description:
        desc += f"\n  Description: {description[:80]}"
    if location:
        desc += f"\n  Location: {location}"
    if attendees:
        desc += f"\n  Attendees: {attendees}"
    _confirm_or_exit(desc, yes)

    body = {
        "summary": summary,
        "start": {"dateTime": _parse_dt(start)},
        "end": {"dateTime": _parse_dt(end)},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = [{"email": a.strip()} for a in attendees.split(",")]

    service = get_calendar_service()
    result = service.events().insert(calendarId=calendar_id, body=body).execute()
    return result


def update_event(event_id, calendar_id=PRIMARY, summary=None, start=None, end=None, description=None, location=None, yes=False):
    """Update a calendar event (partial). Requires --yes."""
    _confirm_or_exit(f"Update event '{event_id}' on calendar '{calendar_id}'", yes)

    body = {}
    if summary:
        body["summary"] = summary
    if start:
        body["start"] = {"dateTime": _parse_dt(start)}
    if end:
        body["end"] = {"dateTime": _parse_dt(end)}
    if description is not None:
        body["description"] = description
    if location is not None:
        body["location"] = location

    if not body:
        print("No fields to update. Provide --summary, --start, --end, --description, or --location.")
        sys.exit(1)

    service = get_calendar_service()
    result = service.events().patch(calendarId=calendar_id, eventId=event_id, body=body).execute()
    return result


def delete_event(event_id, calendar_id=PRIMARY, yes=False):
    """Delete a calendar event. Requires --yes."""
    _confirm_or_exit(f"Delete event '{event_id}' on calendar '{calendar_id}'", yes)
    service = get_calendar_service()
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return {"deleted": event_id, "calendar": calendar_id}


# ---- CLI ----

def _format_event(e, verbose=False):
    """Format an event for display."""
    start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
    end = e.get("end", {}).get("dateTime", e.get("end", {}).get("date", ""))
    summary = e.get("summary", "(no title)")
    eid = e.get("id", "")
    attendees = e.get("attendees", [])
    location = e.get("location", "")

    line = f"  {start[:16]}  {summary}"
    if verbose:
        line += f"\n    ID:       {eid}"
        if location:
            line += f"\n    Location: {location}"
        if attendees:
            emails = [a.get("email", "?") for a in attendees]
            line += f"\n    Attendees: {', '.join(emails)}"
        link = e.get("htmlLink", "")
        if link:
            line += f"\n    Link:     {link}"
    return line


def main():
    parser = argparse.ArgumentParser(description="Google Calendar API CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_me = sub.add_parser("me", help="Get primary calendar info")

    p_cals = sub.add_parser("calendars", help="List all calendars")
    p_cals.add_argument("--json", action="store_true")

    p_events = sub.add_parser("events", help="List events")
    p_events.add_argument("--calendar", default=PRIMARY, help="Calendar ID (default: primary)")
    p_events.add_argument("--days", type=int, default=7, help="Days from now (default: 7)")
    p_events.add_argument("--max", type=int, default=50, help="Max results (default: 50)")
    p_events.add_argument("--query", help="Free-text search filter")
    p_events.add_argument("--start", help="Override start time (ISO 8601)")
    p_events.add_argument("--end", help="Override end time (ISO 8601)")
    p_events.add_argument("--verbose", "-v", action="store_true")
    p_events.add_argument("--json", action="store_true")

    p_event = sub.add_parser("event", help="Get a single event by ID")
    p_event.add_argument("--id", required=True)
    p_event.add_argument("--calendar", default=PRIMARY)
    p_event.add_argument("--json", action="store_true")

    p_create = sub.add_parser("create", help="Create an event (REQUIRES --yes)")
    p_create.add_argument("--calendar", default=PRIMARY)
    p_create.add_argument("--summary", required=True)
    p_create.add_argument("--start", required=True, help="ISO 8601 (e.g. 2026-06-19T15:00)")
    p_create.add_argument("--end", required=True)
    p_create.add_argument("--description")
    p_create.add_argument("--location")
    p_create.add_argument("--attendees", help="Comma-separated emails")
    p_create.add_argument("--yes", action="store_true")

    p_update = sub.add_parser("update", help="Update an event (REQUIRES --yes)")
    p_update.add_argument("--id", required=True)
    p_update.add_argument("--calendar", default=PRIMARY)
    p_update.add_argument("--summary")
    p_update.add_argument("--start")
    p_update.add_argument("--end")
    p_update.add_argument("--description")
    p_update.add_argument("--location")
    p_update.add_argument("--yes", action="store_true")

    p_delete = sub.add_parser("delete", help="Delete an event (REQUIRES --yes)")
    p_delete.add_argument("--id", required=True)
    p_delete.add_argument("--calendar", default=PRIMARY)
    p_delete.add_argument("--yes", action="store_true")

    args = parser.parse_args()

    if args.cmd == "me":
        cal = me()
        print(f"Primary calendar: {cal.get('summary', '?')}")
        print(f"  ID:          {cal.get('id')}")
        print(f"  Time zone:   {cal.get('timeZone', '?')}")
        print(f"  Access role: {cal.get('accessRole', '?')}")

    elif args.cmd == "calendars":
        cals = list_calendars()
        if args.json:
            print(json.dumps(cals, indent=2))
        else:
            print(f"Found {len(cals)} calendars:")
            for c in cals:
                primary = " [PRIMARY]" if c.get("primary") else ""
                access = c.get("accessRole", "?")
                print(f"  {c.get('id', '?'):60s}  {c.get('summary', '?')}{primary}  ({access})")

    elif args.cmd == "events":
        events = list_events(
            calendar_id=args.calendar,
            days=args.days,
            max_results=args.max,
            query=args.query,
            time_min=_parse_dt(args.start) if args.start else None,
            time_max=_parse_dt(args.end) if args.end else None,
        )
        if args.json:
            print(json.dumps(events, indent=2))
        else:
            if not events:
                print("No events found.")
                return
            print(f"Found {len(events)} event(s) on '{args.calendar}' (next {args.days} days):")
            for e in events:
                print(_format_event(e, verbose=args.verbose))

    elif args.cmd == "event":
        e = get_event(args.id, args.calendar)
        if args.json:
            print(json.dumps(e, indent=2))
        else:
            print(_format_event(e, verbose=True))
            if e.get("description"):
                print(f"    Description: {e['description']}")
            if e.get("hangoutLink"):
                print(f"    Meet link:   {e['hangoutLink']}")

    elif args.cmd == "create":
        result = create_event(
            calendar_id=args.calendar,
            summary=args.summary,
            start=args.start,
            end=args.end,
            description=args.description,
            location=args.location,
            attendees=args.attendees,
            yes=args.yes,
        )
        print(f"✓ Created event: {result.get('summary')}")
        print(f"  ID:   {result.get('id')}")
        print(f"  Link: {result.get('htmlLink', '?')}")

    elif args.cmd == "update":
        result = update_event(
            event_id=args.id,
            calendar_id=args.calendar,
            summary=args.summary,
            start=args.start,
            end=args.end,
            description=args.description,
            location=args.location,
            yes=args.yes,
        )
        print(f"✓ Updated event: {result.get('summary')}")
        print(f"  ID: {result.get('id')}")

    elif args.cmd == "delete":
        result = delete_event(args.id, args.calendar, yes=args.yes)
        print(f"✓ Deleted event {result['deleted']} from {result['calendar']}")


if __name__ == "__main__":
    main()
