---
name: meeting-intake
description: 'Process raw meeting notes (Fathom exports, transcripts, hand-added dumps) from the inbox/ folder. Reads each file, proposes filename + date + topics + priority + series links, files to projects/<project>/meetings/, adds frontmatter, updates topic MOCs and project MOC, moves originals to inbox/processed/. Optionally pulls the latest Fathom recordings first via scripts/fathom-fetch.py (see references/fathom-api.md). Use when the user says "process the inbox", "file the new meeting", "triage the inbox", "handle the Fathom dump", or when new files appear in inbox/.'
---

## What this skill does

Pulls meeting captures into the vault, processes them, and files them as structured meeting notes. Captures arrive in `inbox/` from three sources:

1. **Fathom recordings** — auto-fetched by `scripts/fathom-fetch.py` (Fathom API; see `references/fathom-api.md`). User runs that script separately, then triggers this skill to process the output.
2. **Hand-added meeting notes** — user drops a Fathom share-URL or other transcript directly into `inbox/` when a meeting is important for context but they weren't on it.
3. **Other transcripts** — any `.md` file in `inbox/` with a recording URL or transcript.

This skill reads what's in `inbox/`, proposes a structured filing, and on confirmation moves files to `projects/<project>/meetings/` with frontmatter + Related section. Updates topic MOCs and the project MOC. Moves originals to `inbox/processed/`.

The workflow spec lives at `inbox/README.md` — read it first to understand the design.

## When to use it

- User says "process the inbox" / "file the new meeting" / "triage the inbox" / "handle the Fathom dump" / "intake my meetings"
- New files appear in `inbox/` and user indicates they want them filed
- User just ran `python scripts/fathom-fetch.py` (or `--backfill` for all unprocessed) and the output is sitting in `inbox/`

## When NOT to use it

- User has a single specific meeting they want filed differently (do it directly, no batch flow)
- The file is not a meeting (route to appropriate type-based flow instead)
- Inbox is empty AND user just wants to check Fathom — run `scripts/fathom-fetch.py` directly, then come back here

## Related tools and docs

- **`scripts/fathom-fetch.py`** — Fathom API poller. Default: latest unprocessed meeting. `--backfill` flag: walks ALL unprocessed. Output: `inbox/YYYY-MM-DD - <topic>.md`. See `references/fathom-api.md` for endpoints, auth, and known limitations.
- **`references/fathom-api.md`** — research note on the Fathom API. Read before changing the fetch script or debugging wire-up issues.
- **`inbox/README.md`** — workflow spec for the inbox → processed → projects flow. Read first.

## Execution

### Step 0: Optional Fathom pre-fetch

If `inbox/` is empty AND user indicates they want fresh Fathom recordings:

```bash
python scripts/fathom-fetch.py            # latest unprocessed only
python scripts/fathom-fetch.py --backfill # all unprocessed
```

The fetch is a separate skill concern (mechanical, idempotent). After fetching, return to Step 1.

If `inbox/` already has files, skip this step — proceed to inventory.

### Step 1: Inventory

List `inbox/` contents. Skip `inbox/processed/` and any subdirectories. If empty, suggest running `scripts/fathom-fetch.py` (see Step 0) and stop.

### Step 2: Read each file

For each `.md` in `inbox/`, read and extract:

