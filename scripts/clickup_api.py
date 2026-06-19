#!/usr/bin/env python3
"""
clickup_api.py — ClickUp API wrapper.

Functions: list teams / spaces / folders / lists / tasks, get task, create task,
update task, add comment.
Use as a module or run from CLI.

Run examples:
    # Discover
    python scripts/clickup_api.py me
    python scripts/clickup_api.py teams
    python scripts/clickup_api.py spaces
    python scripts/clickup_api.py folders --space <space_id>
    python scripts/clickup_api.py lists --folder <folder_id>
    python scripts/clickup_api.py lists --space <space_id>     # folderless

    # Read tasks
    python scripts/clickup_api.py tasks --list <list_id>
    python scripts/clickup_api.py tasks --list <list_id> --assignee <user_id> --status "In Progress"
    python scripts/clickup_api.py task --id <task_id>

    # Write
    python scripts/clickup_api.py create --list <list_id> --name "..." --description "..." --assignee <user_id> --priority high
    python scripts/clickup_api.py update --id <task_id> --status "Done"
    python scripts/clickup_api.py comment --id <task_id> --text "..."

Setup:
    1. Generate API token: ClickUp → Settings → Apps → API Token → Generate
    2. Add to .env at vault root: CLICKUP_API_TOKEN=pk_...
    3. pip install requests python-dotenv

SAFETY: This script defaults to read-only. Write operations (create, update,
comment) REQUIRE a `--yes` flag. Without `--yes`, the script prints a preview
of the action and prompts for y/N confirmation. Pass `--yes` only after
explicit user approval.

In a shared workspace, any write affects other people's work. The user is
responsible for confirming each write before passing `--yes`.
"""

import os
import sys
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
import requests

# Force UTF-8 stdout/stderr on Windows (cp1252 can't encode ✓ and other chars).
# Use reconfigure() — the io.TextIOWrapper rewrap approach closes the underlying
# buffer when the new wrapper is GC'd and breaks all subsequent prints with
# "I/O operation on closed file". See google_calendar_api.py for the same
# pitfall documented.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VAULT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(VAULT_ROOT / ".env")

API_TOKEN = os.getenv("CLICKUP_API_TOKEN")
BASE_URL = "https://api.clickup.com/api/v2"

# Default fields for task list (reduces payload)
TASK_LIST_FIELDS = "id,name,status,priority,assignees,due_date,tags,date_created,date_updated,url,list"


def _session():
    """Build an authenticated requests Session."""
    if not API_TOKEN:
        sys.exit(
            "CLICKUP_API_TOKEN not set. Add it to .env at vault root. "
            "Get your token: ClickUp → Settings → Apps → API Token → Generate"
        )
    session = requests.Session()
    session.headers.update({
        "Authorization": API_TOKEN,
        "Content-Type": "application/json",
    })
    return session


def _request(method, path, **kwargs):
    """Internal: make an API call and return the JSON response."""
    session = _session()
    url = f"{BASE_URL}{path}"
    response = session.request(method, url, **kwargs)
    response.raise_for_status()
    return response.json()


# --- API functions ---

def get_me():
    """Get the authenticated user (sanity check for token)."""
    return _request("GET", "/user").get("user", {})


def list_teams():
    """List all workspaces the user has access to."""
    return _request("GET", "/team").get("teams", [])


def list_spaces(team_id):
    """List spaces in a team/workspace."""
    return _request("GET", f"/team/{team_id}/space").get("spaces", [])


def list_folders(space_id):
    """List folders in a space."""
    return _request("GET", f"/space/{space_id}/folder").get("folders", [])


def list_lists_in_folder(folder_id):
    """List lists in a folder."""
    return _request("GET", f"/folder/{folder_id}/list").get("lists", [])


def list_lists_in_space(space_id):
    """List folderless lists in a space."""
    return _request("GET", f"/space/{space_id}/list").get("lists", [])


def list_tasks(list_id, statuses=None, assignees=None, archived=False, page=0):
    """List tasks in a list. Optional filters: statuses (list of names), assignees (list of user IDs)."""
    params = {
        "page": page,
        "archived": "true" if archived else "false",
        "subtasks": "true",
    }
    if statuses:
        params["statuses[]"] = statuses
    if assignees:
        params["assignees[]"] = assignees
    return _request("GET", f"/list/{list_id}/task", params=params)


def get_task(task_id, markdown=True):
    """Get a single task by ID. Description returned as markdown if markdown=True (default)."""
    params = {"include_markdown_description": "true"} if markdown else {}
    return _request("GET", f"/task/{task_id}", params=params)


