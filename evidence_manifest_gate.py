#!/usr/bin/env python3
"""EMG-001: read-only integrity preflight; no authenticity or scientific validation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _safe_relative_path(name):
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        return False
    # Interpret portable manifest paths as POSIX, including on Windows.
    if name.startswith("/") or ":" in name or any(p in ("", ".", "..") for p in name.split("/")):
        return False
    return True


def inspect(root):
    """Return (matched_count, listed_count, errors). No write operations."""
    root = Path(root)
    if not root.is_dir():
        return 0, 0, ["INVALID_ROOT: not an accessible directory"]
    if root.is_symlink():
        return 0, 0, ["INVALID_ROOT: symlink not permitted"]
    manifest = root / "evidence_manifest.json"
    if manifest.is_symlink():
        return 0, 0, ["INVALID_MANIFEST: symlink not permitted"]
    try:
        with manifest.open("r", encoding="utf-8") as stream:
            document = json.load(stream, object_pairs_hook=_no_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return 0, 0, [f"INVALID_MANIFEST: {type(exc).__name__}: {exc}"]
    if not isinstance(document, dict) or not isinstance(document.get("files"), dict) or not document["files"]:
        return 0, 0, ["INVALID_SCHEMA: files must be a nonempty mapping"]

    files = document["files"]
    matched = 0
    errors = []
    for name, expected in files.items():
        if not _safe_relative_path(name):
            errors.append(f"UNSAFE_PATH: {name!r}")
            continue
        if not isinstance(expected, str) or _SHA256.fullmatch(expected) is None:
            errors.append(f"INVALID_DIGEST: {name}")
            continue
        pieces = name.split("/")
        candidate = root
        if any((candidate := candidate / piece).is_symlink() for piece in pieces):
            errors.append(f"UNSAFE_PATH: symlink in {name}")
            continue
        if not candidate.is_file():
            errors.append(f"MISSING_OR_NOT_REGULAR: {name}")
            continue
        try:
            digest = hashlib.sha256()
            with candidate.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            errors.append(f"READ_ERROR: {name}: {type(exc).__name__}")
            continue
        if digest.hexdigest() != expected:
            errors.append(f"HASH_MISMATCH: {name}")
        else:
            matched += 1
    return matched, len(files), errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="evidence directory containing evidence_manifest.json")
    args = parser.parse_args(argv)
    matched, total, errors = inspect(args.root)
    print("EXPERIMENT=EMG-001")
    print(f"FILES_LISTED={total}")
    print(f"FILES_HASH_MATCHED={matched}")
    for error in errors:
        print("FINDING=" + error)
    if errors:
        print("GATE=INTEGRITY_CHECK_FAILED")
        return 1
    print("GATE=INTEGRITY_CHECK_PASSED")
    print("SCOPE=LISTED_FILE_HASHES_ONLY_NOT_AUTHENTICITY_OR_TRUTH")
    return 0


if __name__ == "__main__":
    sys.exit(main())
