import hashlib
import json
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

from support import ROOT, child, isolated_env

# Independent distribution contract. Do not import the builder's allowlist here.
EXPECTED = set("""
.env.example .gitignore LICENSE README.md AGENTS.md EXPANSIONS.md aios-intake.md connections.md
requirements.txt archives/README.md context/README.md decisions/log.md docs/SYNC.md inbox/README.md
inbox/processed/README.md scripts/README.md references/clickup-api.md references/fathom-api.md
references/skill-frontmatter.md templates/IDENTITY.md templates/OPERATIONS.md projects/demo-app/README.md
projects/demo-app/topics/metrics.md projects/demo-app/topics/user-research.md
scripts/clickup_api.py scripts/fathom-fetch.py scripts/file-meeting.py scripts/install-kit.py scripts/kit_context.py
scripts/kit_files.py scripts/kit_http.py scripts/lint-skills.py scripts/setup-kit.py
skills/onboard/SKILL.md skills/meeting-intake/SKILL.md
harnesses/pi/README.md harnesses/pi/install.sh harnesses/pi/install.ps1
""".split()) | {
    "projects/demo-app/meetings/2026-06-15 - discovery-call.md",
    "projects/demo-app/meetings/2026-06-17 - planning-sync.md",
    "projects/demo-app/meetings/2026-06-18 - retro.md",
    "projects/demo-app/specs/2026-06-15 - feature-spec.md",
}
DEFAULT_SKILLS = {"onboard/SKILL.md", "meeting-intake/SKILL.md"}
# Match standalone slash tokens in prose, inline code and command examples, not segments of URLs/paths.
SLASH_COMMAND = re.compile(r"(?<![\w./>}-])/([a-z][\w-]*(?::[a-z][\w-]*)?)(?=$|[\s`'\".,;!?()[\]<>])", re.I)


def command_references(text: str):
    for number, line in enumerate(text.splitlines(), 1):
        for match in SLASH_COMMAND.finditer(line):
            yield number, match[1]


def files_below(path: Path) -> set[str]:
    return {file.relative_to(path).as_posix() for file in path.rglob("*") if file.is_file()}


def pi_distribution() -> Path:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        return runpy.run_path(str(ROOT / "scripts/lint-skills.py"))["pi_dist"]()
    finally:
        sys.path.pop(0)


class Distribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = Path(cls.enterClassContext(tempfile.TemporaryDirectory(prefix="kit-package-"))).resolve()
        cls.home = cls.base / "fixture home"
        cls.home.mkdir()
        cls.env = isolated_env(cls.home)
        cls.zip_path = cls.base / "lean-kit.zip"
        cls.extracted = cls.base / "extracted kit"
        child([sys.executable, "-S", "scripts/build-kit.py", "--output", str(cls.zip_path)], cwd=ROOT, env=cls.env)
        with ZipFile(cls.zip_path) as archive:
            names = archive.namelist()
            if set(names) != EXPECTED or len(names) != len(EXPECTED):
                raise AssertionError(f"Unexpected archive inventory: missing={EXPECTED - set(names)} extra={set(names) - EXPECTED}")
            if archive.testzip() is not None:
                raise AssertionError("ZIP has failed checksums")
            archive.extractall(cls.extracted)
        print(f"Archive inventory: {len(names)} classified files, sha256={hashlib.sha256(cls.zip_path.read_bytes()).hexdigest()}")

    def test_distribution_resources_and_literal_references(self):
        self.assertEqual(files_below(self.extracted), EXPECTED)
        checked_links = 0
        for relative in sorted(EXPECTED):
            with self.subTest(path=relative):
                path = self.extracted / relative
                self.assertEqual(path.read_bytes(), (ROOT / relative).read_bytes())
                if not relative.endswith(".md"):
                    continue
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"(?i)(--dry-run|day[- ](?:2|7|14)\b|claude[ ._-])")
                for link in re.findall(r"(?<!\!)\[[^\[\]\n]+\]\(([^)\n]+)\)", text):
                    uri = urlsplit(link)
                    if uri.scheme or not uri.path:
                        continue
                    linked = (path.parent / unquote(uri.path)).resolve()
                    self.assertTrue(linked.is_file(), f"{relative}: broken Markdown link {link}")
                    self.assertIn(linked.relative_to(self.extracted).as_posix(), EXPECTED)
                    if uri.fragment:
                        anchors = [re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-")
                                   for heading in re.findall(r"^#{1,6} (.+)$", linked.read_text(), re.M)]
                        self.assertIn(uri.fragment, anchors, (relative, link))
                    checked_links += 1
                for link in re.findall(r"\[\[([^\]|#]+)(?:[^\]]*)\]\]", text):
                    candidates = [name for name in EXPECTED if Path(name).stem == link]
                    self.assertEqual(len(candidates), 1, f"{relative}: unresolved or ambiguous wiki link {link}")
                    checked_links += 1
                for link in re.findall(r"`((?:scripts|references|templates|harnesses|docs)/[\w/.-]+\.(?:py|md|sh|ps1))\b", text):
                    self.assertTrue((self.extracted / link).is_file(), (relative, link))
                    checked_links += 1
        slots = [line for line in (self.extracted / ".env.example").read_text().splitlines() if line and not line.startswith("#")]
        self.assertEqual(slots, ["FATHOM_API_KEY=", "CLICKUP_API_TOKEN="])
        deps = (self.extracted / "requirements.txt").read_text().splitlines()
        self.assertTrue(all(re.fullmatch(r"[a-z0-9-]+==[0-9.]+", line) for line in deps))
        self.assertEqual({line.split("==")[0] for line in deps},
                         {"requests", "python-dotenv", "urllib3", "certifi", "idna", "charset-normalizer"})
        guide = (self.extracted / "EXPANSIONS.md").read_text()
        self.assertIn("works without Context7", guide)
        self.assertIn("Finding AWS documentation is not an account check", guide)
        print(f"Checked {checked_links} literal links and resource references in the archive")

    def adapter(self, target: Path, home: Path, *, windows: bool = False):
        env = isolated_env(home)
        path = "harnesses/pi/install"
        argv = ["powershell.exe", "-NoProfile", "-File", path + ".ps1"] if windows else ["bash", path + ".sh"]
        return child([*argv, "--vault", str(target)], cwd=self.extracted, env=env)

    def installer_fixtures(self, *, windows: bool = False):
        with tempfile.TemporaryDirectory(dir=self.base, prefix="adapter-") as temp:
            root = Path(temp)
            home, fresh, existing = (root / name for name in ("personal home", "fresh vault", "existing vault"))
            home.mkdir()
            globals_ = {
                ".pi/agent/APPEND_SYSTEM.md": b"Synthetic isolated personal instructions.\r\n",
                ".pi/agent/settings.json": b'{"defaultProjectTrust":"ask"}\n',
                ".claude/settings.json": b'{"fixture":true}\n',
                ".claude/CLAUDE.md": b"Inert personal home instructions.\r\n",
            }
            personal = {
                "AGENTS.md": b"Leave personal rules exactly as they are.\r\n",
                "context/about-me.md": b"- Role: QA\r\n- Team: Atlas\r\n- Project: Capsule\r\n",
                "connections.md": b"- ClickUp scope: QA list A1\r\nLast verified: locally.\r\n",
                "projects/demo-app/README.md": b"Existing project status should win.\r\n",
                "aios-intake.md": b"Do not replay these old answers.\r\n",
                ".env": b"# Personal fixture contents only.\r\n",
                ".pi/settings.json": b"{}\n",
                ".pi/skills/custom-flow/SKILL.md": b"---\nname: custom-flow\n"
                b"description: 'This is a personal fixture, not kit content.'\n---\n",
                ".pi/skills/onboard/SKILL.md": b"Custom version must not be overwritten.\n",
                ".pi/skills/audit/SKILL.md": b"Legacy skill must not be silently removed.\r\n",
                "CLAUDE.md": b"Inert existing project instructions.\r\n",
                ".claude/settings.local.json": b'{"personal":true}\r\n',
                ".claude/skills/onboard/SKILL.md": b"Inert existing personal skill.\r\n",
                "harnesses/claude-code/README.md": b"Personal notes about a former install.\r\n",
            }
            for destination, mapping in ((home, globals_), (existing, personal)):
                for relative, data in mapping.items():
                    file = destination / relative
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes(data)
            if not windows:
                external = home / "personal-skill"
                external.mkdir()
                (existing / ".pi/skills/meeting-intake").symlink_to(external, target_is_directory=True)
            for _ in range(2):
                self.adapter(fresh, home, windows=windows)
                migration = self.adapter(existing, home, windows=windows)
                self.assertIn("Legacy skill left in place", migration.stdout)
                self.assertIn(".pi/skills/onboard/SKILL.md", migration.stdout)
            self.assertEqual(files_below(fresh), EXPECTED | {f".pi/skills/{item}" for item in DEFAULT_SKILLS})
            self.assertEqual(files_below(fresh / ".pi/skills"), DEFAULT_SKILLS)
            for skill_file in DEFAULT_SKILLS:
                self.assertEqual((fresh / ".pi/skills" / skill_file).read_bytes(),
                                 (self.extracted / "skills" / skill_file).read_bytes())
            self.assertEqual((fresh / "AGENTS.md").read_bytes(), (self.extracted / "AGENTS.md").read_bytes())
            self.assertEqual(files_below(home), set(globals_))
            self.assertEqual(files_below(existing / ".claude"),
                             {name.removeprefix(".claude/") for name in personal if name.startswith(".claude/")})
            self.assertEqual(files_below(existing / "harnesses/claude-code"), {"README.md"})
            if not windows:
                self.assertTrue((existing / ".pi/skills/meeting-intake").is_symlink())
                self.assertFalse((home / "personal-skill/SKILL.md").exists())
            self.assertFalse((fresh / ".env").exists())
            self.assertFalse((existing / "MEMORY.md").exists())
            checks = child([sys.executable, "-S", "scripts/setup-kit.py", "--sources", "clickup", "--task",
                            "Check status", "--save"], cwd=existing, env=isolated_env(home))
            self.assertEqual(json.loads(checks.stdout), {"missing": [], "live_sources_checked": []})
            for destination, mapping in ((home, globals_), (existing, personal)):
                for relative, data in mapping.items():
                    self.assertEqual((destination / relative).read_bytes(), data, relative)
            print("Pi native installer: fresh inventory matched; two updates and setup preserved personal Pi and Claude bytes")

    @unittest.skipIf(sys.platform == "win32", "NOT VERIFIED: native macOS/Linux Bash is not available on Windows")
    def test_native_shell_adapters_fresh_and_update(self):
        self.installer_fixtures()

    @unittest.skipUnless(sys.platform == "win32" and shutil.which("powershell.exe"),
                         "NOT VERIFIED: native Windows PowerShell is unavailable")
    def test_native_windows_adapters_fresh_and_update(self):
        self.installer_fixtures(windows=True)

    def test_installer_rejects_unsupported_harness(self):
        target = self.base / "must-not-install"
        result = subprocess.run([sys.executable, "-S", "scripts/install-kit.py", "claude-code", "--vault", str(target)],
                                cwd=self.extracted, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("unrecognized arguments", result.stderr)
        self.assertFalse(target.exists())

    def test_runtime_resources_and_pi_loader_from_archive(self):
        with tempfile.TemporaryDirectory(dir=self.base, prefix="runtime-") as runtime:
            base = Path(runtime)
            vault, home = base / "vault", base / "home"
            agent_dir = home / ".pi/agent"
            agent_dir.mkdir(parents=True)
            (agent_dir / "APPEND_SYSTEM.md").write_text("Synthetic fixture append only.\n")
            (agent_dir / "AGENTS.md").write_text("Synthetic home instructions only.\n")
            installed = self.adapter(vault, home, windows=sys.platform == "win32")
            (vault / "context/about-me.md").write_text("Do not automatically load my profile.")
            observed = child(["node", str(ROOT / "tests/check-pi-resources.mjs"), str(pi_distribution()),
                              str(vault), str(agent_dir)], cwd=vault, env=isolated_env(home))
            resource = json.loads(observed.stdout)
            self.assertTrue(resource["trusted"])
            self.assertEqual(resource["diagnostics"], [])
            self.assertEqual({data["name"]: data["filePath"] for data in resource["skills"]},
                             {name: str(vault / f".pi/skills/{name}/SKILL.md") for name in ("onboard", "meeting-intake")})
            self.assertEqual({data["path"]: data["content"] for data in resource["instructions"]}, {
                str(agent_dir / "AGENTS.md"): "Synthetic home instructions only.\n",
                str(vault / "AGENTS.md"): (vault / "AGENTS.md").read_text(),
            })
            self.assertEqual(resource["append"], ["Synthetic fixture append only.\n"])
            print("Pi SDK loader observed: trusted fixture, two default skills, only fixture instructions and append prompt")

            commands = set(resource["commands"])
            self.assertEqual({name for name in commands if name.startswith("skill:")},
                             {"skill:onboard", "skill:meeting-intake"})
            references = set()
            count = 0
            for path in sorted(self.extracted.rglob("*.md")):
                relative = path.relative_to(self.extracted).as_posix()
                for line, name in command_references(path.read_text(encoding="utf-8")):
                    self.assertIn(name, commands, f"{relative}:{line}: unresolved Pi command /{name}")
                    references.add(name)
                    count += 1
            self.assertTrue({"skill:onboard", "skill:meeting-intake"} <= references)
            for _, name in command_references(installed.stdout):
                self.assertIn(name, commands, f"Pi installer printed an unresolved command /{name}")
            print(f"Resolved {count} shipped slash command references against isolated Pi: {', '.join(sorted(references))}")

            (vault / "scratch").mkdir()
            (vault / "scratch/supplied.md").write_text("Draft pipeline gates from this supplied requirement.\n")
            plan = child([sys.executable, "-S", "scripts/setup-kit.py", "--sources", "supplied", "--task",
                          "Plan pipeline gates", "--material", "scratch/supplied.md"], cwd=vault, env=isolated_env(home))
            self.assertIn("No live sources checked", json.loads(plan.stdout)["brief"]["source_status"])
            self.assertFalse((vault / ".pi/settings.json").exists())
            self.assertFalse((home / ".pi/agent/settings.json").exists())
            self.assertFalse((home / ".pi/agent/mcp.json").exists())
            self.assertFalse((home / ".aws").exists())
            for script in ("file-meeting.py", "install-kit.py", "setup-kit.py", "lint-skills.py"):
                child([sys.executable, "-S", f"scripts/{script}", "--help"], cwd=self.extracted, env=isolated_env(home))
            lint = child([sys.executable, "-S", "scripts/lint-skills.py", "--skills-dir", ".pi/skills", "--strict"],
                         cwd=vault, env=isolated_env(home))
            self.assertIn("Pi loaded: meeting-intake, onboard", lint.stdout)
            result = child([sys.executable, str(ROOT / "tests/extracted_probe.py"), str(self.extracted), str(vault)],
                           cwd=self.extracted, env=isolated_env(home))
            self.assertIn("saved recording fixture-15", result.stdout)
            print(result.stdout.rstrip())
