#!/usr/bin/env python3
"""
gmail_api.py — Gmail API wrapper.

Functions: list, get, send, draft, label operations.
Use as a module or run from CLI.

Run examples:
    python scripts/gmail_api.py list --query "from:mark is:unread" --max 10
    python scripts/gmail_api.py get --id <message_id>
    python scripts/gmail_api.py thread --id <thread_id>
    python scripts/gmail_api.py send --to "x@y.com" --subject "Hi" --body "Test"
    python scripts/gmail_api.py draft --to "x@y.com" --subject "Hi" --body "Draft"
    python scripts/gmail_api.py labels
    python scripts/gmail_api.py label --id <message_id> --name "FollowUp"

Setup:
    1. Complete Google Cloud setup (see references/google-cloud-setup.md)
    2. Run scripts/google_auth.py once to bootstrap token
    3. pip install google-auth google-auth-oauthlib google-api-python-client
"""

import os
import sys
import argparse
import base64
from pathlib import Path
from email.mime.text import MIMEText
from dotenv import load_dotenv
from googleapiclient.errors import HttpError

# Force UTF-8 stdout/stderr on Windows (cp1252 can't encode ✓ and other chars).
# Use reconfigure() — the io.TextIOWrapper rewrap approach closes the underlying
# buffer when the new wrapper is GC'd and breaks all subsequent prints with
# "I/O operation on closed file". Same pitfall documented in google_calendar_api.py.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Import from sibling script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_auth import get_gmail_service

VAULT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(VAULT_ROOT / ".env")


def list_messages(query="", max_results=10, label_ids=None):
    """List messages matching query. Returns list of {id, threadId, snippet}."""
    service = get_gmail_service()
    params = {"userId": "me", "maxResults": max_results}
    if query:
        params["q"] = query
    if label_ids:
        params["labelIds"] = label_ids
    result = service.users().messages().list(**params).execute()
    return result.get("messages", [])


def get_message(message_id, format="full"):
    """Get a single message by ID. format: full|metadata|raw|minimal."""
    service = get_gmail_service()
    return service.users().messages().get(userId="me", id=message_id, format=format).execute()


def get_thread(thread_id):
    """Get a full thread by ID. Returns thread with all messages."""
    service = get_gmail_service()
    return service.users().threads().get(userId="me", id=thread_id).execute()


def get_message_body(message):
    """Extract plain text body from a Gmail message object."""
    payload = message.get("payload", {})

    # Simple message — body is in payload.body
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Multipart — find text/plain or text/html part
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    # Fallback: any text part
    for part in payload.get("parts", []):
        if part.get("body", {}).get("data") and "text" in part.get("mimeType", ""):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    return ""


def get_message_headers(message, header_names=None):
    """Extract headers as {name: value} dict. If header_names given, filter to those."""
    headers = {}
    for h in message.get("payload", {}).get("headers", []):
        name = h["name"]
        if header_names is None or name in header_names:
            headers[name] = h["value"]
    return headers


def send_message(to, subject, body, html=False):
    """Send an email. body is plain text or HTML."""
    service = get_gmail_service()
    mime_type = "html" if html else "plain"
    msg = MIMEText(body, mime_type)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


def create_draft(to, subject, body, html=False):
    """Create a draft email."""
    service = get_gmail_service()
    mime_type = "html" if html else "plain"
    msg = MIMEText(body, mime_type)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = {"message": {"raw": raw}}
    return service.users().drafts().create(userId="me", body=draft).execute()


def list_labels():
    """List all Gmail labels."""
    service = get_gmail_service()
    result = service.users().labels().list(userId="me").execute()
    return result.get("labels", [])


