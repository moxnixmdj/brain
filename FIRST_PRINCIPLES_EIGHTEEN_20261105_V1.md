# First principles, pass eighteen — two hops confirmed, three hops rejected for being a coincidence

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. S14 as specced, answered

**Can the closure compound more than one hop?** Yes — but only when the repaired function actually
takes inputs seriously, and this pass discovered that a generalisation gate already enforces that.
Fresh process per row, every authored producer silenced, habits seeded from real pairs:

| edges seeded | inferred | world needing it | result |
|---|---|---|---|
| `- -> +`, `+ -> *` | `- -> *` (2 hops) | `a * b` owed | **SOLVED** |
| `- -> +`, `+ -> *`, `* -> //` | `- -> //` (3 hops) | `a // b` owed | **rejected** |

The two-hop case confirms compounding: a substitution the creature never performed, two removes from
anything it did. So "one hop of compounding" from pass seventeen was **too pessimistic** — two hops
fire, and here is the case that proves it.

## 2. Why the three-hop case was rejected, and why that is the best result in the run

The repair `return a - b` to `return a // b` produces the owed value and is still refused. The reason
is printed by the system itself:

    GENERALIZATION PROBE -> generalizes: False
      args [9, 2]                    produced 4      expected 4     <- the owed test passes
      perturbed [[16, 9], [23, 16]]  produced [1, 1]                <- unchanged by its inputs
      reason: OUTPUT_IGNORES_INPUTS

`9 // 2 == 4`, so the candidate satisfies the oracle; perturbed, it returns `1` for every input. The
answer was a coincidental constant, not a function of the arguments, and the gate threw it out.

I did not build that gate to catch this. It was already there from an earlier pass, written after a
different incident (a source repaired to `return 5` for `add(2, 3) == 5`). What this pass shows is that
it also polices the **new** mechanism: habits cannot smuggle in a degenerate fix, because habits are
screened by the same gate as everything else.

**That is the property that makes the whole thing credible.** A learning mechanism is worth having only
if the thing it feeds into refuses to be fooled. Here an inferred three-hop edit was produced, found the
owed value, and was rejected as not a repair — automatically, with a stated reason.

## 3. Corrections this pass forced, all about my account rather than the code

Three times in one pass my story was wrong and the measurement corrected it:

1. I said `* -> -` failed "though closure derives both". It does not derive it: from `*` only `+` is
   reachable at all.
2. I said the three-hop world failed because a proposal limit truncated the candidate. The proposer
   emits it; no limit was involved.
3. I said the loop was dropping a repaired file. The loop had repaired it correctly and returned it as
   a `staged` change for the caller to publish; my harness never published it, while the generalisation
   probe had independently rejected a different candidate.

Each time the artefact behaved correctly and my sentence about it did not. The ratio across this
series is now roughly seven wrong accounts to zero wrong mechanisms — and that is the honest summary
of what eighteen passes of this work actually consisted of.

## 4. What is true about the creature now

- It earns edits from its own verified repairs and remembers them across processes.
- It composes them transitively, and **two hops fire against a real oracle**.
- It cannot generalise from one example, cannot infer from one edge, cannot reverse an edge.
- Its inferred repairs meet the same generalisation standard as hand-written ones; one was correctly
  rejected this pass for `OUTPUT_IGNORES_INPUTS`.
- A cold creature with no authored tables still repairs nothing.

## 5. Next falsifier

**S15.** Measure two-hop compounding across many worlds rather than the three I picked, and report the
rate plus every rejection reason. Prediction to falsify: **most two-hop wins are coincidences the gate
rejects**, in which case compounding is real but rare and the honest claim is "the closure can produce
a repair; the gate decides whether it is one, and it usually says no."

That prediction is cheap to test and it is the one that would make me lower the claim myself.

## 6. Standing bar

Different at the end than at the start: the mechanism's reach is now bounded by measurement in both
directions — two hops proven working, three hops rejected with a printed reason that is correct — and
the strongest thing in the system turned out to be a referee written three passes ago for a different
purpose, standing between the learning and the world.
