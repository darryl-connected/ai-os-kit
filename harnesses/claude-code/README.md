# Claude Code adapter

Wires the AIS-OS Kit to **Claude Code**. Uses Claude Code's single-file config convention.

## Install

From the kit root (after unzipping):

**Mac / Linux / WSL / Git Bash:**
```bash
bash harnesses/claude-code/install.sh
```

**Windows PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File harnesses/claude-code/install.ps1
```

## What it does

1. **Copies `skills/*/` → `.claude/skills/*/`** at the vault root. Claude Code reads `SKILL.md` files from this directory at session start.
2. **Confirms `CLAUDE.md` is at the vault root** (already there from the kit). This is the merged identity + operations layer.
3. **Prints customization instructions.**

## What it does NOT do (manual steps)

- **Claude Code installation**: assumes you have Claude Code installed and authenticated. See https://docs.claude.com/claude-code for setup.
- **OAuth credentials**: the connector scripts need `.env` populated with API keys. See `scripts/README.md` and `.env.example`.

## Why a single file?

Claude Code uses one `CLAUDE.md` at the vault root. There's no separate global config file (unlike pi's `APPEND_SYSTEM.md`).

The kit ships the two-layer content (identity + operations) pre-merged into `CLAUDE.md`. If you prefer the split model that pi uses, you can edit the sections apart — but for Claude Code users, the single-file convention is the path of least resistance.

## Re-running the installer

The script is idempotent. Re-run after pulling kit updates:

```bash
bash harnesses/claude-code/install.sh
```

Existing skills are overwritten (you may have local edits — back up first if so). Existing `CLAUDE.md` is NOT overwritten.

## Cross-platform notes

- **Mac/Linux**: `install.sh` works as-is.
- **Windows native**: use `install.ps1` (PowerShell Core 7+ recommended).
- **WSL**: run `install.sh` from inside WSL. Vault path will be `/mnt/c/...` if vault lives on Windows filesystem.
- **Git Bash on Windows**: `install.sh` works via Git Bash.

## See also

- `CLAUDE.md` — the merged identity + operations template at vault root
- `templates/IDENTITY.md` and `templates/OPERATIONS.md` — the split-source versions (for reference; not used by Claude Code directly)
- `docs/SYNC.md` — syncing the vault across Windows + Mac