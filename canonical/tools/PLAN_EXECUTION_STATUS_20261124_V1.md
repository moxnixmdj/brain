# Executing the plan: one step blocked, one step already done, and a stale number of mine

**Date:** 2026-11-24. **Authority:** NONE (producer-run sandbox).
I executed `THE_SMARTHEST_PLAN_20261124_V1.md` in order. Two of its five steps changed status on
contact with the tree, and one of them was wrong *in my own document*. Recorded here so the plan can
be corrected rather than defended.

---

## §1 Step 1 — "wire the decision layer to the computer-use layer" is BLOCKED, and must not be done

**What I found first, and got wrong.** My top-level import grep showed zero cross-references between
`computer_env_v1`, `goal_chase_v1` and `closed_loop_autonomous_controller_v1`. That was an artifact of
my own method — the controller reaches `computer_env_v1` at **four sites via lazy imports inside
functions** (L475, L923, L1147, L1528). The organs *are* connected.

**Then the real finding, which is worse and more useful.** All four call sites are **refusals or
post-hoc elevation** — never action sourcing:

| site | what it actually does |
|---|---|
| L475 | elevate a *verified* `computer_env_v1` survivor into a qualified skill (**after** measurement) |
| L923 | `ground_dom_or_browser_surface` — DOM/browser grounding of a request shape |
| L1147 | `computer_shape` classification → **prevent** Tier-0 recall from jumping ahead of the refusal |
| L1528 | `query_kind(goal)` → **refuse** with `computer_boundary.STATUS` |

And `computer_env_v1.discover()` — the action-discovery engine — is **never called** by the decision
layer. Confirmed by grep: no match in the controller or in `goal_chase_v1`.

**Why that is correct, and why I stopped.** The seam is closed *deliberately*, and the repo says so:

> `confinement_v1` "launches a normal subprocess with the host user's filesystem and network
> authority; it is not an OS sandbox. In a temporary-repository experiment, a confined command wrote a
> sentinel **outside the clone** while the result still reported `host_untouched=True` and
> `verified=True`. Git porcelain equality does not establish that host files are untouched."
> — `CONFINEMENT_FRONT_DOOR_WIRING_DESIGN_20261124_V1.md`, marked **NOT APPROVED**

> "Do not route around these blockers." — same document, and
> `ISOLATED_REPAIR_CARRIER_REVIEW_DESIGN_20261124_V1.md` "grant[s] no authority."

So Step 1 as I wrote it would route a computer-use action source around a confinement boundary whose
isolation substrate is known to leak. **I did not implement it.** This is the standing constraint
working exactly as intended: the plan was wrong to propose it, and the repo's own safety review is
what caught it.

**What would unblock it** (not a research problem): a reviewed isolation boundary with observed
qualification — `zero_ambient_namespace_launcher_v1.py` / `worker_syscall_allowlist_v1.py` /
`brokered_workspace_execution_v1.py` exist but the broker reports `carrier_qualified=False`, and
"candidates, not admission evidence."

---

## §2 Step 3 — "fix transfer, honestly: 1/15 and 1.00× is the load-bearing failure" was ALREADY DONE

**My plan quoted a stale number and I did not check it.** The 1/15 and 1.00× came from
`INSTANT_LEARNING_NEW_INSTANCE_REMEASUREMENT_20261103_V1.md`. That document is honest, and it is
**three weeks old**. The fix landed the same day and is in the code, with its own comment:

> *"Measured 2026-11-03: on genuinely new instances this succeeds in 7 of 15 cases, and the old order
> — replay exact plans, then search with the model as a hint — turned that into a 1.00× speedup that
> cost MORE environment calls than carrying nothing. Planning is the whole reason a model is worth
> storing: reachability over the carried transitions, then execute, then CHECK."*
> — `canonical/runtime/transfer_learning_v1.py`, block **1b**

**I re-ran both instruments. They agree, and both are far from 1.00×:**

