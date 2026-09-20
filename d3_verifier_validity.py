#!/usr/bin/env python3
"""
D3 -- Dynamic Verifier Validity / Monitor Expiration
veritas-eval-harness

Question
--------
An object-level verifier V is valid at t0. After a controlled environment
transition, can a meta-verifier M discriminate "V still valid" from
"V expired", and what does that discrimination COST in labels?

This is the temporal case of the vacuity finding:
    static vacuity   : G cannot discriminate from inception
    temporal vacuity : G discriminates at t0, loses that power by t1

No LLM. No NumPy. No GPU. Stdlib only (matches harness CI, py3.11-3.14).

WHAT BROKE IN v1 -- kept, per method
------------------------------------
(1) NONDETERMINISM IN MY OWN GATE. v1 seeded a QUAL-2 RNG with
    `hash(name) % 1000`. Python randomises str hashing per process, so two
    runs at the SAME --seed produced different QUAL-2 numbers. This is the
    same defect class as quasar's unseeded global RNG: a gate whose verdict
    is redrawn every run. Fixed here by indexing the arm, not hashing it.
    Detected by diffing two same-seed runs, not by reading the code.

(2) THE SCALING CLAIM WAS REFUTED BY A SEED SWEEP. v1 registered
    k* ~ delta^-2 and printed CONSISTENT (slope -2.063) at one seed. Across
    four seeds the slope came out -2.063, -1.365, -1.152, -1.437. The single
    -2.063 was a coin flip. Two causes, both instrument defects rather than
    facts about the world:
      (a) k* was quantised to powers of two -- one octave of resolution;
      (b) the smallest break was CEILING-PINNED at the oracle budget in every
          seed, and right-censoring the large-k* end flattens a fitted slope
          toward zero.
    v2 widens the break range below q=0.5 (assumption inverted, still
    marginal-preserving), refines the k grid to ~1.5x steps, and evaluates
    the slope over a seed ENSEMBLE with QUAL-5 as a stability gate. The
    v1 refutation stands as history; it is not deleted.

(3) A REGISTERED PREDICTION WITH NO FAIL PATH. v2 shipped "P1: M2 exceeds
    the input-only comparator". In this generator the break is
    marginal-preserving, so M0 and M1 are blind BEFORE a single item is
    drawn. P1 as written could not fail -- a vacuous prediction inside the
    harness built to hunt vacuity. Third instance in this one build, after
    (1) and (2). It is RETIRED into QUAL-1/QUAL-3 as an ENTAILED property
    rather than deleted, and P1..P3 are renumbered below. The M0/M1
    separation is a design choice being reported, not a finding.

    Consequence for how this is described: the load-bearing result is the
    SHAPE of the frontier (P1, P3), which could have come out otherwise.
    It is not the separation, which could not.

NO NOVELTY IS CLAIMED. Label-efficient detection of model degradation is an
established line in the drift literature; the supervised-vs-unsupervised
cost tradeoff has been priced before. What is instrumented here is narrower:
the validity of a VERIFIER as a time-varying measurable property, with the
audit budget as the explicit axis.

Exit codes
----------
0  all qualification gates passed, results reported
1  a qualification gate FAILED (instrument not trustworthy; no claim)
2  could not run

Usage
-----
  python3 d3_verifier_validity.py
  python3 d3_verifier_validity.py --seed 20260919 --seeds 5
  python3 d3_verifier_validity.py --sabotage     # must exit 1
"""

import argparse
import hashlib
import json
import math
import random
import sys
import time

# ---------------------------------------------------------------------------
# PREREGISTRATION -- FROZEN GRID
# s, k, thresholds and tolerances are fixed HERE, before any validity run.
# The sha256 below changes if any of them is touched, so post-hoc tuning
# shows up in the output instead of being invisible.
# ---------------------------------------------------------------------------

