# The door was refusing before it had finished binding — and losing the reason

**2026-11-03**, `73975e2`. Ranked item #2 executed: the front-door failures that are *not* behind
the execution gate. Two defects, both real, both **information loss rather than missing
capability**. `test_front_door_crossfile_task_v1.py`: **29 failed / 9 passed → 23 failed / 15
passed**. Four new tests pin the defects themselves.

No regression: the four closest neighbouring suites score **34 failed / 95 passed with and
without** this change (measured by stashing it).

---

## Defect 1 — the frozen template was treated as the whole binding

A complete staged-workflow grammar (`crossfile_task_binding_v1`) binds **one input per stated
path**, request-locally, because it may not modify the shared registry. So its row's frozen
`action_template` names only the slots every request shares:

```json
{"args": {"capability_id": "…", "output_path": "${input.output_path}",
          "source_root": "${input.source_root}"}}
```

`issue_path` is not there — correctly, because only *some* requests state one. The compiler's
completeness check ran **first**, against that template, and refused:

```
GOAL_INPUT_BINDING_REQUIRED:software.repair.choreograph.crossfile.v1:
    unserved_stated_files:<scratch>/issue.json
```

…before anything had a chance to add the slot the sentence had already stated. This is exactly
the defect `OPTIMAL_PLAN_20261103_V1.md` §P3 predicted ("the missing input is dropped
silently"), except the drop happened at *compile* time and the binder that would have fixed it
runs *after*.

**Fix.** The check now runs a second time, against the binding the request-local grammar will
actually use (`_request_local_complete_binding`), and only a binding that consumes **every**
stated path clears the refusal. Nothing is weakened: the fourth test in the new file appends an
unrelated stated file and confirms the request is **still** refused with
`GOAL_INPUT_BINDING_REQUIRED`. The rule is completeness, not leniency.

## Defect 2 — an unrecognised refusal was overwritten by a blander one

```python
if not _is_honest_contract_refusal(result):
    acted = _serve_by_acting(request)      # answers boundary.STATUS
```

`_is_honest_contract_refusal` treats a failure class it does not know as *"try to serve it"*.
`CROSSFILE_TASK_UNBOUND` — "this request names files it does not bind" — was not on the list,
so a precise refusal reached the caller as:

```
FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
```

**That is a statement about the execution boundary, from a code path that never consulted it.**

### Why this one matters more than the file it broke

`test_extra_goal_requirements_refuse_before_execution` exists to prove the refusal is *precise*.
It read the wrong class and failed — reporting a safety property it never touched. And when I
counted "how many of the 984 failures are downstream of the carrier gate", **this class of defect
would have inflated that number**: a failure text that says `REQUIRES_ADMITTED_CONFINEMENT` does
not prove the boundary was reached, only that a refusal passed through `_serve_by_acting`.

**Consequence for the earlier report.** The `blocked_deliberate_refusals` bucket in
`SUITE_BACKLOG_SPLIT_20261103_V1.json` groups by *status text*, so it cannot distinguish:

| | |
|---|---|
| a genuine boundary refusal | the capability really needs execution authority |
| a refusal that was **replaced** by the boundary status | an unknown refusal got re-served |

The 189 is an upper bound on "blocked on a review", not a count. The honest statement is:
**117 failures carry the confinement status, and some unknown fraction of those are this defect
rather than the gate.** Four of them were, in one file, and they are fixed.

## What I did not fix, and why

`test_normal_entry_binds_and_replays_actual_crossfile_change` still fails. The path now compiles
and `bind_context` succeeds — but `_solve_body` returns
`FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED` instead of executing the bound row, so the report is
never written. The context **is** passed as `_typed_swe_plan`; `_solve_body` still composes.
That is the next real piece of work in this file, it is bounded, and I stopped here rather than
start a speculative edit to the execution path with 17 remaining failures depending on it.

Progress, stated as progress and not as a fix: **29 → 23 failing, 9 → 15 passing**, two defects
named, both pinned by tests that would have caught them.

## Non-claims

No capability registered, no family flipped, no `truth.achieved`. The four neighbour suites still
show 34 pre-existing failures, measured identically with and without this change. $0 spent.
