# XPLAT — Cross-platform determinism (registration)

Status: **Registered, UNRUN.** This file is committed alone, before the
workflow that tests it exists. Results go in a dated amendment below; this
text is not edited after commit.

Registered 2026-10-03. Drafted by Claude (Opus 5.5) at Chad Holland's
request; Chad chose the scope (pilot one repo) and owns the decision to merge.

## Question

Every number this harness publishes was produced on one S25 Ultra
(aarch64, Android, Python 3.14) and pinned in CI on one Linux x86_64 runner.
Does the same code produce the same output on other operating systems and
instruction sets — including a big-endian one?

## Legs

| Leg | Runner | ISA | Byte order | Python |
|---|---|---|---|---|
| L1 | ubuntu-latest | x86_64 | little | 3.14 |
| L2 | ubuntu-24.04-arm | aarch64 | little | 3.14 |
| L3 | macos-latest | arm64 | little | 3.14 |
| L4 | windows-latest | x86_64 | little | 3.14 |
| L5 | QEMU-emulated s390x (IBM Z ISA) | s390x | **big** | distro python3 |
| L6 | QEMU-emulated ppc64le (IBM Power ISA) | ppc64le | little | distro python3 |

Scope limits, stated now:
- L5/L6 emulate the IBM instruction sets under QEMU. They are **not** runs
  on IBM hardware and must never be described as such.
- Android cannot run on GitHub runners. L2 shares the S25's ISA, not its OS.
  The S25 itself enters only through the committed `d3_device_v3.txt`.
- Intel macOS, Windows on ARM, and Python 3.11 on non-Linux are not tested.

## Predictions

- **P1 — gates.** On every leg, the existing gates exit 0: pinned numbers
  (sabotage arm, P7, P8), `ci_gate_check.py`, `d3_ci_check.py`,
  `d3_ci_check.py --selftest`.
- **P2 — device agreement.** On every leg, D3 output after normalization is
  byte-identical to the committed S25 record `d3_device_v3.txt`.
- **P3 — cross-leg agreement.** The normalized outputs of `sabotage_arm.py`,
  `p7_structured_f.py`, `p8_precondition.py` and `d3_verifier_validity.py`
  have one sha256 each across all legs that ran.
- **P4 — big-endian.** L5 (s390x) satisfies P1–P3. Registered separately
  because it is the leg most likely to break (any byte-order assumption in
  hashing, struct packing or seeded randomness surfaces here).

## Normalization (declared before any leg runs; nothing else is removed)

1. `\r` removed (Windows writes `\r\n` to redirected stdout).
2. Lines beginning `runtime ` removed (wall-clock).
3. Lines beginning `python          :` removed (interpreter and platform name).

## Anti-vacuity

- Per leg: `ci_gate_check.py` and `d3_ci_check.py --selftest` already prove
  the gates can fail.
- Comparator: `xplat_digest.py --selftest` must show the comparator reports a
  mismatch when one byte of one output is altered, and reports agreement on
  identical inputs. If the selftest passes but the comparator cannot fail,
  P2/P3 are void.

## Outcome rules

- A leg that never starts (runner label or action unavailable) is **VOID**,
  not FAIL, and is reported as such.
- A leg that starts and disagrees is a **finding**, kept, not tuned away. No
  normalization rule is added after seeing results; a new rule needs a new
  registration.
- No claim about determinism on hardware or OSes outside the table.

## Left unrun

- Intel macOS and Windows on ARM.
- Real IBM hardware (s390x/ppc64le) rather than emulation.
- The S25 rerunning the same normalized digest on device.

---

## Amendment 1 — 2026-10-04 (UTC), first run, native legs

Run: GitHub Actions run 37167220414 on `fd9095a` (code as registered).
L5/L6 (emulated) still running at the time of writing; their outcome goes in
Amendment 2. Nothing above this line was edited.

| Leg | P1 gates | P2 D3 vs S25 record | Job |
|---|---|---|---|
| L1 linux x86_64 | pass | MATCH | success |
| L2 linux aarch64 | pass | MATCH | success |
| L3 macOS arm64 | pass | MATCH | success |
| L4 windows x86_64 | gates pass; **tree-clean check FAILS** | MATCH | failure |

**Finding (L4), kept:** `ci_gate_check.py` read, wrote and verified
`veritas_harness.py` in text mode. On Windows the restore step wrote CRLF line
endings back into the file, and its own restore check, also in text mode,
translated them back and reported the file identical. Only the final
`git diff --exit-code` caught it. The docstring promised a byte-for-byte
restore; on Windows that claim was false and the check guarding it could not
see the failure. Reproduced on Linux by writing the CRLF form directly:
text-mode check says unchanged, raw bytes differ.

This is a defect in the existing gate tool, not in the harness's numbers:
every pinned value and the D3 comparison against the S25 record held on L4.
P1 is therefore **not met on L4 as registered**; the fix lands in a separate
commit and is tested by a fresh run, reported in Amendment 2. This amendment
does not count the fixed run as a pass for the original code.
