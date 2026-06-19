# Scripts — connector library

Python scripts that hit external APIs the AIOS reaches. Each script is a thin wrapper — no business logic, no AI calls. They output JSON or human-readable text. AI skills consume them.

## Quick start

```bash
# 1. Copy .env.example to .env at the vault root
cp .env.example .env

# 2. Fill in the API keys you need (leave others blank)
#    See "Setup" sections below for each tool.

# 3. Install dependencies
pip install requests python-dotenv google-api-python-client google-auth-httplib2 google-auth-oauthlib markdown

# 4. Run any script
python scripts/lint-skills.py                      # validates all SKILL.md files
python scripts/google_calendar_api.py events       # next 5 calendar events
python scripts/fathom-fetch.py                      # fetch latest Fathom recording
```

## Scripts

### `lint-skills.py` — validates `SKILL.md` frontmatter

No API key needed. Runs pi's actual skill loader against your `SKILL.md` files to catch YAML errors, missing descriptions, name violations, etc. Use this before committing any new skill.

```bash
python scripts/lint-skills.py                # all skills
python scripts/lint-skills.py --skill NAME   # one skill
python scripts/lint-skills.py --json         # JSON output (for CI)
```

**Prereq:** Node.js in PATH. Optionally set `PI_DIST` env var if pi's dist directory isn't auto-detected.

### `google_auth.py` — OAuth bootstrap for all Google APIs

Helper module imported by the other Google scripts. Handles the OAuth flow (token creation + refresh). Run any Google script once to trigger the first-time consent flow.

```python
from google_auth import get_calendar_service, get_gmail_service, get_drive_service
service = get_calendar_service()
```

**Prereq:** `credentials.json` at the vault root (OAuth client ID). Download from Google Cloud Console → APIs & Services → Credentials → Create OAuth client ID (Desktop app). First run opens a browser for consent; subsequent runs use `token.pickle` / `token.json`.

**Scopes needed:** `https://www.googleapis.com/auth/calendar`, `https://www.googleapis.com/auth/gmail.readonly`, `https://www.googleapis.com/auth/drive` (full drive, not `drive.file`).

### `google_calendar_api.py` — Calendar read/write

```bash
python scripts/google_calendar_api.py events --days 3 --max 30 --verbose
python scripts/google_calendar_api.py today
python scripts/google_calendar_api.py update <event_id> --yes   # WRITE — confirm first
```

**Env:** `GOOGLE_CREDENTIALS_FILE`, `GOOGLE_TOKEN_FILE` (defaults in `.env.example`).

**Write safety:** Update/delete operations prompt for y/N unless `--yes` is passed. The AI is configured to never pass `--yes` without explicit user confirmation.

### `gmail_api.py` — Gmail read (and draft, with confirmation)

```bash
python scripts/gmail_api.py unread --max 10
python scripts/gmail_api.py search "from:alice newer_than:7d" --max 20
python scripts/gmail_api.py send --to user@example.com --subject "..." --body "..." --yes
```

**Env:** Same as Calendar (uses `google_auth.get_gmail_service()`).

**Write safety:** Same as Calendar — `--yes` required for any send operation.

**Cross-platform note:** On Windows, Python's default `cp1252` stdout can crash with "I/O operation on closed file" when printing emoji. The script handles this via `sys.stdout.reconfigure(encoding="utf-8")`. If you fork this script, replicate the reconfigure at the top.

### `google_drive_api.py` — Drive read/write (sandboxed)

**Sandbox enforcement:** This script is locked to a configured folder. Set `GOOGLE_DRIVE_DEFAULT_FOLDER_ID` in `.env` to your sandbox folder ID (get it from a Drive folder URL: `drive.google.com/drive/folders/<this-part>`). All write operations verify the target is within the sandbox before executing. Reads of files outside the sandbox work but require explicit path arg.

```bash
python scripts/google_drive_api.py list --max 20
python scripts/google_drive_api.py upload path/to/file.pdf
python scripts/google_drive_api.py share <file_id> --to user@example.com --role reader --yes
```

**Write safety:** Share/delete/update operations require `--yes`. Sandbox check runs first.

