# First principles, pass seven — what S1, S2 and S3 actually returned

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

This pass ran the three falsifiers from `FIRST_PRINCIPLES_SIX_20261105_V1.md` and reports
the results against the bar the owner set: a change must make the creature **different at
the end of a run than at its start**, and must not cost more than the computation it
replaces. Anything that only reports on itself does not count.

## S1 — does memory pay? **Yes, but only in one regime, and it took three fixes**

Pre-committed branch: if memory costs more than the computation it replaces, delete the
retention path. It did cost more, and it is not deleted — because after removing the costs
the premise turned out to be false in one place and true in another.

Measured, 3 trials each, whole-run wall time:

| configuration | warm (remembering) | cold | verdict |
|---|---|---|---|
| recall as pre-search, duplicate recall sites | 1.63/1.69/1.53 s | 1.26/1.18/1.09 s | **pure tax**, ~0.43 s |
| duplicate removed, still pre-search, small module | 1.23/1.32/1.38 s | 1.27/1.31/1.40 s | no tax, no gain |
| pre-search on a *large* module | 1.54/1.54/1.61 s | 1.29/1.20/1.34 s | **still a tax**, +0.25/+0.34/+0.27 s |
| recall as fallback after search fails | 1.14/1.14/1.22 s | 1.25/1.17/1.22 s | equal or better, same evaluations |

Causes, in the order they were found and fixed:

1. `recall_and_apply_verified` was called **twice per repair** with identical arguments
   (Tier A, then Tier B). One of the two contract-suite evaluations was pure duplication.
2. Recall ran **before** the deterministic synthesizers. That makes it a serial pre-search:
   a miss costs a full suite run and returns nothing. Growing the module did not change the
   sign — the synthesizers scale too.
3. A memo keyed on the world fingerprint was built to remove the duplicate evaluation.
   Once (1) was fixed it changed **no evaluation counts and no timings**, so it was deleted
   rather than shipped. The comment left in `_try_candidate_batch` says so.

Conclusion: **memory as a pre-search is a tax at every size tried; memory as a fallback is
free.** Recall now runs only after the confined candidate batch, the confined multi-file
repair and the coupled zygote repair have all failed on a module.

## S2 — does step *n* consume step *n−1*'s record? **Yes, in the regime that matters**

A taught rule applied in a brand-new world: the `try/except` shape.

    def sub(a, b):            taught once
        try: return a - b
        except TypeError: return 0

    def mul(a, b):            a later, different world
        try: return a - b
        except TypeError: return 0

The lesson is applied to a module it was never shown, and the repaired code passes a
held-out input (`mul(10, 20) == 30`) that neither the lesson nor the test contained.
Direct recall also carries a taught `@property` rule to a new class with different names
and values (`C().v = 6 - 3` → `K().w = 1 - 2`).

## S3 — a deeper finding: the acceptance gate, not the search, was the ceiling

While measuring S1 it turned out the repair organ was **rejecting honest repairs**, and the
gate was the cause, not the search. `_generalization_probe` decided whether a candidate
generalizes, and a rejected candidate is rolled back. It had four blind spots:

| blind spot | symptom | effect |
|---|---|---|
| regex only matched `assert name(args) == lit` | `assert Calc().add(7, 2) == 9` matched nothing | `NO_LITERAL_CALL_TO_PERTURB` → repair discarded |
| lookup required `def <name>(` | lambdas, closures, dict-of-lambdas not found | `DEFINITION_NOT_FOUND` → repair discarded |
| no receiver handling | methods and staticmethods not callable | repair discarded |
| identity check | correctly refuses `head(xs) -> xs` | (unchanged; correct) |

The probe now reads the assertion with `ast` and executes **the test's own call
expression** against the test's own imports. Nothing about strictness was weakened: the
perturbations, the constant-return check, the argument-blindness check and the identity
refusal are the same rules.

Probe verdicts, 12 cases: 11 correct. Both cheats it exists to catch are still caught
(`return 9` → `OUTPUT_IGNORES_INPUTS`; `a - b + 9` → `REPAIRED_CODE_DISAGREES_WITH_OWED_TEST`),
and identity is still refused. The one miss is an honest `@property`.

End-to-end shape coverage of the owed world, cold, nothing taught:

| shape | before | after |
|---|---|---|
| plain function, method, staticmethod, lambda, dict-lambda, closure, comprehension | 2/8 (plain, comprehension) | **7/8** |
| `@property` | fail | **fail** |

## What is still not real

1. ~~**The board does not always schedule a repair inside a short slice.**~~ **RETRACTED,
   same day, by re-measurement.** This was my own instrumentation bug: I read
   `out["repairs"]`, a key the board never returns, and concluded nothing happened. The real
   key is `out["run"]["steps"]`, where a repair appears as
   `{"status": "WORKED", "work": "repair:tests/...", "accepted_into_world": ["pkg/m2.py"]}`.
   Re-measured at slice sizes 155/240/480 and 4/6/8 cycles, the board dispatched the repair
   every time and the file was repaired and persisted every time. **There is no scheduler
   defect.** The lesson is about my own measuring, not the creature: a claim of the form
   "it did not happen" is a claim about my instrument first.
2. **The property gap is not closed.** An honest `@property` repair is refused by the probe
   because no argument can discriminate a constant from a computation. Reading the
   *assertion* (`C().v == 9`) as the evidence would close it, but that weakens a gate that
   exists to stop memorization, so it is left open and named rather than quietly relaxed.
3. **S2 through the board is now open to measurement** — it was blocked only by (1), which
   was retracted. S4 below is the board-level version of S2.
4. Memory still cannot make a run faster than a cold run that *can* solve the problem — by
   construction, since it is only consulted when the cold path has already failed. Its
   value is bounded by the reach of the synthesizers, and 1/8 of the shapes measured are
   outside that reach.

## Falsifiers for the next pass

- **S4.** Take a world the synthesizers cannot reach (a `@property`, a decorator chain),
  have a teacher supply the fix once, and require the *board* — not the daemon — to repair a
  new world of the same shape with no help. Measure through `out["run"]["steps"]`, and
  require the step to name `MEMORY_FALLBACK_RECALL`; a world repaired by the ordinary
  synthesizer proves nothing about memory.
- **S5.** Count, over many runs, how often the fallback fires at all. A fallback that fires
  never is a feature that does not exist; a fallback that fires often is a statement that
  the synthesizers are the actual ceiling.
- **S6.** Ask whether a lesson can be learned **without a teacher** — from the creature's
  own successful repair — and then consumed later. That is the only path by which memory
  could ever pay on problems the synthesizers *can* reach.
