"""Offline runtime smoke test in a separate interpreter pointed at the extracted kit."""

import os
import sys
from pathlib import Path

from support import CLICKUP_FILE, CLICKUP_KEY, FATHOM_FILE, FATHOM_KEY, Wire, cli, meeting


def main() -> None:
    archive_root = Path(sys.argv[1])
    scripts = archive_root / "scripts"
    vault = Path(sys.argv[2])
    sys.path.insert(0, str(scripts))
    wire = Wire()
    with wire.patch():
        os.environ["FATHOM_API_KEY"] = FATHOM_KEY
        wire.replies = [(200, {"items": [meeting(15)]})]
        code, out, err = cli(scripts, FATHOM_FILE, ["--vault", str(vault)])
        assert code == 0, (out, err)
        (recording,) = (path for path in (vault / "inbox").glob("*.md") if path.name != "README.md")
        assert "Transcript fixture 15" in recording.read_text()
        del os.environ["FATHOM_API_KEY"]
        os.environ["CLICKUP_API_TOKEN"] = CLICKUP_KEY
        wire.replies = [(200, {"tasks": [{"name": "Package runtime smoke"}]})]
        code, out, err = cli(scripts, CLICKUP_FILE, ["--vault", str(vault), "tasks", "--list", "123"])
        assert code == 0 and "Package runtime smoke" in out, (out, err)
        assert [req.method for req in wire.ledger] == ["GET", "GET"]
    for module in ("kit_context", "kit_http"):
        assert Path(sys.modules[module].__file__).parent == scripts
    assert not (vault / ".env").exists()
    print(f"Archive runtime {scripts}: real imports, scoped GETs and saved recording fixture-15")


if __name__ == "__main__":
    main()
