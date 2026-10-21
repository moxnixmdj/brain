# Brain Unified Model V1

One artifact. One digest. One entry point. Everything Brain can currently do,
compiled into a single model.

```
canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json
model digest: e7bbe1d07ba91fc9413c1eda66040b8a7414d1d9621e476335d25bd9bfb6d468
```

This is a **compiled projection**, not a new authority. It is a deterministic
function of the repository tree: compile it twice and you get the same bytes.

## What is inside

| Layer | Count | What it is |
|---|---|---|
| Capabilities | **363** | 68 promoted bound capabilities + 295 receipt-backed capabilities from the live verified registry |
| Engines | **26** | 25 unified-cognitive-fabric modes + 1 meta orchestrator |
| Skills | **18** | Internalized `SKILL.md` procedures with their operational lines |
| Knowledge | **168** | 59 laws, 95 documents, 14 structured records — indexed by hash, headings and terms |
| Routing vocabulary | **1,775** | Tokens compiled from declared triggers, weighted by inverse document frequency |
| Weights | **0** | This artifact contains no trained parameters and never claims any |

Knowledge is *indexed, not embedded*: the model stores each document's path,
content hash, headings and retrieval terms. Text is read from disk at query
time. That is the repository's theory — knowledge is external and just-in-time,
capability is what Brain owns.

Laws carry their version verdict. 25 are `CURRENT_LAW`, 21 are
`HISTORICAL_LAW_VERSION`, 13 are `SUPERSEDED_LAW`. Retrieval is not allowed to
hand a superseded law to an agent as present-day authority: when the current
member of a family is relevant at all, it ranks above its own history, while
history remains retrievable by naming its version.

## Run it

```bash
# what the model contains, and what it explicitly cannot claim
python3 -m canonical.runtime.brain_unified_model_v1 status

# deterministic routing over a plain goal
python3 -m canonical.runtime.brain_unified_model_v1 route "extract text from a pdf"

# just-in-time knowledge retrieval
python3 -m canonical.runtime.brain_unified_model_v1 recall "capability acquisition route order"

# route and execute through the verified adapter
python3 -m canonical.runtime.brain_unified_model_v1 solve \
  "audit python source structure" \
  --inputs '{"source_root":"canonical/runtime","output_path":"/tmp/audit.json"}'
```

Call it from Python:

```python
from canonical.runtime.brain_unified_model_v1 import open_model

brain = open_model()
result = brain.solve("rank sources by relevance to an objective", inputs={...})
print(result["pass"], result["status"], result["model_digest"])
```

## The contract

**Routing fails closed.** A goal outside the model's representation returns
`GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED` with the candidate list. It is
never answered by a guess or by an external model. Eight out-of-domain goals
are checked on every verification run and none may route confidently.

**Execution stays with the owner of authority.** Bound capabilities are
dispatched through
`verified_bound_capability_execution_adapter_v1.execute`, which re-reads the
live registry, re-checks the independent-verification evidence, re-renders the
frozen action template, and re-verifies the execution trace. The model cannot
promote, widen or launder anything: remove a capability from the live registry
and the model stops being able to execute it.

**Engine modes are unchanged.** They are dispatched to the unified cognitive
fabric's own `run`, with the same host-provider requirements. Without those
providers they fail closed, which is what the verification run measures.

**Every result carries zero credit.** `capability_credit_delta`,
`ownership_credit_delta` and `terminal_credit_delta` are always `0`.

## What this is not

- It is **not a trained neural network** and contains no weights. The learned
  mechanisms Brain owns keep their own verified records; they are referenced,
  not silently absorbed.
- It is **not an independent verification**. The current measurement is
  `MEASURED_SANDBOX__NOT_INDEPENDENT` with `authority: NONE`.
- It is **not terminal authority**, and it changes no scoreboard.
- It is **not a replacement** for the live registry, the laws, or the gates.
- **Coverage is not capability.** Every live capability is represented and
  routable; executing one still requires its declared substrate.

## Recompile and verify

```bash
# compile (deterministic; no timestamps, no network, no model calls)
python3 canonical/runtime/compile_brain_unified_model_v1.py

# measure on fresh instances (records its seed; writes the JSON report)
python3 canonical/runtime/verify_brain_unified_model_v1.py \
  --seed <seed> \
  --output canonical/verification/BRAIN_UNIFIED_MODEL_V1_VERIFICATION_20261020.json
```

The verifier builds new instances at run time and checks them with separately
written oracles:

| Category | What must hold |
|---|---|
| `ARTIFACT_INTEGRITY` | digest recomputes, recompilation is byte-identical, every capability source and evidence hash matches the tree |
| `LIVE_REGISTRY_COVERAGE` | the model's capability set equals the live loader's set exactly, with nothing invented |
| `ROUTING_FRESH_GOALS` | generated goals put the target in the top 3 at least 80% of the time; out-of-domain goals never route confidently |
| `KNOWLEDGE_RECALL` | held-out term queries find their source document; current law outranks its own history |
| `EXECUTION_FRESH` | Python source audit, tar create/verify, SQLite creation and test execution run on new inputs and agree with independent oracles; a substrate-blocked capability must fail closed and name the gap |
| `NEGATIVE_CONTROLS` | unknown goal, missing inputs, tampered artifact, nonzero-spend capability and provider-less engine are all refused |
| `MODEL_DEPENDENCE_AUDIT` | no model client is imported in the runtime or named in any capability route; zero external calls, zero spend |
| `ONE_FRONT_DOOR` | all 363 capabilities and 26 engines are addressable through this one artifact |

Current result: **33/33 sandbox checks pass** on seeds
`arena-first-run`, `alpha-7`, `beta-19`, `gamma-2026`, `delta-3`,
`arena-final-20261020`. That is a sandbox measurement. Another identity must
re-run the verifier on a clean checkout and sign the result before any of it
counts as independent verification.

## Honest limits, measured now

- 7 capabilities declare dependencies absent from this sandbox: six chart /
  visual capabilities need `PIL`, and browser capture needs `chromedriver`.
  `json.query.jq` has `jq` installed but still fails closed with
  `BOUND_APT_METADATA_NOT_FOUND`; the model reports that instead of hiding it.
- 356 of 363 capabilities have their declared dependencies present. Present is
  not the same as executable: adapters can fail closed on other preconditions.
  Only execution evidence answers that question, which is why the verifier runs
  real instances rather than counting files.
- One artifact is not one capability. This makes all of Brain's owned surface
  **addressable and executable through a single entry point**; it does not add
  a new capability, move a benchmark, or reach the Opus 5.5 checkpoint.

## Files

| Path | Role |
|---|---|
| `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` | the model |
| `canonical/runtime/compile_brain_unified_model_v1.py` | deterministic compiler |
| `canonical/runtime/brain_unified_model_v1.py` | loader, router, solver, retrieval, CLI |
| `canonical/runtime/verify_brain_unified_model_v1.py` | fresh-instance verifier |
| `canonical/tests/test_brain_unified_model_v1.py` | 21 regression tests |
| `canonical/verification/BRAIN_UNIFIED_MODEL_V1_VERIFICATION_20261020.json` | sandbox measurement, authority NONE |
