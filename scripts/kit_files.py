"""Explicit distribution allowlist. Never copy a vault or connector directory wholesale."""

SKILLS = ("onboard", "meeting-intake")
RUNTIME = (
    "clickup_api.py", "fathom-fetch.py", "file-meeting.py", "install-kit.py", "kit_context.py",
    "kit_files.py", "kit_http.py", "lint-skills.py", "setup-kit.py",
)
DISTRIBUTION = (
    ".env.example", ".gitignore", "LICENSE", "README.md", "AGENTS.md", "EXPANSIONS.md", "aios-intake.md", "connections.md",
    "requirements.txt", "archives/README.md", "context/README.md", "decisions/log.md", "docs/SYNC.md",
    "inbox/README.md", "inbox/processed/README.md", "scripts/README.md",
    "references/clickup-api.md", "references/fathom-api.md", "references/skill-frontmatter.md",
    "templates/IDENTITY.md", "templates/OPERATIONS.md",
    "projects/demo-app/README.md",
    "projects/demo-app/meetings/2026-06-15 - discovery-call.md",
    "projects/demo-app/meetings/2026-06-17 - planning-sync.md",
    "projects/demo-app/meetings/2026-06-18 - retro.md",
    "projects/demo-app/specs/2026-06-15 - feature-spec.md",
    "projects/demo-app/topics/metrics.md", "projects/demo-app/topics/user-research.md",
) + tuple(f"scripts/{name}" for name in RUNTIME) + tuple(f"skills/{name}/SKILL.md" for name in SKILLS) + tuple(
    f"harnesses/pi/{name}" for name in ("README.md", "install.sh", "install.ps1")
)
