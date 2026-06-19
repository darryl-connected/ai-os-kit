# SYNC — cross-platform vault sync + migration guide

Platform-agnostic. Works whether you run the kit on Windows, Mac, both, or switch between them.

---

## TL;DR

1. Pick a **cloud storage layer** (OneDrive / iCloud / Dropbox).
2. Point it at your vault folder.
3. Recreate `.env` on each machine (never sync it).
4. Run the harness install script on each machine.
5. Open the vault in your harness and you're done.

---

## Sync layer options

| Provider | Windows | Mac | Notes |
|---|---|---|---|
| **OneDrive** | native | native (Mac app) | Best cross-platform option. Free 5GB, paid 1TB+. |
| **iCloud Drive** | via Windows client | native | Mac-first, Windows client works but slower. Free 5GB. |
| **Dropbox** | native | native | Mature cross-platform. Free 2GB. |
| **Git** (advanced) | any | any | Manual. Use if you want version control over your vault. |

**Recommendation:** OneDrive for most users. It's already installed on Windows by default and has a clean Mac client. The kit's files are all UTF-8 plain text or small Python — OneDrive handles this without issues.

**Pitfall:** Cloud sync can race on rapid edits. If two machines are open in the harness at once and editing the same file, last-write-wins. For most AIOS use (one primary device), this isn't a problem.

---

## `.env` is per-machine

`.env` lives at the vault root and contains API keys. **Never sync it.** The kit's `.gitignore` already excludes it.

When you set up a new machine:
1. Copy `.env.example` to `.env`
2. Fill in your API keys (different keys per machine if you want, or share if the keys support it)
3. Verify OAuth: run any Google script and re-consent if needed (Google OAuth tokens are per-machine anyway)

Some keys (ClickUp, Fathom, Figma) are account-scoped, so the same key works on multiple machines. Just regenerate the OAuth token for Google on each machine.

---

## Harness installation per platform

### Windows

**Pi:**
```powershell
powershell -ExecutionPolicy Bypass -File harnesses/pi/install.ps1
```

**Claude Code:**
```powershell
powershell -ExecutionPolicy Bypass -File harnesses/claude-code/install.ps1
```

### Mac / Linux

**Pi:**
```bash
bash harnesses/pi/install.sh
```

**Claude Code:**
```bash
bash harnesses/claude-code/install.sh
```

### WSL (Windows Subsystem for Linux)

If your vault lives on the Windows filesystem, run the install scripts from inside WSL. Vault paths will be `/mnt/c/Users/.../vault`. Cloud sync handles file movement; you only need the install once per machine.

---

## Python setup per platform

### Windows

1. Install Python 3.11+ from python.org (or via Microsoft Store).
2. Open PowerShell, navigate to vault root.
3. `pip install requests python-dotenv google-api-python-client google-auth-httplib2 google-auth-oauthlib markdown`

### Mac

1. Install Homebrew if you don't have it: https://brew.sh
2. `brew install python@3.11`
3. `pip3 install requests python-dotenv google-api-python-client google-auth-httplib2 google-auth-oauthlib markdown`

### Linux

1. `sudo apt install python3.11 python3-pip` (or your distro's equivalent)
2. `pip3 install requests python-dotenv google-api-python-client google-auth-httplib2 google-auth-oauthlib markdown`

### Cross-platform gotchas

- **UTF-8 stdout on Windows:** Python's default `cp1252` stdout crashes with "I/O operation on closed file" when printing emoji (`✓`, `❌`). All connector scripts handle this via `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`. If you fork a script, replicate the reconfigure at the top.
- **Line endings:** Scripts are LF. Python handles both LF and CRLF on read; don't manually concatenate strings with `\r\n`.
- **Path separators:** Use `pathlib.Path` throughout. Never hardcode `\` or `/`.
- **Home directory:** Scripts use `Path.home()` and `os.environ.get("HOME")` / `os.environ.get("USERPROFILE")` to find the user's home directory. Both Windows and Mac work without changes.

---

## Migration scenarios

### Windows → Mac

1. Sync your vault via OneDrive / iCloud / Dropbox.
2. On Mac: install Python via Homebrew.
3. `pip3 install` the dependencies (see above).
4. Run the harness install script (Mac variant).
5. Copy `.env.example` to `.env`, fill in keys.
6. Verify: open the vault in your harness, run `/audit`. If everything scores well, you're done.

### Mac → Windows

1. Sync your vault via OneDrive / iCloud / Dropbox.
2. On Windows: install Python from python.org.
3. `pip install` the dependencies.
4. Run the harness install script (PowerShell variant).
5. Copy `.env.example` to `.env`, fill in keys.
6. Verify: `/audit` should match your last Mac score.

### First-time setup (no existing vault)

1. Unzip the kit to your preferred location (e.g. `~/vault/` or `C:\Users\you\vault\`).
2. Pick a sync layer (OneDrive / iCloud / Dropbox). Move the vault folder into the sync root.
3. Install Python + dependencies per platform above.
4. Run the harness install script.
5. Copy `.env.example` to `.env`, fill in keys.
6. Run `/onboard` in your harness.

### Multi-device sync (Windows + Mac, primary is Windows)

1. Vault lives in OneDrive on Windows.
2. Mac: install OneDrive, point at the same vault folder.
3. Mac: install Python via Homebrew.
4. Mac: `pip3 install` the dependencies.
5. Mac: run the harness install script.
6. Mac: copy `.env.example` to `.env`, fill in keys (can be the same as Windows for account-scoped services).
7. Verify: open the vault on Mac, run `/audit`. Score should match.

**Anti-pattern:** Don't try to share the same `.env` file across machines. Even if keys are the same, OAuth tokens are per-machine and `.env` should be local to each.

---

## Sync conflicts

If two machines edit the same file before sync:
- Cloud sync (OneDrive / iCloud / Dropbox) typically picks one version and saves the other as a conflict copy (`.<filename>.conflict`).
- Git shows conflicts via markers (`<<<<<<<`, `=======`, `>>>>>>>`).
- For most AIOS use, the AI is editing the vault — only one machine is in active use at a time. Conflicts are rare.

If you do hit a conflict, **don't try to auto-merge**. Read both versions, pick the right one, and discard the other. AIOS files are usually small and structured.

---

## Backup

The kit does NOT auto-backup. Your cloud sync layer is your backup. For additional safety:

- **OneDrive / iCloud / Dropbox:** automatic version history (30 days free, more on paid tiers).
- **Git:** every commit is a backup. Push to a private GitHub repo for off-machine storage.
- **Manual:** quarterly `cp -r vault/ vault-backup-{date}/` to an external drive.

Don't over-engineer this. The cloud sync is enough for most users.

---

## When NOT to sync

- **Harness state files.** Some harnesses store session state in the vault (e.g. `.claude/projects/`). These are per-machine — exclude from sync.
- **OAuth tokens** (`token.pickle`, `token.json`). Per-machine by design.
- **`.env`.** Already gitignored. If you're using a cloud sync that respects `.gitignore` patterns (most don't), manually exclude.

---

## See also

- `docs/SYNC.md` — this file
- `.gitignore` — what's excluded from version control
- `scripts/README.md` — per-script setup, including cross-platform Python notes