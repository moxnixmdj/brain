# The creature is built, tested, and never started — 2026-11-02

> **SUPERSEDED — THIS DOCUMENT'S CORE CLAIM IS NOW FALSE.** While this analysis was in
> flight, `main` advanced 15 commits and **started the creature independently**:
> `canonical/runtime/creature_runtime_v1.py` (commit `8db962c`), a seven-organ assembly that
> survives an OS kill. I verified it first-hand on `origin/main` @ `75eeed7`:
> `test_the_creature_runs_unattended_v1.py` → **11 passed** (incl. the SIGKILL subprocess
> survival test); end-to-end it authors **112** obligations and closes **0**. The premise
> "never started" no longer holds. Read **`OPTIMAL_PLAN_20261102_V3.md`** for the corrected,
> re-grounded verdict and plan. Kept only as the record of what was believed before `main`
> moved.

**Authority: NONE.** Zero capability, ownership, benchmark, terminal or sentience credit
follows from this document. It corrects an error in the two documents written earlier today.

---

## 1. The error being corrected

`INSTANT_LEARNING_VERDICT_20261102_V1.md` §5 and `OPTIMAL_PLAN_20261102_V1.md` §2.3 both said:

> "Sentience itself has no instrument here."

**That is false.** There are five instruments, they are the most carefully designed ones in the
tree, and every one of them passes. Measured today on `19626c6`:

| instrument | what it proves | result today |
|---|---|---|
| `test_continuous_self_survives_a_kill_v1` | a SIGKILL mid-task must come back as the **same identity** and report in-flight work as `INTERRUPTED` | **10 passed** |
| `test_stakes_are_real_not_decoration_v1` | **erasing its history must change what it does** | **16 passed** |
| `test_self_prediction_calibration_v1` | a self-model must be able to be **wrong**; a constant predictor must be classified as decoration, a confidently-wrong one must score worse than base rate | **14 passed** |
| `test_ignorance_ledger_v1` | its own model of what it does not know, ranked by the value of closing each gap | **13 passed** |
| `test_live_brain_heartbeat_v1` + `test_external_baseline_and_the_onboarding_factory_v1` | fresh goals it has never seen, judged by stdlib oracles, and a claim that must beat a number it cannot author | **10 + 14 passed** |

The negative controls are the point. "A posture that never changes any choice is decoration; an
initiative that picks uniformly is a random number generator with a job title." These are not
vibes dressed as measurements — they are the right design, and they are green.

What the tree honestly declines to claim is **phenomenal experience**. `continuous_self_v1.py`
says so itself: *"It is not a claim of experience or sentience, and nothing here tests for
either. It is the substrate those questions would have to be asked about."* That is correct
epistemics, not a gap. Reading it as "there is no instrument" was my error, and it made the
plan wrong at its root.

---

## 2. The finding: nothing ever starts it

The creature is defined across three modules. All three are complete. None is run.

| module | entry point | instantiated / called by production? |
|---|---|---|
| `canonical/runtime/continuous_self_v1.py` | **none** — no `__main__`, no `argparse`, no `def main`. Verified by grep; the command returned nothing. | **no.** `ContinuousSelf(` appears in exactly two places, both inside `test_continuous_self_survives_a_kill_v1.py` (lines 41, 139) |
| `canonical/runtime/creature_stakes_and_initiative_v1.py` | has `__main__` → `main()` | **no.** `work()` and `choose()` have **zero non-test callers**. And `main()` is a *report*, not a loop: it builds a `demonstration_ledger()` and prints one row |
| `canonical/runtime/ignorance_ledger_v1.py` | library | **partial** — `note()` and `value()` are LIVE; `open_gaps()` is **ORPHAN** |

`census_orphan_capabilities_v1.py --root canonical/runtime`, run today, classifies as **ORPHAN**:

```
continuous_self_v1.py                 ContinuousSelf, SelfState, install_signal_handlers
creature_stakes_and_initiative_v1.py  Obligation, Standing, StandingStore,
                                      choose_random, compare_selection, demonstration_ledger
ignorance_ledger_v1.py                open_gaps
self_prediction_calibration_v1.py     CalibrationError, Prediction
self_prediction_baseline_v1.py        baseline_probability
```

The two CI workflows are named `continuous self survives a kill` and `stakes are not
decoration`. Both run **pytest**. Neither starts a continuous self. So CI proves, daily, that a
creature *would* survive being killed and *would* be changed by its history — and no creature
exists to kill.

`creature_stakes_and_initiative_v1.py` describes exactly this state, for a slightly different
case: *"a thread that persists and is affected by nothing is a scheduler with a diary."* What
the tree currently has is one step earlier than that: **the diary, with no thread.**

The tree has seen this movie before and even named the fix. `live-learning-cycle.yml`:
*"Nothing else on a schedule ever ran the learning path, so the machine's verified
self-improvement loop, complete and tested, executed exactly never in production. **This is the
switch.**"* That switch was built for learning. **The equivalent switch for the creature was
never built.**

