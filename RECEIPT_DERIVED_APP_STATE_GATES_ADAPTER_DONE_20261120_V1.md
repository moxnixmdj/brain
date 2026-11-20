# Receipt-derived relational app state gates adapter DONE — 2026-11-20

Authority: `NONE__PRODUCER_RUN_SANDBOX`. This is an owned-mechanism integration
measurement, not a benchmark score, GUI/browser success, independent
verification, capability credit, or §6 completion.

## 0. Requirement confirmation (read fully as new)

1. Own model/weights/architecture/agent; zero runtime model calls.
2. Parameters contain only calculated mechanisms, never memorized world facts.
3. Instant knowledge lives in an external, inspectable/editable/deletable store
   and can be written from a single experience; it is never a parameter lookup.
4. Research the project exhaustively (including non-obvious names), then the
   web/frontier literature; treat findings as inputs, not truth.
5. Find the first-principles bottleneck; design the ultimate minimal plan;
   reject and kill bad designs before building.
6. Build, test the hardest honest cases, separate verified/unverified/failed,
   and keep looping §5 until §6. Never ask questions or stop early.
7. One branch, one merge when the feature is complete.

This round adds exactly one capability: an explicit relational/aggregate app
fact (for example, "the count of events from Calendar") can determine a file
condition only when it is resolved from a structured product-native receipt and
then independently re-measured by the guest. No relation is answered from
parameters, world knowledge, a model, or a task ID.

## 1. Research actually performed

### Project (source of truth)

* `canonical/runtime/osworld_v21_receipt_dataflow_v3.py` already implements
  `resolve_count`, `resolve_projection` (`first`/`last`/`all`) and
  `resolve_filtered_scalar` over prior structured receipts, with provenance,
  sensitive-field refusal, ambiguity refusal and size limits. Its tests show
  receipt-only resolution and fail-closed behavior.
* `canonical/runtime/osworld_v21_workflow_policy_v4.py` already composes that
  dataflow into ordered subgoals, but stops at action selection; it does not
  bind a resolved relation to a DONE-level file assertion.
* `canonical/runtime/osworld_verified_task_ledger_v1.py` gates DONE on fresh
  guest PASS receipts and, after PR #7034, on exact `APP_STATE_FIELD` readback,
  but it compiled requirements only from literal quoted values. A count or
  filtered field had no literal to compile, so DONE could pass on mere file
  existence.
* Web-app operation registry (`osworld_v21_web_app_ops_registry_v1.json`) plus
  `OSWorldHostWebAppOps` already provide registry-only `observe_*` calls;
  `BrainOSWorldAgentV7` and the pinned kernels need no edits.
* Non-obvious routes checked and rejected: `generic_goal_state_verifier_v1–v3`,
  `fixed_bar_aggregate_admission_v1`, `osworld_v21_gui_goal_verifier_v1`,
  `osworld_v21_visual_relational_grounding_v1`, workflow policies v5/v10/v12
  and subject v8. None binds receipt-derived relational values to the adapter's
  DONE ledger.

### Web/frontier (inputs, not capability credit)

* OSWorld 2.1 long-horizon evaluation [1]: 108 tasks, >250 steps, majority
  cross-app, ~27 weighted checkpoints per task, binary completion only when all
  checkpoints pass; reported failure modes include constraint tracking,
  mid-task information, hidden state and skipped verification.
* OSWorld 2.1 failure analysis [2]: cross-source reasoning 46/108 (42.6%),
  implicit-state inference 43/108 (39.8%), multi-item state tracking 43/108
  (39.8%), conflict disambiguation 39/108 (36.1%); agents spend under 7% of
  steps detecting or repairing errors.
* Current benchmark catalog [3]: OSWorld 2.1, ApprenticeBench (100 sequential
  vendor bills, continual learning) and FrontierMemory (15 memory-dependent
  coding/knowledge tasks) are the relevant hard families; older saturated
  variants are not the frontier.

[1] https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/
[2] https://arxiv.org/html/2606.29537v1
[3] https://benchlm.ai/benchmarks

## 2. §3 verdict: true / false / unproven / missing

* **True:** A single executed experience can be replayed in a copied environment
  from external receipts; the ledger already uses this for sensor and guest
  facts. A relational value computed from a receipt is replayable the same way.
* **False:** One experience identifies an arbitrary new goal by itself. The
  instruction must state the relation and target; the store supplies only
  observed values, not intent.
* **False:** "Permanent" blanket learning from one trace. Scope, provenance and
  invalidation are required; a later mutation removes the claim.
* **Unproven:** General computer use, GUI/browser success, original SWE ability,
  unseen-environment transfer and single-experience learning benchmarks. No
  test here establishes any of them.
* **Missing:** A real OSWorld 2.1 task image, CDP browser, hidden evaluator,
  Terminal-Bench/SWE-bench Pro run, independent verification and any
  benchmark score.