- **Date** — from filename if `YYYY-MM-DD` present; else from content (Fathom email date, "Meeting Purpose" timestamp, first line of summary, recording URL timestamp)
- **Topics** — from Key Takeaways + Topics sections
- **Priority** — `workflow | roles | ai-onboarding | none` (map to user's Q-priorities when relevant)
- **Attendees** — names mentioned in transcript/summary
- **Recording URL** — Fathom share link
- **Project** — determine which project the meeting belongs to (heuristics: people mentioned, tools/products referenced, project name in filename or content). If unclear, ASK the user.
- **Observer vs attendee** — if the user's name is absent from attendees/transcript and the file was hand-added, note it (e.g. `note: User was not present (declined per calendar)` in frontmatter). Flag this in the proposal.

### Step 3: Check existing state

For each file:

- Does target `projects/<project>/meetings/` already exist? → duplicate, flag and skip
- Does project have a MOC at `projects/<project>/README.md`? → note for later update
- Which topic MOCs exist that match the inferred topics? List them.
- Any topics new (no MOC yet)? → flag for new-MOC proposal
- Series detection: find earlier meetings with same primary topic in `projects/<project>/meetings/` → offer prev/next links

### Step 4: Propose

Show the full proposal for each file. Format:

```
File 1: ""
  → projects/<project>/meetings/YYYY-MM-DD - <topic>.md
  Date: YYYY-MM-DD (source: filename / content line N)
  Topics: [topic-a, topic-b]  ⚠ if any new
  Priority: <p>
  Series: ← [[prev-or-—]] | → [[next-or-—]]
  Observer: User was/was not on this meeting (source: ...)
  Decisions mentioned: [...]
  Attendees: [...]
  Recording: <url>
```

Wait for user's "go" or specific changes per file.

### Step 4b: Flag name and term inconsistencies

Fathom summaries and speech-to-text are especially prone to drift. Actively scan the file for:

- **Name variants** — same person referenced under different spellings or shorthand (e.g. "Bob" / "Robert" / "Bobby" for the same person).
- **Acronyms** — terms introduced once then referenced by abbreviation without a clear definition.
- **Concept drift** — same concept called by different terms in different places (e.g. "bug log" → "defect tracker", "card" → "tile").
- **Typos from speech-to-text** — single-character errors (e.g. "Kyen" for "Kai", "PEEX" for "PEAKS").
- **Project / tool name drift** — speech-to-text errors on product names ("Mixed Panel" → "Mixpanel").

Output format, grouped by referent:

```
Inconsistencies found in File 1:
  Names:
    - Bob (canonical) appears as: "Bob", "Robert", "Bobby"
    - Carol (canonical) appears as: "Carol", "Caz"
  Terms:
    - TCA: introduced as "content architecture" / "TCA" — full form not stated
    - Mixpanel: appears as "Mixed Panel" (1x) — likely transcription drift
```

Wait for the user to confirm canonical forms. Apply confirmed canonical names in frontmatter, summary sections (Meeting Purpose / Key Takeaways / Topics / Next Steps), and Action Items. **Preserve the verbatim transcript as-is** — add a clarifying note at the top of the transcript block instead, listing the name and acronym mappings so future readers can decode the verbatim text. Historical record stays intact; navigability improves.

### Step 5: File (on confirm)

For each file, in order:

1. `mv` to target path
2. Prepend frontmatter. **First line MUST be `---` with no leading blank** — verify after prepend. Format:
   ```yaml
   ---
   type: meeting
   status: active
   date: YYYY-MM-DD
   topic: [topic-a, topic-b]
   priority: workflow | roles | ai-onboarding | none
   recording: <url>
   attendees: [name-a, name-b]
   note: <optional, e.g. observer context>
   ---
   ```
3. Apply canonical names + terms from Step 4b to frontmatter, summary sections (Meeting Purpose / Key Takeaways / Topics / Next Steps), Action Items, and Related section. **Do NOT alter the transcript block** — the clarifying note added in Step 4b handles decoding for readers.
4. Append "Related" section at end:
   ```markdown
   
   ---
   
   ## Related
   - **Topics:** [[topic-a]], [[topic-b]]
   - **Series:** ← [[prev]] | → [[next]]
   - **Decisions mentioned:**
     - ...
   - **Related notes:** [[other-relevant]]
   ```
5. Update affected topic MOC(s) — add this meeting to their "Meetings" section
6. Update project MOC "Recent meetings" section (cap 5-7; archive older out if needed)
7. If a new topic MOC was proposed + approved, create it (stub form, see `inbox/README.md` for the template structure) and add to project MOC "Topics" section
8. `mv` original from `inbox/` to `inbox/processed/`

### Step 6: Report

Print summary:

```
Filed N meetings:
  ✓ YYYY-MM-DD - topic.md → projects/<project>/meetings/

Updated:
  + topics/<new-moc>.md (new)
  ~ topics/<existing-moc>.md (1 new meeting)
  ~ projects/<project>/README.md (Recent meetings, Topics)

Moved to inbox/processed/:
  - <original-filenames>
```

## Edge cases

| Situation | What to do |
|---|---|
| Inbox empty AND no Fathom fetch triggered | Suggest `python scripts/fathom-fetch.py` (see Step 0). Stop. |
| Inbox empty AND Fathom just fetched | Likely fetch returned nothing new (already processed). Confirm with user. |
| Filename has no date | Parse from Fathom content; ask user to confirm |
| Topic with no MOC yet | Propose new MOC (stub); ask before creating |
| No clear topic (rare) | Ask user to pick from existing topic list |
| Non-meeting file (no transcript, no Fathom URL) | Ask if it should be filed as spec/decision/note instead |
| Duplicate (target file already exists) | Flag and skip |
| Same primary topic as existing meeting | Offer prev/next series links |
| Project MOC "Recent meetings" > 7 entries | Archive older out, keep recent 5-7 |
| File already has frontmatter (re-process) | Confirm intent — overwrite / merge / skip |
| Frontmatter prepend left a leading blank line | Fix: remove the blank, ensure first line is `---` |
| Many name/term inconsistencies in one file | Still do Step 4b as one block, but flag to user that there are many — consider a separate "glossary" decision note if 5+ canonical forms need locking in |
| Inconsistencies span across multiple existing meetings | Same name appears inconsistently across processed files — after Step 4b, offer to grep the vault for other instances and propose a sweep |
| User was not on the meeting (observer context) | Add `note:` to frontmatter, mark **Observer note:** in Related section |
| Fathom API key not in `.env` | Flag to user; do not run `fathom-fetch.py`. See `references/fathom-api.md` for setup. |

## What this skill will NOT do

- **Auto-process on session start.** User triggers.
- **Rename originals.** Moved verbatim to `inbox/processed/`.
- **File silently.** Every batch: propose → confirm → file.
- **Extract decisions to separate notes.** Separate flow if user wants.
- **Touch `inbox/processed/`.** User manages cleanup.
- **Process files outside `inbox/`.** Other files are out of scope.
- **Run the Fathom fetch automatically.** Step 0 is opt-in — user runs the script or asks.

## Notes

- The skill assumes a vault with `inbox/` and `projects/<project>/` structure. If the vault doesn't have it, prompt the user to scaffold first (or use the layout from the kit).
- Series prev/next is sparse initially — fill in as new meetings come in. Don't fabricate links.
- For Obsidian frontmatter YAML, the first line of the file MUST be `---` (no leading blank). Always verify after prepend.
- Effort per meeting: ~30s user side (drop + trigger), ~60s AI side (propose + file).
- If Fathom format changes (different heading structure), update parsing heuristics in Step 2.
- Trigger phrases that work: "process the inbox", "triage the inbox", "file the new meeting", "handle the Fathom dump", "intake my meetings".