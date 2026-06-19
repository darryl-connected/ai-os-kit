# AIS-OS Kit — Personal AI Operating System, harness-agnostic

A free, MIT-licensed starter kit that turns any AI coding harness into your personal **AI Operating System (AIOS)**. Audience: anyone building automations — solopreneurs, small business operators, managers, creators, AI consultants.

Pairs with any harness that reads markdown + structured frontmatter. Built and tested on **pi** and **Claude Code**; works on Cursor, Cline, and other markdown-aware harnesses via the same adapter pattern.

> **AIS-OS** stands for **AI Automation Society OS** — the way Nate Herk designed the original AIOS to be set up for members of his community, [AI Automation Society](https://www.skool.com/ai-automation-socety). This kit extends that work with additional skills, a connector library, and a harness-agnostic adapter layer.

---

## What's different about this kit

| Aspect | Original AIS-OS | This kit |
|---|---|---|
| Skills shipped | 3 (`onboard`, `audit`, `level-up`) | 6 (+ `meeting-intake`, `gameplan`, `push-to-drive`) |
| Harness support | Claude Code only | pi + Claude Code (Cursor/Cline work via adapter pattern) |
| Connectors | None bundled | 9 Python scripts covering Google Workspace, ClickUp, Fathom, Figma |
| Architecture | Single `CLAUDE.md` | Two-layer split (identity + operations) for harnesses that support it |
| Distribution | Git clone | Zip download (git-distributed connectors on the roadmap) |

---

## Quick start

1. **Unzip the kit** to a working folder on your machine.
2. **Install the harness adapter** for the AI tool you use:
   ```bash
   # pi (or any harness using .pi/skills/ convention)
   bash harnesses/pi/install.sh       # Mac/Linux/WSL/Git Bash
   powershell harnesses/pi/install.ps1 # native Windows PowerShell

   # Claude Code
   bash harnesses/claude-code/install.sh
   powershell harnesses/claude-code/install.ps1
   ```
3. **Customize your identity layer.** For pi users: copy `templates/IDENTITY.md` to your global `APPEND_SYSTEM.md` location, fill in your name, business, voice. For Claude Code users: edit `CLAUDE.md` directly.
4. **Customize operations.** Copy `templates/OPERATIONS.md` to your vault root as `AGENTS.md` (pi users) or merge into `CLAUDE.md` (Claude users).
5. **Run `/onboard`** in your harness. Answer the 7 questions in `aios-intake.md`. Day-1 file set drops at the end.
6. **Day 7:** run `/audit`. Read the Four-Cs gap report. Pick one gap to close.
7. **Day 14:** run `/level-up`. The Three Ms interview surfaces one automation worth building. Build it.
8. **Week 3+:** weekly `/level-up` ritual. One shipped artifact per week.

---

## Repo layout

```
ai-os-kit/
├── README.md                      ← you are here
├── LICENSE                        ← MIT + trademark + attribution
├── CLAUDE.md                      ← merged identity + operations (Claude Code)
├── AGENTS.md                      ← operations-only mirror (pi)
├── aios-intake.md                 ← 7-question source of truth
├── EXPANSIONS.md                  ← what to add as you grow
├── .gitignore
├── .env.example                   ← all API key slots stubbed
│
├── templates/                     ← split templates (pi-style two-layer)
│   ├── IDENTITY.md                ← global layer: persona, operator brain, voice
│   └── OPERATIONS.md              ← vault layer: skills, edit policy, conventions
│
├── skills/                        ← SINGLE SOURCE OF TRUTH for skill content
│   ├── onboard/SKILL.md           ← 7-question setup wizard
│   ├── audit/SKILL.md             ← Four-Cs gap report
│   ├── level-up/SKILL.md          ← 3Ms interview, weekly ritual
│   ├── meeting-intake/SKILL.md    ← inbox → filed meeting workflow
│   ├── gameplan/SKILL.md          ← daily plan synthesis
│   └── push-to-drive/SKILL.md     ← MD → Google Doc publish
│
├── harnesses/                     ← per-harness adapters
│   ├── pi/                        ← installs for .pi/skills/ convention
│   └── claude-code/               ← installs for .claude/skills/ convention
│
├── scripts/                       ← connector library (Python)
│   ├── lint-skills.py             ← validates all SKILL.md files
│   ├── google_auth.py             ← OAuth helper for all Google APIs
│   ├── google_calendar_api.py
│   ├── gmail_api.py
│   ├── google_drive_api.py
│   ├── clickup_api.py
│   ├── fathom-fetch.py            ← Fathom API poller
│   ├── figma_api.py
│   ├── push_to_drive.py           ← MD → native Google Doc
│   └── README.md                  ← setup + usage per script
│
├── references/
│   ├── 3ms-framework.md           ← The Three Ms of AI™ (Nate Herk, attribution)
│   └── skill-frontmatter.md       ← generic YAML standard
│
├── context/                       ← about you, your business (filled by /onboard)
├── decisions/log.md               ← append-only decisions
├── connections.md                 ← registry of every system your AIOS reaches
├── archives/                      ← old stuff. Don't delete. Move here.
├── inbox/
│   ├── README.md                  ← workflow spec
│   └── processed/                 ← filed meetings land here after /meeting-intake
│
├── projects/
│   └── demo-app/                  ← generic fake project (delete when ready)
│       ├── README.md
│       ├── meetings/
│       ├── specs/
│       └── topics/
│
└── docs/
    └── SYNC.md                    ← cross-platform sync + migration guide
```

---

## The two-layer split

This kit models the AI's configuration as two layers:

**Identity layer (`templates/IDENTITY.md`)** — WHO the AI is
- Persona, name, operator brain (3Ms), voice
- Lives at the global level for pi (`APPEND_SYSTEM.md`)
- Merged into `CLAUDE.md` for Claude Code (no separate global layer)

**Operations layer (`templates/OPERATIONS.md`)** — HOW the AI behaves in this vault
- Skill list, edit policy, naming conventions, frontmatter rules
- Lives at vault root as `AGENTS.md` for pi
- Merged into `CLAUDE.md` for Claude Code

Each harness's install script handles the mapping. Pick your harness, run its install, the rest is automatic.

---

## Connecting your tools

This kit ships 9 connector scripts. None of them are auto-run — they're examples you can wire up as you need them. Start with:

| Tool | Script | Notes |
|---|---|---|
| Google Calendar | `scripts/google_calendar_api.py` | Read events, response status, free/busy |
| Gmail | `scripts/gmail_api.py` | List, search, mark read |
| Google Drive | `scripts/google_drive_api.py` | List, upload, share |
| ClickUp | `scripts/clickup_api.py` | Lists, tasks, comments |
| Fathom | `scripts/fathom-fetch.py` | Auto-fetch recordings to `inbox/` |
| Figma | `scripts/figma_api.py` | Read design files |
| Push to Drive | `scripts/push_to_drive.py` | MD → native Google Doc |
| Lint skills | `scripts/lint-skills.py` | Validates `SKILL.md` files |

Set API keys in `.env` (never commit). See `scripts/README.md` for per-script setup.

---

## Distribution roadmap

- **Now (v0.1.x)**: zip download. Re-download to update.
- **Next**: connector scripts distributed via git submodule. Pull updates without re-downloading the whole kit.
- **Later**: per-skill plug-in registry. Browse and install skills without touching the kit.

---

## License + attribution

MIT License. © 2026 Nate Herk (original AIS-OS). Skill additions, connector library, and demo project © 2026 Darryl Lim.

The Three Ms of AI™ and The Four Cs of an AIOS™ are trademarks of Nate Herk. Both frameworks ship in this kit via `references/3ms-framework.md` with full attribution intact. Use freely under MIT; don't repackage or rebrand as your own trademarks.

---

## Related docs

- `EXPANSIONS.md` — what to add as your AIOS grows
- `docs/SYNC.md` — cross-platform sync + migration (Windows ↔ Mac)
- `references/skill-frontmatter.md` — YAML standard for `SKILL.md` files
- `references/3ms-framework.md` — the operator brain