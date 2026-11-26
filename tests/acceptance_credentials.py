import os

from support import CLICKUP_FILE, CLICKUP_KEY, FATHOM_FILE, FATHOM_KEY, VaultCase


class CredentialDiagnostics(VaultCase):
    def test_precedence_missing_rejected_success_without_disclosure_or_persistence(self):
        configurations = (
            ("FATHOM_API_KEY", FATHOM_KEY, FATHOM_FILE, ("--check",), "X-Api-Key", {"items": []}, "Fathom"),
            ("CLICKUP_API_TOKEN", CLICKUP_KEY, CLICKUP_FILE, ("check", "--list", "812"), "Authorization",
             {"tasks": []}, "ClickUp"),
        )
        for env_key, inherited, script, args, header, scoped_result, service in configurations:
            with self.subTest(service=service):
                dot_path = self.vault / ".env"
                self.wire.ledger.clear()
                code, out, err = self.run_cli(script, *args)
                self.assertNotEqual(code, 0)
                self.assertIn(f"Missing configuration: set {env_key}", err)
                self.assertNotIn("succeeded", out + err)
                self.assertEqual(self.wire.ledger, [])
                self.assertFalse(dot_path.exists())

                os.environ[env_key] = inherited
                self.wire.replies = [(200, scoped_result)]
                self.assertIn("scoped read succeeded", self.ok(script, *args))
                self.assertFalse(dot_path.exists(), "inherited token must not be saved")
                self.assertEqual(self.wire.ledger[-1].headers[header], inherited)

                dot = "dummy-local-conflicting-token-${OTHER}"
                contents = f"{env_key}='{dot}'\n".encode()
                self.put(".env", contents)
                os.environ["OTHER"] = "must-not-expand"
                self.wire.replies = [(401, {"echo": inherited + dot}), (403, {"echo": dot}), (200, scoped_result)]
                for status in (401, 403):
                    code, out, err = self.run_cli(script, *args)
                    self.assertNotEqual(code, 0)
                    self.assertNotIn(inherited, out + err)
                    self.assertNotIn(dot, out + err)
                    self.assertIn(f"{service} rejected authentication or access to this scope (HTTP {status})", err)
                    self.assertNotIn("succeeded", out + err)
                    self.assertEqual(self.wire.ledger[-1].headers[header], inherited)
                del os.environ[env_key]
                code, out, err = self.run_cli(script, *args)
                self.assertEqual(code, 0, err)
                self.assertIn(f"{service} scoped read succeeded", out)
                self.assertNotIn(inherited, out + err)
                self.assertNotIn(dot, out + err)
                self.assertEqual(self.wire.ledger[-1].headers[header], dot)
                self.assertEqual(dot_path.read_bytes(), contents)
                self.assertEqual({r.method for r in self.wire.ledger}, {"GET"})

                os.environ[env_key] = ""
                self.wire.ledger.clear()
                code, out, err = self.run_cli(script, *args)
                self.assertNotEqual(code, 0)
                self.assertIn("Missing configuration", err)
                self.assertEqual(self.wire.ledger, [])
                self.assertEqual(dot_path.read_bytes(), contents)
                dot_path.unlink()  # Independent connector fixture; no real credential files are used.
                del os.environ[env_key]
        self.assertFalse((self.vault / "inbox").exists())
