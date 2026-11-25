# SWE-bench Pro V2, HARD-51: the engine resolves 0 of 51, and 44 of those 51 are one specific kind of 0

*Rounds dated 2026-11-25. Receipts: `canonical/verification/SWE_PRO_V2_SMOKE3_20261125_V1.json` (smoke),
and the aggregate report of the 51-task run at `canonical/eval/results/swe-bench-pro-v2/swe-pro-v2-hard51-latest.json`
(eval commit `42111ea2`, results commit for run `20261125T162816Z`).
Tools: `canonical/eval/harbor/swebench_pro_v2_agent.py`, `canonical/eval/harbor/swe_pro_v2_ci.py`,
`canonical/tools/swe_pro_v2_run_receipt_v1.py`. Tests this round: 26 + 5 + 2 green.
Every number below comes from a CI run on GitHub's runners against the pinned official images.
Nothing here is simulated, and nothing here is a success claim.*

---

## 0. The measurement

51 tasks — the whole `v2/hard51_ids.txt` set, vendored and byte-diffed against upstream at the pinned
release `31a20c7` — three arms, 6 shards, one attempt each, official container images, each task graded
by **its own** test inside its own container.

| arm | resolved | rate | model calls | cost | trial wall s | engine wall s |
|---|---|---|---|---|---|---|
| **causal (our engine, un-gated)** | **0 / 51** | **0.0 %** | **0** | **$0.00** | 7818.5 | 878.1 (≈17.2 s/task) |
| `nop` (do nothing) | 0 / 51 | 0.0 % | 0 | $0.00 | 6900.0 | — |
| `oracle` (upstream's reference patch) | **50 / 51** | 98.0 % | 0 | $0.00 | 7411.3 | — |

`nop_gate_pass: PASS`. `oracle_gate_pass: **FAIL**` — and that FAIL is load-bearing, see §4.

**Therefore this is not yet a quotable benchmark score.** By the rule this project wrote for itself, a
causal number is interpretable only if the reference patch resolves *every* task in the same job
configuration. 50/51 is not 51/51, so the correct public sentence is:

> the engine scored 0 / 51 on SWE-bench Pro V2 HARD-51 in a run whose oracle control came within one
> errored trial of certification; the number is honest, the certification is not yet complete.

What the 0 is made of — this is the part that is worth more than the rate:

| what the engine did | trials | of which resolved |
|---|---|---|
| `NO_EDITS` — refused to write anything (`FAIL_CLOSED` in 43 cases) | 44 | 0 |
| `EDITS_UPLOADED` — patched, and its own status said `PASS` | 3 | **0** |
| `HARNESS_ERROR` — our guard aborted the trial (§3) | 4 | 0 |

Engine-attributable denominator: 47. **0 / 47.** A refusal and a wrong patch score identically, and the
run says which is which.

## 1. The three tasks where the engine actually tried

| repo | files changed | engine's self-status | verifier | engine seconds |
|---|---|---|---|---|
| teleport (Go) | 1 | `PASS` | 0.0 | 132.1 |
| webclients (TypeScript) | 1 | `PASS` | 0.0 | 254.3 |
| qutebrowser (Python) | 1 | `PASS` | 0.0 | 53.0 |

Three patches, each one file, each one *accepted by the engine's own verification and rejected by the
task's*. This is §9.5's warning measured rather than asserted: an internal check that "the demand I
reconstructed is satisfied" is not the hidden oracle, and a `PASS` from inside the house is worth nothing
on a board. It is also the cleanest statement of the gap: **when the engine acts, it is confidently
wrong; when it does not act, it is honestly stuck.** Both are 0.0, and only one of them is respectable.

## 2. 44 refusals are Wall 1, at benchmark scale, with a distribution

Per-repo breakdown of `NO_EDITS`:

| repo | tasks | refused | patched | harness error |
|---|---|---|---|---|
| ansible (Python) | 8 | 7 | 0 | 1 |
| openlibrary (Python) | 8 | 8 | 0 | 0 |
| flipt (Go) | 7 | 5 | 0 | 2 |
| teleport (Go) | 6 | 5 | 1 | 0 |
| webclients (TS) | 5 | 4 | 1 | 0 |
| element-web (TS) | 4 | 4 | 0 | 0 |
| vuls (Go) | 4 | 4 | 0 | 0 |
| qutebrowser (Python) | 4 | 2 | 1 | 1 |
| navidrome (Go) | 3 | 3 | 0 | 0 |
| NodeBB (JS) | 1 | 1 | 0 | 0 |
| tutanota (TS) | 1 | 1 | 0 | 0 |

Every one of those refusals carries the same note: `store: STORE_FILE_ABSENT`, `engine said:
FAIL_CLOSED`. Two facts follow, and they are the reason this run is worth having.

1. **The refusal is the shape-law, not a crash.** With the instruction and a green suite there is no
   failing test to bind a demand to, and the engine now refuses instead of guessing (`NO_DEFECT_EVIDENCE`
   / `ALREADY_PASSING__NO_PATCH`, the behaviour pinned in
   `canonical/tests/test_workspace_shape_selects_swe_modality_and_no_patch_fails_closed_v1.py`). The
   benchmark showed the law firing 43 out of 43 times it applied. Correct behaviour, 0.0 score.
2. **This run is the ablated-store condition, whether or not it was meant to be.** `STORE_FILE_ABSENT`
   means every task started with no external knowledge: the store did not exist for shard jobs, so
   the 0/51 is *the empty-store arm* of the §6 memory ablation, not "the system with its memory". The
   with-store arm has not been measured yet, and no claim in this file may be read as if it had.

So the bottleneck is not the generator's reach, it is the absence of a selection gradient — the exact
thing "Metamorphic Witness Splitters" (Idea 1 of the current plan) exists to manufacture from the
repo's own passing tests. This run prices that work: without a failing test the engine writes nothing
in 86 % of real hard tasks, and the score is 0.0 %.

## 3. What our own instrumentation did to the number (and the fix)

Four trials died as `HARNESS_ERROR` with `NetworkRefusedByHarness: outbound connect refused`. That is
the harness's `allow_web=False` guard — added one commit earlier to *enforce* what the engine had only
been told — refusing an outbound connect made by the acquisition layer.

The two fixes composed badly, and the run is what proved it: `_http_json_request` was just taught that
"no reply from the network" is a fact about the environment (returns `(0, {"error": "unreachable"})`),
but it recognises that fact only as a `urllib.error.URLError`, and my refusal derived from
`RuntimeError`. So the guard invented a new failure mode instead of being a constraint. It now derives
from `URLError`, and a refusal is handled by exactly the code path a real transport failure uses, while
still being counted in `network_attempts`. Test:
`test_the_guard_refusal_is_a_transport_failure_so_callers_already_handle_it`.

Read narrowly: 4 of 51 trials were lost to our plumbing, 47 were the engine's, and the rate is 0 either
way. Read honestly: an instrument that changes what it measures has to be measured too, and it costs 8 %
of the sample here.

## 4. Why the oracle gate is at 50/51, and why that is not a technicality

The one failing oracle trial is `instance_gravitational__teleport-f432a71a…`: `reward: None`,
`exception: RuntimeError`, 21.5 s — the trial *errored*, it did not grade a gold patch as wrong.
Upstream's `v2/GATE.md` certifies the reference patch 642/642 on their own runner (Modal, 50
concurrent). On GitHub runners, one Go-monorepo control trial did not complete.

