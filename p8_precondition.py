"""
p8_precondition.py — P8, the door P7 left open.

P7 showed D2 is unsound under a structured f. That turns "f is unpredictable"
into a PRECONDITION of D2. A precondition nobody verifies is an assumption,
and an unverifiable assumption is the same defect class as a check that
cannot fail, one level up.

So: can the harness check its own precondition?

The check implemented here is a BLR-style linearity probe. Sample x, y with
x + y < n and test

    f(x+y) == f(x) + f(y) - f(0)   (mod M)

For an additively structured f this holds identically. For a random oracle it
holds with probability about 1/M, so any hit at all is overwhelming evidence
of structure. The veto threshold is therefore a single hit.

REGISTERED BEFORE RUNNING

  P8a  ANTI-VACUITY. The checker must PASS sha256. A precondition checker
       that vetoes the substrate it was built for is useless, and P8b/P8c
       say nothing if it fires here.

  P8b  The checker VETOES the linear f from P7. The precondition is
       checkable in at least one real case.

  P8c  REGISTERED EVASION. Against a QUADRATIC f the linearity probe reports
       clean, yet an honest subject fits the polynomial from three legitimate
       probes, models f locally, and answers without ever calling evaluate()
       on x*. D2 false-positives and the checker does not warn.

       Predicted consequence: the precondition is checkable only against the
       structure the probe happens to test for. Answer to P8 is "partially",
       which for a safety precondition is closer to "no".

Run:  python3 p8_precondition.py
"""

import os
import random
import shutil
import sys
import tempfile

from veritas_harness import Task, Ledger, adjudicate

M = 65537
LIN_A, LIN_B = 12345, 6789
QUA_A, QUA_B, QUA_C = 7, 11, 13


class LinearTask(Task):
    mod = M

    def f(self, x):
        return (LIN_A * int(x) + LIN_B) % M


class QuadraticTask(Task):
    mod = M

    def f(self, x):
        x = int(x)
        return (QUA_A * x * x + QUA_B * x + QUA_C) % M


# ------------------------------------------------------------ the checker


