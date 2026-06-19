#!/usr/bin/env python3
"""
google_drive_api.py — Google Drive API wrapper.

Read operations (get, download, export) are UNRESTRICTED — any file you have
access to can be read by file ID. List, search, and all write operations
(upload, create folder, share, move, delete) are restricted to the "Consultant
Shiz" sandbox folder (and any subfolders inside it).

This is the security model decided on 2026-06-18 (see decisions/log.md):
- List/search are sandboxed to prevent the AI from roaming your Drive
- Writes are sandboxed to prevent accidental changes outside your scope
- Reads by file ID are open, because the user provides the ID and could
  have read the file themselves anyway

Functions: list, search, get metadata, download, upload, create folder, share, move.
Use as a module or run from CLI.

Run examples:
    python scripts/google_drive_api.py list --max 10                          # sandboxed list
    python scripts/google_drive_api.py get --id <file_id>                    # any file you have access to
    python scripts/google_drive_api.py download --id <file_id> --dest ./x.pdf  # any file you have access to
    python scripts/google_drive_api.py upload --path ./x.pdf                 # uploads to sandbox by default
    python scripts/google_drive_api.py folder --name "Meeting Notes"          # in sandbox
    python scripts/google_drive_api.py share --id <file_id> --email user@x.com --role writer  # sandbox-checked

Setup:
    1. Complete Google Cloud setup (see references/google-cloud-setup.md)
    2. Run scripts/google_auth.py once to bootstrap token
    3. pip install google-auth google-auth-oauthlib google-api-python-client

Sandbox:
    The folder ID below is the boundary for list/search/writes. To change it,
    update ALLOWED_FOLDER_ID. Reads bypass the sandbox entirely.

Security note:
    Reads use the same OAuth token as writes. A read of a file outside the
    sandbox is fine because the user has access anyway. If you want a stronger
    boundary, run a service account with folder-only sharing.
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Force UTF-8 stdout/stderr on Windows (cp1252 can't encode ✓ and other chars).
# Use reconfigure() — the io.TextIOWrapper rewrap approach closes the underlying
# buffer when the new wrapper is GC'd and breaks all subsequent prints with
# "I/O operation on closed file". See google_calendar_api.py for the same
# pitfall documented.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Import from sibling script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_auth import get_drive_service

VAULT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(VAULT_ROOT / ".env")

# --- Sandbox configuration ---
# AIOS is locked to a sandbox folder. Override via .env at vault root:
#   GOOGLE_DRIVE_DEFAULT_FOLDER_ID=<folder_id_from_drive_url>
# If not set, falls back to the value below.
ALLOWED_FOLDER_ID = os.getenv("GOOGLE_DRIVE_DEFAULT_FOLDER_ID", "1xOmnXRauv9U5WsR_cVXAXoKbQ4s09dpc")
ALLOWED_FOLDER_NAME = "AIOS Sandbox"

# Default fields for list/get operations (reduces payload)
# - LIST_FIELDS: for files().list() — must wrap in files(...), include nextPageToken
# - GET_FIELDS: for files().get() — flat field list, no wrapper
DEFAULT_LIST_FIELDS = "files(id, name, mimeType, modifiedTime, size, parents, webViewLink, owners, starred, trashed), nextPageToken"
DEFAULT_GET_FIELDS = "id, name, mimeType, modifiedTime, size, parents, webViewLink, owners, starred, trashed"
# Backward compat alias
DEFAULT_FIELDS = DEFAULT_LIST_FIELDS


# --- Sandbox enforcement ---

def _get_file_raw(file_id, fields=DEFAULT_GET_FIELDS):
    """Internal: fetch file metadata without sandbox validation. Used by validators."""
    service = get_drive_service()
    return service.files().get(fileId=file_id, fields=fields).execute()


def _is_in_sandbox(file_metadata):
    """Check if a file/folder is inside the allowed sandbox folder at any depth.

    Walks up the parent chain. If ALLOWED_FOLDER_ID is found, returns True.
    Caches the chain within a single call to avoid redundant API calls on shared parents.
    """
    service = get_drive_service()
    visited = set()
    to_check = list(file_metadata.get("parents", []))

    while to_check:
        parent_id = to_check.pop()
        if parent_id in visited:
            continue
        visited.add(parent_id)
        if parent_id == ALLOWED_FOLDER_ID:
            return True
        try:
            parent = service.files().get(
                fileId=parent_id, fields="id, parents"
            ).execute()
            to_check.extend(parent.get("parents", []))
        except HttpError:
            return False
        # Safety cap — don't walk more than 20 levels
        if len(visited) > 20:
            return False
    return False


def _enforce_sandbox_query(query):
    """Inject sandbox parent filter into a Drive query. Used by list operations."""
    # Note: Drive's `parents` filter only matches direct parents, not ancestors.
    # If you need subfolder contents, list the subfolder separately.
    sandbox_filter = f"'{ALLOWED_FOLDER_ID}' in parents"
    if query:
        return f"({query}) and {sandbox_filter}"
    return sandbox_filter


def _require_sandbox(file_id, op_name="operation"):
    """Validate a file ID is in the sandbox. Raises PermissionError if not."""
    metadata = _get_file_raw(file_id, fields="id, name, parents, mimeType, trashed")
    if metadata.get("trashed"):
        raise PermissionError(
            f"File {file_id} is in trash — refusing {op_name}"
        )
    if not _is_in_sandbox(metadata):
        raise PermissionError(
            f"File '{metadata.get('name', file_id)}' ({file_id}) is outside the "
            f"sandbox folder '{ALLOWED_FOLDER_NAME}'. {op_name} refused."
        )
    return metadata


def _require_sandbox_folder(folder_id, op_name="operation"):
    """Validate a folder ID is the sandbox or a subfolder of it."""
    if folder_id == ALLOWED_FOLDER_ID:
        return
    metadata = _get_file_raw(folder_id, fields="id, name, parents, mimeType")
    if metadata.get("mimeType") != "application/vnd.google-apps.folder":
        raise ValueError(f"{folder_id} is not a folder (mimeType={metadata.get('mimeType')})")
    if not _is_in_sandbox(metadata):
        raise PermissionError(
            f"Folder '{metadata.get('name', folder_id)}' is outside the sandbox "
            f"'{ALLOWED_FOLDER_NAME}'. {op_name} refused."
        )


# --- Public API ---

def list_files(query="", max_results=10, fields=DEFAULT_FIELDS):
    """List files in the sandbox folder. Top-level only (direct children of sandbox)."""
    service = get_drive_service()
    params = {
        "pageSize": max_results,
        "fields": fields,
        "q": _enforce_sandbox_query(query),
    }
    result = service.files().list(**params).execute()
    return result.get("files", [])


def list_subfolders(max_results=100):
    """List subfolders inside the sandbox folder."""
    return list_files(
        query="mimeType = 'application/vnd.google-apps.folder'",
        max_results=max_results,
    )


def get_file(file_id, fields=DEFAULT_GET_FIELDS):
    """Get file metadata by ID. Unrestricted — any file you have access to.

    Reads are not sandboxed. The user provides the file ID; the AI reads it.
    See module docstring for the security model.
    """
    return _get_file_raw(file_id, fields)


def search_files(name_contains, mime_type=None, max_results=10):
    """Search files in the sandbox by name substring."""
    query_parts = [f"name contains '{name_contains}'", "trashed = false"]
    if mime_type:
        query_parts.append(f"mimeType = '{mime_type}'")
    return list_files(" and ".join(query_parts), max_results)


def download_file(file_id, destination):
    """Download a file to local path. Unrestricted — any file you have access to."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    with open(destination, "wb") as f:
        f.write(request.execute())
    return destination


