# D3 — Dynamic Verifier Validity / Monitor Expiration

**Status:** instrument QUALIFIED. P1/P2/P3 confirmed on the deterministic
generator and replicated cross-architecture. **P4 registered, NOT RUN.**

**Frozen grid:** `prereg sha256/12 = e50c8d96d882`
**Reporting layer:** `report sha256/12 = 7fe45bed2096`

Reference code: `d3_verifier_validity.py` (stdlib only, py3.11–3.14).

---

## Failures first

Three defects were introduced by the author of this arm and are kept.

1. **Nondeterministic gate.** v1 seeded a QUAL-2 RNG with `hash(name) % 1000`.
   Python randomises `str` hashing per process, so two runs at the same
   `--seed` produced different QUAL-2 numbers. Same class as the quasar
   unseeded-RNG finding: a gate whose verdict is redrawn every run. Found by
   diffing two same-seed runs, not by reading the code.

2. **A registered claim confirmed by a coin flip.** v1 registered
   `k* ~ delta^-2` and printed CONSISTENT at slope −2.063 on one seed. Four
   seeds gave −2.063, −1.365, −1.152, −1.437. Causes were instrumental, not
   factual: `k*` quantised to powers of two, and the smallest break was
   right-censored at the oracle budget in every seed. Censoring the large-`k*`
   end flattens a fitted slope toward zero. Fixed by a ~1.5× `k` grid, breaks
   extended below `q=0.5` (assumption inverted, still marginal-preserving),
   and a seed ensemble with QUAL-5 as a stability gate.

3. **A registered prediction with no fail path.** v2 shipped
   *"P1: M2 exceeds the input-only comparator."* The break is
   marginal-preserving, so M0 and M1 are blind before a single item is drawn.
   P1 could not fail — a vacuous prediction inside the harness built to hunt
   vacuity. **Retired** into QUAL-1/QUAL-3 as an ENTAILED property; claims
   renumbered. The M0/M1 separation is a design choice being reported, never
   a finding.

---

## No novelty claimed

Label-efficient detection of model degradation is an established line in the
concept-drift literature, and the supervised-vs-unsupervised cost tradeoff has
been priced before. What is instrumented here is narrower: the validity of a
**verifier** as a time-varying measurable property, with the **audit budget**
as the explicit axis.

Relation to prior work in this estate: `vacuity_lint.py` detects **static**
vacuity — a gate that cannot discriminate from inception. D3 addresses
**temporal** vacuity — a gate that discriminates at t₀ and has lost that power
by t₁. Static vacuity is detectable from source; temporal vacuity is not.

---

## Construction

Latents `L_j ~ Bern(0.5)`, j = 0..4, unobservable.
Truth `y = 1 iff sum(L) >= 3`.
Proxy `P_j = L_j` w.p. `q_j`, else `1 − L_j`. Observable.
Verifier `V = 1 iff sum(P) >= 3`. Frozen at t₀; sees only proxies.
Plus two nuisance features `V` does not use.

`q_j = 0.90` for all j at t₀. The validity shift moves `q_2` only.

**Marginal preservation.** `P(P_j = 1) = 0.5q + 0.5(1−q) = 0.5` for any `q`,
and the proxies stay mutually independent. Breaking — or inverting — an
assumption moves no observable marginal and no observable pairwise
correlation. `V`'s own pass rate is pinned at 0.5 throughout.

### Arms

| Arm | V valid at t₁ | nuisance shifts | assumption breaks |
|---|---|---|---|
| STABLE | yes | no | no |
| SURFACE | yes | **yes** | no |
| VALIDITY | **no** | no | **yes** |
| COUPLED | **no** | **yes** | **yes** |

SURFACE is the anti-vacuity control: an always-abstain monitor fails it.

### Monitors

| | information set |
|---|---|
| M0 | V's PASS/FAIL stream only. Zero cost. |
| M1 | + unlabeled inputs. Multiplicity-corrected drift test on every observable. **Comparator.** |
| M2 | + labeled audit budget `k` per window. |
| M3 | M2 at `k = k_oracle`. Ceiling. |

---

## Claims

