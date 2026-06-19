# Inbox — workflow spec

Raw meeting captures (Fathom exports, hand-added transcripts, screenshots) land here. The `/meeting-intake` skill reads `inbox/`, proposes a structured filing, and on confirmation moves files to `projects/<project>/meetings/`.

## Flow

```
inbox/                    ← raw captures land here
  ↓  /meeting-intake
inbox/processed/          ← originals moved here after filing (historical record, never deleted)
  ↓
projects/<slug>/meetings/ ← filed meeting notes with frontmatter + Related section
```

## Three sources of captures

1. **Fathom recordings** — auto-fetched by `python scripts/fathom-fetch.py`. Output: `inbox/YYYY-MM-DD - <topic>.md`. Default mode fetches the latest unprocessed meeting. `--backfill` flag walks ALL unprocessed.
2. **Hand-added meeting notes** — drop a Fathom share-URL or other transcript directly into `inbox/` when a meeting is important for context but you weren't on it (e.g. observed-only meetings).
3. **Other transcripts** — any `.md` file with a recording URL or transcript.

## What `/meeting-intake` does (summary)

Reads each `.md` in `inbox/`, proposes:
- Target filename (`YYYY-MM-DD - <topic-slug>.md`)
- Topics (matches against existing topic MOCs in `projects/<project>/topics/`)
- Priority (workflow / roles / ai-onboarding / none)
- Series links (prev/next)
- Canonical names from name/term drift (transcript preserved verbatim with clarifying note at top)

On confirm:
1. Moves to `projects/<project>/meetings/`
2. Prepends frontmatter
3. Updates topic MOCs + project MOC "Recent meetings"
4. Moves original to `inbox/processed/`

## Do not edit `inbox/processed/` contents

Raw files there stay verbatim — they're historical record. If you need to re-process a meeting, copy it back to `inbox/` and run `/meeting-intake` again.

## Empty inbox is normal

An empty `inbox/` is the steady state. If you want fresh Fathom recordings: `python scripts/fathom-fetch.py` (default) or `python scripts/fathom-fetch.py --backfill` (all unprocessed).