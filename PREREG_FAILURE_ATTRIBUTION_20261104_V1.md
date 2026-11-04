# Pre-registration: attributing a failure the way an outsider would

**Written before implementing. 2026-11-04 · authority NONE · `truth.achieved` false**

## What the previous document got wrong

It said the top-ranked move was to "wire `helped=False` to a real outcome instead of a caller's
opinion", and treated that as a wiring problem. Having read the actual call sites, it is not:

- Callers get a string body back and use it immediately. (`python_feature_implement_function_spec.py`
  raises if it is empty and proceeds — no validation at emission.)
- So at emission time **nobody knows** whether the body is right. The synthesizer cannot decide; that
  is not a wiring gap, it is a fact about when knowledge exists.

The gap is therefore narrower and more honest than I wrote: **the notice must come from outside the
library. What belongs inside is ATTRIBUTION** — deciding which concept, of possibly several used in
one failed program, is responsible.

## The measurement that motivates it (already done, 2026-11-04)

`record_concept_outcome` takes a single `concept_id`. One failed program that used concepts A and B
can only be reported against one of them, and nothing in the API records which. The two available
behaviours are both bad:

1. blame every concept in the program (punishes an innocent A alongside a guilty B), or
2. blame none (the library stays blind, which is the state I just fixed).

## The mechanism under test

A program's failure is **not** evidence about one concept. The test is whether removing the concept
makes the program correct. Formally, for a failed program using concepts {A, B}:

    suspects(A) = A is retired  AND  substituting A's body textually into the program
                                    makes it pass the same examples

An innocent concept stays alive; a guilty one is retired by its own refutation. Retiring is
reversible (`revive`), because a retirement caused by one program is weaker evidence than a
threshold's worth.

## Predictions (falsifiable, stated before the run)

**P1 (innocence).** A failure of a program that uses an innocent concept and a guilty one must not
be charged to both. After attribution, the guilty concept is retired and the innocent one is not.

**P2 (the notice changes behaviour).** After attribution, the same problem is re-synthesized and the
answer differs from the answer with the un-attributed library — and the new answer does not use the
retired concept.

**P3 (refutation, not blame, is the evidence).** If a concept is a suspect in a failed program but
substituting it makes the program *still* fail, it must not be retired. I predict
`retire` is reached only via substitution-under-refutation, never by a mere failure count.

**P4 (reversibility).** `revive` restores an over-retired concept to full prior, and the library
returns to its pre-retirement behaviour.

**P5 (honest bound, predicted to hold).** Nothing in this change makes the creature *notice* a
failure. There is still no component that observes a failed outcome and initiates the audit; the
audit is invoked. I predict this benchmark cannot demonstrate initiative, only correct attribution.

---

## POST-RUN: the pre-registered mechanism (P1–P3) was VACUOUS

Recorded after running it, before replacing it. The error is conceptual, not a coding slip:

> **Inlining a concept's body preserves its semantics by definition.** So "does the program pass
> without concept X", implemented by substitution, is *identical* to asking whether it passes with
> X. Measured: both concepts in a two-concept failed program came back "innocent", including the
> guilty one, because the substituted program still failed — as it must, since the substitution was
> a no-op.

A counterfactual that provably cannot change the outcome is not a counterfactual. P1, P2 and P3 as
written are therefore **void**, and were not evidence either way. This is the sixth instrument error
in the project and the first that was wrong at the level of the idea rather than the implementation.

### The replacement, still pre-registered before it is run

Ablate the concept from the **search**, not the program. Re-synthesize the same problem with the
suspect concept unavailable:

- **re-synthesis without the suspect SUCCEEDS** → the concept was not necessary; the search could
  have found a correct program without it, so it was actively misleading. Charge it.
- **re-synthesis without the suspect ALSO FAILS** → the concept was not the cause; the problem is
  beyond the search either way. Leave it alone.

Revised predictions:

**Q1.** A guilty concept is charged, and an innocent concept in the same failed program is not.
**Q2.** After charging, the same problem re-synthesized with the updated library yields a correct
program that does not call the charged concept.
**Q3 (the honest one).** If the problem is simply unsolvable, nothing is charged. I predict this
because the mechanism must not manufacture a culprit.
**Q4.** `revive` restores a concept to full standing and the library returns to its prior behaviour.
