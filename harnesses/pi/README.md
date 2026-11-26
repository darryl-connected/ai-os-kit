# Pi adapter

From the extracted kit root, run `bash harnesses/pi/install.sh` on macOS/Linux or `powershell -File harnesses/pi/install.ps1` on Windows. The wrapper uses Python 3.11+ (`PYTHON` can point to another interpreter). No connector dependencies are needed for the adapter.

Start Pi in the vault root and grant project trust after reviewing the files if Pi asks. Pi discovers the two project skills in `.pi/skills/`. Use `/skill:onboard` and `/skill:meeting-intake`; `/reload` refreshes skills in an existing session. Pi loads `AGENTS.md` as vault instructions. Read relevant `context/about-me.md`, connection scope and project notes on demand. No global identity or Context7 change is required.

See [setup](../../README.md) and [safe migration](../../docs/SYNC.md) for existing vaults. Existing personal files and installed custom skills are left alone.
