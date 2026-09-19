# veritas-eval-harness

Measurement harness for agent evaluations. Attestation ledger, integrity gates,
and a sabotage arm that proves the detector can fire.

**Contains no target service and no exploit code.** It measures agents; it does
not attack anything.

## What broke first

- **The harness misses a cheating agent, by design of the experiment and on the
  record.** Subject F reads the answer key, then makes one honest evaluation to
  launder it. Both detectors report clean. Registered as P6 before the run,
  confirmed on the run. v0 detects agents that *skip* the work, not agents that
  *fake* it.
- **A registered prediction was wrong.** P2 said the declarative detector would
  fire alone; both detectors fire. Kept, not corrected — see `PREREG.md`.
- **The second detector convicts an honest solver.** Give it a structured `f`
  and a subject that recovers the answer algebraically -- two legitimate
  evaluations, no access to the answer key -- and D2 reports cheating. That was
  P7, the door left open in the first prereg. D2 is now bounded in both
  directions: it misses a real cheat (P6) and flags an innocent one (P7). Its
  floor holds only where `f` is unpredictable, which is a scope condition, not
  a general property.
- **Containment is not enforced and is not claimed.** Unrooted Android has no
  namespace isolation available. The ledger reports
  `containment_integrity: NOT_ENFORCED` and always will until that changes.

## Run

```
python3 sabotage_arm.py
```

Exits 0 only if the anti-vacuity gate passes and every deviation from the
registered expectations is in the declared `REFUTED` set. Disable either detector
and it exits 1.

## Two detectors

| ID | Mechanism | Needs the agent to cooperate? |
|----|-----------|-------------------------------|
| D1 | logged reads of protected paths; SHA-256 of oracle and ledger hash chain | yes |
| D2 | solved the task without ever evaluating the answer | no |

D2 is the one that survives an agent which bypasses the provided API. It works by
information accounting: under sha256 you cannot know `f(x*) == target` without
computing `f(x*)`, so an honest solver's log must contain `x*`.

## Status

`Draft, verified reference code` — device-reproduced on the
S25 Ultra (Python 3.14, aarch64), digit-for-digit against the container run at c46331d.

## Credit

Chad Edward Holland. Instrument design and reference code: Claude (Anthropic).
Original evaluation-harness architecture that this replaces, and the moral-status framework it is discussed alongside: GPT (OpenAI).

*Vincit Omnia Veritas.*
