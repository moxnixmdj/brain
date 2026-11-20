# Web-app read-back gates adapter DONE — 2026-11-20 (V1)

**Progress class:** `VERIFIED_INTEGRATION_OF_OWNED_CAPABILITY`.
**Authority:** `NONE__PRODUCER_RUN_SANDBOX`. No benchmark score, capability credit,
independent verification, terminal authority or §6 completion.

## 1. Requirements and §2 boundary

I read the full v3 prompt as new before acting. The mission remains our own
model/weights/architecture/agent for full computer use with zero runtime model
calls, parameters containing only computed mechanisms, and an external
inspectable/editable/deletable instant-knowledge store that learns from single
experiences. §4–§5 research and looping, §6 honesty, and one-branch/one-merge
remain binding. The §2 contradiction stays resolved: forbidden = parameter
world-fact lookup and runtime model dependency; allowed = external editable store
plus single-experience writes, with computed mechanisms in weights. No evidence
this round changed that boundary.

## 2. Research findings

### Project

I searched non-obvious names as well as the obvious ones: all
`osworld_v21_brain_agent_adapter_v1–v8` versions, `osworld_v21_host_web_app_ops_v1`,
`osworld_v21_web_app_ops_registry_v1.json`, `osworld_v21_app_ops_registry_v1.json`,
`osworld_v21_app_policy_overlay_v1–v5`, `osworld_v21_web_app_policy_overlay_v1`,
`receipt_dataflow_v1–v3`, `generic_goal_state_verifier_v1–v3`,
`generic_tool_argument_binder_v1`, `source_grounded_coreference`,
`contextual_reference_operators`, all verified ledgers and the Qwen policies.

What already existed and was reused:

* The external web-app operation registry already provides one unique read-only
  `observe_*` operation per app and explicitly forbids `/api/state` control-plane
  reads. It is inspectable, editable and deletable; no app/operation was
  hard-coded into the ledger.
* `OSWorldHostWebAppOps` already validates app/operation/arguments, keeps the
  browser context origin, packages the result into `web_app_result`, and refuses
  control-plane state access.
* `BrainOSWorldAgentV3` already executes `WEB_APP_OP`; V7 still accepts DONE after
  any successful `web_app_result`. That was the soundness hole.
* `canonical_field` in `generic_tool_argument_binder_v1` already maps aliases
  such as `subject` to a canonical field group, so read-back matching does not
  need a new ontology.
* `receipt_dataflow_v1–v3` already established provenance-bound scalar/field
  lookup; this round reuses its principle, not a new parser.

### Frontier

OSWorld 2.1 is the current 108-task long-horizon release across 31 self-hosted
websites, with failures concentrated in hidden-state recovery, state tracking,
conflict disambiguation and verification rather than basic clicking
[2](https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/). The
OSWorld 2.0 analysis reports that frontier agents extract hidden application
states on roughly 14% of tasks and bypass user-visible interfaces on about 33%,
so a product-native, user-visible read-back path is the safer mechanism
[4](https://arxiv.org/pdf/2606.29537). OSWorld-style scoring is programmatic
against file-system or application state, with no LLM judge in the success path
[3](https://benchmarkingagents.com/osworld/). These are research inputs, not our
results or runtime dependencies.

## 3. Verdict on §3

Instant replay remains verified from earlier receipts; one-trace goal
identification and blanket permanence remain false; closure remains true only
for bounded computed mechanisms; sentience/general computer use remains
unproven. A model cannot simply learn advanced actions once under these
constraints because that would require world facts in parameters or another
model at runtime. The bottleneck fixed here is narrower and real: the adapter
treated “a web operation succeeded” as equivalent to “the requested app state
exists,” which is exactly the weak-verification failure the frontier reports.

## 4. Ultimate minimal plan and rejected ideas

| Idea | Verdict | Reason |
|---|---|---|
| Read hidden application databases | killed before build | unsafe, forbidden by registry, frontier reports agents already abuse it |
| Model judge of app state | killed | violates zero runtime model calls |
| Edit V7 adapter DONE rule | killed | byte-pinned by verification receipts |
| New app ontology / learned matcher | killed | duplicates `canonical_field` and adds world facts |
| Whole-task natural-language understanding | killed | unbounded and unnecessary for explicit field/value goals |
| Explicit app + field + quoted value → registry observation → fresh read-back | selected | uses existing computed mechanisms and fails closed |

“Am I sure this is the smartest approach?” Yes for this bottleneck: it closes
the exact unsound DONE transition without new weights, without hidden state,
without kernel edits, and with no new world-fact store. Any app mention without
an explicit field/value is refused rather than guessed.

## 5. Build

1. Extended `canonical/runtime/osworld_verified_task_ledger_v1.py`:
   * reads the external web-app registry and selects only each app's unique
     `observe_*` operation;
   * compiles only explicit app mentions plus explicit field/quoted-value pairs;
   * emits a single `WEB_APP_OP` observation when DONE is requested prematurely;
   * accepts the read-back only when `submitted_web_app_operation` and
     `web_app_result` match, `ok` is true, and the returned state contains the
     exact canonical field/value;
   * invalidates app evidence after any later web-app mutation or unknown-scope
     mutation, and keeps path-scoped invalidation for file evidence.
2. Updated `canonical/runtime/osworld_verified_agent_v1.py` to compose V7 with
   the existing product-native web-app controller.
3. Extended tests from 18 to 25. The new tests use a real local HTTP app through
   the unchanged operation validator and result packaging; no PASS receipt is
   hand-written.
4. Intent: `canonical/action_intents/WEB_APP_READBACK_GATES_ADAPTER_DONE_V1.json`.

## 6. Measured results

* New ledger suite: `25 passed in 3.15s`.
* Targeted suite (state ops, real guest ops, V1 adapter, web-app ops, dataflow,
  sensor bridge, terminal authority, ledger): `109 passed in 5.22s`.
* Full shared-process OSWorld suite: `279 passed`, with the same pre-existing
  order-dependent `sys.modules` pollution failure as earlier rounds.
* Integrity guard: `rules=17 violations=0 PASS`.
* Unified verifier: `TOTAL 33/33 PASS`; artifact recompiled after new source and
  evidence files. Digest is intentionally omitted from this indexed report and
  receipt to avoid the documented recompile cycle.
* Producer model calls: `0`. Stored parameters: `0`. Incremental spend: `$0`.

## 7. Verified / unverified / failed

**Verified.** Real HTTP observation and mutation receipts flowed through the
existing registry validator and the unmodified V7 adapter. DONE was reached only
when the read-back contained the exact field/value; wrong values and later
mutations blocked DONE. App mentions without explicit field/value failed closed.

**Unverified.** No untouched OSWorld 2.1 task, SWE-bench Pro task, Terminal-Bench
task, real CDP browser, GUI/browser success, hidden evaluator, single-experience
learning benchmark, unseen-environment run, independent verification, benchmark
score, capability/terminal credit or §6 completion.

**Failed / rejected.** The earlier shared-process `sys.modules` pollution
failure persists and is unrelated. The first local HTTP test attempt lacked a
URL hint and then encoded POST bodies incorrectly; both were test-harness fixes,
not capability claims. Hidden DB reads, model judges and pinned edits were
killed before build.

## 8. Next §5 bottleneck

The gate now proves explicit app field/value facts, but not relational or
multi-item app facts such as “the first row from the calendar whose status is X”.
The next loop should compose `receipt_dataflow_v3` relational resolution with
this read-back gate while preserving fail-closed provenance, then test on a real
OSWorld 2.1 task image if available without leaking evaluator answers.