The gate rule refuses to let that pass as "close enough". If a control arm can lose a trial to the
environment, then a 0 in the causal arm is not known to mean "the tests rejected the patch" — it might
mean "this runner could not run this task". The gate is what distinguishes a score from an artifact of
the rig, so it fails closed at 50/51 and the run is marked not certifiable. Re-running to obtain a
clean 51/51 is the next measurement step, not a rephrasing of this one.

## 5. Corrections, in this round's own wake

| claim | status |
|---|---|
| "the harness can run the official benchmark" | **verified now**, end to end, 153 trials in one run, artifacts and per-task verdicts committed by CI |
| "the causal arm's 3.54 s/trial vs nop's 48.6 s discrepancy is engine speed" | **resolved by splitting the columns**: harbor trial wall and `agent_seconds` are separate; engine time is ≈17.2 s/task at scale, trial wall ≈153 s/task |
| "0/3 on a smoke subset" | superseded by 0/51; the smoke set is kept as the harness's own regression case |
| "the guard enforces no-network without side effects" | **false as first written** — see §3, fixed by deriving from `URLError` |
| "Terminal-Bench 4.0" | still corrected: 4.1 is current (2026-11-09); not yet run by us at all |
| "§6 is met" | **NO.** Zero resolve rate, store ablated, one benchmark, no unseen-environment single-experience transfer measured on it |

