# A missing answer is not a missing language — round 25

**Date:** 2026-11-04
**Pre-registration:** `PREREG_IT_ONLY_EVER_SEES_THE_DIAGONAL_20261104_V1.md` (written before the code)
**Status:** `truth.achieved: false` · `authority: NONE` · $0 · no sentience claim · no external models · no neural weights

---

## What this round pre-registered, and what survived

The pre-registration predicted that the limit had moved one layer below inference, into **perception**,
and named three measurements. Two held. One was falsified. The falsification is the most useful part of
this round.

| | Prediction | Result |
|---|---|---|
| P1 | `derive_probe_space` crashes on unhashable input | **CONFIRMED** — `TypeError: unhashable type: 'list'` |
| P2 | every probe is on the diagonal, so 2-arg tasks are only ever seen at `f(n,n)` | **CONFIRMED** — then **superseded**, see below |
| P4 | `table_evidence_requirement(P) = 4P` against a floor of `2P` | **MEASURED, NOT FIXED** — recorded as open |

## P1 — the crash

`settlement_v1.derive_probe_space` keyed a `set` with `tuple(ex_in)`. For `[1,2,3]`, `{'a':1}` or
`{1,2,3}` this raised rather than refusing, so the failure escaped into whatever called it. Four rounds
of inference work never saw it because no earlier round ever passed a list.

Fixed with `canonical_key(value)`, which maps any nested container to a hashable form:
`canonical_key([[1,2],{'a':[3]}]) == ('list', (('list',(1,2)), ('dict',(('a',('list',(3,))),))))`.

After the fix: `list→len` 2/2, `list→sorted` 2/2, `dict→len` 1/1, all observational-equivalent.

## P2 — the diagonal, and why it stopped being the interesting answer

Every probe was `tuple([x] * arity)`, so a two-argument task was only ever observed at `f(n, n)`. `x+y`
is affine on the diagonal; `x*y+1` is not. **No improvement in search could have reached it** — the
creature was being shown a slice of its own domain and asked to generalise off it.

Non-diagonal probes were added, derived from gaps in the observed data, in both directions, plus
all-slots-moved. `x*y` then solved 3/3.

**But `x*y+1` still returned `NO_CONSISTENT_HYPOTHESIS`, and the first explanation was wrong.**

## The falsification: the limit was a constant, not a grammar

The natural reading — "the grammar cannot express `x*y+1`" — was checked and is false.
`((x0 * x1) + 1)` is in the grammar and is found in **64 ms**. It was unreachable because every call
site in `meta_circular_organ_graph_v1.py` searched with `max_bank_size` **64–80**, while the
synthesizer's own default is **900** and `evidence_demand_v1.DEFAULT_BANK` is **5000**.

    x*y+1, examples ((1,2),3) ((2,3),7) ((4,1),5)
      bank   72 -> None            (bank FILLED, 72/72)
      bank  900 -> ((x0 * x1) + 1) (found in 64 ms)
      bank 5000 -> ((x0 * x1) + 1)

At a 72-entry bank the search fills the bank and misses the body. The organ graph reported
`NO_CONSISTENT_HYPOTHESIS` — **a statement about the language — for a limit that was a statement about
an integer.**

This is not a tuning problem. `evidence_demand_v1` already refuses to make this substitution and has
`SEARCH_TRUNCATED` for exactly this case; the organ graph's fast path never consulted it. Coverage was
recorded only on the `collect_admissible` path, so the default path — the one the organ graph uses —
returned `None` and explained nothing at all.

### What was changed

1. `swe_observational_program_synthesizer_v1` now records coverage on **every** miss, collecting or not.
2. `_observational_body_with_proven_budget` escalates a bank ladder (72 → 900 → 5000) **only while the
   failure is a budget**, and records whether the final attempt actually finished. The cheap attempt is
   kept first so ordinary tasks stay fast: the widening cost is paid only on a miss.
3. A non-exhaustive empty pool now returns `SEARCH_TRUNCATED`, not `NO_CONSISTENT_HYPOTHESIS`.
4. When the ladder ends, one collecting sweep at the top budget decides "grammar exhausted" vs "budget
   exhausted", so the refusal names its real cause. Without this, `x*y-7` reported `SEARCH_TRUNCATED`
   from a 900 bank that filled while the 5000 sweep was **complete** with 12 admissible bodies, none of
   them a law.

### Result

| task | before | after |
|---|---|---|
| `x*y+1` | `NO_CONSISTENT_HYPOTHESIS` | solved exactly, 5/5 held-out |
| `2*x*y` | `NO_CONSISTENT_HYPOTHESIS` | solved exactly, 3/3 held-out |
| `x*y+4` | refused | solved exactly |
| `(x+y)*2` | solved | solved |
| `x+y`, `x*y`, `x-y` | solved | solved |

## A false positive found on the way, and rejected by construction

Widening the search exposed a worse pre-existing failure. `x*y - 7` was crystallised as

    if x0 == 1: return -(x0 + 4)
    elif x0 == 2: return -1
    return x1 - 4

