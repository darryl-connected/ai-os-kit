import hashlib
import os
from urllib.parse import unquote

from support import FATHOM_FILE, FATHOM_KEY, VaultCase, meeting


class FathomIntake(VaultCase):
    def test_safe_collision_paths_and_newest_unfiled_default(self):
        os.environ["FATHOM_API_KEY"] = FATHOM_KEY
        # Place the older pending meeting first on the wire. Both use unsafe title characters.
        title = "../Planning: Q4 / Release?"
        older = meeting(1, start="2026-11-20T08:15:00Z", title=title)
        newest = meeting(2, start="2026-11-20T09:15:00Z", title=title)
        already_saved = meeting(3, start="2026-11-20T10:15:00Z", title=title)
        self.put("inbox/processed/existing.md", f"recording: {already_saved['share_url']}\n".encode())
        payload = (200, {"items": [older, already_saved, newest]})
        self.wire.replies = [payload, payload, payload]
        out = self.ok(FATHOM_FILE)
        self.assertIn("meeting-intake", out)
        folder = self.vault / "inbox"
        captures = list(folder.glob("*.md"))
        self.assertEqual(len(captures), 1)
        self.assertIn("Transcript fixture 2", captures[0].read_text())
        first_bytes = captures[0].read_bytes()
        self.ok(FATHOM_FILE, "--backfill", "--limit", "15")
        self.ok(FATHOM_FILE, "--backfill", "--limit", "15")
        all_paths = sorted(folder.glob("*.md"))
        self.assertEqual(len(all_paths), 2)
        self.assertEqual(captures[0].read_bytes(), first_bytes)
        for recording in (older, newest):
            matching = [file for file in all_paths if f"]({recording['share_url']})" in file.read_text()]
            self.assertEqual(len(matching), 1)
            file = matching[0]
            self.assertRegex(file.name, r"^2026-11-20 - planning-q4-release - [a-z0-9]+\.md$")
            for key in ("Summary", "Action", "Transcript"):
                self.assertIn(f"{key} fixture {recording['recording_id']}", file.read_text())
        self.assertEqual(len(self.wire.ledger), 3)
        print(f"Fathom default selected fixture-2; distinct safe captures: {[path.name for path in all_paths]}")

    def test_help_and_exact_recording_selector(self):
        out = self.ok(FATHOM_FILE, "--help")
        for flag in ("--limit", "--backfill", "--vault", "--share-url", "--check"):
            self.assertIn(flag, out)
        self.assertNotIn("--dry-run", out)
        self.assertNotIn("process-inbox", out)
        self.assertEqual(self.wire.ledger, [])
        os.environ["FATHOM_API_KEY"] = FATHOM_KEY
        self.wire.replies = [(200, {"items": [meeting(1), meeting(2)]})]
        self.ok(FATHOM_FILE, "--limit", "2", "--share-url", meeting(2)["share_url"])
        capture, = (self.vault / "inbox").glob("*.md")
        self.assertIn("Transcript fixture 2", capture.read_text())
        self.wire.replies = [(200, {"items": [meeting(2)]})]
        self.assertIn("scoped read succeeded", self.ok(FATHOM_FILE, "--check", "--limit", "2", "--share-url",
                                                       meeting(2)["share_url"]))
        self.assertEqual(list((self.vault / "inbox").glob("*.md")), [capture])


class RetainFullCapture(VaultCase):
    def test_approved_original_survives_and_old_capture_not_swept(self):
        # Deliberate CRLF and trailing space make a text-normalising archive fail too.
        original = (
            b"---\r\nrecording: https://fathom.video/share/fixture-87\r\n---\r\n"
            b"# Planning capture\r\n\r\n## Meeting Purpose\r\nQA handoff.\r\n"
            b"## Fathom action items\r\nJenna to confirm.\r\n\r\n## Transcript\r\n"
            b"[@00:00:03] Someone: Jena will check it. We said 24 July.  \r\n"
            b"## Follow-up email capture\r\nNo launch date confirmed.\r\n"
        )
        historical = b"Previous full capture, assessed a long time ago.\n"
        original_path = self.put("inbox/2026-07-12 - planning.md", original)
        old_processed = self.put("inbox/processed/retained-old.md", historical)
        old_raw = self.put("inbox/old-pending.md", historical)
        for old in (old_processed, old_raw):
            os.utime(old, (1, 1))
        draft = self.put("scratch/summary.md", b"# QA handoff\n\n## Decisions\nNone confirmed.\n\n## Proposals\n"
                         b"Review the checklist.\n\n## Actions\nOwner and date pending.\n\n## Unresolved\n"
                         b"Jena or Jenna: confirm who owns the check. 24 July: milestone type unknown.\n")
        args = ("--capture", "inbox/2026-07-12 - planning.md", "--draft", "scratch/summary.md",
                "--destination", "projects/atlas/meetings", "--date", "2026-07-12")
        summary = self.vault / "projects/atlas/meetings" / original_path.name
        archived = old_processed.parent / original_path.name
        preview = self.ok("file-meeting.py", *args)
        self.assertIn("Preview only; no files changed", preview)
        self.assertIn("Jena or Jenna", preview)
        self.assertFalse(summary.exists())
        self.assertFalse(archived.exists())
        self.assertEqual(original_path.read_bytes(), original)

        self.ok("file-meeting.py", *args, "--apply")
        self.assertFalse(original_path.exists())
        self.assertEqual(archived.read_bytes(), original)
        self.assertTrue(old_processed.is_file(), "Old capture was removed despite O4 retention")
        self.assertEqual(old_processed.read_bytes(), historical)
        self.assertEqual(old_raw.read_bytes(), historical)
        self.assertEqual(old_processed.stat().st_mtime, 1)
        self.assertIn(draft.read_bytes(), summary.read_bytes())
        note = summary.read_text()
        self.assertNotIn("Transcript", note)
        self.assertNotIn("Fathom action items", note)
        self.assertIn('recording: "https://fathom.video/share/fixture-87"', note)
        link = unquote(note.split("[Full original capture](", 1)[1].split(")", 1)[0])
        self.assertEqual((summary.parent / link).resolve(), archived)
        self.assertEqual(self.wire.ledger, [])
        print(f"Retained original SHA256={hashlib.sha256(archived.read_bytes()).hexdigest()}, with old fixtures intact")

    def test_inline_transcript_and_different_existing_capture_refused(self):
        name = "same-name.md"
        capture = self.put(f"inbox/{name}", b"## Summary\nFull notes.\n")
        archived = self.put(f"inbox/processed/{name}", b"Older recording, different bytes.\n")
        draft = self.put("scratch/summary.md", b"## Transcript\nLong raw material.\n")
        args = ("--capture", f"inbox/{name}", "--draft", "scratch/summary.md", "--destination",
                "projects/atlas/meetings", "--date", "2026-07-12", "--apply")
        code, _, err = self.run_cli("file-meeting.py", *args)
        self.assertNotEqual(code, 0)
        self.assertIn("without an inline transcript", err)
        draft.write_bytes(b"A short separate summary.")
        code, _, err = self.run_cli("file-meeting.py", *args)
        self.assertNotEqual(code, 0)
        self.assertIn("different content", err)
        self.assertTrue(capture.exists())
        self.assertEqual(archived.read_bytes(), b"Older recording, different bytes.\n")
        self.assertFalse((self.vault / "projects").exists())
