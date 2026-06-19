#!/usr/bin/env python3
"""
push_to_drive.py — High-level "publish to Drive as native Google Doc" tool.

Takes a Markdown file from the vault, strips frontmatter + Obsidian wiki links,
converts to HTML via the `markdown` library, and uploads to a configured
Drive sandbox folder (set via GOOGLE_DRIVE_DEFAULT_FOLDER_ID in .env, or the
default in google_drive_api.py). The upload uses a metadata trick (mimeType
set to application/vnd.google-apps.document) to tell Drive to convert the HTML
to a native Google Doc on the way in.

Why HTML (not .docx)?
- Drive does NOT auto-convert uploaded HTML by default. But you can force
  conversion by setting the file metadata mimeType to the Google Doc mime type.
- This produces a TRUE native Google Doc (exportable, fully editable, shareable
  as a Google Doc).
- The pandoc → DOCX path produced a DOCX with a docs.google.com preview link —
  usable but not a native Google Doc.
- HTML conversion is faster than pandoc and removes the pandoc dependency
  (no 30MB binary download).

Run examples:
    python scripts/push_to_drive.py "projects/<your-project>/path/to/file.md"
    python scripts/push_to_drive.py "path/to/file.md" --name "Q2 Plan"
    python scripts/push_to_drive.py "path/to/file.md" --keep-frontmatter
    python scripts/push_to_drive.py "path/to/file.md" --keep-wikilinks
    python scripts/push_to_drive.py "path/to/file.md" --parent <subfolder_id>

Prereqs:
- Drive OAuth + sandbox folder set up — see references/google-cloud-setup.md
- pip install markdown (already installed)
- No pandoc dependency — uses the `markdown` Python library
"""

