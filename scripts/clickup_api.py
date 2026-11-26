#!/usr/bin/env python3
"""Read ClickUp in an agreed scope or preview an exact write for approval."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from kit_context import VAULT, KitError
from kit_http import credential, request_json

BASE_URL = "https://api.clickup.com/api/v2"


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError("use a ClickUp ID, not a URL or path")
    return value


def nonblank(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("use non-blank text")
    return value


def api(root: Path, method: str, path: str, **options: Any) -> Any:
    token = credential(root, "CLICKUP_API_TOKEN")
    return request_json("ClickUp", method, BASE_URL + path, {"Authorization": token}, **options)


def confirm() -> bool:
    try:
        return input("Send this exact ClickUp write? [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def write(args: argparse.Namespace) -> int:
    fields: tuple[str, ...]
    if args.cmd == "create":
        method, path = "POST", f"/list/{args.list}/task"
        fields = ("name", "description", "assignees", "status", "priority", "due_date", "tags")
    elif args.cmd == "update":
        method, path = "PUT", f"/task/{args.id}"
        fields = ("name", "description", "status", "priority", "due_date")
    else:
        method, path = "POST", f"/task/{args.id}/comment"
        fields = ("comment_text", "notify_all")
    payload = {key: getattr(args, key) for key in fields if getattr(args, key) is not None}
    if not payload:
        raise KitError("No changes supplied. Nothing sent.")
    print(json.dumps({"method": method, "destination": BASE_URL + path, "payload": payload}, indent=2))
    if args.preview:
        print("Preview only; nothing sent.")
        return 0
    if not args.yes and not confirm():
        print("Aborted; nothing sent.")
        return 0
    api(args.vault, method, path, expect_json=False, json=payload)
    print("ClickUp accepted the write.")
    return 0


def read(args: argparse.Namespace) -> int:
    params: dict[str, Any] = {}
    if args.cmd == "me":
        path = "/user"
    elif args.cmd in ("teams", "user-id"):
        path = "/team"
    elif args.cmd == "spaces":
        path = f"/team/{args.team}/space"
    elif args.cmd == "folders":
        path = f"/space/{args.space}/folder"
    elif args.cmd == "lists":
        path = f"/folder/{args.folder}/list" if args.folder else f"/space/{args.space}/list"
    elif args.cmd == "task":
        path = f"/task/{args.id}"
        params["include_markdown_description"] = "true"
    else:
        path = f"/list/{args.list}/task"
        params["page"] = 0
        if args.cmd == "tasks":
            if args.page < 0:
                raise KitError("Page must be zero or greater.")
            params.update(page=args.page, archived=str(args.archived).lower(), subtasks="true")
            if args.status:
                params["statuses[]"] = args.status
            if args.assignee:
                params["assignees[]"] = args.assignee
    data = api(args.vault, "GET", path, params=params)
    if not isinstance(data, dict):
        raise KitError("ClickUp returned an unexpected response format.")
    if args.cmd in ("check", "tasks") and not isinstance(data.get("tasks"), list):
        raise KitError("ClickUp did not return a task list for the requested scope.")
    if args.cmd == "check":
        print("ClickUp scoped read succeeded (requested list). No writes.")
        return 0
    if args.cmd == "user-id":
        for workspace in data.get("teams", []):
            for member in workspace.get("members", []):
                user = member.get("user", {})
                if user.get("email", "").casefold() == args.email.casefold() and user.get("id") is not None:
                    print(user["id"])
                    return 0
        raise KitError("No matching user ID found in the accessible workspaces.")
    print(json.dumps(data, indent=2))
    if args.cmd == "tasks" and data.get("lastPage") is False:
        print(f"More pages: use --page {args.page + 1}.", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=VAULT, help="Vault root (defaults to this kit folder)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("me", help="Read the authenticated user")
    sub.add_parser("teams", help="Discover accessible workspaces")
    sub.add_parser("spaces", help="Discover spaces in a workspace").add_argument("--team", type=identifier, required=True)
    sub.add_parser("folders", help="Discover folders in a space").add_argument("--space", type=identifier, required=True)
    lists = sub.add_parser("lists", help="Discover lists in a folder or folderless lists in a space")
    source = lists.add_mutually_exclusive_group(required=True)
    source.add_argument("--folder", type=identifier)
    source.add_argument("--space", type=identifier)
    check = sub.add_parser("check", help="Validate read access to the specified list without printing task data")
    check.add_argument("--list", type=identifier, required=True)
    tasks = sub.add_parser("tasks", help="Read tasks in a list")
    tasks.add_argument("--list", type=identifier, required=True)
    tasks.add_argument("--status", action="append", help="Status name (repeatable)")
    tasks.add_argument("--assignee", type=int, action="append", help="Assignee ID (repeatable)")
    tasks.add_argument("--archived", action="store_true")
    tasks.add_argument("--page", type=int, default=0)
    sub.add_parser("task", help="Read one task").add_argument("--id", type=identifier, required=True)
    sub.add_parser("user-id", help="Look up a user ID by email").add_argument("--email", required=True)

    create = sub.add_parser("create", help="Preview or create a task")
    create.add_argument("--list", type=identifier, required=True)
    create.add_argument("--assignee", dest="assignees", type=int, action="append")
    create.add_argument("--tag", dest="tags", action="append")
    update = sub.add_parser("update", help="Preview or update a task")
    update.add_argument("--id", type=identifier, required=True)
    comment = sub.add_parser("comment", help="Preview or add a comment")
    comment.add_argument("--id", type=identifier, required=True)
    comment.add_argument("--text", dest="comment_text", type=nonblank, required=True)
    comment.add_argument("--no-notify", dest="notify_all", action="store_false", help="Send notify_all=false")
    for command in (create, update):
        command.add_argument("--name", type=nonblank, required=command is create)
        command.add_argument("--description")
        command.add_argument("--status", type=nonblank)
        command.add_argument("--priority", type=int, choices=(1, 2, 3, 4), help="1=Urgent, 2=High, 3=Normal, 4=Low")
        command.add_argument("--due", dest="due_date", type=int, help="Due date as Unix milliseconds")
    for command in (create, update, comment):
        approval = command.add_mutually_exclusive_group()
        approval.add_argument("--preview", action="store_true", help="Print the exact target and payload; send nothing")
        approval.add_argument("--yes", action="store_true", help="Skip prompt only after approval of the exact preview")
    args = parser.parse_args(argv)
    try:
        return write(args) if args.cmd in ("create", "update", "comment") else read(args)
    except KitError as error:
        print(error, file=sys.stderr)
    except (AttributeError, KeyError, TypeError):
        print("ClickUp returned an unexpected response format.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
