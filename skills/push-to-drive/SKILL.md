---
name: push-to-drive
description: 'Use when the user wants to push a Markdown file from the vault to Google Drive as a native Google Doc. Triggers on "push to Drive", "publish as Google Doc", "upload to Drive as a doc", "make this a Google Doc", "send X to Drive", "publish X". Wraps the full pipeline: strip frontmatter, strip Obsidian wiki links, convert .md → HTML via the `markdown` library, upload to a configured sandbox folder with metadata mimeType set to trigger Drive conversion to a true native Google Doc. No pandoc dependency.'
---

# Push to Drive

Publish a vault Markdown file to a configured Google Drive folder as a Google Doc. One command, one URL back.

## When to use

- User says "push X to Drive", "publish X as Google Doc", "upload X to Drive", "make this a Google Doc", "send X to Drive"
- User wants to share a vault document with someone who works in Google Docs
- User wants a vault file backed up to Drive in an editable format

## When NOT to use

- User wants to share a file as raw Markdown (use `google_drive_api.py upload` directly)
- User wants to upload a non-Markdown file (PDF, image, etc.) — use `google_drive_api.py upload` directly
- User wants to add a file to a folder outside the configured sandbox — refuse, use Drive UI
- User wants to edit an already-published Google Doc — direct them to the Google Docs URL from the previous publish

## Pre-conditions

- `scripts/google_drive_api.py` and `scripts/google_auth.py` are set up (see `scripts/README.md`)
- `markdown` Python library is installed (`pip install markdown`)
- OAuth token is valid (`token.pickle` / `token.json` exists and isn't expired/revoked)
- `GOOGLE_DRIVE_DEFAULT_FOLDER_ID` (or `PUSH_TO_DRIVE_FOLDER_ID`) is set in `.env` to the destination folder
- Source file is a `.md` or `.markdown` file

## Execution

The skill is a thin wrapper around `scripts/push_to_drive.py`. Run the script with appropriate args.

### Basic usage

```bash
python scripts/push_to_drive.py "path/to/file.md"
```

This uploads to the configured sandbox folder with the file's name (without `.md` extension). The script prints the native Google Doc URL on success.

### Options

| Flag | Effect |
|---|---|
| `--name "Q2 Plan"` | Custom name in Drive (default: source filename without `.md`) |
| `--parent <folder_id>` | Upload to a specific subfolder of the sandbox |
| `--keep-frontmatter` | Keep YAML frontmatter (default: strip) |
| `--keep-wikilinks` | Keep `[[...]]` wiki links literal (default: strip brackets, keep display text) |

### What gets stripped (by default)

- **YAML frontmatter** between the first two `---` markers at the top
- **Obsidian wiki links** like `[[QA Upskilling Plan]]` → "QA Upskilling Plan", and `[[Page|Display]]` → "Display"

These are Obsidian-specific and don't make sense in a Google Doc.

### What the script does

1. Read the source `.md` file
2. Strip frontmatter + wiki links (unless `--keep-*` flags)
3. Convert cleaned Markdown to HTML via the `markdown` Python library (extensions: tables, fenced_code, toc, sane_lists, nl2br)
4. Wrap in a full HTML document with sane default CSS (Drive strips most of it, but the wrap is needed for proper parsing)
5. Upload to the sandbox folder with file metadata mimeType set to `application/vnd.google-apps.document` — this is the trick that tells Drive to convert the HTML to a native Google Doc on the way in
6. Print the native Google Doc URL (`docs.google.com/document/d/...`, mime type comes back as `application/vnd.google-apps.document`)

## Confirming success

After running, verify and report to the user:
- File name in Drive
- The `docs.google.com/document/d/...` URL (this is the Google Docs editor link for a native Google Doc)
- The mime type came back as `application/vnd.google-apps.document` (a true native Google Doc, not a DOCX preview)

If the printed URL has `drive.google.com/file/d/...` instead, OR if the mime type came back as `text/html`, the conversion failed. Investigate:
- Did the markdown library succeed? (check stderr)
- Was the metadata mimeType set to `application/vnd.google-apps.document`?
- Is the OAuth scope correct? (needs full `drive` scope, not `drive.file`)

## Limitations

- **Sandboxed to configured folder** — script-level enforcement, same as `google_drive_api.py`
- **One-way** — the script doesn't sync changes. If you edit the `.md` in the vault, re-run the script to update. The script always creates a NEW Google Doc (it doesn't update the existing one).
- **No two-way sync** — if you edit the Google Doc, those changes don't flow back to the `.md`. The vault is the source of truth.
- **Wiki links** — the `[[...]]` syntax is Obsidian-specific. After stripping, the Google Doc shows plain text references. If you need the Google Doc to link to another Google Doc, do that manually in the Google Docs UI.

## Why HTML (not .md or .docx)?

Google Drive's API does not auto-convert `.md` files to Google Docs. The default upload of `.html` ALSO does not auto-convert. However, you can force conversion by setting the file metadata mimeType to the target Google-native format (e.g. `application/vnd.google-apps.document`). The Python v3 client doesn't expose a `convert=true` parameter directly, so we use this metadata trick.

The `.md` → `.docx` via pandoc → Drive pipeline produces DOCX files with a docs.google.com preview link — not true native Google Docs. The HTML path is faster (no pandoc binary), simpler (no 30MB dependency), AND produces real native Google Docs that are exportable via the Google Docs API.

Quality: HTML conversion preserves headings, lists, tables, bold/italic, links, inline code, horizontal rules. Code blocks lose monospace formatting, task list checkboxes become literal `[x]` text, blockquotes lose semantic structure. For typical vault content (meeting notes, MOCs, specs), this is more than adequate.

## Related

- `scripts/push_to_drive.py` — the wrapper script
- `scripts/google_drive_api.py` — underlying Drive operations
- `scripts/google_auth.py` — OAuth bootstrap
- `references/google-drive-api.md` (if you've written one) — Drive API reference