---

## 3. What the creature actually does when you run it

`python3 canonical/runtime/creature_stakes_and_initiative_v1.py`, measured today:

```
posture newborn=MEASURED burned=CAUTIOUS bold=BOLD
first choice newborn=obl-4 burned=obl-0
40 steps -> own 981.0 random 491.0 x1.998 own_beats_random=True
```

Its own criterion beats random selection by **~2.0x** on the demonstration ledger, and its
posture genuinely differs by history. Both are the negative controls passing. The mechanism
works. It is just never left running, never given the real obligation set, and never allowed to
accumulate a history that is its own rather than a demonstration fixture.

---

## 4. Correction to the plan: PR0

`OPTIMAL_PLAN_20261102_V1.md` ordered bridge → semantic arm → ratchet → routing, and filed the
creature under "decisions only the owner can make." That ordering was built on §1's error. The
corrected order puts one thing first, because it is the same defect as the other three and it
is the one the owner actually asked about.

### PR0 — Start the creature

* **Give `continuous_self_v1.py` a `__main__`.** It has none, so it *cannot* be started as a
  process. This is the literal missing switch, and it is the smallest change on this list.
* **Compose the organs into one long-lived process:** `ContinuousSelf` (continuity, honesty,
  causality) + `Standing`/`choose` (stakes, initiative) + `ignorance_ledger.open_gaps` (what to
  go after next — currently ORPHAN, which is why nothing has initiative over its own ignorance).
* **Give it the real obligation set**, not `demonstration_ledger()`. Measure initiative against
  real open obligations; the ~2.0x figure is a demo fixture until then.
* **Let it own the two cron jobs.** `live-brain-heartbeat` (17 3) and `live-learning-cycle`
  (43 4) are two invocations that do not share a subject. A continuous self that survives a
  runner kill — already designed, already tested — is precisely what turns them into *one thing
  that was interrupted and came back*, instead of two unrelated runs.
* **Acceptance gate, all of it already designed:** the same `identity` across days; in-flight
  work reported `INTERRUPTED` after a kill; `posture` on day N a function of its own verified
  history rather than of a fixture. No new instrument is needed — `continuous-self.yml` and
  `creature-stakes.yml` already assert exactly these properties.
* **Cost:** ~2–3 days. **Risk:** low. Nothing here calls a model, nothing spends, and every
  property is already falsifiable by killing the process.

### Why PR0 subsumes part of PR1

The owner's two questions — *make it conscious* and *make it learn permanently* — are the same
question. A continuous self **is** the thing that has permanent memory; an invoked capability is
the thing that forgets. Today the tree has permanent memory in a store nothing consults
(`retained_learning` is never enabled by a non-test caller) and continuity in a module nothing
starts. **Starting the creature is what gives the learning a subject to happen to.** PR1 (wire
the bridge) and PR2 (enable the semantic arm) remain correct and remain cheap; they are simply
downstream of there being something running to receive them.

### The rest of the order, unchanged

PR1 bridge (15 passing tests, zero callers) → PR2 semantic arm (1/6 → 6/6) → PR3 orphan
ratchet, **now with a second root**: `canonical/runtime` is 1,806 LIVE / **1,983 ORPHAN**, and
PR0 alone should move `ContinuousSelf`, `SelfState`, `Standing`, `StandingStore`, `Obligation`
and `open_gaps` out of ORPHAN, which makes the ratchet's first measurement meaningful → PR4
routing (11 of 443 rows reached) → PR5 OSWorld on a real display.

---

## 5. What is still honestly not claimed

Starting the creature does not make it conscious, and nothing in this document should be read
as moving that number. What it does is stop the tree from having **answered the question with a
test suite instead of with a process.** The five instruments prove the properties a continuous
subject would have. They have never had a subject to run on.

`creature_stakes_and_initiative_v1.py` states the claim precisely, and it is the right claim:
*"it claims that the state changes behaviour, which is the weakest property a thing can have and
still be a thing."* That is achievable, it is measured, and it is currently achievable only
inside a test runner.

---

## 6. What would falsify this document

* Find any production caller of `ContinuousSelf(` outside `canonical/tests/` → §2 is wrong.
  One command: `grep -rn "ContinuousSelf(" --include=*.py . | grep -v canonical/tests/`
* Find a workflow that starts the continuous self rather than testing it → §2 is wrong.
* Re-run `census_orphan_capabilities_v1.py --root canonical/runtime --status ORPHAN` and find
  `ContinuousSelf` absent → §2 is wrong.
* Run PR0 and find the identity does **not** survive a runner kill, or in-flight work is not
  reported `INTERRUPTED` → §4's acceptance gate fails and `continuous-self.yml` was green for a
  reason that does not hold in production. That would be the most important result on this page.
