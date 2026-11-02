# PR0 execution record — the creature is started — 2026-11-02

**Authority: NONE.** Zero capability, ownership, benchmark, terminal or sentience credit
follows from this document or from the code it records. A creature that ran is not a creature
that proved anything. Spend $0. Model dependency 0.

This is the execution record for PR0 of `OPTIMAL_PLAN_20261102_V2.md`: **start the creature.**
The finding that motivated it is `CREATURE_NEVER_STARTED_20261102_V1.md`.

---

## 1. What was true before this change

Three modules, each passing its own tests, none ever started:

| module | tests | why it never ran |
|---|---:|---|
| `continuous_self_v1` | 10 | no `__main__`; `ContinuousSelf(` appeared only inside its own test |
| `creature_stakes_and_initiative_v1` | 16 | `choose()`/`work()` had zero non-test callers; `main()` prints a report, is not a loop |
| `ignorance_ledger_v1` | 13 | `open_gaps()` classified ORPHAN |

So `continuous-self.yml` and `creature-stakes.yml` proved on every PR that a creature *would*
survive a kill and *would* be changed by its history — and no creature existed to kill.

## 2. What this change adds

One new module, one new test file, one new workflow, one gitignore line. **Purely additive:**
nothing that existed before imports `creature_v1`, and no `SCHEMA` collides.

| file | what it is |
|---|---|
| `canonical/runtime/creature_v1.py` | the composition. `next_task` ← `choose(standing, obligations)`; `obligations` ← `ignorance_ledger.rank()`; `perform` → `live_brain_route_admission.solve`; outcome → `standing.record()` **and** `ledger.resolve()`. Has the `__main__` the substrate lacked. |
| `canonical/tests/test_creature_v1.py` | **12 tests**, negative-control style (§4) |
| `.github/workflows/the-creature-actually-runs.yml` | the switch. `workflow_dispatch` + `pull_request`. **Not scheduled** — see §6. |
| `.gitignore` | `canonical/astra_runtime/state/creature_v1/` — continuity carried as an artifact, never committed, exactly like the durable learning store |

The last two edges in `perform` are the ones that make it a creature rather than a runner:
`standing.record` makes the next choice a function of this one, and `ledger.resolve` teaches the
ledger which ignorance mattered — without it, the ledger's own docstring applies: *"rank() is a
guess dressed up as a calculation."*

## 3. Measured on this change

| measurement | result |
|---|---|
| `test_creature_v1.py` | **12 passed** |
| composed modules, re-run for regression | `continuous_self` **10**, `stakes` **16**, `ignorance_ledger` **13**, `self_prediction_calibration` **14** — all still pass |
| `repo_integrity_guard_v1.py` (static+diff) | **17 rules, 0 violations, PASS** |
| ruff `--select E,F,W` (the gate's invocation) | **0 F-rules**; 120 E501, which is house style — the merged siblings carry 23–31 each |
| census, `--root canonical/runtime` | **8 symbols moved ORPHAN → LIVE**: `ContinuousSelf`, `install_signal_handlers`, `open_gaps`, `Standing`, `StandingStore`, `Obligation`, `choose`, `compare_selection`, `work` |
| `--report` on the REAL tracked ledger | 82 open obligations; own criterion **10.06 vs random 7.74, ×1.30, own_beats_random=True**; tracked ledger hash **unchanged** |

The ×1.30 is on the real 82-gap ledger, not the `demonstration_ledger()` fixture whose ×2.0 is
what was on record before. It is a smaller number and a real one.

## 4. The tests are negative controls, in house style

Every property here is cheap to fake, so each is judged by the thing that would expose a fake:

* **DECISIVE** `test_a_history_of_failure_changes_what_it_does_next` — two creatures, identical
  ledgers, opposite verdicts. Same posture ⇒ `record` is wired to nothing and the stakes are
  decoration. Asserts good→BOLD, bad→CAUTIOUS.
* **DECISIVE** `test_it_survives_being_killed_and_comes_back_as_the_same_creature` — SIGKILL
  mid-task **through the composition**, in a subprocess. Must resume as the same identity with
  the in-flight gap INTERRUPTED.
* **HONEST** `test_it_never_invents_work_when_it_knows_nothing` — empty ledger idles;
  `demonstration_ledger()` is not reachable from a run.
* **HONEST** `test_a_failure_of_this_box_is_not_recorded_as_a_failure_of_the_creature` — an
  environment blocker changes neither posture nor ledger.
* **ISOLATION** `test_a_run_against_a_temp_ledger_never_writes_the_tracked_one` — sha256 of the
  tracked ledger before/after.
* plus: the ledger learns (pass resolves+helps, fail retries), an exception is *unverified* not
  *wrong*, standing carries across two lives, a fresh CLI start is **epoch 1** not 2, and a
  saturated budget is reported as the non-comparison it is.

## 5. The defect the tests caught while being written

`test_a_fresh_start_through_main_is_epoch_one_not_two` failed on first run: a fresh birth
reported **epoch 2** with a phantom `RESUME` journal row. Root cause: `ContinuousSelf.run()`
already calls `resume()` on its first line, and `Creature.run()` called it again first. On a real
restart the first resume consumed the interrupted-work record before the second could report it —
so the kill test would have under-reported. The epoch is the one number a continuity module must
not misreport. Fixed by removing the extra `resume()` and reading the result from the loop's own
return value; standing now loads lazily after identity settles. Journal is now `BIRTH, STOP`.

This is recorded because it is the point of the negative controls: the double-resume was invisible
to every library-level test and only a test that drove the **process path** caught it.

## 6. What this change deliberately does NOT do

* **It is not scheduled.** A cron trigger would give the machine a standing reason to act on its
  own initiative between invocations. What it is permitted to initiate is the owner's decision
  (`OPTIMAL_PLAN_20261102_V2.md` §7.3), not an agent's. The workflow proves it runs; it does not
  turn it loose. Adding the schedule + artifact-carry that makes it persist across days is the
  owner's call.
* **It registers no capability.** `BOUND_CAPABILITY_REGISTRY_V1.json` is untouched. The creature
  is a composition of existing capabilities, not a new one, and `AGENTS.md` rule 5 forbids
  self-registration.
* **It claims no sentience.** `terminal_authority` is false throughout; the run row carries
  `NO_SENTIENCE_OR_EXPERIENCE_IS_MEASURED_OR_CLAIMED`. The claim is the one
  `creature_stakes_and_initiative_v1` already states: *the state changes behaviour, the weakest
  property a thing can have and still be a thing.*
* **It does not widen any tolerance or flip any family.** No acceptance row moves.

## 7. What would falsify this record

* `python3 -m pytest canonical/tests/test_creature_v1.py` not 12-passed.
* `grep -rn "ContinuousSelf(" --include=*.py . | grep -v canonical/tests/` returning nothing —
  then the creature is still only instantiated by tests and §3's census delta is wrong.
* `python3 -m canonical.runtime.creature_v1 --report --json --ledger <tracked>` changing the
  tracked ledger's hash.
* A fresh `--max-steps 0` start reporting `epoch != 1`, or a journal containing `RESUME` before
  any `BIRTH`.