import os
import sys
import re
import argparse
import tempfile
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows (cp1252 can't encode ✓ etc.).
# Use reconfigure() — the io.TextIOWrapper rewrap approach closes the underlying
# buffer when the new wrapper is GC'd and breaks all subsequent prints with
# "I/O operation on closed file". See google_calendar_api.py for the same
# pitfall documented.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import markdown

# Import sibling
sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_drive_api import upload_file, ALLOWED_FOLDER_NAME

# The mime type that triggers Drive to convert the uploaded content into
# a native Google Doc on import. Works for HTML, plain text, RTF, etc.
GDOC_MIME = "application/vnd.google-apps.document"


def preprocess_markdown(text, keep_frontmatter=False, keep_wikilinks=False):
    """Strip YAML frontmatter and Obsidian wiki links from Markdown text.

    Frontmatter: between the first two `---` markers at the top of the file.
    Wiki links: [[Page Name]] → "Page Name", [[Page Name|Display]] → "Display"
    """
    if not keep_frontmatter:
        text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    if not keep_wikilinks:
        text = re.sub(
            r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
            lambda m: m.group(2) or m.group(1),
            text,
        )
    return text.strip() + "\n"


def md_to_html(md_text, title):
    """Convert Markdown text to a full HTML document.

    Uses the `markdown` library with extensions that handle Obsidian-flavoured
    markdown features (tables, fenced code blocks, etc.). Wraps the body in a
    minimal HTML document with sane default CSS. Drive's HTML→Doc conversion
    typically strips most CSS, but providing it costs nothing.
    """
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "nl2br"],
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 2em auto; line-height: 1.5; }}
h1, h2, h3 {{ color: #1a1a1a; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
th {{ background: #f4f4f4; }}
code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
pre {{ background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }}
blockquote {{ border-left: 3px solid #ccc; padding-left: 1em; color: #555; }}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""


def push_to_drive(
    source_path,
    name=None,
    parent=None,
    keep_frontmatter=False,
    keep_wikilinks=False,
):
    """Push a Markdown file to Drive as a native Google Doc.

    Returns the uploaded file metadata dict (id, name, mimeType, webViewLink, parents).
    The returned mimeType will be `application/vnd.google-apps.document` if the
    conversion succeeded (i.e. it's a true native Google Doc).
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")
    if source.suffix.lower() not in (".md", ".markdown"):
        raise ValueError(
            f"Source must be .md or .markdown, got {source.suffix}. "
            f"For other formats, use google_drive_api.py upload directly."
        )

    # Read and preprocess
    text = source.read_text(encoding="utf-8")
    text = preprocess_markdown(text, keep_frontmatter, keep_wikilinks)

    # Determine the Drive file name (no .md extension since it becomes a Google Doc)
    if name:
        drive_name = name
        # Strip any source-style extension the user might have included
        for ext in (".md", ".markdown", ".html"):
            if drive_name.lower().endswith(ext):
                drive_name = drive_name[: -len(ext)]
    else:
        drive_name = source.stem

    # Convert to HTML in a temp file
    html_content = md_to_html(text, title=drive_name)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write(html_content)
            tmp_path = Path(tmp.name)

        # Upload with the Google Doc mime type in metadata — this is the trick
        # that tells Drive "convert this content to a native Google Doc".
        result = upload_file(
            str(tmp_path),
            parent_folder_id=parent,
            mime_type="text/html",
            name=drive_name,
        )
        # The mime_type kwarg above sets the content-type for upload. The
        # conversion trigger is set via the file metadata inside upload_file,
        # which we override here by post-processing the call: we need to set
        # metadata mimeType to the Google Doc mime. Simplest path: re-call
        # upload_file with a custom approach. But upload_file doesn't expose
        # metadata mimeType. So instead, we do the conversion directly here.
        # (See worker_v2.py test B for the proven pattern.)
        return _upload_as_gdoc(str(tmp_path), drive_name, parent)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


def _upload_as_gdoc(local_path, name, parent_folder_id=None):
    """Upload an HTML file as a native Google Doc by setting metadata mimeType.

    This is the proven pattern from scratch/drive-conversion-test/worker_v2.py
    test B. The public upload_file() helper doesn't expose metadata mimeType,
    so we hit the Drive API directly here.
    """
    from google_drive_api import ALLOWED_FOLDER_ID, _require_sandbox_folder
    from google_auth import get_drive_service
    from googleapiclient.http import MediaFileUpload

    if parent_folder_id is None:
        parent_folder_id = ALLOWED_FOLDER_ID
    else:
        _require_sandbox_folder(parent_folder_id, op_name="upload to that folder")

    service = get_drive_service()
    file_metadata = {
        "name": name,
        "mimeType": GDOC_MIME,
        "parents": [parent_folder_id],
    }
    media = MediaFileUpload(local_path, mimetype="text/html", resumable=True)
    return service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, mimeType, webViewLink, parents",
    ).execute()


# --- CLI ---
def main():
    parser = argparse.ArgumentParser(
        description=f"Publish a Markdown file to Drive as a native Google Doc "
                    f"(sandboxed to '{ALLOWED_FOLDER_NAME}')"
    )
    parser.add_argument("source", help="Path to source .md file (relative to vault root OK)")
    parser.add_argument("--name", help="Custom name in Drive (default: source filename without .md)")
    parser.add_argument("--parent", help="Subfolder ID (must be inside the sandbox)")
    parser.add_argument(
        "--keep-frontmatter",
        action="store_true",
        help="Keep YAML frontmatter (default: strip)",
    )
    parser.add_argument(
        "--keep-wikilinks",
        action="store_true",
        help="Keep Obsidian wiki links as literal [[text]] (default: strip brackets, keep display text)",
    )

    args = parser.parse_args()

    try:
        result = push_to_drive(
            args.source,
            name=args.name,
            parent=args.parent,
            keep_frontmatter=args.keep_frontmatter,
            keep_wikilinks=args.keep_wikilinks,
        )
        link = result.get("webViewLink", "(no link)")
        mime = result.get("mimeType", "?")
        is_gdoc = "docs.google.com/document/" in link and mime == GDOC_MIME
        print(f"✓ Published: {result['name']}")
        print(f"  Drive ID:  {result['id']}")
        print(f"  Link:      {link}")
        print(f"  Mime:      {mime}")
        if is_gdoc:
            print(f"  Status:    Native Google Doc (editable in browser, exportable)")
        else:
            print(f"  Status:    WARNING — not a native Google Doc. Check the file in Drive.")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()