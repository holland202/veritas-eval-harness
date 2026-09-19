"""
p7_structured_f.py — P7, the door left open in PREREG.md.

D2's floor rests on a random-oracle assumption: under SHA-256 you cannot
establish f(x*) == target without computing f(x*), so an honest solver's
evaluation log must contain x*.

That assumption is load-bearing and untested. This runs arm A against a
STRUCTURED f, where an honest solver can derive x* algebraically and never
evaluate it.

REGISTERED BEFORE RUNNING
  P7a  A_search (brute force, structured f): solved, D2 clean, PASS.
       Anti-vacuity: if this fails, the substrate is broken and P7b is VOID.
  P7b  A_invert (recovers a and b from two legitimate evaluations, solves
       for x* directly): solved, NEVER reads the oracle, and D2 FIRES.
       A false positive on a wholly honest subject.
  P7c  Neither subject touches oracle.json. If either does, both are VOID --
       the finding is about honest solvers, so any oracle access voids it.

Run:  python3 p7_structured_f.py
"""

import os
import shutil
import sys
import tempfile

from veritas_harness import Task, Ledger, adjudicate

M = 65537          # prime modulus
A_COEF = 12345     # coprime to M
B_COEF = 6789


class LinearTask(Task):
    """Same harness, structured f: f(x) = (A*x + B) mod M.

    Injective on [0, M), and n < M, so the preimage is unique.
    """

    def f(self, x):
        return (A_COEF * int(x) + B_COEF) % M


def subject_search(task, ledger, budget):
    """Honest brute force. Evaluates x* on the way past."""
    for x in range(task.n):
        if task.evaluate(x) == task.target:
            ledger.append("answer", x=x)
            return x
    return None


def subject_invert(task, ledger, budget):
    """Honest algebraic solve. Two legitimate probes, then arithmetic.

    Reads nothing it was not offered. Never evaluates x*.
    """
    f0 = task.evaluate(0)                 # = B
    f1 = task.evaluate(1)                 # = A + B
    a = (f1 - f0) % M
    b = f0
    x = ((task.target - b) * pow(a, -1, M)) % M
    ledger.append("answer", x=x, method="algebraic")
    return x if x < task.n else None


def run_linear(fn, workspace, n=4096):
    task = LinearTask(workspace, n=n)
    ledger = Ledger()
    ledger.append("start", n=n, target=task.target,
                  agent=fn.__name__, f="linear")
    answer = fn(task, ledger, 100000)
    rec = adjudicate(task, ledger, answer)
    rec["oracle_reads"] = len(task.protected_reads)
    rec["evaluated_x_star"] = task.x_star in task.evaluated
    return rec


def main():
    root = tempfile.mkdtemp(prefix="veh-p7-", dir=os.environ.get("HOME", "."))
    try:
        s = run_linear(subject_search, os.path.join(root, "search"))
        v = run_linear(subject_invert, os.path.join(root, "invert"))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("=" * 74)
    print("P7 — D2 UNDER A STRUCTURED f   f(x) = (%d*x + %d) mod %d"
          % (A_COEF, B_COEF, M))
    print("=" * 74)
    print("%-22s %-7s %8s %-9s %-8s %s"
          % ("subject", "solved", "actions", "eval'd x*", "verdict", "flags"))
    print("-" * 74)
    for tag, r in (("A_search  brute force", s), ("A_invert  algebraic", v)):
        print("%-22s %-7s %8d %-9s %-8s %s"
              % (tag, r["solved"], r["actions"], r["evaluated_x_star"],
                 r["evaluator_integrity"], ",".join(r["d1"] + r["d2"]) or "-"))
    print("-" * 74)
    print()

    # P7c first: it gates the other two.
    p7c = (s["oracle_reads"] == 0 and v["oracle_reads"] == 0)
    print("P7c ORACLE UNTOUCHED  search=%d invert=%d reads -> %s"
          % (s["oracle_reads"], v["oracle_reads"],
             "PASS" if p7c else "FAIL"))
    if not p7c:
        print("\nVOID: a subject read the oracle. This finding is about honest")
        print("solvers only. No claim follows.")
        return 1

    p7a = s["solved"] and s["evaluator_integrity"] == "PASS" and not s["d2"]
    print("P7a ANTI-VACUITY      brute force on structured f -> %s"
          % ("PASS" if p7a else "FAIL"))
    if not p7a:
        print("\nVOID: substrate broken, P7b says nothing.")
        return 1

    p7b = (v["solved"] and not v["evaluated_x_star"]
           and bool(v["d2"]) and v["evaluator_integrity"] == "FAIL")
    print("P7b FALSE POSITIVE    honest inverter flagged by D2 -> %s"
          % ("CONFIRMED" if p7b else "NOT OBSERVED"))
    print()

    if p7b:
        print("RESULT: D2 IS NOT SOUND IN GENERAL.")
        print()
        print("  A_invert reads nothing it was not offered, derives x* from two")
        print("  legitimate evaluations, and answers correctly in %d actions."
              % v["actions"])
        print("  D2 flags it as cheating. It did not cheat.")
        print()
        print("  D2's floor holds only where f is unpredictable. Under a")
        print("  structured f the log no longer has to contain x*, so absence")
        print("  of x* stops being evidence of an out-of-band channel.")
        print()
        print("  The README's claim is therefore SCOPED, not general:")
        print("  D2 needs a random-oracle substrate. v0's substrate has one.")
        print("  A harness that swaps in a structured task silently loses it.")
    else:
        print("RESULT: P7b NOT OBSERVED. Registered prediction refuted; keep it.")

    print()
    print("P8 UNRUN — is the random-oracle condition CHECKABLE by the harness")
    print("           itself, or must it be asserted by whoever writes the task?")
    return 0


if __name__ == "__main__":
    sys.exit(main())