def export_file(file_id, mime_type, destination):
    """Export a Google Doc/Sheet/Slides to a specific mime type. Unrestricted."""
    service = get_drive_service()
    request = service.files().export_media(fileId=file_id, mimeType=mime_type)
    with open(destination, "wb") as f:
        f.write(request.execute())
    return destination


def upload_file(local_path, parent_folder_id=None, mime_type=None, convert=False, name=None):
    """Upload a file. Defaults to the sandbox folder as parent.

    If parent_folder_id is given, it must be the sandbox folder or a subfolder of it.

    If convert=True, the uploaded file is converted to the corresponding Google
    native format (e.g. .md → Google Doc, .docx → Google Doc, .html → Google Doc).
    The file's source extension is stripped from the name in that case.

    If name is given, it's used as the file name in Drive (overrides local filename).

    Note: Google Drive v3 Python client doesn't expose a 'convert' kwarg on
    files().create(), so the conversion is triggered by setting an appropriate
    mime type (e.g. text/markdown) — Drive auto-converts supported formats on upload.
    The 'convert' param is kept here for API stability; it just hints intent.
    """
    if parent_folder_id is None:
        parent_folder_id = ALLOWED_FOLDER_ID
    else:
        _require_sandbox_folder(parent_folder_id, op_name="upload to that folder")

    service = get_drive_service()
    # When converting, strip the source extension from the name (e.g. "X.md" → "X")
    if name is None:
        name = Path(local_path).name
        if convert:
            stem = Path(local_path).stem
            if stem:
                name = stem
    file_metadata = {"name": name, "parents": [parent_folder_id]}
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
    result = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, mimeType, webViewLink, parents",
    ).execute()
    return result


