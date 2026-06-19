#!/usr/bin/env python3
"""
lint-skills.py — Validate every SKILL.md in the vault against pi's actual loader.

Catches:
- YAML parse errors in frontmatter (causes skill to silently not load)
- Missing or empty description (skill won't load)
- Missing or invalid name (warnings, but flag them)
- Description > 1024 chars (spec violation)

Exits 0 if all skills pass, 1 otherwise.

Usage:
    python scripts/lint-skills.py                # lint all vault skills
    python scripts/lint-skills.py --skill NAME   # lint one skill
    python scripts/lint-skills.py --json         # machine-readable output
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows (cp1252 can't encode ✓ ✗ ⚠ etc.).
# Use reconfigure() — the io.TextIOWrapper rewrap approach closes the underlying
# buffer when the new wrapper is GC'd and breaks all subsequent prints with
# "I/O operation on closed file". See google_calendar_api.py for the same
# pitfall documented.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VAULT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = VAULT_ROOT / (
    os.getenv("LINT_SKILLS_DIR")
    or ".pi/skills"   # post-install default for pi users
)

# Pi's actual limits from dist/core/skills.js
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")


def run_pi_loader(skill_paths=None):
    """Run pi's loadSkills() in a Node subprocess and return the JSON output.

    Falls back to a pure-Python YAML check if Node/pi isn't reachable,
    so the linter works in CI without the full pi install.
    """
    # Pass data via stdin to dodge Windows shell-escaping issues with backslashes.
    loader_script = r"""