def create_task(list_id, name, description=None, assignees=None, status=None, priority=None, due_date_ms=None, tags=None):
    """Create a task in a list. Returns the created task object.

    priority: 1=Urgent, 2=High, 3=Normal, 4=Low
    due_date_ms: Unix timestamp in milliseconds
    """
    body = {"name": name}
    if description:
        body["description"] = description
    if assignees:
        body["assignees"] = assignees
    if status:
        body["status"] = status
    if priority:
        body["priority"] = priority
    if due_date_ms:
        body["due_date"] = due_date_ms
    if tags:
        body["tags"] = tags
    return _request("POST", f"/list/{list_id}/task", json=body)


def update_task(task_id, **fields):
    """Update a task. Fields: name, description, status, priority, due_date, assignees."""
    return _request("PUT", f"/task/{task_id}", json=fields)


def add_comment(task_id, text, notify_all=False):
    """Add a comment to a task."""
    body = {"comment_text": text, "notify_all": notify_all}
    return _request("POST", f"/task/{task_id}/comment", json=body)


# --- Helpers ---

def get_user_id_by_email(email):
    """Look up a user ID by email. Returns None if not found."""
    teams = list_teams()
    for team in teams:
        for member in team.get("members", []):
            user = member.get("user", {})
            if user.get("email", "").lower() == email.lower():
                return user.get("id")
    return None


def _confirm_or_exit(preview, yes):
    """Print a preview of the action and ask for y/N confirmation. Exit if not confirmed.

    This is a safety gate for the SHARED ClickUp workspace — see module docstring.
    Pass yes=True (the --yes CLI flag) only after explicit user approval.
    """
    if yes:
        return
    print(preview)
    print()
    try:
        answer = input("Confirm? [y/N] ").strip().lower()
    except EOFError:
        answer = "n"
    if answer not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)


