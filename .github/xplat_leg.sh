#!/usr/bin/env bash
# One XPLAT leg (see XPLAT_PREREG.md). Same script on every platform.
# Usage: PY=python bash .github/xplat_leg.sh OUTDIR
set -euo pipefail
OUT="$1"
PY="${PY:-python3}"
mkdir -p "$OUT"
git config --global --add safe.directory '*' 2>/dev/null || true

# Record what this leg actually ran on. Not a .txt, so never compared.
"$PY" -c "import platform, sys; print(platform.platform(), platform.machine(), sys.byteorder, sys.version.split()[0])" | tee "$OUT/platform.info"

echo "== P1: existing gates"
"$PY" sabotage_arm.py > "$OUT/arm.txt"
grep -qE "honest brute force +True +1218" "$OUT/arm.txt"
grep -q "P0  PASS" "$OUT/arm.txt"
grep -q "UNACCOUNTED DEVIATIONS: none" "$OUT/arm.txt"
grep -q "RUN VALID: YES" "$OUT/arm.txt"

"$PY" p7_structured_f.py > "$OUT/p7.txt"
grep -q "P7b FALSE POSITIVE    honest inverter flagged by D2 -> CONFIRMED" "$OUT/p7.txt"
grep -qE "A_invert  algebraic +True +2 " "$OUT/p7.txt"

"$PY" p8_precondition.py > "$OUT/p8.txt"
grep -q "P8a ANTI-VACUITY   checker does not veto sha256 -> PASS" "$OUT/p8.txt"
grep -q "P8b CATCHES LINEAR checker vetoes the P7 substrate  -> PASS" "$OUT/p8.txt"
grep -qE "quadratic +PASS +0/400 +True +False +FAIL" "$OUT/p8.txt"

"$PY" ci_gate_check.py
"$PY" d3_ci_check.py
"$PY" d3_ci_check.py --selftest

echo "== P2: D3 output vs the S25 record"
"$PY" d3_verifier_validity.py > "$OUT/d3.txt"
"$PY" xplat_digest.py --selftest
"$PY" xplat_digest.py compare d3_device_v3.txt "$OUT"

echo "== digests for P3 (compared across legs in the final job)"
"$PY" xplat_digest.py digest "$OUT"

git diff --exit-code
echo "LEG PASS"