import fs from 'fs';
async function main() {
  // Locate pi's dist directory. Override via PI_DIST env var if auto-detect fails.
  // Tries: env var, then common nvm paths, then home-relative nvm paths.
  const home = process.env.HOME || process.env.USERPROFILE || '';
  const candidates = [
    process.env.PI_DIST,
    `${home}/AppData/Local/nvm/v24.16.0/node_modules/@earendil-works/pi-coding-agent/dist`,
    `${home}/.nvm/versions/node/*/lib/node_modules/@earendil-works/pi-coding-agent/dist`,
    '/usr/local/lib/node_modules/@earendil-works/pi-coding-agent/dist',
  ].filter(Boolean);
  let piDist = null;
  for (const c of candidates) {
    if (c.includes('*')) continue; // glob not expanded here; handled by user override
    try { if (fs.existsSync(`${c}/core/skills.js`)) { piDist = c; break; } } catch (_) {}
  }
  if (!piDist) {
    process.stdout.write(JSON.stringify({ error: 'pi dist not found. Set PI_DIST env var to the @earendil-works/pi-coding-agent/dist directory.' }));
    return;
  }
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  let parsed;
  try { parsed = JSON.parse(input); } catch (e) { process.stdout.write(JSON.stringify({ error: 'bad stdin: ' + e.message })); return; }
  const { skillPaths, cwd } = parsed;
  try {
    const mod = await import(`file:///${piDist}/core/skills.js`);
    const result = mod.loadSkills({
      cwd,
      includeDefaults: true,
      skillPaths,
    });
    process.stdout.write(JSON.stringify({
      skills: result.skills.map(s => ({
        name: s.name,
        description: s.description,
        filePath: s.filePath,
      })),
      diagnostics: result.diagnostics,
    }));
  } catch (e) {
    process.stdout.write(JSON.stringify({ error: e.message }));
  }
}
main();
"""
    payload = json.dumps({
        "skillPaths": skill_paths or [],
        "cwd": str(VAULT_ROOT),
    })
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", loader_script],
            input=payload,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return {"error": f"node exited {result.returncode}: {result.stderr.strip()}"}
        return json.loads(result.stdout)
    except FileNotFoundError:
        return {"error": "node not found in PATH"}
    except subprocess.TimeoutExpired:
        return {"error": "node timed out"}
    except json.JSONDecodeError as e:
        return {"error": f"failed to parse node output: {e}; raw={result.stdout[:200]!r}"}


def parse_frontmatter(content: str):
    """Lightweight YAML frontmatter parser for the fallback path."""
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return None, "no frontmatter delimiters found"
    block = m.group(1)
    fields = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fm = re.match(r"^([\w-]+):\s*(.*)$", line)
        if not fm:
            return None, f"malformed frontmatter line: {line!r}"
        key, value = fm.group(1), fm.group(2).strip()
        # strip surrounding quotes if present
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            value = value[1:-1]
        fields[key] = value
    return fields, None


def lint_skill_file(skill_dir: Path):
    """Lint a single skill directory. Returns list of issues."""
    issues = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [("error", "SKILL.md missing")]

    content = skill_md.read_text(encoding="utf-8")

    # --- Parse frontmatter (lightweight first, then defer to pi's loader) ---
    fields, err = parse_frontmatter(content)
    if err:
        issues.append(("error", f"frontmatter parse failed: {err}"))
        # Can't continue without parsed fields
        return issues

    name = fields.get("name") or skill_dir.name
    description = fields.get("description", "").strip()

    # --- Name checks ---
    if not fields.get("name"):
        issues.append(("warning", "name missing from frontmatter; falling back to directory name"))
    if len(name) > MAX_NAME_LENGTH:
        issues.append(("error", f"name exceeds {MAX_NAME_LENGTH} chars ({len(name)})"))
    if not NAME_PATTERN.match(name):
        issues.append(("error", f"name contains invalid chars (must be lowercase a-z, 0-9, hyphens): {name!r}"))
    if name.startswith("-") or name.endswith("-"):
        issues.append(("error", "name must not start or end with hyphen"))
    if "--" in name:
        issues.append(("error", "name must not contain consecutive hyphens"))

    # --- Description checks ---
    if not description:
        issues.append(("error", "description is empty or missing — skill will NOT load"))
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        issues.append(("error", f"description exceeds {MAX_DESCRIPTION_LENGTH} chars ({len(description)})"))
    else:
        # Style: warn if unquoted and contains YAML gotchas
        # Find the raw line to check if it was actually quoted
        m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        raw_desc_line = next(
            (l for l in m.group(1).splitlines() if l.startswith("description:")), ""
        )
        raw_value = raw_desc_line.split(":", 1)[1].strip()
        is_quoted = (raw_value.startswith("'") and raw_value.endswith("'")) or (
            raw_value.startswith('"') and raw_value.endswith('"')
        )
        if not is_quoted:
            gotchas = []
            if re.search(r":\s", raw_value):
                gotchas.append("colon+space")
            if raw_value.lstrip().startswith("#"):
                gotchas.append("leading hash")
            if raw_value.lstrip().startswith(("-", "?")):
                gotchas.append("leading dash/question")
            if raw_value.startswith(("[", "{")):
                gotchas.append("leading bracket")
            if gotchas:
                issues.append((
                    "warning",
                    f"description unquoted with risky chars ({', '.join(gotchas)}); "
                    f"wrap in single quotes to be safe",
                ))

    return issues


def main():
    ap = argparse.ArgumentParser(description="Lint vault skills against pi's loader.")
    ap.add_argument("--skill", help="lint only this skill (by directory name)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--skills-dir", help="override skills directory (e.g. 'skills' for kit source, '.claude/skills' for Claude Code)")
    args = ap.parse_args()
    if args.skills_dir:
        SKILLS_DIR = VAULT_ROOT / args.skills_dir

    if not SKILLS_DIR.exists():
        print(f"SKILLS_DIR not found: {SKILLS_DIR}", file=sys.stderr)
        return 2

    # Discover skills
    if args.skill:
        skill_dirs = [SKILLS_DIR / args.skill]
        if not skill_dirs[0].exists():
            print(f"skill not found: {skill_dirs[0]}", file=sys.stderr)
            return 2
    else:
        skill_dirs = sorted(
            d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
        )

    if not skill_dirs:
        print("no skills found", file=sys.stderr)
        return 2

    # Run pi's loader as the source of truth
    # Pass each skill dir explicitly so pi's auto-discovery from cwd doesn't matter.
    loader_result = run_pi_loader(skill_paths=[str(d) for d in skill_dirs])
    loader_loaded_names = set()
    loader_diagnostics = []
    if "error" not in loader_result:
        loader_loaded_names = {s["name"] for s in loader_result.get("skills", [])}
        loader_diagnostics = loader_result.get("diagnostics", [])
    else:
        print(f"warning: pi loader unavailable ({loader_result['error']}); using Python-only checks",
              file=sys.stderr)

    # Lint each skill
    results = []
    for skill_dir in skill_dirs:
        issues = lint_skill_file(skill_dir)
        # Cross-check: did pi's loader actually load this skill?
        if "error" not in loader_result:
            fm_match = re.match(r"^---\n.*?name:\s*(\S+)", skill_dir.joinpath("SKILL.md").read_text(encoding="utf-8"), re.DOTALL)
            declared_name = fm_match.group(1).strip() if fm_match else skill_dir.name
            if declared_name not in loader_loaded_names:
                issues.append(("error", f"pi's loader did NOT load this skill (missing from registered set)"))
        results.append({"skill": skill_dir.name, "issues": issues})

    # Surface loader diagnostics — merge into existing entries instead of duplicating
    for diag in loader_diagnostics:
        m = re.search(r"[\\/]skills[\\/]([^\\/]+)[\\/]SKILL\.md", diag.get("path", ""))
        skill_name = m.group(1) if m else "(unknown)"
        msg = f"[pi loader] {diag.get('message', '').splitlines()[0]}"  # first line only
        # Find the matching entry in results, append to its issues
        target = next((r for r in results if r["skill"] == skill_name), None)
        if target:
            target["issues"].append((diag.get("type", "warning"), msg))
        else:
            results.append({
                "skill": skill_name,
                "issues": [(diag.get("type", "warning"), msg)],
            })

    # Compute aggregate state before emit (used for both modes)
    has_errors = any(lvl == "error" for r in results for lvl, _ in r["issues"])
    total = len(results)
    errors = sum(1 for r in results for lvl, _ in r["issues"] if lvl == "error")
    warnings = sum(1 for r in results for lvl, _ in r["issues"] if lvl == "warning")

    # Emit
    if args.json:
        print(json.dumps({
            "total": total,
            "errors": errors,
            "warnings": warnings,
            "results": results,
        }, indent=2))
    else:
        for r in results:
            print(f"\n{r['skill']}/SKILL.md")
            if not r["issues"]:
                print("  ok")
                continue
            for level, msg in r["issues"]:
                marker = "✗" if level == "error" else "⚠"
                print(f"  {marker} [{level}] {msg}")

        print(f"\n{'='*40}")
        print(f"{total} skills, {errors} errors, {warnings} warnings")

    if has_errors or (args.strict and any(r["issues"] for r in results)):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())