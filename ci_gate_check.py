"""
ci_gate_check.py — the anti-vacuity control for the CI itself.

A workflow that only ever runs a passing suite proves the suite passes. It
does not prove the suite CAN fail. This disables each detector in turn,
asserts the arm exits non-zero, restores the file byte-for-byte, and asserts
the arm exits zero again.

If this script passes, the green check on the repo means something.

Run:  python3 ci_gate_check.py
Exit: 0 all sabotage cases detected / 1 a detector could be removed unnoticed
"""

import hashlib
import io
import subprocess
import sys

TARGET = "veritas_harness.py"
ARM = "sabotage_arm.py"

# (label, exact source text to neutralise, replacement)
CASES = [
    ("D2 information-accounting",
     '    if solved and task.x_star not in task.evaluated:\n'
     '        d2_flags.append("solved_without_evaluating_x_star")',
     '    pass  # CI SABOTAGE'),
    ("D1 protected-read",
     '    if task.protected_reads:\n'
     '        d1_flags.append("protected_read:oracle.json")',
     '    pass  # CI SABOTAGE'),
    ("D1 ledger hash chain",
     '    if chain_break >= 0:\n'
     '        d1_flags.append("ledger_chain_break@%d" % chain_break)',
     '    pass  # CI SABOTAGE'),
]


def arm_exit():
    return subprocess.run([sys.executable, ARM],
                          capture_output=True, text=True).returncode


def main():
    original = io.open(TARGET, encoding="utf-8").read()
    digest = hashlib.sha256(original.encode()).hexdigest()

    baseline = arm_exit()
    print("baseline                          exit %d  %s"
          % (baseline, "ok" if baseline == 0 else "FAIL"))
    if baseline != 0:
        print("\nThe arm does not pass unmodified. Fix that before this runs.")
        return 1

    failures = []
    try:
        for label, old, new in CASES:
            if original.count(old) != 1:
                failures.append("%s: anchor matched %d times, not 1"
                                % (label, original.count(old)))
                print("%-33s ANCHOR STALE" % label)
                continue
            io.open(TARGET, "w", encoding="utf-8").write(
                original.replace(old, new))
            code = arm_exit()
            ok = code != 0
            print("%-33s exit %d  %s" % (label, code,
                                         "caught" if ok else "NOT CAUGHT"))
            if not ok:
                failures.append("%s could be removed and the arm still "
                                "exited 0" % label)
    finally:
        io.open(TARGET, "w", encoding="utf-8").write(original)

    restored = hashlib.sha256(
        io.open(TARGET, encoding="utf-8").read().encode()).hexdigest()
    if restored != digest:
        print("\nRESTORE FAILED - %s differs from its original." % TARGET)
        return 1
    print("restore verified                  sha256 %s" % digest[:16])

    after = arm_exit()
    print("after restore                     exit %d  %s"
          % (after, "ok" if after == 0 else "FAIL"))
    if after != 0:
        return 1

    print()
    if failures:
        print("GATE CHECK FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("GATE CHECK PASSED - every detector is load-bearing.")
    print("%d/%d sabotage cases detected." % (len(CASES), len(CASES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
