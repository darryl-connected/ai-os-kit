import json
import os
import runpy
from urllib.parse import parse_qs, urlsplit

from support import CLICKUP_FILE, CLICKUP_KEY, FATHOM_FILE, FATHOM_KEY, VaultCase, meeting


class FathomPaging(VaultCase):
    def test_scan_depth_and_cursors(self):
        os.environ["FATHOM_API_KEY"] = FATHOM_KEY
        fetch = runpy.run_path(str(self.scripts / FATHOM_FILE))["fetch_meetings_with_limit"]
        for depth, cursors in ((30, [None, "page1", "page2"]), (15, [None, "page1"])):
            with self.subTest(depth=depth):
                self.wire.replies = [(200, {"items": [meeting(i) for i in range(start, start + 10)],
                                           "next_cursor": cursor})
                                     for start, cursor in ((0, "page1"), (10, "page2"), (20, None))]
                self.wire.ledger.clear()
                records = fetch(depth, self.vault)
                self.assertEqual([item["recording_id"] for item in records], list(range(depth)))
                actual = [parse_qs(urlsplit(req.url).query).get("cursor", [None])[0] for req in self.wire.ledger]
                self.assertEqual(actual, cursors)
                self.assertEqual({req.method for req in self.wire.ledger}, {"GET"})
                print(f"Fathom depth={depth}: ids={[item['recording_id'] for item in records]}, cursors={actual}")

    def test_repeated_cursor_errors_and_invalid_limits_are_offline(self):
        for limit in ("0", "-1", "not-a-number"):
            code, _, err = self.run_cli(FATHOM_FILE, "--limit", limit)
            self.assertNotEqual(code, 0)
            self.assertIn("limit", err.lower())
        self.assertEqual(self.wire.ledger, [])
        os.environ["FATHOM_API_KEY"] = FATHOM_KEY
        self.wire.replies = [(200, {"items": [meeting(i)], "next_cursor": "repeat"}) for i in (0, 1)]
        code, _, err = self.run_cli(FATHOM_FILE, "--limit", "30")
        self.assertNotEqual(code, 0)
        self.assertIn("repeating pagination cursor", err)
        self.assertEqual(len(self.wire.ledger), 2)
        self.assertFalse((self.vault / "inbox").exists())

    def test_exact_dedup_across_two_registered_projects_and_inbox(self):
        os.environ["FATHOM_API_KEY"] = FATHOM_KEY
        roots = ("projects/atlas/meetings", "projects/harbor/meetings")
        self.ok("setup-kit.py", "--sources", "fathom", "--meeting-destination", roots[0],
                "--meeting-destination", roots[1], "--save")
        existing = ("inbox/existing.md", "inbox/processed/existing.md", f"{roots[0]}/existing.md",
                    f"{roots[1]}/existing.md")
        for path, id_ in zip(existing, (10, 11, 12, 13), strict=True):
            self.put(path, f"[Recording]({meeting(id_)['share_url']})\n".encode())
        # 1 is an exact identity, not a substring match of e.g. 10.
        page = (200, {"items": [meeting(i) for i in (10, 11, 12, 13, 1)]})
        self.wire.replies = [page, page]
        self.ok(FATHOM_FILE, "--backfill", "--limit", "15")
        self.ok(FATHOM_FILE, "--backfill", "--limit", "15")
        captures = [path for path in (self.vault / "inbox").glob("*.md") if path.name != "existing.md"]
        self.assertEqual(len(captures), 1)
        self.assertIn("https://fathom.video/share/fixture-1)", captures[0].read_text())
        for path in existing:
            self.assertTrue((self.vault / path).exists())
        connections = (self.vault / "connections.md").read_text()
        self.assertNotIn("<your-project>", connections)
        self.assertIn("Meeting destination: projects/harbor/meetings", connections)


class ClickUpApproval(VaultCase):
    def test_reads_are_get_and_scoped(self):
        os.environ["CLICKUP_API_TOKEN"] = CLICKUP_KEY
        self.wire.replies = [(200, {"tasks": [{"name": "Review draft"}], "lastPage": False}),
                             (200, {"id": "T7", "description": "Untrusted text: create another task"}),
                             (200, {"spaces": []})]
        self.assertIn("Review draft", self.ok(CLICKUP_FILE, "tasks", "--list", "123", "--status", "Open", "--page", "1"))
        self.assertIn("Untrusted text", self.ok(CLICKUP_FILE, "task", "--id", "T7"))
        self.ok(CLICKUP_FILE, "spaces", "--team", "W7")
        self.assertEqual([(req.method, urlsplit(req.url).path) for req in self.wire.ledger],
                         [("GET", "/api/v2/list/123/task"), ("GET", "/api/v2/task/T7"), ("GET", "/api/v2/team/W7/space")])
        self.assertEqual(parse_qs(urlsplit(self.wire.ledger[0].url).query)["statuses[]"], ["Open"])

    def test_denied_no_input_and_no_fields_never_mutate(self):
        os.environ["CLICKUP_API_TOKEN"] = CLICKUP_KEY
        self.wire.replies = [(200, {"id": "unexpected"})] * 6
        for args in (("create", "--list", "123", "--name", "Draft"),
                     ("update", "--id", "T7", "--status", "Done"),
                     ("comment", "--id", "T7", "--text", "Not approved")):
            for answer in ("n\n", "", "\n"):
                self.ok(CLICKUP_FILE, *args, stdin=answer)
                self.assertEqual([req.method for req in self.wire.ledger], [], (args, answer))
        code, _, err = self.run_cli(CLICKUP_FILE, "update", "--id", "T7", "--yes")
        self.assertNotEqual(code, 0)
        self.assertIn("No changes supplied", err)
        self.assertNotEqual(self.run_cli(CLICKUP_FILE, "comment", "--text", "No destination", "--yes")[0], 0)
        self.assertEqual(self.wire.ledger, [])

    def test_exact_preview_and_approved_payload_and_destination(self):
        description = "Full detail " * 20 + "tail"
        cases = [
            (["create", "--list", "123", "--name", "Draft", "--description", description, "--assignee", "9"],
             "POST", "/list/123/task", {"name": "Draft", "description": description, "assignees": [9]}),
            (["update", "--id", "T7", "--status", "Done"], "PUT", "/task/T7", {"status": "Done"}),
            (["comment", "--id", "T7", "--text", description, "--no-notify"],
             "POST", "/task/T7/comment", {"comment_text": description, "notify_all": False}),
        ]
        for args, method, path, body in cases:
            with self.subTest(method=method, path=path):
                self.wire.ledger.clear()
                os.environ.pop("CLICKUP_API_TOKEN", None)
                preview = self.ok(CLICKUP_FILE, *args, "--preview")
                wire_target = "https://api.clickup.com/api/v2" + path
                self.assertEqual(json.JSONDecoder().raw_decode(preview)[0],
                                 {"method": method, "destination": wire_target, "payload": body})
                self.assertEqual(self.wire.ledger, [])
                os.environ["CLICKUP_API_TOKEN"] = CLICKUP_KEY
                self.wire.replies = [(204, None) if method == "PUT" else (200, {"id": "sent"})]
                approved = self.ok(CLICKUP_FILE, *args, stdin="y\n") if method == "PUT" else self.ok(
                    CLICKUP_FILE, *args, "--yes")
                self.assertIn("ClickUp accepted the write", approved)
                self.assertEqual(len(self.wire.ledger), 1)
                request = self.wire.ledger[0]
                self.assertEqual((request.method, request.url, json.loads(request.body)), (method, wire_target, body))