PREREG = {
    "version": "D3-v2",
    "m_proxies": 5,
    "n_nuisance": 2,
    "q0": 0.90,
    "broken_index": 2,
    # s-axis. Below 0.5 the assumption is INVERTED, not merely decoupled.
    # Marginals are preserved at every value (see draw_labeled docstring).
    "q_post_expired": [0.70, 0.60, 0.50, 0.35, 0.20, 0.05],
    "p_nuisance_0": 0.50,
    "p_nuisance_surface": 0.15,
    "k_grid": [8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768,
               1024, 1536],
    "k_oracle": 2048,
    "n_unlabeled_M1": 800,
    "trials": 40,
    "n_seeds": 5,
    "z_decision": 1.645,
    "z_drift": 1.960,
    "eps_target": 0.10,
    "qual1_M0_band": [0.45, 0.55],
    "qual2_passrate_band": [0.48, 0.52],
    "qual2_acc_tol": 0.02,
    "qual3_M1_band": [0.45, 0.55],
    "qual3_M1_surface_min": 0.80,
    "qual4_oracle_min": 0.95,
    "qual5_slope_range_max": 0.60,   # across-seed spread of the slope estimate
    "slope_predicted": -2.0,
    "slope_band": 0.60,
    "diag_chance": 0.20,
}

PREREG_HASH = hashlib.sha256(
    json.dumps(PREREG, sort_keys=True).encode()
).hexdigest()[:12]

# ---------------------------------------------------------------------------
# REPORTING LAYER -- deliberately NOT part of PREREG_HASH.
#
# The frozen experimental grid above is unchanged from the run replicated on
# device at prereg e50c8d96d882. Folding claim labels or the diagnosis grid
# into that dict would change the hash and break the link to that run, so the
# reporting layer carries its own hash. At the next grid revision the two
# merge. DIAG_GRID does not perturb existing numbers: M2_diagnose is seeded
# per (seed, trial, k), so adding k values leaves k=64/256/2048 identical.
# ---------------------------------------------------------------------------

CLAIMS = {
    "QUAL-1": "M0 floor. A_M0 ~ 0.50 is ENTAILED by marginal preservation, "
              "not measured. Out of band => generator broken.",
    "QUAL-2": "t0 operating-characteristic (ROC) equivalence across arms.",
    "QUAL-3": "M1 comparator. A_M1 ~ 0.50 is ENTAILED. The SURFACE fire rate "
              "is the live part: it proves M1 is not inert.",
    "QUAL-4": "Oracle ceiling. The break must be separable at k_oracle.",
    "QUAL-5": "Across-seed stability of the exponent estimate.",
    "P1": "k*(eps,s) is finite for every s and strictly decreasing in delta.",
    "P2": "Assumption diagnosis exceeds chance; report k at saturation.",
    "P3": "Exponent of k* ~ delta^b is -2 +/- 0.6.",
    "P4": "UNRUN. Does k*(eps,s) survive an audit policy the adversary can "
          "predict? Uniform sampling is assumed everywhere above.",
    "RETIRED": "v2's P1 ('M2 exceeds the input-only comparator') had no fail "
               "path in this generator. Retired into QUAL-1/QUAL-3.",
}
DIAG_GRID = [8, 16, 32, 64, 256, PREREG["k_oracle"]]
DIAG_SATURATION = 0.95

REPORT_HASH = hashlib.sha256(
    json.dumps({"claims": CLAIMS, "diag": DIAG_GRID, "sat": DIAG_SATURATION},
               sort_keys=True).encode()
).hexdigest()[:12]

#   name        valid   nuisance shifts   assumption breaks
ARMS = [
    ("STABLE",   True,  False, False),
    ("SURFACE",  True,  True,  False),
    ("VALIDITY", False, False, True),
    ("COUPLED",  False, True,  True),
]


# ---------------------------------------------------------------------------
# Generator. Ground-truth validity is known exactly because we own it.
# ---------------------------------------------------------------------------

