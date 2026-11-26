#!/usr/bin/env python3
"""Build a lean installable ZIP from the explicit distribution allowlist."""

import argparse
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from kit_context import VAULT, KitError, vault_path
from kit_files import DISTRIBUTION


def build(output: Path) -> None:
    if len(set(DISTRIBUTION)) != len(DISTRIBUTION):
        raise KitError("Distribution has duplicate paths.")
    contents = [(name, vault_path(VAULT, name).read_bytes()) for name in sorted(DISTRIBUTION)]
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w") as archive:
        for name, body in contents:
            archive.writestr(ZipInfo(name), body, compress_type=ZIP_DEFLATED)
    with ZipFile(output) as archive:
        if set(archive.namelist()) != set(DISTRIBUTION) or archive.testzip() is not None:
            raise KitError("Archive inventory or checksums do not match the distribution.")
        print(f"Built {output} ({len(archive.namelist())} files)")
        print("\n".join(archive.namelist()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=VAULT / "dist/ai-os-kit.zip")
    try:
        build(parser.parse_args().output)
    except (KitError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