## 6. Rejected readings of this run

- **Reporting "0 % on SWE-bench Pro"** as if it were a leaderboard row: 51 tasks of a 642-task set,
  one attempt each, empty store, oracle short of certification. Quotable only with all four qualifiers.
- **Reporting "43/51 refusals = the fail-closed law works, so really 43/43 correct"** — a refusal that
  scores 0.0 is a failure against the benchmark. The law being respected is not a result; it is the
  reason the number is clean rather than contaminated by guesses.
- **Retrying the run until the oracle hits 51/51 and treating the first non-certifiable run as void** —
  the re-run has to report both, or the gate is decoration.
- **Seeding the store with knowledge mined from these very repos** to lift the score: that would
  warehouse the benchmark inside the external store, which §2's boundary forbids as squarely as it
  forbids putting it in weights. Store content must come from the house's own experience, and the
  ablation must say which arm is which.

---

## Next, in order

1. re-run `swe-pro-v2-hard51` with the `URLError` composition fix and `conditions` plumbing, aiming at
   an oracle 51/51 and zero guard-induced `HARNESS_ERROR`s; report both runs side by side if the second
   is still short;
2. the store arm of the ablation — and the one temptation this run creates must be refused in writing,
   see §7;
3. Wall 1 as the target it now demonstrably is: a green suite must be turned into a failing oracle from
   the repo's own tests and the instruction's relational words, with no hidden test in sight. The 44
   refusals are the baseline that work has to move, and 0/47 engine-attributable is the floor.

## 7. Why this run's store will not be fed back into the same 51 tasks

The agent already writes its store back (`store_saved`, `skills_newly_admissible` per trial), so the
cheapest possible way to raise the next score is to commit the stores from run N and mount them for
run N+1 on the same tasks. That must not be done, and the reason is not squeamishness:

a skill crystallised from an attempt at task X is a cached *patch for X*. Re-presenting X with that
entry in the store turns the benchmark into a lookup — the exact thing §2 forbids for weights,
forbidden here for the store, because the store is part of the shipped system. The boundary test in
§2 is "can it be added and removed without retraining", not "is it in a .py file"; a store seeded
from the test set passes that test and fails the mission.

What is legitimate, and what will be measured instead:

- **same run, later tasks:** within one run, tasks are attempted in a fixed order and each shard's
  store accumulates as it goes, so any lift is transfer between *different* tasks (and the report
  shows which tasks admitted skills). That effect is already in the 0/51: 43 admissions were possible
  and 43 refusals followed.
- **cross-set transfer:** a store grown on one set of repositories (self-play on passing tests, §9.4.4,
  or a first pass on a disjoint slice of the 642) evaluated on a **disjoint** set. Any transfer claim
  in this project must be of this shape, or it is not a transfer claim.