def draw_labeled(rng, n, q):
    """n items -> (proxies, y, v).

    latents L_j ~ Bern(0.5) iid, UNOBSERVABLE
    truth    y   = 1 iff sum(L) >= 3        (balanced by symmetry)
    proxy    P_j = L_j w.p. q[j] else 1-L_j (the verifier's assumption)
    verdict  v   = 1 iff sum(P) >= 3        (V is frozen; it sees only P)

    MARGINAL PRESERVATION. P(P_j=1) = 0.5q + 0.5(1-q) = 0.5 for ANY q, and
    the P_j remain mutually independent because the latents are. So breaking
    -- or inverting -- an assumption moves no observable marginal and no
    observable pairwise correlation. V's own pass rate is likewise pinned at
    0.5 throughout. That is what makes the break invisible without labels,
    BY CONSTRUCTION. See LIMITATION 1 in the footer: this decorrelation is a
    design choice, not a fact about real deployments.
    """
    m = len(q)
    half = m // 2 + 1
    P, Y, V = [], [], []
    r = rng.random
    for _ in range(n):
        lat = [1 if r() < 0.5 else 0 for _ in range(m)]
        y = 1 if sum(lat) >= half else 0
        px = [lat[j] if r() < q[j] else 1 - lat[j] for j in range(m)]
        v = 1 if sum(px) >= half else 0
        P.append(px); Y.append(y); V.append(v)
    return P, Y, V


def draw_observable(rng, n, q, p_nuis):
    """Unlabeled observables only: m proxy marginals + nuisance marginals."""
    m = len(q)
    nn = PREREG["n_nuisance"]
    cols = [0] * (m + nn)
    r = rng.random
    for _ in range(n):
        for j in range(m):
            lat = 1 if r() < 0.5 else 0
            cols[j] += lat if r() < q[j] else 1 - lat
        for t in range(nn):
            cols[m + t] += 1 if r() < p_nuis else 0
    return [c / n for c in cols]


def q_vector(q_broken, broken):
    q = [PREREG["q0"]] * PREREG["m_proxies"]
    if broken:
        q[PREREG["broken_index"]] = q_broken
    return q


# ---------------------------------------------------------------------------
# Meta-verifiers
# ---------------------------------------------------------------------------

def M0_decide(rng, q_pre, q_post, n=800):
    """M0: V's PASS/FAIL stream only. No inputs, no labels. Zero-cost floor."""
    _, _, v0 = draw_labeled(rng, n, q_pre)
    _, _, v1 = draw_labeled(rng, n, q_post)
    se = math.sqrt(2 * 0.25 / n)
    return abs(sum(v0) / n - sum(v1) / n) > PREREG["z_drift"] * se


def M1_decide(rng, q_pre, q_post, p_pre, p_post):
    """M1: + unlabeled inputs. Two-proportion drift test on every observable
    feature, multiplicity-corrected. Still no labels. This is the comparator."""
    n = PREREG["n_unlabeled_M1"]
    a = draw_observable(rng, n, q_pre, p_pre)
    b = draw_observable(rng, n, q_post, p_post)
    d = len(a)
    z_corr = PREREG["z_drift"] * math.sqrt(1 + math.log(d))
    se = math.sqrt(2 * 0.25 / n)
    return any(abs(a[i] - b[i]) > z_corr * se for i in range(d))


def M2_curve(rng, q_pre, q_post, ks):
    """M2: labeled audit budget k per window, evaluated for every k in ks.

    One oracle-sized window is drawn per side and each k is scored on its
    PREFIX. Nested subsamples, so A_M(k) is correlated across k within a
    trial -- deliberate: it removes draw-to-draw noise from the SHAPE of the
    curve, which is what the k* slope fit depends on.
    """
    kmax = max(ks)
    _, y0, v0 = draw_labeled(rng, kmax, q_pre)
    _, y1, v1 = draw_labeled(rng, kmax, q_post)
    c0 = c1 = 0
    out, acc_post = [], None
    prev = 0
    for k in sorted(ks):
        for i in range(prev, k):
            c0 += (y0[i] == v0[i])
            c1 += (y1[i] == v1[i])
        prev = k
        a0, a1 = c0 / k, c1 / k
        tau = PREREG["z_decision"] * math.sqrt(2 * 0.25 / k)
        out.append((k, (a0 - a1) > tau))
        acc_post = a1
    return out, acc_post


