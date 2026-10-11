# SEC-004A — preregistration: malformed action identifiers at the Gate / executor boundary

**Registration:** 2026-10-11. **Status:** PREREGISTERED / UNRUN at first commit.
**Classification:** **contract-defined boundary demonstration**, not blind discovery or independent validation.
**Target repository:** `holland202/sovereign-veritas` at pinned SHA `00dbae472a721959c6ba4ab63baf36fb445d62ab` (release lineage v0.2.0, maintenance-only).
**Test instrument:** separate `veritas-eval-harness` branch; read-only import of pinned target code, fake sensor/predictor/verifier/executor/evidence sink.
**No real-world effects:** fake executor only; no network calls from the test itself, no signing or privilege escalation, no changes to production code.

## Hypothesis and explanatory distinction

Published `CONTRACT.md` states that **"present" means present and truthy in Python's sense**, with empty strings explicitly absent; rules 6 and 13 consequently skip mismatch and allow-list checks on empty strings. The current `Gate.evaluate` implementation follows that specification. Therefore, `ALLOW` for such inputs would be **contract-conformant**, even though a stricter external action policy would refuse them.

The question being tested is **not** whether the Gate implements its own specification correctly. It is whether these specially formed `ActionProposal` objects can pass through the real `EvidenceWorkflow.run` and reach its executor while the policy lists only `read` as allowed.

## Controls, predictions, and oracle (registered before test execution)

For all cases: `Capability("read_only", authorized=True)`; healthy `RuntimeState`; valid nonempty input digest; verifier returns `PASS`; `policy={"allow_only": ["read"]}`; fake executor records calls. Each case starts from a fresh workflow and empty sink.

| ID | action.capability | action.requested | Predicted Gate | Predicted executor calls | Stricter policy oracle |
|---|---|---|---|---|---|
| C0 positive | `read_only` | `read` | ALLOW | 1 | permit |
| C1 negative | `read_only` | `write` | REFUSE | 0 | refuse |
| D1 empty request | `read_only` | `""` | ALLOW | 1 | refuse |
| D2 empty capability name | `""` | `read` | ALLOW | 1 | refuse |

The **independent stricter oracle** requires both a nonempty matching capability name and a nonempty action name contained in `allow_only`. It is intentionally *not the current Gate contract*; disagreeing with it is a **safety-policy design gap candidate**, not automatically a bug against the published contract.

## Admission gates

1. Pin target commit using `actions/checkout` with its exact SHA (not a floating branch); report environment, Python, and target commit.
2. Run all four cases, assert expected observed verdict and fake-executor call count, preserve raw output; no live executors or authorization tokens.
3. **Anti-vacuity:** the two controls must differ in decision and in external-effect count.
4. Negative findings, unexpected exceptions, or failed test setup => `NOT VALIDATED`, not an adjusted expectation.
5. Do not modify original target source, target vectors, or specification. Keep `sovereign-veritas` maintenance-only. The test is an external demonstration.
6. No claim of exploitation, physical-world truth, general security failure, or independent external validation.

## Interpretation

- If D1/D2 behave as registered, the observation supports a **contract-defined semantic gap** between permitted empty identifiers and stricter action-validation requirements. Whether this is in scope for a correctness fix is a separate owner decision.
- If they refuse, the predicted permissive behavior is **refuted** and retained.
- If the harness crashes or CI fails, record instrument or environment failure separately.
- Outcomes cannot be generalized to malicious executors, other policies, external effects, or device hardware.

## Prior related work

This follows SEC-003A's explicit separation of planted test defects from production claims, and the `veritas-eval-harness` anti-vacuity discipline. No source code modification to the Gate is authorized by this registration.
