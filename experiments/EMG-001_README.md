# EMG-001 — Read-only evidence manifest preflight

**Status:** Experimental; preregistered and locally self-tested (10/10 unit tests on a Linux container). **Not independently validated.** CI cross-version status is separate from this local result.

See [EMG-001_PREREG.md](EMG-001_PREREG.md) for registered predictions and outcome rules.

## Purpose

Detect absent or altered files in a published evidence package **before** describing that package as complete. Motivating case: [Sovereign Veritas SEC-003A draft PR #74](https://github.com/holland202/sovereign-veritas/pull/74) includes an `evidence_manifest.json` naming `fuzzer.log` and `replay.log` but does not include those two logs. A `confirmed: true` label in `replay_status.json` does not replace those diagnostic artifacts.

## Usage

Run with Python 3.11+ (standard library only):

```sh
python3 evidence_manifest_gate.py /path/to/evidence/directory
```

The directory must contain `evidence_manifest.json`, with a nonempty `files` mapping of POSIX-style relative paths to lowercase SHA-256 digests. The tool checks every listed file and reports all missing or mismatched paths. Exit 0 indicates *only* that each listed local file matches its declared digest. Any error is nonzero.

```sh
python3 -m unittest discover -s tests -p 'test_evidence_manifest_gate.py' -v
```

## Nonclaims and limitations

- The checker is not a cryptographic trust anchor: an attacker may replace an unsigned manifest and all files coherently.
- It cannot prove discovery, sanitizer truth, replay validity, external effects, independence, or scientific success.
- Missing unlisted files cannot be detected. Source and executable hashes listed outside `files` are **not** independently checked by this preflight.
- Local filesystems subject to concurrent hostile mutation are out of scope; path checks are not a sandbox.
- The SEC-003A logs must be recovered from the original local experiment and added as exact-byte artifacts before the draft PR's evidence-completeness blocker can be removed. **Do not regenerate missing logs and claim they are the originals.**
- This tool is in `veritas-eval-harness`, not the maintenance-only `sovereign-veritas` kernel.

## Workflow provenance

The small stage-gate process borrows planning and review ideas from [TRIP-workflow](https://github.com/PiLastDigit/TRIP-workflow) without importing its agent skills, external Codex wrappers, YOLO mode, bulk staging, or automatic release steps.