def M2_diagnose(rng, q_post, k):
    """Which assumption moved? Leave-one-out: drop proxy j from the vote and
    see whose removal most improves agreement with truth on audited items."""
    m = PREREG["m_proxies"]
    half = m // 2 + 1
    P, Y, _ = draw_labeled(rng, k, q_post)
    base = sum(1 for i in range(k) if Y[i] == (1 if sum(P[i]) >= half else 0))
    best_j, best_gain = -1, -2.0
    for j in range(m):
        hit = 0
        for i in range(k):
            s = sum(P[i]) - P[i][j]
            hit += 1 if Y[i] == (1 if s >= half else 0) else 0
        g = (hit - base) / k
        if g > best_gain:
            best_gain, best_j = g, j
    return best_j


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def lsq_slope(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / den


# ---------------------------------------------------------------------------
# One seed
# ---------------------------------------------------------------------------

def run_seed(seed, q_levels, ks, T):
    q0 = PREREG["q0"]
    p0, ps = PREREG["p_nuisance_0"], PREREG["p_nuisance_surface"]
    res = {}

    r = random.Random(seed)
    _, y, v = draw_labeled(r, 20000, q_vector(q0, False))
    res["acc0"] = sum(1 for i in range(len(y)) if y[i] == v[i]) / len(y)
    res["pass0"] = sum(v) / len(v)
    res["base_y"] = sum(y) / len(y)

    # QUAL-2: arm indexed, NOT hashed (v1 defect)
    res["qual2"] = []
    for ai, (name, _v, _n, _b) in enumerate(ARMS):
        rr = random.Random(seed + 991 + ai)
        _, yy, vv = draw_labeled(rr, 8000, q_vector(q0, False))
        a = sum(1 for i in range(len(yy)) if yy[i] == vv[i]) / len(yy)
        res["qual2"].append((name, a, sum(vv) / len(vv)))

    m0 = [0, 0, 0, 0]   # tn, n_neg, tp, n_pos
    m1 = [0, 0, 0, 0]
    surf_fire = surf_n = 0
    for ti in range(T):
        for qi, qp in enumerate(q_levels):
            for ai, (name, valid, nz, brk) in enumerate(ARMS):
                qpre, qpost = q_vector(q0, False), q_vector(qp, brk)
                ppost = ps if nz else p0
                d0 = M0_decide(random.Random(seed + 7_000_000 + ti * 977 + qi * 31 + ai),
                               qpre, qpost)
                d1 = M1_decide(random.Random(seed + 8_000_000 + ti * 977 + qi * 31 + ai),
                               qpre, qpost, p0, ppost)
                if valid:
                    m0[1] += 1; m0[0] += (not d0)
                    m1[1] += 1; m1[0] += (not d1)
                else:
                    m0[3] += 1; m0[2] += d0
                    m1[3] += 1; m1[2] += d1
                if name == "SURFACE":
                    surf_n += 1; surf_fire += d1
    res["A_M0"] = 0.5 * (m0[0] / m0[1] + m0[2] / m0[3])
    res["A_M1"] = 0.5 * (m1[0] / m1[1] + m1[2] / m1[3])
    res["M0_n"] = m0[1] + m0[3]
    res["surf_fire"] = surf_fire / surf_n

    res["curve"] = {}
    res["s_meas"] = {}
    for qi, qp in enumerate(q_levels):
        tn = [0] * len(ks); tp = [0] * len(ks)
        n_neg = n_pos = 0
        s_sum = 0.0; s_cnt = 0
        for ti in range(T):
            for ai, (_n, valid, _z, brk) in enumerate(ARMS):
                rr = random.Random(seed + 3_000_000 + ti * 8191 + qi * 131 + ai)
                pts, a1 = M2_curve(rr, q_vector(q0, False), q_vector(qp, brk), ks)
                if valid:
                    n_neg += 1
                    for i, (_k, d) in enumerate(pts):
                        tn[i] += (not d)
                else:
                    n_pos += 1
                    s_sum += a1; s_cnt += 1
                    for i, (_k, d) in enumerate(pts):
                        tp[i] += d
        res["curve"][qp] = [0.5 * (tn[i] / n_neg + tp[i] / n_pos)
                            for i in range(len(ks))]
        res["s_meas"][qp] = s_sum / s_cnt

    target = 1 - PREREG["eps_target"]
    res["kstar"] = {}
    for qp in q_levels:
        res["kstar"][qp] = next(
            (k for k, a in zip(ks, res["curve"][qp]) if a >= target), None)

    xs, ys, cens = [], [], 0
    for qp in q_levels:
        ks_ = res["kstar"][qp]
        delta = res["acc0"] - res["s_meas"][qp]
        if ks_ is None or ks_ >= PREREG["k_oracle"] or delta <= 0:
            cens += 1
            continue
        xs.append(math.log(delta)); ys.append(math.log(ks_))
    res["slope"] = lsq_slope(xs, ys)
    res["n_fit"] = len(xs)
    res["censored"] = cens

    res["diag"] = {}
    for k in DIAG_GRID:
        hit = 0
        for ti in range(T):
            rr = random.Random(seed + 5_000_000 + ti * 613 + k)
            hit += (M2_diagnose(rr, q_vector(q_levels[-1], True), k)
                    == PREREG["broken_index"])
        res["diag"][k] = (hit, T)
    return res


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260919)
    ap.add_argument("--seeds", type=int, default=PREREG["n_seeds"])
    ap.add_argument("--trials", type=int, default=PREREG["trials"])
    ap.add_argument("--sabotage", action="store_true",
                    help="neuter the validity shift; QUAL-4 must fail, exit 1")
    args = ap.parse_args()

    t0 = time.time()
    ks = PREREG["k_grid"] + [PREREG["k_oracle"]]
    q_levels = PREREG["q_post_expired"]
    if args.sabotage:
        q_levels = [PREREG["q0"]] * len(q_levels)
    seeds = [args.seed + 10007 * i for i in range(args.seeds)]

    print("=" * 74)
    print("D3 -- DYNAMIC VERIFIER VALIDITY / MONITOR EXPIRATION")
    print("veritas-eval-harness | stdlib only | deterministic")
    print("=" * 74)
    print(f"base seed       : {args.seed}   ensemble: {seeds}")
    print(f"prereg sha256/12: {PREREG_HASH}   (frozen grid)")
    print(f"report sha256/12: {REPORT_HASH}   (claim map + diag grid)")
    print(f"python          : {sys.version.split()[0]}  platform={sys.platform}")
    print(f"sabotage        : {args.sabotage}   trials/config: {args.trials}")
    print()
    print("-- CLAIM MAP " + "-" * 61)
    for cid in ("QUAL-1", "QUAL-2", "QUAL-3", "QUAL-4", "QUAL-5",
                "P1", "P2", "P3", "P4", "RETIRED"):
        body = CLAIMS[cid]
        print(f"  {cid:8s} {body[:60]}")
        for i in range(60, len(body), 60):
            print(f"  {'':8s} {body[i:i+60]}")
    print()

    R = [run_seed(s, q_levels, ks, args.trials) for s in seeds]
    fails = []

    print("-- t0 CHARACTERIZATION " + "-" * 51)
    print(f"  V accuracy at t0 : {sum(r['acc0'] for r in R)/len(R):.4f}")
    print(f"  V pass rate      : {sum(r['pass0'] for r in R)/len(R):.4f}"
          f"   EXPECTED 0.5000")
    print(f"  base rate of y   : {sum(r['base_y'] for r in R)/len(R):.4f}"
          f"   EXPECTED 0.5000")
    print()

    print("-- QUAL-2  t0 OPERATING-CHARACTERISTIC MATCH " + "-" * 29)
    lo, hi = PREREG["qual2_passrate_band"]
    ok2 = True
    for ai, (name, _v, _n, _b) in enumerate(ARMS):
        a = sum(r["qual2"][ai][1] for r in R) / len(R)
        p = sum(r["qual2"][ai][2] for r in R) / len(R)
        good = lo <= p <= hi
        ok2 &= good
        print(f"  {name:9s} acc={a:.4f}  pass={p:.4f}  "
              f"EXPECTED pass 0.5000 [{lo:.2f},{hi:.2f}]  {'OK' if good else 'FAIL'}")
    accs = [sum(r["qual2"][ai][1] for r in R) / len(R) for ai in range(len(ARMS))]
    spread = max(accs) - min(accs)
    good = spread <= PREREG["qual2_acc_tol"]
    ok2 &= good
    print(f"  ROC-equivalence spread = {spread:.4f}  tol={PREREG['qual2_acc_tol']:.4f}"
          f"  {'OK' if good else 'FAIL'}")
    if not ok2:
        fails.append("QUAL-2")
    print()

    print("-- QUAL-1  M0 FLOOR (verdict stream only, zero cost) " + "-" * 21)
    A0 = sum(r["A_M0"] for r in R) / len(R)
    n0 = sum(r["M0_n"] for r in R)
    lo, hi = PREREG["qual1_M0_band"]
    ci = wilson(round(A0 * n0), n0)
    good = lo <= A0 <= hi
    if not good:
        fails.append("QUAL-1")
    print(f"  A_M0 = {A0:.4f}  95% [{ci[0]:.4f},{ci[1]:.4f}]  "
          f"EXPECTED 0.5000 [{lo:.2f},{hi:.2f}]  {'OK' if good else 'FAIL'}")
    print("  [ENTAILED, NOT MEASURED] marginal preservation makes M0 blind")
    print("  BY CONSTRUCTION. Out of band means the GENERATOR is broken. This")
    print("  is a design property being reported, never a result.")
    print()

    print("-- QUAL-3  M1 COMPARATOR (free unlabeled inputs) " + "-" * 25)
    A1 = sum(r["A_M1"] for r in R) / len(R)
    fire = sum(r["surf_fire"] for r in R) / len(R)
    lo, hi = PREREG["qual3_M1_band"]
    gb, gf = lo <= A1 <= hi, fire >= PREREG["qual3_M1_surface_min"]
    if not (gb and gf):
        fails.append("QUAL-3")
    print(f"  A_M1 = {A1:.4f}  EXPECTED 0.5000 [{lo:.2f},{hi:.2f}]  "
          f"{'OK' if gb else 'FAIL'}")
    print(f"  M1 fire rate on SURFACE = {fire:.4f}  min="
          f"{PREREG['qual3_M1_surface_min']:.2f}  {'OK' if gf else 'FAIL'}")
    print("  [ENTAILED, NOT MEASURED] A_M1 ~ 0.50 follows from the same")
    print("  marginal preservation. The LIVE half is the fire rate: an M1")
    print("  that never fired would also score 0.50 and mean nothing.")
    print()

    print("-- P1  AUDIT-COST FRONTIER (ensemble mean) " + "-" * 31)
    print("  A_M = balanced accuracy, valid V vs expired V")
    print("  q_post  s_meas " + "".join(f"{k:>6d}" for k in ks) + "   k*(0.10)")
    kstars, deltas = [], []
    acc0_mean = sum(r["acc0"] for r in R) / len(R)
    for qp in q_levels:
        curve = [sum(r["curve"][qp][i] for r in R) / len(R) for i in range(len(ks))]
        sm = sum(r["s_meas"][qp] for r in R) / len(R)
        tgt = 1 - PREREG["eps_target"]
        kk = next((k for k, a in zip(ks, curve) if a >= tgt), None)
        kstars.append(kk); deltas.append(acc0_mean - sm)
        print(f"  {qp:5.2f}   {sm:.4f} " + "".join(f"{a:6.2f}" for a in curve)
              + f"   {kk if kk is not None else '>'+str(PREREG['k_oracle'])}")
    finite = all(k is not None and k < PREREG["k_oracle"] for k in kstars)
    mono = all(kstars[i] > kstars[i + 1] for i in range(len(kstars) - 1)
               if kstars[i] is not None and kstars[i + 1] is not None)
    p1 = finite and mono
    print(f"  P1  finite for every s: {'yes' if finite else 'NO'}"
          f"   strictly decreasing in delta: {'yes' if mono else 'NO'}"
          f"   -> {'CONFIRMED' if p1 else 'REFUTED'}")
    print("  (v1 REFUTED this: k* was ceiling-pinned, so finite failed)")
    print()

    print("-- QUAL-4  ORACLE CEILING " + "-" * 48)
    orc = sum(r["curve"][q_levels[-1]][-1] for r in R) / len(R)
    good = orc >= PREREG["qual4_oracle_min"]
    if not good:
        fails.append("QUAL-4")
    print(f"  A_M2 at k={PREREG['k_oracle']}, q_post={q_levels[-1]:.2f} = {orc:.4f}"
          f"  min={PREREG['qual4_oracle_min']:.2f}  {'OK' if good else 'FAIL'}")
    print("  if the oracle cannot separate them the break is too weak and")
    print("  every A_M above is uninterpretable")
    print()

    print("-- QUAL-5 (stability) + P3 (exponent of k* ~ delta^b) " + "-" * 20)
    slopes = [r["slope"] for r in R if r["slope"] is not None]
    cens = sum(r["censored"] for r in R)
    for i, r in enumerate(R):
        print(f"  seed {seeds[i]:>9d}  slope="
              f"{('%+.3f' % r['slope']) if r['slope'] is not None else '  n/a '}"
              f"  n_fit={r['n_fit']}  censored={r['censored']}")
    if len(slopes) < 2:
        fails.append("QUAL-5")
        print("  QUAL-5 FAIL: fewer than two usable slope estimates")
    else:
        rng_ = max(slopes) - min(slopes)
        mean = sum(slopes) / len(slopes)
        stab = rng_ <= PREREG["qual5_slope_range_max"]
        if not stab:
            fails.append("QUAL-5")
        print(f"  slope mean = {mean:+.3f}   across-seed range = {rng_:.3f}"
              f"   max={PREREG['qual5_slope_range_max']:.2f}"
              f"  {'OK' if stab else 'FAIL'}")
        pred, band = PREREG["slope_predicted"], PREREG["slope_band"]
        inb = abs(mean - pred) <= band
        print(f"  PREDICTED {pred:+.3f} +/- {band:.2f}  ->  "
              f"{'CONSISTENT' if inb else 'REFUTED'}")
        print(f"  right-censored points dropped from fits: {cens}"
              f"  (censoring flattens the slope toward zero)")
    print()

    print("-- P2  ASSUMPTION DIAGNOSIS (which of 5 moved) " + "-" * 27)
    sat = None
    above = None
    for k in DIAG_GRID:
        hit = sum(r["diag"][k][0] for r in R)
        tot = sum(r["diag"][k][1] for r in R)
        p = hit / tot
        ci = wilson(hit, tot)
        is_above = ci[0] > PREREG["diag_chance"]
        if is_above and above is None:
            above = k
        if p >= DIAG_SATURATION and sat is None:
            sat = k
        print(f"  k={k:5d}  top-1={p:.4f}  95% [{ci[0]:.4f},{ci[1]:.4f}]  "
              f"chance={PREREG['diag_chance']:.2f}  "
              f"{'ABOVE' if is_above else 'NOT ABOVE'} chance")
    print(f"  P2  least k above chance = {above}"
          f"   least k at saturation (>= {DIAG_SATURATION:.2f}) = {sat}"
          f"   -> {'CONFIRMED' if above is not None else 'REFUTED'}")
    print()

    print("-- P4  REGISTERED, NOT RUN " + "-" * 47)
    print("  " + CLAIMS["P4"][:66])
    print("  Every k above assumes the auditor samples UNIFORMLY at random.")
    print("  An adversary who knows the audit policy need not defeat M2: it")
    print("  need only keep V accurate on items that will be audited and let")
    print("  the rest rot. The arm is a change to the sampling in M2_curve,")
    print("  not a new experiment. If k* diverges under a predictable policy,")
    print("  the frontier above is an artifact of auditor unpredictability.")
    print("  STATUS: NOT VALIDATED. No number here bears on it.")
    print()

    print("-- LIMITATIONS (registered, not discovered afterwards) " + "-" * 19)
    print("  1. Input change and validity change are DECORRELATED by design.")
    print("     M1's 0.50 ceiling is therefore a property of this generator,")
    print("     not a measured defeat of drift detection. In the wild the two")
    print("     are correlated, which is why input monitoring works at all.")
    print("  2. k* is grid-quantised; the slope inherits that resolution.")
    print("  3. V, the shift, and the label oracle are all synthetic. Nothing")
    print("     here transfers to an LLM verifier without a separate arm.")
    print()

    dt = time.time() - t0
    print("=" * 74)
    print(f"runtime {dt:.1f}s   seeds {seeds}   prereg {PREREG_HASH}")
    if fails:
        print(f"GATE FAILURE: {', '.join(sorted(set(fails)))} -- not qualified.")
        print("No claim is admissible from this run.")
        print("=" * 74)
        return 1
    print("ALL QUALIFICATION GATES PASSED.")
    print("Container numbers only. Not claimable until the aarch64/Termux run")
    print("matches digit-for-digit.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"could not run: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
