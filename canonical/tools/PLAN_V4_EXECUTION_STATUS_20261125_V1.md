# Plan v4 execution: the deletion step, done

**Date:** 2026-11-25. **Authority:** NONE (producer-run sandbox).
Execution record for `THE_SMARTEST_PLAN_V4_ELON_20261125_V1.md`.

## Step 1: DELETE the falsified JitRL dead code — DONE

Plan v4 §2: "JitRL `use_advantage` code (plan v3) — dead code; delete."
Removed from `canonical/runtime/transfer_learning_v1.py`: the `use_advantage`/`beta`
parameters of `recall` and `drive`, the advantage-scoring block, the docstring
paragraph, and the call-site threading. `recall` is back to its original single
`score = sim * evidence` ranking. No residual references repo-wide.

**Verification (insanely fast, all green):**
- `test_transfer_learning_v1.py`: 28 passed
- `test_transfer_new_instance_probe_20261103.py` + `test_transfer_learning_off_control_v1.py`
  + `test_changed_state_transfer_benchmark_v1.py`: 15 passed, 2 subtests
- 15-case probe re-run: **8/15 genuine saving, 6.333× trials, 2.259× acts, 0/15 worse** —
  identical to the pre-deletion baseline. The deletion is behavior-neutral, as a
  falsified opt-in default-off path must be.
- `recall` speed unchanged: 0.028 ms/call.

## Step 2: AUDIT the three giants for deletion — VERDICT: all load-bearing, they stay

Falsifier #4 said: "If a 'complex' module is actually load-bearing, it stays (and that
is a finding)." It fired for all three:

| module | lines | importers | verdict |
|---|---|---|---|
| `astra_runtime.py` | 7,780 | **48 files** | load-bearing, stays |
| `goal_compiler.py` | 7,554 | **84 files** | load-bearing, stays |
| `live_brain_route_admission_v1.py` | 7,292 | **193 files** | load-bearing, stays |

(The import scan used unanchored grep, catching lazy in-function imports.)

**What this means.** The 558K-line mass is not a pile of dead weight — it is a dense
dependency graph, and deletion at the top of it would cascade. The deletable parts are
exactly the parts nothing imports: the falsified experiments. That is the honest form
of "best part is no part" for this repo — **delete the falsified, keep the load-bearing**,
and let falsifiers decide which is which. A future deletion pass must go bottom-up
(leaf modules with zero importers), not top-down.

## Scorecard update

| plan v4 item | status |
|---|---|
| §2 delete JitRL dead code | **DONE** (behavior-neutral, 43 tests green) |
| §2 audit giants for deletion | **DONE** — all load-bearing, no deletion |
| §2 do-not-promote angelic engine / leave certificates / weight-space moot | standing (unchanged from v3) |
| §4 Idea 1 minimal loop (recall→synthesize→verify) | untested — needs the repair corpus (blocked on HF data, as in v2/v3) |
| §4 Idea 2 speed gate (ms + tokens per mechanism) | **PARTIALLY APPLIED** — measured set: recall 0.028 ms, OE 1.69 ms, stochastic 41.62 ms, ensemble 171 ms; all zero tokens |

Reach remains **0 passes** on the certified HARD-51. Deletion removed no capability
(it removed a falsified ranking experiment) and the probe baseline is untouched.
