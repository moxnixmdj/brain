# SWE-bench Pro V2: the first measured run is 0/3, and the harness is what makes that readable

*Round dated 2026-11-25. Receipt: `canonical/verification/SWE_PRO_V2_SMOKE3_20261125_V1.json`.
Tools: `canonical/eval/harbor/swe_pro_v2_ci.py`, `canonical/eval/harbor/swebench_pro_v2_agent.py`,
`canonical/tools/swe_pro_v2_run_receipt_v1.py`. Tests: 23 green (receipt 5, harness 16, kernel shape-laws 2).
One real CI run, 3 official tasks × 3 arms, inside the pinned official container images,
0 model calls, $0.00, 22 m 45 s of runner time.*

---

## 0. The answer on one page

Step 3 of the last plan said: *fire the GitHub Actions Docker eval and publish hard, reproducible
$0.00-spend numbers next to the frontier scores.* It fired, four times, and this is what came back.

| measured | result |
|---|---|
| benchmark | SWE-bench Pro **V2**, `v2/hard51_ids.txt` subset — 3 qutebrowser tasks (a smoke set, not the set) |
| container images | `ghcr.io/scaleapi/swe-bench_pro-v2:<instance>`, pulled anonymously, upstream pinned at `31a20c7` |
| who graded | each task's **own** verifier, inside the task's own container. Nothing in this repo grades a fix |
| **causal arm (our engine)** | **0 / 3 resolved (0.0 %)** — and 0 / 2 when the one trial that died in the harness is excluded |
| `nop` control | 0 / 3 ✓ (the tests are not free) |
| `oracle` control (reference patch) | 3 / 3 ✓ (the tests are not impossible) |
| gates in the same job config | `oracle_gate_pass: PASS`, `nop_gate_pass: PASS` |
| model calls, cost | **0, $0.00**, asserted per trial by the agent and re-summed by the collector |
| engine wall time | 3.54 s per task recorded (see §4 — this number is under audit) |
| what the engine actually did | 1 × `EDITS_UPLOADED` (its own status said `PASS`, 1 file changed, verifier said 0.0), 1 × `NO_EDITS` (`FAIL_CLOSED`), 1 × `HARNESS_ERROR` |
| is §6 met | **NO.** Not close |

The result is a zero. It is the kind of zero that is worth having: produced by official images,
official tests, with both controls green, in a job anyone can re-run from this branch. Three
earlier runs of the same harness also printed `0 / 3` — and meant *nothing*, because no trial
had been read at all. §2 is about telling those two zeros apart, which turned out to be the
harder engineering problem than making the engine patch anything.

---

## 1. Two zeros that look identical and are not

```
run 45635668245   causal 0/3   nop 0/3   oracle 0/3   ←  oracle 0/3 is IMPOSSIBLE upstream (642/642 certified)
run 45644331703   causal 0/3   nop 0/3   oracle 3/3   ←  the first number that means 0/3
```

In the first three runs every job was green and every arm scored nothing. The only field that
distinguished them was a control that could not possibly fail — the reference patch — and it took
two more rounds of instrumentation to find why the report couldn't say so itself:

- the collector counted its **own `NOT_RUN` placeholders** as reported rows, so the machine-readable
  report of a void run said `run_produced_number: true` while the markdown was right to shout;
- harbor builds a trial's name from the task name **truncated to 32 characters**
  (`models/trial/config.py: generate_trial_name() → f"{task_name[:32].rstrip('_-')}__{ShortUUID(7)}"`)
  while the manifest ids are 105 characters (`…-v<sha>`). Keying trials by the name in
  `result.json` produced three real rows under three names the manifest didn't recognise, and all
  three expected ids fell back to placeholders. `n_reported: 3` and `missing_trials: 3` simultaneously.

The fix is not "match harder": `resolve_task_id` accepts an exact id, then an **unambiguous** prefix
relation in either direction, and anything left over is kept as an extra row and listed under
`unmatched_trial_keys`, with a named section in the markdown. A scored trial can no longer be
silently dropped, and an ambiguous one is reported as unresolved rather than guessed.