Why not simply let a model experience advanced coding actions once and learn
them? A trace records what happened, not what the goal was, which field is
authoritative, or which later mutation invalidates it. Storing that inference in
weights would turn parameters into a world-fact warehouse and would remove the
external, editable provenance needed to correct one experience. The computed
mechanism here is receipt selection, canonical field lookup, equality checking
and invalidation; the fact stays outside the weights.

What stops us now: no owned sensory/actuator stack for arbitrary GUIs, no
general goal parser, no verified single-experience learning benchmark result,
and no independent evaluator. This round removes one narrow unsoundness only.

## 3. Bottleneck and smartest minimal design

First-principles bottleneck: long-horizon failures cluster at hidden-state and
mid-task value tracking plus weak verification. The concrete unsoundness was
that a relational value (e.g., count, first matching field) could influence a
later file write, yet the DONE ledger only checked that the file existed.

Selected route: **compose, do not invent**. Reuse receipt dataflow V3 as the
only relation evaluator; extend the unpinned ledger so that:

1. A relational clause first emits one registry-bound `APP_OBSERVATION`
   requirement (one `observe_*` op for the app named in the clause).
2. The relation is resolved from prior structured receipts only. Its value
   becomes a `TEXT_CONTAINS` requirement with both `ASSERT_TEXT_CONTAINS` and
   `ASSERT_TEXT_EQUALS`; the resolved provenance row indices are retained.
3. DONE requires the product observation, an adapter-visible guest PASS for
   the exact derived value, and no later app or path mutation.
4. Ambiguous, sensitive, multi-reference, non-registry or directory-target
   relations fail closed.

Rejected ideas (killed before build):

* A new ontology or second relation parser — dataflow V3 already exists and is
  pinned by an independent verification receipt.
* A new model/LLM judge or learned value predictor — forbidden and unnecessary.
* Storing the count/status in weights or pretraining data — forbidden.
* Reading hidden app/database state or `/api/state` — forbidden by registry.
* Treating any successful `WEB_APP_OP` as the relation answer — proven unsound
  in PR #7034's predecessor problem.
* Asserting only `ASSERT_TEXT_CONTAINS` — `"12"` would satisfy count `2`; the
  derived condition also requires exact equality.
* Editing byte-pinned kernels (state ops, guest ops, adapter V1/V7, web app
  ops, workflow V10) — all untouched.

## 4. Build

Changed files:

* `canonical/runtime/osworld_verified_task_ledger_v1.py`: imports dataflow V3;
  `compile_requirements(instruction, prior_rows=())` adds `APP_OBSERVATION` and
  receipt-derived `TEXT_CONTAINS` requirements; audit verifies observation
  receipts, exact equality and post-provenance invalidation; `decide` emits the
  registry observation while the relation is unresolved.
* `canonical/tests/test_osworld_verified_task_ledger_v1.py`: local HTTP
  Calendar endpoint, five new tests including real HTTP readback, real guest
  assertion receipts, wrong value, later mutation and V7 adapter DONE.
* `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` and
  `canonical/verification/BRAIN_UNIFIED_MODEL_V1_VERIFICATION_20261020.json`:
  recompiled and reverified after the source change.

No parameters, model clients, task IDs, benchmark answers or reference
trajectories were added. Producer model calls this round: 0. Stored parameters:
0. Incremental spend: $0.

## 5. Honest measurements

* New ledger suite: **30 passed** (was 25; 5 new tests).
* Targeted suite (state ops, guest ops, adapter V1, web app ops, sensor bridge,
  dataflow V3, terminal authority, ledger): **114 passed**.
* Full `canonical/tests/test_osworld*`: **284 passed, 1 pre-existing
  order-dependent `sys.modules` pollution failure** in
  `test_v3_loaded_module_graph_excludes_obsolete_and_model_backed_policy_routes`.
  Not attributed to this change.
* Repo-integrity guard: `rules=17 violations=0 -> PASS`.
* Unified compile reached a fixed point across two consecutive compiles; the
  unified verifier reported `TOTAL 33/33 PASS`. The digest is deliberately not
  embedded in an indexed artifact because that creates a recompile cycle.
* Verified: local HTTP product-native Calendar receipt → receipt-derived count
  `2` → real guest write and equality assertion → V7 adapter DONE. Wrong file
  value and later Calendar mutation block DONE.
* Unverified: real CDP browser, untouched OSWorld 2.1 task, SWE-bench Pro,
  Terminal-Bench, GUI/browser success, hidden evaluator, unseen environment,
  single-experience learning benchmark, independent verification, benchmark
  score and §6 completion.
* Failed during build (harness only, fixed): wrong-value assertion raised
  `GuestOpsError` because the assertion correctly failed; local server lacked
  `/api/calendar/actions`; URL hint needed both `mailhub` and `calendar`. None
  changed pinned code.

## 6. Next §5 step

Extend the same receipt-derived gate to first/last/filtered relational fields
with explicit target paths and multi-clause workflows, then seek a real
OSWorld 2.1 cross-app checkpoint environment. §6 remains open.
