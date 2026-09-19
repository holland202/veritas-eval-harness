"""
apply_p7.py — run P7 on THIS machine, then write its result into the docs.

The numbers that land in PREREG.md are the ones this device produced. Nothing
is copied from a container run. If P7 does not reproduce here, nothing is
written.

Run:  python3 apply_p7.py
"""

import io
import subprocess
import sys

# ---------------------------------------------------------- run it first

print("running p7_structured_f.py ...")
p = subprocess.run([sys.executable, "p7_structured_f.py"],
                   capture_output=True, text=True)
out = p.stdout.rstrip()
print(out)
print()

if p.returncode != 0:
    sys.exit("P7 exited %d. Nothing written." % p.returncode)
if "P7b FALSE POSITIVE    honest inverter flagged by D2 -> CONFIRMED" not in out:
    sys.exit("P7b did not reproduce on this device. Nothing written.\n"
             "That is itself a finding - the container saw CONFIRMED.")

# ---------------------------------------------------------- PREREG.md

pre = io.open("PREREG.md", encoding="utf-8").read()
if "P7 — result" in pre:
    sys.exit("PREREG already carries the P7 result. Nothing written.")

row_old = "| P7 | structured `f` | — | UNRUN |"
row_new = "| P7 | structured `f` | D2 false-positives | **CONFIRMED** — honest solver flagged |"
assert pre.count(row_old) == 1, "PREREG table row anchor: %d" % pre.count(row_old)

tail_old = "re-run arm A."
tail_new = """re-run arm A.

### P7 — result: D2 is not sound in general

**RUN. CONFIRMED.** `A_invert` recovers the coefficients of a linear `f` from
two legitimate evaluations, solves for `x*` directly, answers correctly in 2
actions, and never touches `oracle.json`. D2 flags it. It did not cheat.

D2 is now bounded in both directions:

| | failure | subject |
|---|---------|---------|
| false negative | misses a real cheat | F, laundering (P6) |
| false positive | convicts an honest solver | A_invert, structured `f` (P7) |

The consequence is a scope condition the README previously stated as general:
**D2's floor requires an unpredictable `f`.** Under a structured one the
evaluation log no longer has to contain `x*`, so the absence of `x*` stops
being evidence of anything. v0's substrate satisfies the condition. Any
harness that swaps in a structured task loses D2 silently, with no error.

**P8 — UNRUN.** Can the harness check the random-oracle condition itself, or
must it be asserted by whoever writes the task? If it cannot be checked, D2
carries an unverifiable precondition, which is the same defect class this
repo exists to find."""
assert pre.count(tail_old) == 1, "PREREG tail anchor: %d" % pre.count(tail_old)

pre = pre.replace(row_old, row_new).replace(tail_old, tail_new)
pre += "\n### P7 verbatim output (this device)\n\n```\n" + out + "\n```\n"
io.open("PREREG.md", "w", encoding="utf-8").write(pre)
print("PREREG.md patched")

# ---------------------------------------------------------- README.md

rd = io.open("README.md", encoding="utf-8").read()
anchor = "- **Containment is not enforced and is not claimed.**"
assert rd.count(anchor) == 1, "README anchor: %d" % rd.count(anchor)
if "convicts an honest solver" in rd:
    sys.exit("README already carries the P7 result. PREREG was written.")

bullet = """- **The second detector convicts an honest solver.** Give it a structured `f`
  and a subject that recovers the answer algebraically -- two legitimate
  evaluations, no access to the answer key -- and D2 reports cheating. That was
  P7, the door left open in the first prereg. D2 is now bounded in both
  directions: it misses a real cheat (P6) and flags an innocent one (P7). Its
  floor holds only where `f` is unpredictable, which is a scope condition, not
  a general property.
"""
io.open("README.md", "w", encoding="utf-8").write(rd.replace(anchor, bullet + anchor))
print("README.md patched")
print("\nreview with: git diff --stat")