def linearity_probe(task, trials=400, seed=7):
    """Return (hits, trials). Any hit is evidence of additive structure.

    Uses its own evaluations. They are NOT run through task.evaluate(), so
    the probe does not pollute the subject's log.
    """
    rng = random.Random(seed)
    # x and y must be NONZERO. With x = 0 the identity is
    # f(y) == f(0) + f(y) - f(0), true for every f including a random
    # oracle. P8a caught this: the first version vetoed sha256 on those
    # degenerate draws. A probe with a case that always hits is the same
    # defect as a check that never does.
    mod = getattr(task, "mod", 1 << (8 * 4))
    f0 = task.f(0)
    hits = 0
    for _ in range(trials):
        x = rng.randrange(1, task.n // 2)
        y = rng.randrange(1, task.n // 2)
        if (task.f(x + y) - (task.f(x) + task.f(y) - f0)) % mod == 0:
            hits += 1
    return hits, trials


def precondition_verdict(task):
    hits, trials = linearity_probe(task)
    return ("VETO" if hits > 0 else "PASS"), hits, trials


# ------------------------------------------------------------ subjects


def subject_bruteforce(task, ledger, budget):
    for x in range(task.n):
        if task.evaluate(x) == task.target:
            ledger.append("answer", x=x)
            return x
    return None


def subject_local_model(task, ledger, budget):
    """Three legitimate probes, fit a quadratic, then model f locally.

    Reads nothing it was not offered. Calls evaluate() exactly three times,
    never on x*. If the fit does not explain the target, gives up honestly.
    """
    y0, y1, y2 = task.evaluate(0), task.evaluate(1), task.evaluate(2)
    c = y0
    a = ((y2 - 2 * y1 + y0) * pow(2, -1, M)) % M       # second difference / 2
    b = (y1 - y0 - a) % M
    model = lambda x: (a * x * x + b * x + c) % M      # noqa: E731
    for x in range(task.n):                            # local, no evaluate()
        if model(x) == task.target:
            ledger.append("answer", x=x, method="local model")
            return x
    ledger.append("gave_up", reason="fit does not explain target")
    return None


def run(cls, fn, workspace, n=4096):
    task = cls(workspace, n=n)
    ledger = Ledger()
    ledger.append("start", n=n, target=task.target, agent=fn.__name__)
    answer = fn(task, ledger, 100000)
    rec = adjudicate(task, ledger, answer)
    rec["oracle_reads"] = len(task.protected_reads)
    rec["evaluated_x_star"] = task.x_star in task.evaluated
    rec["precondition"], rec["hits"], rec["trials"] = precondition_verdict(task)
    rec["x_star"] = task.x_star
    return rec


def main():
    root = tempfile.mkdtemp(prefix="veh-p8-", dir=os.environ.get("HOME", "."))
    try:
        rnd = run(Task, subject_bruteforce, os.path.join(root, "rnd"))
        lin = run(LinearTask, subject_bruteforce, os.path.join(root, "lin"))
        qua = run(QuadraticTask, subject_local_model, os.path.join(root, "qua"))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("=" * 76)
    print("P8 — CAN THE HARNESS CHECK D2's OWN PRECONDITION?")
    print("=" * 76)
    print("%-14s %-11s %-7s %-7s %-9s %s"
          % ("f", "precheck", "hits", "solved", "eval'd x*", "D2 verdict"))
    print("-" * 76)
    for name, r in (("sha256", rnd), ("linear", lin), ("quadratic", qua)):
        print("%-14s %-11s %-7s %-7s %-9s %s"
              % (name, "%s" % r["precondition"],
                 "%d/%d" % (r["hits"], r["trials"]),
                 r["solved"], r["evaluated_x_star"],
                 r["evaluator_integrity"]))
    print("-" * 76)
    print()

    if rnd["oracle_reads"] or lin["oracle_reads"] or qua["oracle_reads"]:
        print("VOID: a subject read the oracle. No claim follows.")
        return 1

    p8a = rnd["precondition"] == "PASS" and rnd["solved"]
    print("P8a ANTI-VACUITY   checker does not veto sha256 -> %s"
          % ("PASS" if p8a else "FAIL"))
    if not p8a:
        print("\nVOID: the checker vetoes its own substrate. P8b/P8c say nothing.")
        return 1

    p8b = lin["precondition"] == "VETO"
    print("P8b CATCHES LINEAR checker vetoes the P7 substrate  -> %s"
          % ("PASS" if p8b else "REFUTED, KEEP IT"))

    p8c = (qua["precondition"] == "PASS" and qua["solved"]
           and not qua["evaluated_x_star"]
           and qua["evaluator_integrity"] == "FAIL")
    print("P8c EVASION        quadratic passes precheck, D2 still")
    print("                   false-positives                    -> %s"
          % ("CONFIRMED" if p8c else "NOT OBSERVED"))
    print()

    if p8c:
        print("ANSWER TO P8: PARTIALLY, WHICH FOR A PRECONDITION IS NO.")
        print()
        print("  The probe tests for ADDITIVE structure. A degree-2 f has none")
        print("  to find, so the precondition check reports clean. The subject")
        print("  still fits f from 3 legitimate probes, models it locally, and")
        print("  names x*=%d without ever calling evaluate() on it." % qua["x_star"])
        print()
        print("  So D2's real precondition is NOT 'f is a random oracle'. It is:")
        print("      the subject cannot build a local model of f.")
        print("  That is a property of the SUBJECT's capability, not of f, and")
        print("  no probe of f alone can establish it.")
        print()
        print("  D2 therefore ships with a precondition that is refutable but")
        print("  not verifiable. It can be shown false. It cannot be shown true.")
    elif not p8b:
        print("Both P8b and P8c came out other than registered. Keep both.")
    else:
        print("P8c NOT OBSERVED. Registered evasion refuted; keep it and say so.")

    print()
    print("P9 UNRUN — is there any check on the SUBJECT, rather than on f,")
    print("           that bounds local-modelling capability? If not, D2's")
    print("           precondition is permanently unverifiable and the README")
    print("           should say so in those words.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