## 2. The receipt, because a table is not a claim

`canonical/tools/swe_pro_v2_run_receipt_v1.py` decides *whether a run may be quoted at all*. It
recomputes produced-ness from per-task rows instead of trusting the report's flag (§1 is exactly
what happens when a receipt inherits a wrong flag), nulls out `resolved` and `resolve_rate_pct`
when no trial was read, and states its rule in one line: **quotable ⇔ rows were read and the
reason list is empty.** Reasons it will emit: `NO_TRIAL_DATA`, `ORACLE_GATE`, `NOP_GATE`,
`MODEL_CALLS`, `COST`, `ATTRIBUTION`, `*_CONTROL_DIRTIED`.

On the void runs it said `NO_MEASUREMENT__HARNESS_ONLY`, and it refused to also accuse the controls
of being broken, because they were never exercised. On this run it says
`OFFICIAL_TASK_VERDICTS__GATES_PASSED`, `claimable: true`, `reasons: []`.

## 3. What the 0/3 says about the engine

One row of the three is a genuine engine result, and it is the interesting one:

- the engine **produced a patch and believed it**: `engine_result_status: PASS`, one file rewritten
  via `tree-mutation`, uploaded into the container — and the task's own tests said `0.0`.
- that is the same failure mode §9.5 warns about in a different costume: our internal check is not
  the hidden oracle. The engine's `PASS` means "my reconstruction of the demand is satisfied", not
  "the graded behaviour is satisfied". Nothing about this run supports the claim that a self-check
  substitutes for the task's test.
- `FAIL_CLOSED` on the second task is the new shape-law doing its job: with a green suite and no
  defect evidence it refused to write anything, rather than emitting a guess. Correct behaviour,
  and it still scores 0. Refusal is not a patch.
- `HARNESS_ERROR` on the third is ours, not the engine's: counted in the benchmark rate, excluded
  from the engine's own denominator, and the cause is now captured (this run pre-dated the field).

3 tasks of 51 is not a resolve rate for anything. It is a proof that the measurement pipeline
works, on the hardest open set we could actually run, and a first real counterexample for the
engine's self-judgement.

## 4. Open, unresolved, stated plainly

- **Wall time.** The causal arm reports 3.54 s mean trial wall; the `nop` control reports 48.62 s
  under the same configuration. One of those is not what it looks like. `agent_seconds` (engine time)
  and harbor's trial span are now separate columns and separate totals, so the next run says which
  is which instead of averaging two quantities into one. Until then **no speed claim is made** —
  neither 0.35 s nor 3.5 s is quotable from this evidence.
- **Diagnosed on the following run** (`080753b7`): the `HARNESS_ERROR` was
  `URLError: <urlopen error [Errno 111] Connection refused>` — a fallback path inside the engine
  reached for the network even though `inputs["allow_web"] = False` was set. So the flag was
  *declared* and not *enforced*, and one trial's capability question turned into a plumbing error
  that scored 0 for a reason that says nothing about the solver. The harness now refuses
  outbound connects in-process while `allow_web` is false, counts the attempts, and prints the
  count in the report (`network_guard: enforced`, `network_attempts: N`). What is still open is
  *which* engine path needed the fetch, and that answer is in §4b.
- `materialize` writes task dirs whose names differ from the ids in the manifest's own report keys
  (105-char `-v<sha>` form). Reconciled by tolerant matching; still worth pinning at the source.
- n = 1 trial per task. No variance estimate.
- The `hard51` list is vendored and re-diffed against upstream `31a20c7` in CI (byte-identical,
  verified twice), but the 51-task number itself has not been run yet.

## 4b. The fetch was never about the web

The guard found the path, and the path was not a knowledge lookup: `_http_json_request` in
`canonical/runtime/epistemic_scan_acquire_compress_v1.py` probes the *environment's own* HTTP
service (`/openapi.json`, `/token`) as part of learning an API by observation. Nothing was
listening inside the runner, so the transport raised `URLError: [Errno 111]`, the function had a
handler for `HTTPError` (a response) and none for `URLError` (no response), and the exception aborted
the whole solve.

