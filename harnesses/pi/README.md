# pi adapter

Wires the AIS-OS Kit to the **pi** coding agent. Uses pi's two-layer config convention.

## Install

From the kit root (after unzipping):

**Mac / Linux / WSL / Git Bash:**
```bash
bash harnesses/pi/install.sh
```

**Windows PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File harnesses/pi/install.ps1
```

## What it does

1. **Copies `skills/*/` → `.pi/skills/*/`** at the vault root. pi reads `SKILL.md` files from this directory at session start.
2. **Copies `templates/OPERATIONS.md` → `AGENTS.md`** at the vault root (only if `AGENTS.md` doesn't already exist). This is the vault-operations layer.
3. **Prints manual instructions** for installing the global identity layer (`APPEND_SYSTEM.md`).

## What it does NOT do (manual steps)

- **Identity layer (`APPEND_SYSTEM.md`)**: pi loads a system-wide `APPEND_SYSTEM.md` from a global location (typically `~/.pi/agent/APPEND_SYSTEM.md`). This is NOT a vault file — it's per-machine. The install script doesn't touch your global pi config. You copy `templates/IDENTITY.md` content into that file by hand.

- **OAuth credentials**: the connector scripts need `.env` populated with API keys. See `scripts/README.md` and `.env.example`.

## Why two layers?

Pi splits AI config into two files:

| Layer | File | Scope | Controls |
|---|---|---|---|
| Identity | `APPEND_SYSTEM.md` (global) | System-wide | Persona, voice, operator brain, connections summary |
| Operations | `AGENTS.md` (vault) | Per-vault | Skills, edit policy, naming, frontmatter rules |

Pi reads both at session start. The kit ships them as separate templates so you can version-control the vault operations file (in git) without exposing your identity layer (in your global pi config).

## Re-running the installer

The script is idempotent. Re-run after pulling kit updates:

```bash
bash harnesses/pi/install.sh
```

Existing skills are overwritten (you may have local edits — back up first if so). Existing `AGENTS.md` is NOT overwritten — back it up manually and re-copy from `templates/OPERATIONS.md` if you want a fresh start.

## Cross-platform notes

- **Mac/Linux**: `install.sh` works as-is.
- **Windows native**: use `install.ps1` (PowerShell Core 7+ recommended).
- **WSL**: run `install.sh` from inside WSL. Vault path will be `/mnt/c/...` if vault lives on Windows filesystem.
- **Git Bash on Windows**: `install.sh` works via Git Bash.

## See also

- `templates/IDENTITY.md` — the global-layer template
- `templates/OPERATIONS.md` — the vault-layer template
- `docs/SYNC.md` — syncing the vault across Windows + Mac