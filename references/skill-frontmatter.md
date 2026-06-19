---
type: reference
status: active
date: 2026-06-18
---

# Skill Frontmatter Standard

How to write `SKILL.md` frontmatter so pi's loader never silently drops your skill.

## The rule

**Always wrap the `description` value in single quotes.**

```yaml
---
name: my-skill
description: 'Single line, quoted. Add more detail here if needed.'
---
```

That's it. Single quotes are the safest YAML scalar for free-form prose because the only escape needed is doubling a single quote (`''`).

## Why

Pi's skill loader runs a YAML parser on every `SKILL.md`. If parsing fails, the description is dropped. If the description is empty, the skill is **not loaded** — silently. The file sits on disk looking valid, but it's not registered.

We hit this on 2026-06-18 with `push-to-drive`: description had unquoted colons (`"push to Drive":`, `"publish as Google Doc":`), YAML read them as nested mappings, parse failed, skill never appeared in the system prompt.

## Gotchas to avoid

If you ever drop the quotes for any reason, watch out for these in your description value:

| Char / pattern | Risk | Example |
|---|---|---|
| `: ` (colon + space) | Read as nested mapping | `Triggers on "x: y"` |
| Leading `#` | Read as comment | `#1 cause of bugs` |
| Leading `-` or `?` | Read as list / key indicator | `- foo` |
| `:` or `-` at end of value | Read as mapping / list | `description: foo:` |
| `[` or `{` followed by space | Read as flow sequence / mapping | `see [docs]` |
| Unbalanced quotes | String terminates early | `it's` |
| Multi-line value | Needs `\|` or `>` block scalar | line 1<br>line 2 |

## Validation script

Run before committing any new skill:

```bash
python scripts/lint-skills.py
```

Lints every `SKILL.md` under `.pi/skills/`. Uses pi's actual `loadSkills()` so it catches the same errors pi would at session start. Returns non-zero exit code on any failure.

To lint a single skill:

```bash
python scripts/lint-skills.py --skill push-to-drive
```

## Template

Copy this and fill in:

```yaml
---
name: my-skill
description: 'One-paragraph summary. Triggers on "phrase one", "phrase two", "phrase three". What the skill does and when to load it.'
---

# My Skill

Short skill title and one-line value prop.

## When to use

- Trigger phrase
- User goal

## When NOT to use

- Adjacent task that's covered elsewhere

## Pre-conditions

- Setup needed before first use

## Execution

Step-by-step.
```

## Checklist before shipping

- [ ] `description` wrapped in single quotes
- [ ] `name` matches parent directory (convention; not enforced)
- [ ] `name` is lowercase a-z, 0-9, hyphens only
- [ ] `name` ≤ 64 chars
- [ ] `description` ≤ 1024 chars
- [ ] No leading/trailing hyphens in `name`, no consecutive hyphens
- [ ] `python scripts/lint-skills.py` exits 0

## Related

- `scripts/lint-skills.py` — the validator
- `pi docs: skills.md` — full Agent Skills spec
- `decisions/log.md` — 2026-06-18 entry on this standard