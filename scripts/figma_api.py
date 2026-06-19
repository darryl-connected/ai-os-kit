"""
figma_api.py — Figma REST API wrapper (read-only).

Functions: me, file, pages, frames, text, export.

Setup:
    1. Figma > Settings > Account > Personal access tokens > Generate
    2. Add FIGMA_API_TOKEN=figd_xxxxx to .env
    3. pip install requests python-dotenv (already installed for clickup_api.py)

Run examples:
    python scripts/figma_api.py me
    python scripts/figma_api.py file --key oDWiUNeRbTIFflWrFYgZtv
    python scripts/figma_api.py pages --key oDWiUNeRbTIFflWrFYgZtv
    python scripts/figma_api.py frames --key oDWiUNeRbTIFflWrFYgZtv --page 3403:8347
    python scripts/figma_api.py text --key oDWiUNeRbTIFflWrFYgZtv --page 3403:8347
    python scripts/figma_api.py export --key oDWiUNeRbTIFflWrFYgZtv --ids 3403:8347,1:27999 --format png --dest scratch/figma-exports

Auth:
    Personal access token, sent as X-Figma-Token header.
    No OAuth dance, no team admin, free on all Figma tiers.

Rate limits:
    ~60 requests/min for personal tokens. Plenty for our use case.
    Response headers: X-Figma-Plan-Tier, X-RateLimit-Remaining, X-RateLimit-Reset.
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

# Windows UTF-8 stdout (cp1252 crashes on unicode like ✓).
# Use reconfigure() — the io.TextIOWrapper rewrap approach closes the underlying
# buffer when the new wrapper is GC'd and breaks all subsequent prints with
# "I/O operation on closed file". See google_calendar_api.py for the same
# pitfall documented.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Load .env from vault root
load_dotenv()

FIGMA_API_BASE = "https://api.figma.com/v1"


def get_headers():
    token = os.getenv("FIGMA_API_TOKEN")
    if not token:
        raise ValueError("FIGMA_API_TOKEN not set. Add to .env (Figma > Settings > Personal access tokens).")
    return {"X-Figma-Token": token, "Content-Type": "application/json"}


def _request(method, path, **kwargs):
    """Make API request with error handling."""
    url = f"{FIGMA_API_BASE}{path}"
    r = requests.request(method, url, headers=get_headers(), **kwargs)
    if r.status_code != 200:
        print(f"Error: {r.status_code} {r.reason}")
        try:
            print(f"Body: {json.dumps(r.json(), indent=2)}")
        except Exception:
            print(f"Body: {r.text[:500]}")
        r.raise_for_status()
    return r


def me():
    """Get authenticated user info."""
    r = _request("GET", "/me")
    data = r.json()
    return {
        "email": data.get("email"),
        "id": data.get("id"),
        "handle": data.get("handle"),
        "img_url": data.get("img_url"),
        "teams": [{"id": t.get("id"), "name": t.get("name")} for t in data.get("teams", [])],
    }


def file_meta(file_key, depth=2):
    """Get file metadata + top-level structure.

    depth=2: pages only
    depth=4: pages + frames
    depth=8: deep walk (for text extraction)
    """
    r = _request("GET", f"/files/{file_key}?depth={depth}")
    return r.json()


def list_pages(file_key):
    """List all pages in a file with frame counts."""
    data = file_meta(file_key, depth=4)
    doc = data.get("document", {})
    pages = []
    for page in doc.get("children", []):
        frames = [c for c in page.get("children", []) if c.get("type") == "FRAME"]
        pages.append({
            "id": page.get("id"),
            "name": page.get("name"),
            "type": page.get("type"),
            "frame_count": len(frames),
            "frame_ids": [f.get("id") for f in frames],
        })
    return {
        "file_name": data.get("name"),
        "last_modified": data.get("lastModified"),
        "version": data.get("version"),
        "pages": pages,
    }


def list_frames(file_key, page_id=None):
    """Flat list of all frames in a file, optionally filtered to one page."""
    data = file_meta(file_key, depth=4)
    doc = data.get("document", {})
    frames = []
    for page in doc.get("children", []):
        if page_id and page.get("id") != page_id:
            continue
        for child in page.get("children", []):
            if child.get("type") == "FRAME":
                frames.append({
                    "id": child.get("id"),
                    "name": child.get("name"),
                    "page": page.get("name"),
                    "page_id": page.get("id"),
                })
    return frames


def extract_text(file_key, page_id=None):
    """Walk the file tree and collect all TEXT node content.

    Returns a list of {id, characters, page, page_id, frame_id, frame_name}.
    """
    data = file_meta(file_key, depth=10)
    doc = data.get("document", {})
    texts = []

    def find_page(node_id):
        for p in doc.get("children", []):
            if p.get("id") == node_id:
                return p
        return None

    def find_frame(page, frame_id):
        for c in page.get("children", []):
            if c.get("id") == frame_id:
                return c
        return None

    def walk(node, page, frame):
        if node.get("type") == "TEXT":
            characters = node.get("characters", "").strip()
            if characters:
                texts.append({
                    "id": node.get("id"),
                    "characters": characters,
                    "page": page.get("name") if page else None,
                    "page_id": page.get("id") if page else None,
                    "frame": frame.get("name") if frame else None,
                    "frame_id": frame.get("id") if frame else None,
                })
        for child in node.get("children", []):
            # If we're at a top-level frame, set the frame context
            new_frame = frame
            if node.get("type") == "FRAME" and frame is None:
                new_frame = node
            walk(child, page, new_frame)

    for page in doc.get("children", []):
        if page_id and page.get("id") != page_id:
            continue
        for child in page.get("children", []):
            if child.get("type") == "FRAME":
                walk(child, page, child)
            else:
                walk(child, page, None)
    return texts


def export_frames(file_key, node_ids, format="png", scale=2, dest="scratch/figma-exports"):
    """Export specific frame(s) as image(s). Returns list of saved file paths.

    The Figma /images endpoint returns S3 URLs that expire in 30 days.
    We fetch the URL and save to disk.
    """
    if isinstance(node_ids, str):
        node_ids = [n.strip() for n in node_ids.split(",")]
    valid_formats = ["png", "jpg", "svg", "pdf"]
    if format not in valid_formats:
        raise ValueError(f"format must be one of {valid_formats}")

    params = {"ids": ",".join(node_ids), "format": format, "scale": scale}
    r = _request("GET", f"/images/{file_key}", params=params)
    data = r.json()
    if data.get("err"):
        raise RuntimeError(f"Figma API error: {data['err']}")
    images = data.get("images", {})

    dest_path = Path(dest)
    if dest_path.suffix:
        # Single file destination
        dest_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        dest_path.mkdir(parents=True, exist_ok=True)

    saved = []
    for node_id, url in images.items():
        if not url:
            print(f"Warning: no image returned for node {node_id}")
            continue
        img_r = requests.get(url)
        img_r.raise_for_status()
        if dest_path.suffix:
            file_path = dest_path
        else:
            file_path = dest_path / f"{node_id}.{format}"
        with open(file_path, "wb") as f:
            f.write(img_r.content)
        saved.append(str(file_path))
        print(f"  ✓ Exported {node_id} -> {file_path} ({len(img_r.content):,} bytes)")
    return saved


# ---- CLI ----

def main():
    parser = argparse.ArgumentParser(description="Figma API CLI (read-only)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_me = sub.add_parser("me", help="Get authenticated user info")

    p_file = sub.add_parser("file", help="Get file metadata + structure")
    p_file.add_argument("--key", required=True)
    p_file.add_argument("--depth", type=int, default=2)
    p_file.add_argument("--json", action="store_true")

    p_pages = sub.add_parser("pages", help="List pages with frame counts")
    p_pages.add_argument("--key", required=True)
    p_pages.add_argument("--json", action="store_true")

    p_frames = sub.add_parser("frames", help="List frames (optionally filtered to one page)")
    p_frames.add_argument("--key", required=True)
    p_frames.add_argument("--page", help="Filter to one page ID")
    p_frames.add_argument("--json", action="store_true")

    p_text = sub.add_parser("text", help="Extract text content from file or page")
    p_text.add_argument("--key", required=True)
    p_text.add_argument("--page", help="Filter to one page ID")
    p_text.add_argument("--json", action="store_true")

    p_export = sub.add_parser("export", help="Export frame(s) as image")
    p_export.add_argument("--key", required=True)
    p_export.add_argument("--ids", required=True, help="Comma-separated node IDs")
    p_export.add_argument("--format", default="png", choices=["png", "jpg", "svg", "pdf"])
    p_export.add_argument("--scale", type=float, default=2.0)
    p_export.add_argument("--dest", default="scratch/figma-exports")

    args = parser.parse_args()

    if args.cmd == "me":
        info = me()
        print(f"User: {info['email']}")
        print(f"Handle: {info['handle']}")
        print(f"Teams: {len(info['teams'])}")
        for t in info['teams']:
            print(f"  - {t['name']} ({t['id']})")
        if not info['teams']:
            print("  (No teams — files must be shared directly to your account)")

    elif args.cmd == "file":
        data = file_meta(args.key, args.depth)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"Name: {data.get('name')}")
            print(f"Key: {data.get('key')}")
            print(f"Last modified: {data.get('lastModified')}")
            print(f"Version: {data.get('version')}")
            print(f"Thumbnail: {data.get('thumbnailUrl')}")
            doc = data.get("document", {})
            print(f"Top-level pages: {len(doc.get('children', []))}")

    elif args.cmd == "pages":
        result = list_pages(args.key)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"File: {result['file_name']}")
            print(f"Last modified: {result['last_modified']}")
            print()
            for p in result['pages']:
                print(f"  {p['id']:20s}  {p['name']:50s}  ({p['frame_count']} frames)")

    elif args.cmd == "frames":
        frames = list_frames(args.key, args.page)
        if args.json:
            print(json.dumps(frames, indent=2))
        else:
            if not frames:
                print("No frames found.")
                return
            for f in frames:
                print(f"  {f['id']:20s}  [{f['page']}]  {f['name']}")

    elif args.cmd == "text":
        texts = extract_text(args.key, args.page)
        if args.json:
            print(json.dumps(texts, indent=2))
        else:
            print(f"Extracted {len(texts)} text elements")
            print()
            current_frame = None
            for t in texts:
                if t['frame'] != current_frame:
                    current_frame = t['frame']
                    print(f"\n--- {t['page']} > {current_frame} ---")
                print(f"  {t['characters']}")

    elif args.cmd == "export":
        paths = export_frames(args.key, args.ids, args.format, args.scale, args.dest)
        print(f"\nExported {len(paths)} file(s) to {args.dest}")


if __name__ == "__main__":
    main()
