# SEC-004A — registered demonstration results (2026-10-11)

**Experiment status:** completed once in GitHub Actions (two Python-version legs); **both matched the registered predictions**. This is a **source-entailable, contract-conformant demonstration**, **not independent validation, not exploitation, and not a newly discovered security vulnerability**.

## Frozen reference and preregistration

- Preregistration committed first: `0e2ef5b3a14bc0507957b1f3f56cb924af74197d` — `experiments/SEC-004A_PREREG.md`.
- Probe implementation: `59aaf7dcef029cc13019aad1805a6cf149125451`.
- Workflow as run: `0a2ec7e9b53ef6c75b5aa9c1b5a6dd019d22529a`.
- Target: `holland202/sovereign-veritas` SHA `00dbae472a721959c6ba4ab63baf36fb445d62ab`; verified by `git rev-parse HEAD` before execution.
- Environment: GitHub-hosted Linux x86_64 jobs, Python 3.11.17 and Python 3.14.8. **Not run on the owner's S25 device.**
- Test only used an in-memory executor/sink and synthetic sensor/predictor/verifier fixtures. **External effects: none.**
- Source SHA-256 values and stdout were uploaded as workflow artifacts, not retroactively embedded into the preregistration.

## Primary evidence references

- [Workflow run 38162646707](https://github.com/holland202/veritas-eval-harness/actions/runs/38162646707), two completed successful jobs.
- Python 3.11 job `114538600511`; artifact `sec004a-3.11-1` (ID `11710619215`, archive SHA-256 `2be7ca713879908a81995a6d8e214794c0d7a633d0306906f3cb0927853a64cd`).
- Python 3.14 job `114538600738`; artifact `sec004a-3.14-1` (ID `11710687711`, archive SHA-256 `4f12b88fc69a998d9d8a1f9969d302ca7456379ba0f109d19aad94257f97b669`).

## Observed values — both Python versions

| Case | Requested action | Action capability | Gate | Mock calls | Strict oracle | Registered |
|---|---|---|---|---:|---|---|
| C0 | `read` | `read_only` | ALLOW | 1 | permit | match |
| C1 | `write` | `read_only` | REFUSE (`action_not_permitted_by_policy`) | 0 | refuse | match |
| D1 | `""` | `read_only` | ALLOW | 1 | refuse | match |
| D2 | `read` | `""` | ALLOW | 1 | refuse | match |

Reported end-of-run tags on both jobs:
```text
GATE=SEC004A_REGISTERED_BEHAVIOR_OBSERVED
INTERPRETATION=CONTRACT_DEFINED_DEMONSTRATION_NOT_UNKNOWN_VULNERABILITY
EXTERNAL_EFFECTS=NONE
```

**Anti-vacuity control:** C0 allowed and made one fake call; C1 refused and made zero fake calls. The runner could distinguish at least those behaviors.

## Interpretation and limitations

The published `CONTRACT.md` defines `present` as **truthy in Python's sense**, so empty-string `action.requested` and `action.capability` values do not trigger rules 13 and 6. Accordingly, the observed ALLOW behavior is consistent with the contract and code at the pinned commit.

A stricter independent policy would reject empty action identifiers; the discrepancy is a **normative safety-policy gap candidate** (whether empty identifiers should be rejected), not a measured divergence from the current contract. This is largely predictable from the specification and thus a *demonstration*, not an unknown finding.

- Tests were implemented, registered, and executed within one project; no independent external verification or adversarial review.
- A fake executor recording a call does **not** establish what a production executor or physical system would do.
- Two Python versions ran on GitHub Linux; no Android device result, fault injection, or external side effect.
- No source in `sovereign-veritas` was changed. Its maintenance-only status still applies.
- If the contract is ever tightened, that is a **separate explicit owner decision**, requiring new versioned specification, vectors, independent verifier analysis, and regression tests. Do not change tests or erase these observations retroactively.

**Decision:** `OBSERVATION_RECORDED`; `DEFER_NORMATIVE_CONTRACT_CHANGE`; `NOT_INDEPENDENTLY_VALIDATED`.
