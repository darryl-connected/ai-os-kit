#!/usr/bin/env python3
"""
google_auth.py — OAuth 2.0 bootstrap for Google services (Gmail + Drive + Calendar).

Handles first-run OAuth flow + token refresh. Use as a module to get
authenticated service objects:

    from google_auth import get_gmail_service, get_drive_service, get_calendar_service
    gmail = get_gmail_service()
    drive = get_drive_service()
    calendar = get_calendar_service()

Or run standalone to pre-authenticate:
    python scripts/google_auth.py

Setup:
    1. Create OAuth client in Google Cloud Console (see references/google-cloud-setup.md)
    2. Download credentials.json to vault root
    3. Run this script — browser opens, sign in, grant scopes
    4. token.json is saved — subsequent runs use it (auto-refreshed)

Scopes requested:
    - Gmail: gmail.modify, gmail.send, gmail.compose (read + write + send)
    - Drive: drive (full access — needed for shared vault work)
    - Calendar: calendar (full read/write — needed for meeting correlation, weekly brief)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Windows UTF-8 stdout (cp1252 crashes on unicode like ✓).
# Use reconfigure() — the io.TextIOWrapper rewrap approach closes the underlying
# buffer when the new wrapper is GC'd and breaks all subsequent prints with
# "I/O operation on closed file". See google_calendar_api.py for the same
# pitfall documented.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# --- Config ---
VAULT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(VAULT_ROOT / ".env")

CREDENTIALS_FILE = VAULT_ROOT / "credentials.json"
TOKEN_FILE = VAULT_ROOT / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
]


def get_credentials():
    """Get valid credentials, running OAuth flow if needed."""
    if not CREDENTIALS_FILE.exists():
        sys.exit(
            f"credentials.json not found at {CREDENTIALS_FILE}.\n"
            "Follow references/google-cloud-setup.md to create OAuth client first."
        )

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
        print(f"Token saved to {TOKEN_FILE}")

    return creds


def get_service(api_name, api_version):
    """Get authenticated service object for a Google API."""
    from googleapiclient.discovery import build
    creds = get_credentials()
    return build(api_name, api_version, credentials=creds, cache_discovery=False)


def get_gmail_service():
    """Get authenticated Gmail service."""
    return get_service("gmail", "v1")


def get_drive_service():
    """Get authenticated Drive service."""
    return get_service("drive", "v3")


def get_calendar_service():
    """Get authenticated Google Calendar service."""
    return get_service("calendar", "v3")


if __name__ == "__main__":
    print("Running OAuth flow for Gmail + Drive + Calendar...")
    print(f"Credentials: {CREDENTIALS_FILE}")
    print(f"Token:       {TOKEN_FILE}")
    get_credentials()
    print("✓ Auth successful. token.json saved.")
    print("Test with:")
    print("  python scripts/gmail_api.py list --query 'is:unread' --max 5")
    print("  python scripts/google_drive_api.py list --max 10")
    print("  python scripts/google_calendar_api.py calendars")
    print("  python scripts/google_calendar_api.py events --days 7")
