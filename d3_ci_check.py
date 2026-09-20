#!/usr/bin/env python3
"""
d3_ci_check.py -- wire D3's gates to CI.

Runs d3_verifier_validity.py in both directions and asserts the pinned
verdicts and numbers. Without this, D3's qualification gates only fire when
someone remembers to run the file by hand, which means a later edit can
silently disable QUAL-1..QUAL-5 and nothing says so. A harness whose own
gates are not wired to CI is a soft version of the defect it hunts.

Stdlib only. Same checker runs in CI and on device -- no YAML-embedded greps
that drift from the local invocation.

PINS are verbatim substrings of the qualified run, replicated digit-for-digit
on x86_64/py3.12 (container) and aarch64/py3.14 (Termux, S25 Ultra).
Commit: 8789832.

Exit codes
----------
0  both arms behaved; every pin present
1  a pin is missing, or an arm returned the wrong exit code
2  could not run

Usage
-----
  python3 d3_ci_check.py
  python3 d3_ci_check.py --selftest    # anti-vacuity: prove the checker fails
"""

import argparse
import subprocess
import sys

TARGET = "d3_verifier_validity.py"

# ---------------------------------------------------------------------------
# Normal arm: must exit 0 and contain every line below verbatim.
# ---------------------------------------------------------------------------
PINS_PASS = [
    # provenance
    "prereg sha256/12: e50c8d96d882",
    "report sha256/12: 7fe45bed2096",
    # t0 characterization
    "V accuracy at t0 : 0.8455",
    # gates
    "A_M0 = 0.5083  95% [0.4942,0.5225]  EXPECTED 0.5000 [0.45,0.55]  OK",
    "A_M1 = 0.5012  EXPECTED 0.5000 [0.45,0.55]  OK",
    "M1 fire rate on SURFACE = 1.0000  min=0.80  OK",
    "A_M2 at k=2048, q_post=0.05 = 0.9875  min=0.95  OK",
    "slope mean = -1.997   across-seed range = 0.279   max=0.60  OK",
    # entailed tags must survive edits -- these are what stop a future reader
    # quoting the M0/M1 separation as a result
    "[ENTAILED, NOT MEASURED] marginal preservation makes M0 blind",
    "[ENTAILED, NOT MEASURED] A_M1 ~ 0.50 follows from the same",
    # claims
    "P1  finite for every s: yes   strictly decreasing in delta: yes   -> CONFIRMED",
    "P2  least k above chance = 8   least k at saturation (>= 0.95) = 64   -> CONFIRMED",
    "PREDICTED -2.000 +/- 0.60  ->  CONSISTENT",
    "P4  REGISTERED, NOT RUN",
    "STATUS: NOT VALIDATED. No number here bears on it.",
    # frontier, k* column anchored to its break
    "   0.70   0.7929 ",
    "   0.05   0.6244 ",
    "  1536",
    "ALL QUALIFICATION GATES PASSED.",
]
KSTAR_ROW_ENDS = ["1536", "512", "384", "192", "96", "64"]

# ---------------------------------------------------------------------------
# Sabotage arm: the validity shift is neutered, so the gates must FAIL.
# A gate that cannot fail is the thing this repo exists to catch, so CI
# checks the failure direction too.
# ---------------------------------------------------------------------------
PINS_SABOTAGE = [
    "P1  finite for every s: NO",
    "P2  least k above chance = None",
    "GATE FAILURE: QUAL-4, QUAL-5 -- not qualified.",
    "No claim is admissible from this run.",
]


def run(args):
    p = subprocess.run([sys.executable, TARGET] + args,
                       capture_output=True, text=True, timeout=1800)
    return p.returncode, p.stdout + p.stderr


def check(out, pins, label):
    missing = [p for p in pins if p not in out]
    for p in pins:
        print(f"  [{'ok ' if p in out else 'MISS'}] {label}: {p[:62]}")
    return missing


def check_kstar(out):
    """k* column, each value anchored to its own frontier row."""
    rows = [l for l in out.splitlines()
            if l.startswith("   0.") and l.count(".") > 5]
    if len(rows) != len(KSTAR_ROW_ENDS):
        print(f"  [MISS] frontier: expected {len(KSTAR_ROW_ENDS)} rows, "
              f"got {len(rows)}")
        return ["frontier row count"]
    bad = []
    for row, want in zip(rows, KSTAR_ROW_ENDS):
        got = row.split()[-1]
        ok = got == want
        print(f"  [{'ok ' if ok else 'MISS'}] k* {row.split()[0]} -> "
              f"{got} (want {want})")
        if not ok:
            bad.append(f"k* {row.split()[0]}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="corrupt a pin and confirm this checker reports failure")
    args = ap.parse_args()

    if args.selftest:
        # anti-vacuity on the CHECKER. If this passes, the checker is inert
        # and every green CI run above it means nothing.
        fake = "ALL QUALIFICATION GATES PASSED.\nslope mean = -9.999\n"
        missing = [p for p in PINS_PASS if p not in fake]
        ok = len(missing) > 0
        print(f"SELFTEST: corrupted output -> {len(missing)} pins missing")
        print(f"SELFTEST: checker {'REPORTS FAILURE (correct)' if ok else 'IS INERT'}")
        return 0 if ok else 1

    fails = []

    print("== D3 normal arm ==")
    rc, out = run([])
    print(f"  exit={rc} (want 0)")
    if rc != 0:
        fails.append(f"normal arm exit {rc}")
    fails += check(out, PINS_PASS, "pass")
    fails += check_kstar(out)

    print()
    print("== D3 sabotage arm (gates must FAIL) ==")
    rc_s, out_s = run(["--sabotage"])
    print(f"  exit={rc_s} (want 1)")
    if rc_s != 1:
        fails.append(f"sabotage arm exit {rc_s}, expected 1")
    fails += check(out_s, PINS_SABOTAGE, "sabotage")

    print()
    if fails:
        print(f"D3 CI CHECK FAILED: {len(fails)} item(s)")
        for f in fails:
            print(f"  - {f}")
        print("D3's qualified numbers no longer reproduce. Do not paper over")
        print("this: a drift here is either a real finding or a real bug.")
        return 1
    print("D3 CI CHECK PASSED: both arms, all pins, k* column intact.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"could not run: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