def find_or_create_label(name):
    """Find a label by name (case-insensitive) or create it. Returns label ID."""
    service = get_gmail_service()
    for label in list_labels():
        if label["name"].lower() == name.lower():
            return label["id"]
    # Create
    body = {
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    new_label = service.users().labels().create(userId="me", body=body).execute()
    return new_label["id"]


def add_label(message_id, label_name):
    """Add a label to a message. Creates the label if it doesn't exist."""
    service = get_gmail_service()
    label_id = find_or_create_label(label_name)
    return service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": [label_id]}
    ).execute()


def archive_message(message_id):
    """Archive a message (remove from INBOX)."""
    service = get_gmail_service()
    return service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["INBOX"]}
    ).execute()


# --- CLI ---
def main():
    parser = argparse.ArgumentParser(description="Gmail API CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List messages")
    p_list.add_argument("--query", "-q", default="", help="Gmail search query")
    p_list.add_argument("--max", "-n", type=int, default=10, help="Max results")
    p_list.add_argument("--label", action="append", help="Filter by label ID (repeatable)")

    p_get = sub.add_parser("get", help="Get a message by ID")
    p_get.add_argument("--id", required=True, help="Message ID")

    p_thread = sub.add_parser("thread", help="Get a full thread by ID")
    p_thread.add_argument("--id", required=True, help="Thread ID")

    p_send = sub.add_parser("send", help="Send an email")
    p_send.add_argument("--to", required=True)
    p_send.add_argument("--subject", "-s", required=True)
    p_send.add_argument("--body", "-b", required=True)
    p_send.add_argument("--html", action="store_true", help="Body is HTML")

    p_draft = sub.add_parser("draft", help="Create a draft")
    p_draft.add_argument("--to", required=True)
    p_draft.add_argument("--subject", "-s", required=True)
    p_draft.add_argument("--body", "-b", required=True)
    p_draft.add_argument("--html", action="store_true", help="Body is HTML")

    sub.add_parser("labels", help="List all labels")

    p_label = sub.add_parser("label", help="Add a label to a message")
    p_label.add_argument("--id", required=True, help="Message ID")
    p_label.add_argument("--name", required=True, help="Label name (created if missing)")

    p_archive = sub.add_parser("archive", help="Archive a message (remove from INBOX)")
    p_archive.add_argument("--id", required=True, help="Message ID")

    args = parser.parse_args()

    try:
        if args.cmd == "list":
            messages = list_messages(args.query, args.max, args.label)
            if not messages:
                print("(no messages)")
            for msg in messages:
                print(f"{msg['id']}  {msg.get('snippet', '')[:80]}")

        elif args.cmd == "get":
            msg = get_message(args.id)
            headers = get_message_headers(msg, ["From", "To", "Subject", "Date"])
            print("=" * 60)
            for k, v in headers.items():
                print(f"{k}: {v}")
            print("=" * 60)
            body = get_message_body(msg)
            print(body)

        elif args.cmd == "thread":
            thread = get_thread(args.id)
            for msg in thread.get("messages", []):
                headers = get_message_headers(msg, ["From", "Date", "Subject"])
                print("---")
                print(f"From: {headers.get('From', '?')}")
                print(f"Date: {headers.get('Date', '?')}")
                print(f"Subject: {headers.get('Subject', '?')}")
                print()
                print(get_message_body(msg))

        elif args.cmd == "send":
            result = send_message(args.to, args.subject, args.body, args.html)
            print(f"✓ Sent: {result['id']}  Thread: {result['threadId']}")

        elif args.cmd == "draft":
            result = create_draft(args.to, args.subject, args.body, args.html)
            print(f"✓ Draft created: {result['id']}")

        elif args.cmd == "labels":
            for label in list_labels():
                print(f"{label['id']:30}  {label['name']}  ({label.get('type', '?')})")

        elif args.cmd == "label":
            result = add_label(args.id, args.name)
            print(f"✓ Labeled {args.id} with '{args.name}'")

        elif args.cmd == "archive":
            result = archive_message(args.id)
            print(f"✓ Archived {args.id}")

    except HttpError as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