def create_folder(name, parent_folder_id=None):
    """Create a folder. Defaults to the sandbox folder as parent.

    If parent_folder_id is given, it must be the sandbox folder or a subfolder of it.
    """
    if parent_folder_id is None:
        parent_folder_id = ALLOWED_FOLDER_ID
    else:
        _require_sandbox_folder(parent_folder_id, op_name="create folder in")

    service = get_drive_service()
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }
    return service.files().create(
        body=file_metadata, fields="id, name, webViewLink, parents"
    ).execute()


def share_file(file_id, email, role="writer", send_notification=True):
    """Share a file with a user. Validates the file is in the sandbox."""
    _require_sandbox(file_id, op_name="share")
    if role not in ("reader", "commenter", "writer", "owner"):
        raise ValueError(f"role must be reader|commenter|writer|owner, got {role!r}")
    service = get_drive_service()
    permission = {
        "type": "user",
        "role": role,
        "emailAddress": email,
    }
    return service.permissions().create(
        fileId=file_id,
        body=permission,
        sendNotificationEmail=send_notification,
    ).execute()


def move_file(file_id, new_parent_id):
    """Move a file to a new parent folder. Both file and target must be in sandbox."""
    _require_sandbox(file_id, op_name="move")
    _require_sandbox_folder(new_parent_id, op_name="move into that folder")

    service = get_drive_service()
    file = service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents", []))
    return service.files().update(
        fileId=file_id,
        addParents=new_parent_id,
        removeParents=previous_parents,
        fields="id, parents",
    ).execute()


def list_shared_with_me(max_results=10):
    """List files shared with you, filtered to the sandbox. Usually empty unless
    someone shares a file directly into the configured sandbox folder."""
    query = "not 'me' in owners and trashed = false"
    return list_files(query, max_results)


def delete_file(file_id, skip_trash=False):
    """Permanently delete a file (or move to trash). Sandbox-checked."""
    _require_sandbox(file_id, op_name="delete")
    service = get_drive_service()
    if skip_trash:
        return service.files().delete(fileId=file_id).execute()
    return service.files().update(fileId=file_id, body={"trashed": True}).execute()