# --- CLI ---
def main():
    parser = argparse.ArgumentParser(description="ClickUp API CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("me", help="Get authenticated user (token sanity check)")

    sub.add_parser("teams", help="List all workspaces/teams")

    p_spaces = sub.add_parser("spaces", help="List spaces in a team")
    p_spaces.add_argument("--team", required=True, help="Team ID")

    p_folders = sub.add_parser("folders", help="List folders in a space")
    p_folders.add_argument("--space", required=True, help="Space ID")

    p_lists = sub.add_parser("lists", help="List lists (in folder or folderless in space)")
    p_lists.add_argument("--folder", help="Folder ID")
    p_lists.add_argument("--space", help="Space ID (use for folderless lists)")

    p_tasks = sub.add_parser("tasks", help="List tasks in a list")
    p_tasks.add_argument("--list", required=True, help="List ID")
    p_tasks.add_argument("--status", action="append", help="Filter by status name (repeatable)")
    p_tasks.add_argument("--assignee", type=int, action="append", help="Filter by user ID (repeatable)")
    p_tasks.add_argument("--archived", action="store_true", help="Include archived")
    p_tasks.add_argument("--page", type=int, default=0)

    p_task = sub.add_parser("task", help="Get a single task by ID")
    p_task.add_argument("--id", required=True)

    p_create = sub.add_parser("create", help="Create a task in a list")
    p_create.add_argument("--list", required=True, help="List ID")
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--description", help="Description (markdown or HTML)")
    p_create.add_argument("--assignee", type=int, action="append", help="User ID (repeatable)")
    p_create.add_argument("--status", help="Status name (must match list's statuses)")
    p_create.add_argument("--priority", type=int, choices=[1, 2, 3, 4], help="1=Urgent 2=High 3=Normal 4=Low")
    p_create.add_argument("--due", type=int, help="Due date as Unix ms")
    p_create.add_argument("--tag", action="append", help="Tag name (repeatable)")
    p_create.add_argument("--yes", action="store_true",
                          help="Skip the confirmation prompt. Only use after explicit user approval.")

    p_update = sub.add_parser("update", help="Update a task")
    p_update.add_argument("--id", required=True)
    p_update.add_argument("--name")
    p_update.add_argument("--description")
    p_update.add_argument("--status")
    p_update.add_argument("--priority", type=int, choices=[1, 2, 3, 4])
    p_update.add_argument("--due", type=int, dest="due_date")
    p_update.add_argument("--yes", action="store_true",
                          help="Skip the confirmation prompt. Only use after explicit user approval.")

    p_comment = sub.add_parser("comment", help="Add a comment to a task")
    p_comment.add_argument("--id", required=True)
    p_comment.add_argument("--text", required=True)
    p_comment.add_argument("--no-notify", action="store_true", help="Don't notify assignees")
    p_comment.add_argument("--yes", action="store_true",
                           help="Skip the confirmation prompt. Only use after explicit user approval.")

    p_user = sub.add_parser("user-id", help="Look up user ID by email")
    p_user.add_argument("--email", required=True)

    args = parser.parse_args()

    def fmt_task(t):
        return f"{t.get('id', '?'):25}  {t.get('status', {}).get('status', '?'):15}  {t.get('name', '?')[:60]}"

    try:
        if args.cmd == "me":
            u = get_me()
            print(f"User: {u.get('username', '?')} (id={u.get('id', '?')})  email={u.get('email', '?')}")
        elif args.cmd == "teams":
            for t in list_teams():
                print(f"{t.get('id', '?'):15}  {t.get('name', '?')}")
        elif args.cmd == "spaces":
            for s in list_spaces(args.team):
                print(f"{s.get('id', '?'):15}  {s.get('name', '?')}")
        elif args.cmd == "folders":
            for f in list_folders(args.space):
                print(f"{f.get('id', '?'):15}  {f.get('name', '?')}")
        elif args.cmd == "lists":
            if args.folder:
                lists = list_lists_in_folder(args.folder)
            elif args.space:
                lists = list_lists_in_space(args.space)
            else:
                sys.exit("Either --folder or --space is required")
            for l in lists:
                print(f"{l.get('id', '?'):15}  {l.get('name', '?')}")
        elif args.cmd == "tasks":
            data = list_tasks(args.list, args.status, args.assignee, args.archived, args.page)
            tasks = data.get("tasks", [])
            if not tasks:
                print("(no tasks)")
            for t in tasks:
                print(fmt_task(t))
            if data.get("lastPage") is False:
                print(f"\n(more pages — use --page {args.page + 1})")
        elif args.cmd == "task":
            t = get_task(args.id)
            print(f"ID:        {t.get('id', '?')}")
            print(f"Name:      {t.get('name', '?')}")
            print(f"Status:    {t.get('status', {}).get('status', '?')}")
            print(f"Priority:  {t.get('priority', {}).get('priority', '?')}")
            assignees = [a.get("username", "?") for a in t.get("assignees", [])]
            print(f"Assignees: {', '.join(assignees) or '(none)'}")
            due = t.get("due_date")
            print(f"Due:       {due if due else '(none)'}")
            print(f"URL:       {t.get('url', '?')}")
            print("---")
            desc = t.get("description") or t.get("text", "")
            if desc:
                print(desc)
        elif args.cmd == "create":
            desc_len = len(args.description or "")
            preview = (
                "About to CREATE task:\n"
                f"  List:        {args.list}\n"
                f"  Name:        {args.name}\n"
                f"  Status:      {args.status or '(list default)'}\n"
                f"  Priority:    {args.priority or '(default)'}\n"
                f"  Assignees:   {args.assignee or '(none)'}\n"
                f"  Due:         {args.due or '(none)'}\n"
                f"  Tags:        {args.tag or '(none)'}\n"
                f"  Description: {desc_len} chars"
            )
            _confirm_or_exit(preview, args.yes)
            t = create_task(
                list_id=args.list,
                name=args.name,
                description=args.description,
                assignees=args.assignee,
                status=args.status,
                priority=args.priority,
                due_date_ms=args.due,
                tags=args.tag,
            )
            print(f"Created: {t.get('id', '?')} — {t.get('name', '?')}")
            print(f"URL:     {t.get('url', '?')}")
        elif args.cmd == "update":
            fields = {k: v for k, v in vars(args).items()
                      if k not in ("cmd", "id", "yes") and v is not None}
            field_preview = "\n".join(f"  {k}: {v}" for k, v in fields.items()) or "  (no changes)"
            preview = (
                f"About to UPDATE task {args.id}:\n"
                f"{field_preview}"
            )
            _confirm_or_exit(preview, args.yes)
            t = update_task(args.id, **fields)
            print(f"Updated: {t.get('id', '?')} — {t.get('name', '?')} → {t.get('status', {}).get('status', '?')}")
        elif args.cmd == "comment":
            text_preview = (args.text[:80] + "…") if len(args.text) > 80 else args.text
            preview = (
                f"About to ADD COMMENT to task {args.id}:\n"
                f"  Notify: {not args.no_notify}\n"
                f"  Text:   {text_preview}"
            )
            _confirm_or_exit(preview, args.yes)
            c = add_comment(args.id, args.text, notify_all=not args.no_notify)
            print(f"Comment added: id={c.get('id', '?')}")
        elif args.cmd == "user-id":
            uid = get_user_id_by_email(args.email)
            if uid:
                print(f"{args.email} → user id {uid}")
            else:
                sys.exit(f"User with email {args.email} not found in any accessible team")
    except requests.HTTPError as e:
        if e.response is not None:
            print(f"API error: {e.response.status_code} {e.response.reason}", file=sys.stderr)
            try:
                err_body = e.response.json()
                print(json.dumps(err_body, indent=2), file=sys.stderr)
            except Exception:
                print(e.response.text, file=sys.stderr)
        else:
            print(f"API error (no response): {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Network error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