which fits all three examples and returns **16 where the truth is 193** at (10, 20). It survives as the
only candidate, and `_survivors_disagree_on_domain` returns `False` for a single survivor, so it was
**crystallised as a law**.

The discriminator is not size and not error — the body has zero error on its evidence. It is that the
body **branches on equality with an observed input**: a predicate true only where the creature was
already shown the answer has no content anywhere else. `_is_a_restatement` rejects that shape. A genuine
STUN body also branches, but on **inequalities** (`x < 3`), which partition the domain instead of
enumerating it — so rounds 23/24's piecewise laws are untouched.

The guard is passed *into* the search rather than applied after it, so a rejected body keeps the ladder
climbing and the final completeness flag describes the grammar rather than one rung.

## Two more defects the widening exposed

**Arity crash in the growth path.** `_grow_operator_from_evidence` built every probe as
`(last_x0 + 1,)` — a one-slot tuple — at two separate sites, whatever the task's arity. Any
two-argument task reaching growth raised `TypeError: missing 1 required positional argument`. A crash
inside the refusal path is worse than a refusal: it removes the honest answer too. Both sites now
advance the whole tuple.

**A zero-residual fit is not corroboration.** Not fixed, and marked `xfail(strict=True)` in the suite so
it cannot disappear quietly:

    x*x + y over three points  ->  (4.5*x0) + (-0.5*x1) + -0.5
    at (10, 20):  claimed 34.5, truth 120

Three observations exactly determine an affine fit's three parameters. Zero residual on zero leftover
data is **the definition of a curve drawn through three points**, not evidence that it is the law. This
is the same root cause as the budget defect: a claim about the world issued from evidence structurally
incapable of testing it. It is the next round's question.

## What was NOT done

- **P4 (the 4× constant) was measured and left open.** Long-path spend is 25 / 35 / 55 for P = 5 / 7 / 11
  against a floor of `2P` = 10 / 14 / 22 and `4P` = 20 / 28 / 44 — a 4× constant *and* loop overshoot.
  Both leak. Tightening it without losing accuracy was not attempted; leaving it recorded is better than
  a rushed constant that costs a capability.
- **No claim that the creature is smarter in general.** Every result above is a specific, measured
  behaviour change with a held-out accuracy number attached.

## Regression status

- New suite `canonical/tests/test_it_only_ever_saw_the_diagonal_v1.py`: **28 passed, 1 xfailed**.
- 19-suite regression around this subsystem: **279 passed, 20 subtests**, 1 pre-existing failure
  (`test_a_fallback_is_held_to_the_same_evidence_v1`, fails identically on the stashed baseline).
- Round 24's compositions at the public API with 9 seeds and `growth_enabled=False`: `T+x`, `T−x`, `T*x`,
  `T+x²` all **0/150 held-out wrong**.
- Round 23's `x*x`: the baseline crystallised the *memoriser* (`parametric_table_20`, which returns
  `0.0` at 10⁶). This round refuses without an oracle and crystallises `(x0 / 1) * x0` with one, exact
  at 10⁶ and at −6 in 3 questions.

## The thesis this round hands to the next one

The last four rounds made the creature better at **answering** while its **senses** and its **budget**
were fixed. Both were silently load-bearing. A creature that is only ever shown the diagonal, or that
stops looking after 72 candidates, is not limited by how well it reasons — and it will report the limit
as a fact about the world.

`truth.achieved` remains **false**. What is true is narrower and checkable: a missing answer is not a
missing language, and the tree now says so in the place where it used to say otherwise.

---

## Correction: the "rewind" was a shallow-clone artefact

An earlier report to the owner stated that `origin/main` had been **rewound** — that `72e27486` (the merge
commit of #6636) was no longer an ancestor of main and that there was **no merge base** with this branch.
That report was **wrong**, and the way it was wrong is worth recording.

`.git/shallow` listed `72e27486` and `48d18c84` as graft boundaries. Git will not walk past a boundary, so
`git merge-base --is-ancestor` answered "no" and `git diff origin/main...HEAD` failed with *"no merge base"* —
both of which read exactly like rewritten history, and neither of which was checked against the one file
that explains them.

`git cat-file -p` was enough to disprove it: `48d18c84`'s **first parent is `72e27486`**. After
`git fetch --unshallow`:

    merge-base(origin/main, HEAD) = 72e27486
    72e27486 IS an ancestor of origin/main
    commits ahead: 1   commits behind: 22

No history was lost. **A shallow clone can forge both "not an ancestor" and "no merge base", and both were
reported as findings before the shallow file was read.** The tree keeps this because the same mistake was
made twice — it was reported to the owner, and it shaped a round of decisions.

What remains true: this branch is 22 commits behind main, so it must be brought up to date before merge, and
the round-24 note travels with round 25 because round 24 only ever existed in the working tree. The gate
also admits exactly one action intent per PR, so round 24 keeps its note and not a second intent.
