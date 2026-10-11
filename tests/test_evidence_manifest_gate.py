"""Preregistered EMG-001 positive and negative controls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

# Allow tests from a checkout with no package installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_manifest_gate import inspect

SCRIPT = Path(__file__).resolve().parents[1] / "evidence_manifest_gate.py"


class ManifestGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {}
        self.add_file("source.c", b"int main(){return 0;}\n")
        self.add_file("fuzzer.log", b"asan discovery\n")
        self.add_file("replay.log", b"asan replay\n")
        self.add_file("replay_status.json", b'{"confirmed": true}\n')
        self.write_manifest()

    def add_file(self, name, contents):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contents)
        self.files[name] = hashlib.sha256(contents).hexdigest()

    def write_manifest(self):
        (self.root / "evidence_manifest.json").write_text(
            json.dumps({"experiment": "SEC-003A", "files": self.files}, sort_keys=True),
            encoding="utf-8")

    def cli(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root)], text=True, capture_output=True)

    def test_p0_valid(self):
        self.assertEqual(inspect(self.root), (4, 4, []))
        run = self.cli()
        self.assertEqual(run.returncode, 0)
        self.assertIn("GATE=INTEGRITY_CHECK_PASSED", run.stdout)
        self.assertIn("NOT_AUTHENTICITY_OR_TRUTH", run.stdout)

    def test_p1_missing_two_logs_despite_confirmed_status(self):
        (self.root / "fuzzer.log").unlink()
        (self.root / "replay.log").unlink()
        run = self.cli()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("MISSING_OR_NOT_REGULAR: fuzzer.log", run.stdout)
        self.assertIn("MISSING_OR_NOT_REGULAR: replay.log", run.stdout)
        self.assertIn("GATE=INTEGRITY_CHECK_FAILED", run.stdout)

    def test_p2_tampered_file(self):
        (self.root / "source.c").write_bytes(b"int main(){return 1;}\n")
        run = self.cli()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("HASH_MISMATCH: source.c", run.stdout)

    def test_p3_traversal(self):
        self.files["../escape"] = "a" * 64
        self.write_manifest()
        self.assertIn("UNSAFE_PATH", str(inspect(self.root)[2]))

    def test_p3_absolute_and_backslash(self):
        self.files["/tmp/anything"] = "a" * 64
        self.files[r"..\escape"] = "b" * 64
        self.write_manifest()
        _, _, errors = inspect(self.root)
        self.assertEqual(sum(x.startswith("UNSAFE_PATH") for x in errors), 2)

    def test_p3_symlink(self):
        (self.root / "source.c").unlink()
        try:
            (self.root / "source.c").symlink_to(self.root / "replay.log")
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        _, _, errors = inspect(self.root)
        self.assertIn("UNSAFE_PATH: symlink in source.c", errors)

    def test_p4_duplicate_json_key(self):
        (self.root / "evidence_manifest.json").write_text(
            '{"files": {"source.c": "' + self.files["source.c"] + '", "source.c": "' + self.files["source.c"] + '"}}')
        self.assertIn("INVALID_MANIFEST", str(inspect(self.root)[2]))

    def test_p4_empty_mapping(self):
        (self.root / "evidence_manifest.json").write_text('{"files": {}}')
        self.assertIn("INVALID_SCHEMA", str(inspect(self.root)[2]))

    def test_p4_malformed_digest(self):
        self.files["source.c"] = "NOT_A_DIGEST"
        self.write_manifest()
        self.assertIn("INVALID_DIGEST: source.c", inspect(self.root)[2])

    def test_p4_malformed_json(self):
        (self.root / "evidence_manifest.json").write_text("{")
        self.assertIn("INVALID_MANIFEST", str(inspect(self.root)[2]))


if __name__ == "__main__":
    unittest.main()