| ID | Claim | Status |
|---|---|---|
| QUAL-1 | `A_M0 ≈ 0.50`. **ENTAILED**, not measured. Out of band ⇒ generator broken. | PASS |
| QUAL-2 | t₀ ROC equivalence across arms within tolerance. | PASS |
| QUAL-3 | `A_M1 ≈ 0.50` **ENTAILED**; SURFACE fire rate is the live half. | PASS |
| QUAL-4 | Oracle separates the largest break. | PASS |
| QUAL-5 | Across-seed stability of the exponent estimate. | PASS |
| P1 | `k*(ε,s)` finite for every `s` and strictly decreasing in `delta`. | CONFIRMED |
| P2 | Diagnosis exceeds chance; report `k` at saturation. | CONFIRMED |
| P3 | Exponent of `k* ~ delta^b` is −2 ± 0.6. | CONSISTENT |
| **P4** | **Does `k*(ε,s)` survive an audit policy the adversary can predict?** | **NOT RUN** |

---

## Measured — device, aarch64/Termux/py3.14, S25 Ultra

Replicated digit-for-digit against x86_64/py3.12. Runtime 75.2 s vs 26.9 s;
only the runtime line differs.

```
V accuracy at t0      0.8455      pass rate 0.4986      base rate y 0.4995
A_M0                  0.5083      95% [0.4942, 0.5225]
A_M1                  0.5012      SURFACE fire rate 1.0000
oracle A_M2(2048)     0.9875
```

Audit-cost frontier, `k*(ε = 0.10)`:

| q_post | s_meas | delta | k* |
|---|---|---|---|
| 0.70 | 0.7929 | 0.0526 | 1536 |
| 0.60 | 0.7666 | 0.0789 | 512 |
| 0.50 | 0.7404 | 0.1051 | 384 |
| 0.35 | 0.7019 | 0.1436 | 192 |
| 0.20 | 0.6637 | 0.1818 | 96 |
| 0.05 | 0.6244 | 0.2211 | 64 |

Exponent, 5-seed ensemble: −1.823, −2.025, −2.056, −2.102, −1.980.
**mean −1.997, across-seed range 0.279**, zero censored.
Independent base seeds: −1.951, −1.859, −1.867.

Diagnosis (which of five assumptions moved, chance 0.20):

| k | top-1 | 95% |
|---|---|---|
| 8 | 0.5200 | [0.4510, 0.5882] |
| 16 | 0.7600 | [0.6963, 0.8139] |
| 32 | 0.9050 | [0.8564, 0.9383] |
| 64 | 0.9950 | [0.9722, 0.9991] |
| 256 | 1.0000 | [0.9812, 1.0000] |

Least `k` above chance = 8. Least `k` at saturation (≥0.95) = 64.
Diagnosis saturates roughly 6× cheaper than detection at the same break.

### Gate proven both directions

`--sabotage` neuters the validity shift. Observed: QUAL-4 0.5167 FAIL,
QUAL-5 FAIL, P1 REFUTED (not finite), P2 REFUTED (never above chance),
diagnosis 0.185–0.210 against chance 0.20, **exit 1**.

---

## Limitations — registered, not discovered afterwards

1. **Input change and validity change are decorrelated by design.** M1's 0.50
   ceiling is a property of this generator, not a measured defeat of drift
   detection. In deployment the two are correlated, which is why input
   monitoring works at all.
2. `k*` is grid-quantised; the exponent inherits that resolution.
3. `V`, the shift, and the label oracle are all synthetic. Nothing here
   transfers to an LLM verifier without a separate arm.
4. Audit sampling is uniform everywhere above. See P4.

---

## P4 — the open door

Every `k` above assumes the auditor samples uniformly at random. An adversary
who knows the audit policy need not defeat M2: it need only keep `V` accurate
on items that will be audited and let the rest rot. The arm is a change to the
sampling in `M2_curve`, not a new experiment.

If `k*(ε,s)` diverges under a predictable policy, the frontier above is an
artifact of auditor unpredictability rather than a property of the audit
channel. **NOT VALIDATED. No number in this document bears on it.**

---

## Reproduce

```
python3 d3_verifier_validity.py                 # exit 0, ~75 s on device
python3 d3_verifier_validity.py --sabotage      # exit 1
```

Determinism: two runs at the same seed are byte-identical apart from the
runtime line.

Credit: experiment design and reference code by Claude (Anthropic); the
original epistemic-regime-shift framing, the V/M split, the three-arm
anti-vacuity requirement, and the removal of a premature model-comparison
hypothesis came from GPT. Both defects (1) and (3) above are Claude's.

*Vincit Omnia Veritas.*
