# Vault Operations — {{Your Name}}'s AIOS

How the AI behaves inside this specific vault. Distinct from the identity/persona layer (see `APPEND_SYSTEM.md` for pi users, or the top section of `CLAUDE.md` for Claude Code users).

**For pi users:** copy this file to your vault root as `AGENTS.md`. Pi reads this file at session start.

**For Claude Code users:** the content of this file is already merged into your `CLAUDE.md` at the vault root. Edit that file directly.

---

## Edit policy

- **Consult before editing existing project files** unless the change is purely additive (new file, append to a log, frontmatter tweak). {{Your Name}} catches things they didn't expect — that's a feature, not friction.
- **New files are fair game** — scripts, research notes, new project folders. Don't ask to create them, ask to confirm where they go.
- **Renames / moves / deletions of existing files: confirm first.** Always.
- **Decisions go in `decisions/log.md`** when they affect future work, scope a project, or commit to a direction. Format: dated heading + Decision / Why / Alternatives / Owner.

---

## Naming conventions

- **Research notes:** `references/{tool}-api.md` — endpoints, auth, common queries, one file per wired tool.
- **Scripts:** `scripts/{action}.py` — lowercase, verb-noun. Each script that hits an API needs a corresponding `references/{tool}-api.md`.
- **Project folders:** `projects/{project-slug}/` — one folder per active project. Inside: meeting notes, MOCs, work-in-progress.
- **Meeting files:** `YYYY-MM-DD - {topic-slug}.md` — date prefix, hyphenated slug. Filename matches the meeting title (sluggified).
- **Archives:** `archives/{YYYY-MM-DD-HHMM}/{filename}` — full snapshot with timestamp, never overwrite.
- **Inbox → Processed → Project flow:**
  - Raw captures land in `inbox/` (Fathom dumps, screenshots, loose notes).
  - `/meeting-intake` files them to `inbox/processed/` and routes to `projects/{slug}/meetings/`.
  - Old inbox items never deleted; moved to `inbox/processed/`.

---

## When to archive vs delete

- **Archive (move to `archives/`)** when: file is replaced by a better version, content has been captured elsewhere, or you're unsure.
- **Delete** only when: file is genuinely empty/wrong, OR contains sensitive data that shouldn't persist (then redact first).
- **Raw files in `inbox/processed/`** stay there indefinitely — they're historical record.

---

## Frontmatter conventions

Every project file (meetings, specs, MOCs) gets YAML frontmatter. Minimum:

```yaml
---
type: <meeting|spec|moc|focus|reference>
status: <active|archived>
date: YYYY-MM-DD
---
```

Add `topic:`, `priority:`, `recording:`, `attendees:` as relevant. See any meeting file for the full template.

---

## Skill frontmatter (strict rule)

Files under `<harness>/skills/<name>/SKILL.md` follow a stricter rule set. The non-negotiables:

- **`description` is always wrapped in single quotes.** Unquoted descriptions with colons, hashes, or other YAML metacharacters silently break the skill loader — the skill won't appear in the system prompt. Single quotes make the value a literal string.
- **New and edited `SKILL.md` files must pass `python scripts/lint-skills.py`** (exit 0) before commit. Lint runs pi's actual `loadSkills()` against the vault, so it catches every failure mode pi would hit at session start.

See `references/skill-frontmatter.md` for the full spec.

---

## The Default Shift

Before doing any manual task 3+ times, ask: *"To what extent could AI be leveraged here?"* If there's a clear automation candidate, surface it — don't wait for `/level-up`. If automation is too heavy for the current scope, log it as a candidate for the next `/level-up` session.

---

## Voice for vault content

- **Short sentences. Bullet points over paragraphs. No em dashes.**
- **External content** (LinkedIn, client emails): don't fake the user's voice. Draft, show, then send.
- **Internal content** (this vault): match the user's casual-professional register per `references/voice.md`. Notes can be loose.
- **System prompts and skill files**: no jokes, no fluff, structurally clean. Function over form.