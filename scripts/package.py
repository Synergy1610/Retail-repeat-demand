"""Build deterministic flat submission ZIPs for the two model variants.

The hackathon runner expects a flat archive with no nested paths. This script
packages only the required inference files, verifies the result, and prints a
SHA-256 manifest.

Examples::

    python scripts/package.py
    python scripts/package.py --model adapted --output-dir dist --force
"""

import argparse
import hashlib
import json
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODELS = {
    "pre-twist": {
        "source": ROOT / "models" / "v2.1-pre-twist",
        "required": {"solution.py", "features.py", "starter_model.json"},
        "archive": "Team-99_v2.1_pre-twist.zip",
    },
    "adapted": {
        "source": ROOT / "models" / "v2.1-adapted",
        "required": {
            "solution.py",
            "features.py",
            "feed_adapter.py",
            "starter_model.json",
        },
        "archive": "Team-99_v2.1_adapted.zip",
    },
}

ALLOWED_SUFFIXES = {".py", ".json"}
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def collect(source, required):
    """Return required files after checking the flat-package allowlist."""
    if not source.is_dir():
        raise ValueError(f"Model source does not exist: {source}")

    files = {}
    for path in sorted(source.iterdir(), key=lambda item: item.name):
        if path.name == "README.md" or path.is_dir():
            continue
        if path.is_symlink():
            raise ValueError(f"Model files cannot be symlinks: {path.name}")
        if not path.is_file():
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError(f"Unsupported file in model directory: {path.name}")
        if path.name not in required:
            raise ValueError(f"Unexpected file in model directory: {path.name}")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"File exceeds 2 MiB: {path.name}")
        files[path.name] = path

    missing = required - files.keys()
    if missing:
        raise ValueError(f"Missing required files: {', '.join(sorted(missing))}")
    total = sum(path.stat().st_size for path in files.values())
    if total > MAX_TOTAL_BYTES:
        raise ValueError("Model exceeds the 16 MiB uncompressed limit")
    return files, total


def build(definition, output_dir, force):
    """Write and verify one flat archive; return its manifest."""
    source = definition["source"]
    output = output_dir / definition["archive"]

    if output.exists() and not force:
        raise ValueError(f"Archive already exists (use --force): {output}")
    if output.resolve().parent == source.resolve():
        raise ValueError("Write archives outside the model source directory")

    files, total = collect(source, definition["required"])
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        output, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, path in files.items():
            info = zipfile.ZipInfo(filename=name, date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )

    with zipfile.ZipFile(output, mode="r") as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if set(names) != set(files) or len(names) != len(files):
            raise ValueError("ZIP contents do not match the allowlist")
        if any("/" in name or "\\" in name for name in names):
            raise ValueError("ZIP entries must be flat")
        for entry in entries:
            mode = entry.external_attr >> 16
            if not stat.S_ISREG(mode):
                raise ValueError(f"ZIP entry is not a regular file: {entry.filename}")
            if entry.file_size > MAX_FILE_BYTES:
                raise ValueError(f"ZIP entry exceeds 2 MiB: {entry.filename}")
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC verification failed")

    return {
        "archive": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
        "files": sorted(files),
        "uncompressed_bytes": total,
        "archive_bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        choices=("pre-twist", "adapted", "all"),
        default="all",
        help="Which model to package (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "dist",
        help="Directory for the ZIPs (default: dist)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing archives",
    )
    args = parser.parse_args(argv)

    output_dir = args.output_dir.resolve()
    selected = ["pre-twist", "adapted"] if args.model == "all" else [args.model]

    try:
        manifests = [build(MODELS[name], output_dir, args.force) for name in selected]
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))

    checksum_path = output_dir / "SHA256SUMS"
    lines = [f"{item['sha256']}  {Path(item['archive']).name}" for item in manifests]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"archives": manifests, "checksums": str(checksum_path)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
