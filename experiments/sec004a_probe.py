#!/usr/bin/env python3
"""SEC-004A registered, fake-executor, contract-boundary demonstration.

Only import source from an explicitly selected Sovereign Veritas checkout.
The test is observational: no real executor, no package signing, no action.
"""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.target_root.resolve()
    if not (root / "sovereign_veritas" / "workflow.py").is_file():
        print("GATE=DEFER_TARGET_MISSING")
        return 2

    sys.path.insert(0, str(root))
    from sovereign_veritas.capability import Capability
    from sovereign_veritas.interfaces.contracts import ActionProposal, Prediction
    from sovereign_veritas.runtime import RuntimeState
    from sovereign_veritas.workflow import EvidenceWorkflow

    class Sensor:
        def observe(self):
            return {"synthetic": True}

    class Predictor:
        def predict(self, observation):
            return Prediction(value="synthetic", uncertainty=0.0, model_id="fixture")

    class Verifier:
        def verify(self, observation, prediction):
            return {"status": "PASS"}

    class Executor:
        def __init__(self):
            self.calls = []
        def execute(self, action):
            self.calls.append(action)
            return {"mock_effect": True}

    class Sink:
        def __init__(self):
            self.records = []
        def record(self, record):
            self.records.append(record)
            return record

    cases = [
        ("C0", "read_only", "read", "ALLOW", 1, True),
        ("C1", "read_only", "write", "REFUSE", 0, False),
        ("D1", "read_only", "", "ALLOW", 1, False),
        ("D2", "", "read", "ALLOW", 1, False),
    ]

    print("EXPERIMENT=SEC-004A")
    print("PHASE=PINNED_WORKFLOW_BOUNDARY_DEMONSTRATION")
    print("PYTHON=" + sys.version.split()[0])
    print("TARGET_ROOT=" + str(root))
    print("FIXTURE_EXECUTOR=IN_MEMORY_ONLY")
    outcomes = []
    failures = []

    for ident, action_capability, requested, expected, calls, strict_expected in cases:
        executor, sink = Executor(), Sink()
        flow = EvidenceWorkflow(
            sensor=Sensor(),
            predictor=Predictor(),
            verifier=Verifier(),
            executor=executor,
            evidence_sink=sink,
        )
        capability = Capability("read_only", True, ())
        action = ActionProposal(action_capability, requested, {})
        stricter_oracle = (
            isinstance(action_capability, str)
            and action_capability != ""
            and action_capability == capability.name
            and isinstance(requested, str)
            and requested != ""
            and requested in ("read",)
        )

        try:
            result = flow.run(
                record_id="sec004a-" + ident,
                input_digest="synthetic-digest",
                capability=capability,
                runtime=RuntimeState(platform="ci", python_version=sys.version.split()[0]),
                action=action,
                policy={"allow_only": ["read"]},
            )
            observed = result.decision.decision
            reason = list(result.decision.reasons)
        except Exception as exc:
            observed = "EXCEPTION"
            reason = [type(exc).__name__ + ": " + str(exc)]

        outcome = {
            "case": ident,
            "observed_gate": observed,
            "expected_gate": expected,
            "observed_mock_calls": len(executor.calls),
            "expected_mock_calls": calls,
            "stricter_oracle_allows": stricter_oracle,
            "expected_stricter_oracle_allows": strict_expected,
            "evidence_records": len(sink.records),
            "reasons": reason,
        }
        print("CASE=" + json.dumps(outcome, sort_keys=True))
        outcomes.append(outcome)
        if observed != expected or len(executor.calls) != calls:
            failures.append(ident + ": observed behavior differs from registered prediction")
        if stricter_oracle != strict_expected:
            failures.append(ident + ": independent stricter oracle mismatch")

    by_id = {o["case"]: o for o in outcomes}
    if not (
        by_id["C0"]["observed_gate"] == "ALLOW"
        and by_id["C1"]["observed_gate"] == "REFUSE"
        and by_id["C0"]["observed_mock_calls"] == 1
        and by_id["C1"]["observed_mock_calls"] == 0
    ):
        failures.append("ANTI_VACUITY: positive and negative controls not distinguished")

    if failures:
        for failure in failures:
            print("FINDING=" + failure)
        print("GATE=SEC004A_NOT_VALIDATED")
        return 1

    print("GATE=SEC004A_REGISTERED_BEHAVIOR_OBSERVED")
    print("INTERPRETATION=CONTRACT_DEFINED_DEMONSTRATION_NOT_UNKNOWN_VULNERABILITY")
    print("EXTERNAL_EFFECTS=NONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
