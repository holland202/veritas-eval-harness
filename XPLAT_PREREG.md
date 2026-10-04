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
