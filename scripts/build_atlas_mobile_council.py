"""Build a dependency-free ATLAS PAPER Council zipapp from this checkout."""
from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "council.py",
    "council_adapters.py",
    "council_training.py",
    "executive.py",
    "nine_seat_council.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Destination .pyz path")
    args = parser.parse_args()
    if args.output.suffix != ".pyz":
        parser.error("The output filename must end in .pyz.")
    if args.output.exists():
        parser.error("The destination already exists. Choose a new filename.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.output.parent) as temp_dir:
        temporary = Path(temp_dir) / args.output.name
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("app/__init__.py", "")
            archive.writestr("app/intelligence/__init__.py", "")
            for module in MODULES:
                path = f"app/intelligence/{module}"
                archive.writestr(path, (ROOT / path).read_bytes())
            entrypoint = ROOT / "scripts/atlas_mobile_council.py"
            archive.writestr("__main__.py", entrypoint.read_bytes())
        # Exclusive creation preserves any file that appeared after the first check.
        with args.output.open("xb") as output:
            output.write(temporary.read_bytes())
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
