"""Real CLIs, isolated vault fixtures, and a no-network HTTP transport boundary."""

import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parent.parent
FATHOM_FILE = "fathom-fetch.py"
CLICKUP_FILE = "clickup_api.py"
FATHOM_KEY = "dummy-inherited-fathom-private-token"
CLICKUP_KEY = "dummy-inherited-clickup-private-token"


def isolated_env(home: Path) -> dict[str, str]:
    result = {"PATH": os.environ.get("PATH", os.defpath), "HOME": str(home), "USERPROFILE": str(home),
              "PI_CODING_AGENT_DIR": str(home / ".pi/agent"), "CLAUDE_CONFIG_DIR": str(home / ".claude"),
              "PYTHON": sys.executable, "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(home), "LANG": "en_US.UTF-8"}
    for key in ("SystemRoot", "PI_DIST"):
        if key in os.environ:
            result[key] = os.environ[key]
    return result


def child(argv: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise AssertionError(f"{argv} exited {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result


def cli(scripts: Path, name: str, args: list[str], stdin: str = "") -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with (patch.object(sys, "argv", [str(scripts / name), *args]), patch.object(sys, "stdin", io.StringIO(stdin)),
          contextlib.redirect_stdout(out), contextlib.redirect_stderr(err)):
        try:
            runpy.run_path(str(scripts / name), run_name="__main__")
        except SystemExit as exc:
            assert isinstance(exc.code, int)
            return exc.code, out.getvalue(), err.getvalue()
    raise AssertionError(f"{name} did not exit")


class Wire:
    """Fake HTTP only after requests prepared the real method, URL, headers and body."""

    def __init__(self) -> None:
        self.ledger: list[requests.PreparedRequest] = []
        self.replies: list[tuple[int, object]] = []

    def send(self, session, request: requests.PreparedRequest, **kwargs) -> requests.Response:
        self.ledger.append(request)
        if not self.replies:
            raise AssertionError(f"Unexpected HTTP operation: {request.method} {request.path_url}")
        status, data = self.replies.pop(0)
        response = requests.Response()
        response.status_code = status
        response._content = b"" if data is None else json.dumps(data).encode()
        response.headers["Content-Type"] = "application/json"
        response.url = request.url
        response.request = request
        return response

    def patch(self):
        return patch.object(requests.Session, "send", autospec=True, side_effect=self.send)


def meeting(number: int, *, start: str = "2026-11-20T08:30:00Z", title: str = "Quarterly Review") -> dict:
    return {
        "recording_id": number, "share_url": f"https://fathom.video/share/fixture-{number}",
        "recording_start_time": start, "title": title,
        "default_summary": {"markdown_formatted": f"## Meeting Purpose\n\nSummary fixture {number}"},
        "action_items": [{"description": f"Action fixture {number}",
                          "recording_playback_url": f"https://fathom.video/share/fixture-{number}?timestamp=5"}],
        "transcript": [{"timestamp": "00:00:05", "speaker": {"display_name": "Jena"},
                        "text": f"Transcript fixture {number}"}],
    }


class VaultCase(unittest.TestCase):
    def setUp(self):
        self.vault = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="kit-fixture-"))).resolve()
        self.home = self.vault / "fixture-home"
        self.home.mkdir()
        self.scripts = ROOT / "scripts"
        self.enterContext(patch.dict(os.environ, isolated_env(self.home), clear=True))
        self.enterContext(patch.object(sys, "path", [str(self.scripts), *sys.path]))
        self.wire = Wire()
        self.enterContext(self.wire.patch())

    def put(self, relative: str, data: bytes) -> Path:
        path = self.vault / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def run_cli(self, name: str, *args: str, stdin: str = "") -> tuple[int, str, str]:
        return cli(self.scripts, name, ["--vault", str(self.vault), *args], stdin)

    def ok(self, name: str, *args: str, stdin: str = "") -> str:
        code, out, err = self.run_cli(name, *args, stdin=stdin)
        self.assertEqual(code, 0, err)
        return out
