# AI-OS Kit: meetings and tasks

Turn meetings and task context into reviewed notes, plans, test scenarios and follow-ups. Start from supplied material, or connect Fathom and/or ClickUp for the work you actually need. Coding is optional.

## Start here

1. Extract the lean ZIP into a new working folder. Use Python 3.11+ and your existing Pi installation. Install the [Pi adapter](harnesses/pi/README.md) from the kit root: `bash harnesses/pi/install.sh` on macOS/Linux or `powershell -File harnesses/pi/install.ps1` on Windows.
2. Open that folder in Pi and run `/skill:onboard`. Tell it one real task and the context needed to start. Skip connections you don't need. There is no separate global identity setup or required schedule.
3. To review and file a meeting, run `/skill:meeting-intake`. [Meeting intake](inbox/README.md) describes the preview and retention rules.

If you already have a vault, **do not extract over it**. Follow the [update and migration guide](docs/SYNC.md). The adapter does not replace your files or global settings. Only `onboard` and `meeting-intake` are installed by default.

## Optional connections

You can draft from supplied notes without installing connector dependencies or configuring any token. Say which sources were actually checked; a local draft with no live read should say **No live sources checked**.

For a connector, use an activated Python virtual environment and run `python -m pip install -r requirements.txt`. If `python` is named `python3` on your machine, use that instead. Record the relevant non-secret scope in [connections.md](connections.md). Then follow the [Fathom](references/fathom-api.md) or [ClickUp](references/clickup-api.md) instructions to check your chosen scope.

**Credentials are optional.** Set `FATHOM_API_KEY` or `CLICKUP_API_TOKEN` privately in the process environment, or copy [.env.example](.env.example) to `.env` and fill in only the key you use. Do not paste keys into chat, project notes, command arguments or tickets. `.env` is plaintext: accidental commits, backups, cloud sync, and sharing a whole vault can expose it. `.gitignore` is not encryption and does not protect against backups or sync. Keep `.env` local and restrict access. An explicitly defined process value wins, even if blank. Otherwise the connector reads the literal value from this vault's `.env`, with no variable expansion. It never copies an inherited token to disk.

## Where information lives

- [Profile](context/README.md): stable role, team, project context and optional preferences in `context/about-me.md` when needed.
- [Connection scope](connections.md): which sources to use, where to file meetings, and what access was actually checked. No keys.
- [Project example](projects/demo-app/README.md): project status and working notes live with each project. Ask the assistant to read relevant files; normal Markdown is not automatically loaded.
- [Decisions](decisions/log.md): record decisions and reasoning that affect future work. [Archives](archives/README.md) and [processed captures](inbox/processed/README.md) are separate from active project notes.

See [scripts and examples](scripts/README.md), [skill linting](references/skill-frontmatter.md), and [optional documentation lookup](EXPANSIONS.md).

## Licence and attribution

[MIT](LICENSE). The original AIS-OS is by Nate Herk (AI Automation Society); kit adaptations are by Darryl Lim. The Three Ms of AI™ and The Four Cs of an AIOS™ are Nate Herk's trademarks. The preserved licence mentions the previous distribution; those framework and scoring materials are not part of this lean ZIP.