### `clickup_api.py` — ClickUp lists, tasks, comments

```bash
python scripts/clickup_api.py lists --space <space_id>
python scripts/clickup_api.py tasks --list <list_id> --max 30
python scripts/clickup_api.py comment <task_id> "message" --yes
```

**Env:** `CLICKUP_API_TOKEN`, `CLICKUP_WORKSPACE_ID`.

**Write safety:** Same `--yes` gate. Comment / create / update operations prompt unless `--yes` is passed.

**Pitfall:** URL paths like `/v/l/8cgrkt6-XXXXX` are **views**, not lists. Use `GET /api/v2/view/<id>` to resolve to a list ID if you only have a view URL.

### `fathom-fetch.py` — Fathom API poller

```bash
python scripts/fathom-fetch.py              # latest unprocessed meeting
python scripts/fathom-fetch.py --backfill   # all unprocessed
python scripts/fathom-fetch.py --dry-run    # preview without writing
```

Output: `inbox/YYYY-MM-DD - <topic>.md` with full markdown (summary + transcript + action items with WATCH links). Use `/meeting-intake` skill after fetching to file into `projects/<project>/meetings/`.

**Env:** `FATHOM_API_KEY`.

**Idempotency:** Default mode stops at the first meeting already processed (compared against `inbox/processed/`). Use `--backfill` to walk all unprocessed.

**Limitations:** API key only sees meetings you recorded or that were shared with you. Confirm sharing on team members' accounts if you want their meetings to flow through.

### `figma_api.py` — Figma file reader

```bash
python scripts/figma_api.py file <file_key>
python scripts/figma_api.py nodes <file_key> --ids "1:2,3:4"
```

**Env:** `FIGMA_ACCESS_TOKEN`, `FIGMA_DEFAULT_FILE_KEY`.

**Use case:** Skim design systems, grab frames as images, audit color/spacing tokens.

### `push_to_drive.py` — MD → native Google Doc

```bash
python scripts/push_to_drive.py path/to/file.md
python scripts/push_to_drive.py path/to/file.md --name "Q2 Plan" --parent <folder_id>
python scripts/push_to_drive.py path/to/file.md --keep-frontmatter --keep-wikilinks
```

**Env:** Same as `google_drive_api.py` (uses Drive API).

**How it works:** Markdown → HTML via the `markdown` library → upload with metadata `mimeType: application/vnd.google-apps.document`. This metadata trick triggers Drive to convert the HTML to a true native Google Doc on the way in (not a DOCX preview).

**Stripped by default:** YAML frontmatter, Obsidian wiki links (`[[...]]` → display text).

**One-way:** Always creates a new Google Doc. Doesn't update existing ones. Re-run to publish a new version.

## General patterns

### Cross-platform Python

- **Windows UTF-8 fix**: `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at the top of any script that prints emoji (`✓`, `❌`, `⚠`) or non-ASCII. The default `cp1252` stdout can't encode them.
- **Paths**: Use `pathlib.Path` throughout, never `os.path.join` with backslashes.
- **Line endings**: All scripts are LF. Python handles both fine on read; just don't manually concatenate strings with `\r\n`.

### Secrets

- **Never commit `.env`.** `.gitignore` covers it.
- **API tokens read from `.env` via `python-dotenv`.** Each script calls `load_dotenv(VAULT_ROOT / ".env")` at startup.
- **OAuth tokens** (Google): `token.pickle` / `token.json` at vault root, also gitignored.

### Write safety

Every connector script that can write follows the same pattern:
- Print a preview of the action
- Prompt `y/N` unless `--yes` is passed
- Refuse to proceed on `N`

The AI skill layer is configured to **never** pass `--yes` without explicit user confirmation. This is enforced by convention, not by code — users can override but shouldn't.

### When to add a new connector

If `/audit` flags a Tier-1 domain as unreachable AND no MCP exists for it, the right move is usually:
1. Research the API once → `references/{tool}-api.md`
2. Write a thin Python script following the patterns above
3. Document in this README

Skipping research and re-using patterns from existing scripts is fine; reinventing the auth + write-safety boilerplate is not.