- **ablation:** empty store vs grown store on the same disjoint evaluation set, reported as a pair.
  Run 20261125T162816Z is the empty arm, and only the empty arm.

## 8. Two follow-up runs, and the law this run has to answer to

**Run 2 (`45654709738`, eval commit `314aa70f`, marker armed by the guard fix): lost to the harness,
and lost silently — which was the worse half.** 15 of 18 shard jobs failed because harbor exits nonzero
when a *task* errors and GitHub runs every step under `bash -e`: the shard aborted before it could
record or publish anything. The aggregate itself succeeded, wrote a report, and then **skipped the
results commit** because the old gate excluded `RUN_FAILED` runs — so the branch showed nothing and the
only trace was in Actions logs, which this sandbox cannot read at all
(`results-receiver.actions.githubusercontent.com` and `*.blob.core.windows.net` both EOF at the network
edge). Fixed by `ff7c7b94`: a failed run is now committed as a report that says it produced no number
(`run_produced_number: false`, `run_failed: true`), the aggregate records what the mode resolver decided
(benchmark, arms, shards, engine budget, `run_failed`) inside the report JSON, and a shard job survives a
nonzero harbor exit (exit code always recorded, one retry) while a collect failure publishes
`COLLECT_FAILED` instead of killing the step that would have reported it. **Silence was the bug**: an
auditable harness has to publish its own failures.

**Run 3 (`45656646429`, eval commit `8098519b`): the re-armed full HARD-51**, with the guard that no
longer throws through the acquisition layer, the budget and commit recorded as conditions, the engine's
`engine_diagnosis` per trial, the receipt generated by CI, and the hardened shard lifecycle. All 18
shard jobs were `in_progress` simultaneously — no pre-failures, unlike run 2 — and its verdict is
reported only when it lands on this branch. A cheap `smoke3` pass (`45663363378`, 3 qutebrowser tasks,
1 shard) is queued behind it to validate the same chain quickly.

**The cross-check that matters.** `canonical/swe_kernel/capability_law_v1.py --pinned` recomputes from
six pinned receipts in this repo (it refuses to run if one is missing or changed) and reports:

```
P(correct behaviour | one action) = P(determined) x P(seen)
  determined 0.5469   seen 0.5445 (density 0.6788 x strength 0.8021)
  operating point: p_correct 0.2978 | value-bearing 0.1167
  leverage: check_density slope 0.5469 controllable -> 0.5469
            check_strength slope 0.3712 controllable -> 0.3712
            determined     slope 0.5445 NOT controllable -> 0.0
```

What that licenses, and what it does not. The law is measured on **one action against a shell
environment with real programs on a real disk**; a HARD-51 trial is a multi-file patch judged by hidden
tests over a whole suite, so `0.2978^k` is **not** an estimate of the SWE resolve rate and I do not use it
as one. What it does say, and says about this repository rather than about a leaderboard, is directional:
the only controllable term is `P(seen)` — how many checks exist and how strong they are — while
`P(determined)` is capped by the observation, and the measured SWE result is dominated by a term the law
does not even model: **44 of 51 tasks never reached an action at all** (`STORE_FILE_ABSENT` →
`FAIL_CLOSED`). So the honest reading of 0/51 against the law is that the run exposes a *pre-action*
failure the lever list does not contain, and the lever for it is store construction and admission, not
`check_density`. Any future claim that "the law predicted the SWE score" would be a category error, and
this document is where it would be caught.

**One path correction, kept visible because the ledger is the memory.** This file lives at the repo
root, which is the convention here (425 sibling `*_V1.md` ledgers); my working note had it under
`canonical/verification/ledgers/`, a directory that does not exist in this repository. The receipt and
the benchmark reports are where they were described: `canonical/verification/SWE_PRO_V2_HARD51_20261125_V1.json`
and `canonical/eval/results/swe-bench-pro-v2/`.
