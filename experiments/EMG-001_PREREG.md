# EMG-001 — Preregistration: evidence-manifest integrity preflight

**Status:** REGISTERED / UNRUN. This commit precedes implementation and testing.
**Repository:** `holland202/veritas-eval-harness`, experimental branch `experiment/evidence-manifest-gate-001`.
**Target:** independent, read-only, standard-library verifier for a manifest's listed file SHA-256 digests.
**Motivation:** SEC-003A's GitHub evidence manifest lists `fuzzer.log` and `replay.log` even though neither log was committed; the draft PR must not be promoted as a complete inspectable evidence package.

## Question

Can a tool-independent preflight reliably reject incomplete or altered artifact sets before an AI agent describes them as complete?

## Registered checks

- **P0 (positive control):** a non-empty manifest whose listed files exist, are regular files under the evidence root, and match exact lowercase SHA-256 digests exits 0 with `GATE=INTEGRITY_CHECK_PASSED`.
- **P1 (SEC-003A-style missing logs):** a manifest that names `fuzzer.log` and `replay.log`, but those files are absent, must exit non-zero and identify both missing paths, even if a separate replay-status record claims `confirmed: true`.
- **P2 (mutation):** replacing one byte of a named file without changing its manifest digest must exit non-zero with a hash mismatch.
- **P3 (path attack):** absolute, traversal, Windows backslash, or symlink paths that may escape the evidence root must not be read as valid evidence.
- **P4 (schema):** malformed JSON, duplicate keys, empty/malformed file maps, or malformed digests must not produce a passing verdict.
- **P5 (anti-vacuity):** a passing control and all four negative classes must be exercised in automated tests, with asserted verdicts (no tests silently skipped).

## Scope and limits

- No calls to models, networks, executors, or repository mutation.
- SHA-256 file identity and package completeness **only**; this does not prove file authenticity, evidence truth, freshness, independent scientific reproduction, security of the subject, or source origin.
- A hash in a mutable local manifest alone provides no external trust anchor; an attacker able to replace files and manifest coherently can evade this preflight.
- TOCTOU and hostile concurrent filesystem mutation are out of scope. Symlinks are refused on inspection; this is not a sandbox or race-free filesystem boundary.
- The experiment's original evidence is not edited. SEC-003A's missing original logs cannot be reconstructed from this tool.
- **No changes to `sovereign-veritas`**, which remains maintenance-only. No auto-release, auto-merge, bulk staging, or installation of TRIP scripts.

## Decision rule

Any failed negative control, incorrectly passing malformed set, or failure to run tests => **NOT VALIDATED**. Keep the failed result and do not weaken a test to force a pass.

## Prior art and attribution

Process design borrows the plan → implement → review → test idea from [TRIP-workflow](https://github.com/PiLastDigit/TRIP-workflow) (consulted 2026-10-11). This is a tailored experiment, not an installation of TRIP or a claim that its methods are independently validated.