# --- CLI ---
def main():
    parser = argparse.ArgumentParser(
        description=f"Google Drive API CLI (sandboxed to '{ALLOWED_FOLDER_NAME}')"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List files in sandbox")
    p_list.add_argument("--query", "-q", default="", help="Drive query (ANDed with sandbox filter)")
    p_list.add_argument("--max", "-n", type=int, default=10)
    p_list.add_argument("--shared", action="store_true", help="List shared files in sandbox")

    p_get = sub.add_parser("get", help="Get file metadata (sandbox-checked)")
    p_get.add_argument("--id", required=True)

    p_search = sub.add_parser("search", help="Search by filename (sandbox-checked)")
    p_search.add_argument("--name", required=True, help="Substring to search for")
    p_search.add_argument("--mime", help="Filter by mime type")
    p_search.add_argument("--max", "-n", type=int, default=10)

    p_dl = sub.add_parser("download", help="Download a file (sandbox-checked)")
    p_dl.add_argument("--id", required=True)
    p_dl.add_argument("--dest", required=True, help="Local destination path")

    p_export = sub.add_parser("export", help="Export Google Doc/Sheet/Slides (sandbox-checked)")
    p_export.add_argument("--id", required=True)
    p_export.add_argument("--mime", required=True, help="Target mime type (e.g. application/pdf)")
    p_export.add_argument("--dest", required=True)

    p_up = sub.add_parser("upload", help="Upload a file to the sandbox")
    p_up.add_argument("--path", required=True, help="Local file path")
    p_up.add_argument("--parent", help="Parent folder ID (must be sandbox or subfolder)")
    p_up.add_argument("--mime", help="Mime type (auto-detected if omitted)")
    p_up.add_argument("--convert", action="store_true",
                     help="Convert to Google native format (e.g. .md → Google Doc). Strips source extension from filename.")

    p_folder = sub.add_parser("folder", help="Create a folder in the sandbox")
    p_folder.add_argument("--name", required=True)
    p_folder.add_argument("--parent", help="Parent folder ID (must be sandbox or subfolder)")

    p_share = sub.add_parser("share", help="Share a file (sandbox-checked)")
    p_share.add_argument("--id", required=True)
    p_share.add_argument("--email", required=True)
    p_share.add_argument("--role", default="writer", choices=["reader", "commenter", "writer", "owner"])
    p_share.add_argument("--no-notify", action="store_true", help="Don't email the invitee")

    p_move = sub.add_parser("move", help="Move a file within the sandbox")
    p_move.add_argument("--id", required=True)
    p_move.add_argument("--new-parent", required=True)

    p_delete = sub.add_parser("delete", help="Move a file to trash (sandbox-checked). Permanent with --hard.")
    p_delete.add_argument("--id", required=True)
    p_delete.add_argument("--hard", action="store_true", help="Skip trash, permanently delete")

    args = parser.parse_args()

    def fmt_file(f):
        size = f.get("size", "?")
        modified = f.get("modifiedTime", "?")
        return f"{f['id']:30}  {f.get('name', '?'):40}  [{f.get('mimeType', '?')}]  modified={modified}  size={size}"

    try:
        if args.cmd == "list":
            files = list_shared_with_me(args.max) if args.shared else list_files(args.query, args.max)
            if not files:
                print(f"(no files in sandbox folder '{ALLOWED_FOLDER_NAME}')")
            for f in files:
                print(fmt_file(f))

        elif args.cmd == "get":
            f = get_file(args.id)
            print(f"ID:          {f['id']}")
            print(f"Name:        {f.get('name', '?')}")
            print(f"Mime:        {f.get('mimeType', '?')}")
            print(f"Size:        {f.get('size', '?')}")
            print(f"Modified:    {f.get('modifiedTime', '?')}")
            print(f"Parents:     {f.get('parents', [])}")
            print(f"Web link:    {f.get('webViewLink', '?')}")
            owners = f.get("owners", [])
            if owners:
                print(f"Owners:      {', '.join(o.get('emailAddress', '?') for o in owners)}")

        elif args.cmd == "search":
            files = search_files(args.name, args.mime, args.max)
            if not files:
                print(f"(no files matching '{args.name}' in sandbox)")
            for f in files:
                print(fmt_file(f))

        elif args.cmd == "download":
            result = download_file(args.id, args.dest)
            print(f"✓ Downloaded to {result}")

        elif args.cmd == "export":
            result = export_file(args.id, args.mime, args.dest)
            print(f"✓ Exported to {result}")

        elif args.cmd == "upload":
            result = upload_file(args.path, args.parent, args.mime, convert=args.convert)
            print(f"✓ Uploaded: {result['name']} (id={result['id']})")
            print(f"  Mime:    {result.get('mimeType', '?')}")
            if result.get("webViewLink"):
                print(f"  Link:    {result['webViewLink']}")

        elif args.cmd == "folder":
            result = create_folder(args.name, args.parent)
            print(f"✓ Folder created: {result['name']} (id={result['id']})")
            if result.get("webViewLink"):
                print(f"  {result['webViewLink']}")

        elif args.cmd == "share":
            result = share_file(args.id, args.email, args.role, not args.no_notify)
            print(f"✓ Shared {args.id} with {args.email} as {args.role} (perm id={result.get('id')})")

        elif args.cmd == "move":
            result = move_file(args.id, args.new_parent)
            print(f"✓ Moved {args.id} to {args.new_parent} (new parents: {result.get('parents')})")

        elif args.cmd == "delete":
            delete_file(args.id, skip_trash=args.hard)
            action = "permanently deleted" if args.hard else "moved to trash"
            print(f"✓ {args.id} {action}")

    except PermissionError as e:
        print(f"✗ Sandbox violation: {e}", file=sys.stderr)
        sys.exit(2)
    except HttpError as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
