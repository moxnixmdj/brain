# Verified task ledger gates OSWorld DONE — 2026-11-20 (V1)

**Progress class:** `VERIFIED_INTEGRATION_OF_OWNED_CAPABILITY`.
**Authority:** `NONE__PRODUCER_RUN_SANDBOX`. No benchmark score, no capability credit,
no independent verification, no §6 completion claim.

## 1. Requirement restated before acting

The user's task is still to build our own model/weights/architecture/agent that can
solve arbitrary computer-use and SWE problems, learn from one experience, and make
**zero runtime model calls**, with parameters that are computed mechanisms rather
than memorized world facts. Knowledge may live only in an external inspectable,
editable, deletable store. Work must continue through §5 until §6, on one branch,
with one final merge, honest verified/unverified/failed separation, exhaustive
project and web research, first-principles bottleneck analysis, rejected ideas,
and kill-before-build.

This round does **not** claim §6. It targets one measured long-horizon failure:
a deterministic policy may say `DONE` without a fresh, machine-checkable record
that the task's final state satisfies its own explicit conditions.

## 2. Exhaustive project and frontier input

Project search covered `osworld_v21_generic_policy_v1`–`v3`,
`osworld_v21_workflow_policy_v1`–`v13`, `osworld_v21_unified_policy_v10`–`v17`,
`osworld_v21_recovery_policy_v1`/`v2`, `osworld_v21_receipt_dataflow_v1`–`v3`,
adapters `v1`–`v8`, the pinned state/host-guest kernels, the GUI goal verifier,
the admitted sensor bridge, and the two forbidden model-backed Qwen policies.
Reads showed:

* the base stack already compiles GUI actions and state ops, and its adapter
  records real guest receipts into history;
* `workflow_policy_v13` tracks explicit subgoals but gates completion on its own
  local evidence, not an external task ledger;
* `receipt_dataflow_v3` materializes explicit references but does not decide
  whether the final state is verified;
* `unified_policy_v17` composes the verified capability stack but can still emit
  `DONE` from its own decision path;
* the previously merged `ASSERT_SENSOR_REQUEST` bridge gives a real directory
  assertion whose field and value are re-measured, not policy-supplied;
* `osworld_v21_local_qwen_policy_v1` and `osworld_v21_qwen35_planner_v1` call
  models and are disqualified as runtime routes.

Frontier input used only as research, never as borrowed capability or runtime
dependency: OSWorld 2.0's failure taxonomy (hidden-state inference, multi-item
tracking, conflict disambiguation, weak verification), LongHorizon-Harness's
explicit audited task state, zero-call compiled end-state agreement checks, and
WebArena's programmatic evaluator framing. All use models or external systems;
only the architecture lesson — keep auditable state outside the executor — is
adopted here.

## 3. First-principles bottleneck and killed designs

**Bottleneck.** Long-horizon computer use fails when the decision to stop is not
causally tied to a fresh observation of the requested end state. More clicking,
more perception, or a larger model does not close that gap. The minimal sufficient
change is to make completion a fail-closed function of real receipts.

| Route | Verdict | Reason |
|---|---|---|
| DELETE | rejected | bridge, policies and adapter are load-bearing |
| BYPASS | rejected | permits unverified `DONE`, the defect itself |
| edit pinned kernels | killed | byte-pinned by verification receipts |
| more GUI perception | killed | frontier failures cluster on verification and state drift |
| model planner / judge | killed | violates zero runtime model calls |
| REUSE + ADAPT + COMPOSE + INTEGRATE | selected | wrap existing deterministic policy, compile explicit requirements, gate `DONE` on fresh receipts |

Best part is no part: no new weights, no task inventory, no learned selector, no
model call. The selector is a compiler from explicit instruction evidence to
pinned assertions.

## 4. What was built

1. `canonical/runtime/osworld_verified_task_ledger_v1.py`
   * compiles only absolute paths and quoted literals present in the instruction;
   * maps directory paths to the admitted `ASSERT_SENSOR_REQUEST`, files to
     `ASSERT_PATH_EXISTS` / `ASSERT_TEXT_CONTAINS`;
   * accepts a receipt only when the matching pinned op is in the submitted ops,
     the guest execution returned PASS, and no later mutation invalidated it;
   * rejects ambiguous quotes, multiple-path quote binding, wrong-path PASS,
     forged sensor PASS without `fresh_measurement` admission, GUI instructions
     with no explicit state path, and any override of `FAIL`;
   * emits missing pinned assertions instead of an early `DONE`, and can finish
     a stalled policy only after all explicit requirements are fresh-verified.
2. `canonical/runtime/osworld_verified_policy_v1.py` — thin runtime composition
   of `unified_policy_v17` with the ledger. No pinned kernel was edited.
3. `canonical/tests/test_osworld_verified_task_ledger_v1.py` — 11 tests. Real
   guest subprocesses produce directory and file receipts through the admitted
   bridge and pinned state-op compiler; there are no hand-written PASS receipts.
4. Intent: `canonical/action_intents/VERIFIED_TASK_LEDGER_GATES_OSWORLD_DONE_V1.json`.
5. Unified-model artifact and its verification receipt were recompiled because
   two new runtime modules enter the source index.

## 5. Measured results

* New suite: `11 passed`.
* Targeted combined suite (state ops, real guest ops, adapter, sensor bridge,
  ledger): `71 passed in 2.94s`.
* Repo integrity guard: `rules=17 violations=0 PASS`.
* Unified model: recompiled after adding runtime and evidence files; compile digest is recorded in the receipt; verifier `TOTAL 33/33 PASS`, seed `ab6e15ab137ed07f`.
* Producer model calls: `0`. Stored parameters: `0`. Incremental spend: `$0`.

## 6. Verified / unverified / failed

**Verified in this sandbox.** Real guest processes created a fresh directory and
file; the admitted sensor bridge returned a fresh-admission PASS; the pinned file
assertion returned PASS; the ledger allowed `DONE` only with those receipts. Later
mutation, stale PASS, wrong path, missing fresh admission, ambiguous quotes, GUI
instructions without an explicit state path, and a base `FAIL` were all refused.

**Unverified.** No untouched OSWorld 2.1 benchmark task was executed; no GUI or
browser task was solved; no hidden evaluator agreement, single-experience
learning test, unseen-environment run, independent verification, terminal
authority, or benchmark credit was obtained. The requirement compiler is
deliberately narrow: it cannot yet bind a quoted value to one of several paths or
to GUI state, and fails closed instead of guessing.

**Failed / rejected.** `canonical/tests/test_osworld*` in one shared pytest
process produced `1 failed, 265 passed`; the failure was
`test_v3_loaded_module_graph_excludes_obsolete_and_model_backed_policy_routes`
complaining that `osworld_v21_browser_ops_v1` was already in `sys.modules`. It
reproduces when the new test file is excluded, passes in isolation, and is an
order-dependent pre-existing import-pollution issue, not a new capability claim.
The design was killed before build where appropriate: model judge, pinned-kernel
edits, GUI perception expansion and answer lookup were all rejected.

## 7. Next §5 loop

Attack the narrowness explicitly: bind cross-clause quoted values to the correct
path from the instruction's own explicit relations, and add a real adapter-level
end-to-end test where the emitted assertion batch is executed by
`BrainOSWorldAgent` before `DONE`. Until then, this is a verified harness gate,
not a general computer-use solution.