`transfer_learning_new_instance_probe_20261103.py` (the one that produced 1/15):

| | 2026-11-03 | **today** |
|---|---|---|
| WARM genuine saving (fewer trials **and** no more act calls) | 1/15 | **8/15** |
| WARM fewer trials than COLD | 1/15 | **8/15** |
| WARM reached the goal in 1 trial | 1/15 | **8/15** |
| WARM **worse** on trials than COLD | — | **0/15** (hard invariant) |
| mean trial speedup | 1.00× | **6.333×** |
| mean act-call speedup | 0.977× | **2.259×** |
| WARM spent more act calls | 14/15 | 7/15 (worst 1.398×) |

`canonical/tools/changed_state_transfer_benchmark_v1.py` (10 target cases):

| | result |
|---|---|
| genuine saving (fewer trials and no more calls) | **8 / 10** |
| total trials, cold vs warm | 256 vs 160 → **1.60×** |
| per-family | `toggles`, `accumulator`, `grid`, `modulo` all 8→1 or 16→1; **`lock` unchanged** |

**So transfer is no longer the load-bearing failure.** It is 8/15 with a mean 6.333× trial speedup and
a hard invariant that memory may cost act calls but never trials. The residual is bounded and
localized: act-call overhead in the `lock` family (1.106×–1.133×) and in 7/15 probe cases.

**Both instruments' own caveats stand and I am not relaxing them:** five *constructed* families,
producer-run, *"not independent verification, and it says nothing about GUI or unbounded computer
use."* 8/15 on toy states is not 8/15 on OSWorld.

---

## §3 What I checked instead — the strongest real-transfer organ is wired and load-bearing

`environment_fit_v1` — "reads a project's own declarations (CI workflow → `package.json` → `Makefile`
→ `pyproject`), then ADAPT → PROVISION → FOLLOW… the strongest thing in the tree" — is imported by
**7 modules**: `autonomous_v1`, `verifier_falsification_v1`, `autonomous_awake_loop_v1`,
`goal_dag_executor_v1`, `the_environment_broker_v1` (3 sites). It is not an orphan.

That matters for the plan: the *real-environment* transfer claim rests on this organ, and it is wired.
It still has no direct test file under `canonical/tests/` — coverage is indirect, through its 7
consumers. That is the gap to close, and it is unblocked.

---

## §4 Corrected plan

| step | was | now |
|---|---|---|
| 1. Wire decision ↔ computer-use | do first | **BLOCKED** — do not route around confinement. Unblocks only on a reviewed isolation boundary. |
| 2. Elevation as default observation | do second | unblocked but **unmeasurable** without OSWorld traces; blocked on the same infra as step 5 |
| 3. Fix transfer | "1/15, 1.00× is the load-bearing failure" | **ALREADY DONE** — 8/15, 6.333×, 0/15 worse-on-trials. Residual: `lock` act-call overhead. |
| 4. Whole-file judging | always | unblocked, correct, **currently vacuous** — there are 0 passes to judge until reach improves |
| 5. Measure on OSWorld 2.1 | the wall | **BLOCKED** on gated datasets / KVM / 14.9 GB QCOW2 |

**The honest consequence:** of five steps, two are blocked on infrastructure and one was already done.
The plan's spine was right — attack the frontier's measured wall, not its strength — but it assumed
the binding constraint was transfer, and it is not. Transfer is fixed. The binding constraints are
**reach** (0 passes on the repair corpus; 0/51 certified on SWE-bench Pro V2) and **isolation**
(no untrusted execution without a reviewed boundary).

**Next, unblocked and highest-value:** close the reach gap on the oracle-given corpus, and judge every
candidate with the whole test file (44.44% of wrong fixes pass the target node; the whole file catches
56.25% of them). That is the only step that is both unblocked and measurable today — and it is the
necessary condition for anything downstream, including the blocked ones.

**§6 is not met.** Nothing here claims otherwise.