Two laws fall out of that, and they are not the same law:

1. **An unreachable service is a fact, not an error.** `_http_json_request` now returns
   `(0, {"error": "unreachable", "reason": …, "url": …})` for `URLError`/`OSError`, so the gap stays
   open and the rest of the solve continues; a 401 or a 404 is still returned as the response it is,
   because a reply *is* evidence. Tests: `test_unreachable_service_is_a_fact_not_an_error_v1.py` (5,
   including a live loopback server proving real replies are not swallowed and a raw `OSError` case).
2. **`allow_web` means no external knowledge, not no IPC.** The first version of the harness guard
   refused *every* outbound connect, which would have blocked the engine from probing a service it
   started itself — a capability quietly deleted in the name of a constraint. The guard now refuses
   non-loopback addresses only, decided on the literal address (no DNS: resolving a name in order to
   decide would itself be a lookup), and treats unix socket paths as local. That distinction is the
   test `test_the_guard_blocks_the_web_and_leaves_the_environment_alone`.

Worth stating precisely, because it changes the verdict on the engine: the probe is not a
hallucinated endpoint. `acquire_missing_knowledge` only reaches for `http_spec` when the scan
manifest *declares* `http.base_url` and the goal vocabulary is about HTTP — so the environment
declared a service and the service was not there. The correct handling of "declared but dead" is
exactly what fix (1) now does: record it, keep the gap open, spend nothing more on it.

## 5. Corrections to what earlier rounds asserted

| earlier claim | status now |
|---|---|
| "run the eval by `workflow_dispatch`" | **failed here**: this sandbox's token gets HTTP 403 on dispatch. Eval mode is armed by a one-shot marker file consumed by the aggregate job, so a push queues exactly one run |
| "add a `swe-bench-pro-v2-eval.yml` workflow" | **dead**: this repo carries 728 workflow files and new ones do not register (404 on the API). The jobs live in the registered `engine-docker-eval.yml` |
| "Terminal-Bench 4.0" | **corrected**: 4.1 is current (released 2026-11-09, regrades 4.0 trials) |
| "Harbor, whatever is installed" | **pinned**: 0.22.0, the version upstream's own `v2/GATE.md` certified the images with |
| frontier scores from aggregator sites (Muse Spark 1.1 61.5 %, Opus 5.5 64.8 / 99.4 etc.) | **unverified third-party**, different sets and cut-offs; not comparable to our 0/3 and never placed beside it as if they were |
| "engine is un-gated and ready for the benchmark" | **partly false**: it is un-gated and it runs, and it resolves 0 of 2 attributable tasks. §6 is not met; §11.1 (live numbers beside the frontier) now exists as a mechanism with one measurement in it |

## 6. Rejected alternatives, and why

- **Report `0/3` as "SWE-bench Pro: 0 %"** — that would be a lie in the other direction: 3 tasks
  from a 51-task subset of a 642-task benchmark is not a benchmark score. The title of this file is
  the claim; nothing larger is made.
- **Retry the dispatch API with a different scope, or create a new workflow file** — both measured
  as unavailable, and the marker path is already built, tested and used five times.
- **Have the aggregate job "fix" the truncation mismatch by string-similarity heuristics** — a
  fuzzy match between a task and its own grading is exactly the leakage-shaped hole §6 forbids.
  Prefix matching is exact-or-nothing and ambiguous cases are reported, not resolved.
- **Let `status: PASS` from the engine count toward a fix** — the harness has never accepted the
  agent's word for anything; only `verifier/reward.txt` / `verifier_result` sets `resolved`.

---

## Next, in order

1. re-run smoke3 with the attribution and error fields live (one marker commit) — confirms the
   `HARNESS_ERROR` cause and the wall-time split;
2. `swe-pro-v2-hard51` at `shards=6`, all three arms — the first number with a real denominator;
3. take the two failure shapes (`PASS`-but-rejected, `FAIL_CLOSED`) back to the engine as the
   bottleneck they actually are: the self-check is not the oracle, and a refusal to patch scores 0
   exactly like a wrong patch does.
