import json
import os

from support import CLICKUP_FILE, CLICKUP_KEY, FATHOM_FILE, FATHOM_KEY, VaultCase, meeting


class AdaptiveSetup(VaultCase):
    def test_existing_profile_only_missing_scope_and_append_only(self):
        profile = b"# Profile\r\n\r\n- **Role:** QA tester\r\n- team: Atlas\r\n- Project: Capsule\r\nPersonal rule: be precise.\r\n"
        profile_path = self.put("context/about-me.md", profile)
        old_scope = b"# Private scope\r\n\r\n- ClickUp scope: Atlas W7, Mobile S9, QA list 123\r\nChecked: read worked.\r\n"
        path = self.put("connections.md", old_scope)
        intake = self.put("aios-intake.md", b"Legacy intake: other project, no longer valid.\n")
        project = self.put("projects/capsule/README.md", b"Only current priority: verify expiry.\n")
        args = ("--task", "Draft acceptance cases", "--sources", "both")
        result = json.loads(self.ok("setup-kit.py", *args))
        self.assertEqual(result, {"missing": ["Fathom scope"], "live_sources_checked": []})
        print(f"Onboarding with existing profile and first task requested only {result['missing']}")
        self.assertEqual(profile_path.read_bytes(), profile)
        self.assertEqual(path.read_bytes(), old_scope)
        update = ("--role", "do not replay this", "--clickup-scope", "do not replace this",
                  "--fathom-scope", "Approved planning feed", "--meeting-destination", "projects/capsule/meetings", "--save")
        self.assertEqual(json.loads(self.ok("setup-kit.py", *args, *update))["missing"], [])
        snapshot = path.read_bytes()
        self.assertTrue(snapshot.startswith(old_scope))
        self.assertIn(b"Fathom scope: Approved planning feed", snapshot)
        self.assertIn(b"Meeting destination: projects/capsule/meetings", snapshot)
        self.ok("setup-kit.py", *args, *update)
        self.assertEqual(path.read_bytes(), snapshot)
        self.assertEqual(profile_path.read_bytes(), profile)
        self.assertEqual(intake.read_bytes(), b"Legacy intake: other project, no longer valid.\n")
        self.assertEqual(project.read_bytes(), b"Only current priority: verify expiry.\n")
        self.assertFalse((self.vault / "MEMORY.md").exists())
        self.assertFalse((self.vault / ".env").exists())
        self.assertEqual(self.wire.ledger, [])

    def test_supplied_only_fathom_only_clickup_only(self):
        text = "Requirement: locked accounts cannot create an invite.\nNeed a coverage draft.\n"
        notes = self.put("scratch/supplied.md", text.encode())
        result = json.loads(self.ok("setup-kit.py", "--sources", "supplied", "--task", "Draft QA cases",
                                    "--material", str(notes)))
        self.assertNotIn("Fathom scope", result["missing"])
        self.assertNotIn("ClickUp scope", result["missing"])
        self.assertEqual(result["live_sources_checked"], [])
        self.assertIn("No live sources checked", result["brief"]["source_status"])
        self.assertEqual(result["brief"]["supplied_material"], text)
        self.assertEqual(self.wire.ledger, [])

        os.environ["FATHOM_API_KEY"] = FATHOM_KEY
        self.wire.replies = [(200, {"items": [meeting(7)]})]
        self.ok(FATHOM_FILE)
        captures = list((self.vault / "inbox").glob("*.md"))
        self.assertEqual(len(captures), 1)
        self.assertIn("Transcript fixture 7", captures[0].read_text())
        self.assertEqual([r.method for r in self.wire.ledger], ["GET"])

        self.wire.ledger.clear()
        del os.environ["FATHOM_API_KEY"]
        os.environ["CLICKUP_API_TOKEN"] = CLICKUP_KEY
        self.wire.replies = [(200, {"tasks": [{"id": "T7", "name": "Check invite rules"}]})]
        self.assertIn("Check invite rules", self.ok(CLICKUP_FILE, "tasks", "--list", "123"))
        self.assertEqual([r.path_url for r in self.wire.ledger],
                         ["/api/v2/list/123/task?page=0&archived=false&subtasks=true"])
