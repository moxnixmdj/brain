# One origin derives the judge — 2026-11-20

Authority: `NONE__PRODUCER_RUN_SANDBOX`. No acceptance, capability or terminal credit; no
independent verification; no runtime model call; zero stored parameters.

## What was removed

`coverage_completes_the_closure_v1` removed the hand-written law choice but still passed a judge
per damage class. That judge contained a task string (`local edit`), so the learner was told what
the hidden work was. This round derives the verifier from one *observed damaged origin*: refs, HEAD,
status, stash blob digests, worktree bytes and the target tree. No task name, no `preserve` flag, no
damage string, no threshold and no parameter enters the judge.

The judge requires: clean `main`, empty stash, no in-progress operation, target commit an ancestor,
every non-main ref unchanged, no newly tracked file, and each target-tree file at either its target
digest or — exactly when that file's bytes were in the origin's stash — the observed stash digest.
This is a computed verifier over measured facts, not a model and not a lookup table.

## Measured result

Tool: `canonical/tools/one_origin_derives_the_judge_v1.py`; tests:
`canonical/tests/test_one_origin_derives_the_judge_v1.py`; receipt:
`canonical/verification/ONE_ORIGIN_DERIVES_THE_JUDGE_20261120_V1.json`.

- Both repositories (`pypa/packaging` train, `pypa/pyproject-hooks` held) produced 180/179 judged
  rows from one origin per class. In both stash classes the minimal repair was again to drop the
  single `head` clause; the two side classes needed no repair.
- The derived judgments selected the unique three-law closure
  `ref_preserve + tracking_preserve + stash_restore`, matching the previous supplied-judge result.
- Held-out: 160 holes, 19 legitimate states, 0 false accepts and 0 false rejects. Training:
  161 holes, 19 legitimate, 0/0.
- On every judged state the derived verdict agreed with the old supplied judge: **0 disagreements**
  over 359 rows. The supplied judge was read only for this audit; it never selected the closure.
- All five declared criteria D1–D5 are true; 14/14 targeted tests pass; full run 366.2 s.

A shared helper change keeps the on-disk copy of a judged state when duplicate states are pruned from
the search frontier, so a later audit can re-read the evidence path. Duplicate states still never
re-enter the frontier.

## What this does and does not show

It shows one real observation can compute a verifier that agrees with the old supplied verifier on
this task family and selects the same transferable closure. It does **not** show that the derived
verifier is the user's preference: the damage classes, action vocabulary, law algebra, target commit
and one origin per class are still supplied. No unseen environment, GUI, browser, benchmark score,
independent verification or single-experience learning of an arbitrary goal is demonstrated. §6
remains unmet.

## Next bottleneck

The verifier is now derived, but the origin and the repair vocabulary are still selected by the
experiment. The next test must start from a state the machine reaches without being handed a damage
class, derive its own verifier, and refit under a held-out class; falsifiers are a wrong verdict, a
closure that accepts a constructed hole, or any parameter/model call.
