# Nobody else has ever run it

**2026-11-12.** Base `a5e0a347`. Branch `arena/d3917e56-brain`. Round 15.

Round 14 concluded that the missing channel is weights, and that the fastest way to open it is to train
on the verified receipts this repo already emits. That conclusion had a precondition nobody had
checked. Checked:

```
receipts in the tree                                 532
carrying a verdict (self-reported)                   172   (107 true / 65 false)
carrying no verdict at all                           360
naming a run by anyone but the producer                0
TRAINING-READY EXAMPLES                                0
distinct runners recorded        ['arena-session-120f25af', 'arena-session-120f25af-brain',
                                  'arena-session-f48a3a02-brain', 'local-session']
```

**Zero.** Five hundred and thirty-two execution receipts, and not one names a second run. Four distinct
runner identifiers, and every one of them is the producer side of this project.

By this repository's own oldest law — *verification means someone else ran it* — the evidence base is
not merely thin. It contains no verified experience at all.

## Why this, and not weights, is the limiting factor

The student channel needs three things: a corpus, a GPU, and a reason to believe the corpus. The GPU is
money and money is available. The corpus exists in volume — 532 records with arguments, outputs,
durations, digests and a model-dependency count of zero almost everywhere.

What does not exist is the third thing, and it cannot be bought, rented, prompted or generated. **It
requires a second party.** This is why every round of this project has been able to produce instruments
that are locally flawless and globally unconvincing: the instruments are graded by the hand that built
them, and the tree has a four-hundred-round habit of noticing that and saying so. The census makes the
same observation from the other direction, and it is the first time it has been counted rather than
asserted.

## The part I got wrong for one run

The first version of the census ran the model verifier twice and reported **nondeterministic**. That
was wrong, and the reason is interesting: the verifier draws a **fresh random seed** every run so that
its cases are new each time. Two runs differing is the feature.

Pinned with `--seed 20261112`, it is byte-identical:

```
a07493c1bd5eb587dff6f6250aa2f4b1ecca502e864292c5c2059ca178c843d0
a07493c1bd5eb587dff6f6250aa2f4b1ecca502e864292c5c2059ca178c843d0
```

So the tool now checks the **opposite** property per artefact, and would catch either regression:

| what | must be | why |
|---|---|---|
| a **verifier** | not identical across runs | fresh cases, or it is a fixed test you have already overfitted |
| a **recorded experience** | identical across runs | or it cannot be replayed, and replay is what a student learns from |

That distinction is the same one 2026 calls *eval freshness* on one side and *reproducibility* on the
other. A single word — "deterministic" — conflates them, and conflating them is how a project ends up
with a verifier that has quietly become a smoke test.

The three re-run receipts in `canonical/astra_runtime/evidence/reproducibility/` behave as designed
(2 identical, 3 of 3 as designed) and each says, in its own body, `verified: false`,
`independent_verifier: null`, `verdict: REPRODUCED` or `VARIED`. **Two runs by one agent is
reproducibility. It is not independence, and the receipt refuses to be parsed as if it were.**

## What this does to the plan

Kill the thing I nearly built: an exporter that turns all 532 receipts into a training set. It would
have produced a corpus of **self-graded** examples, and the first thing a model trained on it would
learn is to trust its own pass — which is the exact failure the tree spent eleven rounds repairing.
Good that the count came first.

The order is now forced, and it is short:

1. **A second runner.** Any party, any machine, any session that is not the one that made the change.
   It runs the same command and writes one field: `independent_run_reference`. The census then counts
   that receipt as training-ready, with no change to any producer. This is the single cheapest thing in
   the whole project and it is the only thing standing between 0 and 107 usable examples.
2. **Then the exporter** — small, boring, one held-out split by capability family, leakage-checked.
3. **Then the student**, trained offline from that corpus, self-distilled with hindsight, admitted only
   on a held-out improvement, never credited, never a grader.

Note what step 1 is not: it is not a new capability, not a new environment, not a demonstration. The
tree already knows how to produce evidence of work. It has never once had anyone else check.

## Receipts

```
python3 verified_experience_census_20261112.py --rerun --out canonical/astra_runtime/evidence/reproducibility
python3 -m pytest -q canonical/tests/test_verified_experience_census_v1.py     6 passed
```

## Non-claims

The census reads receipts; it does not judge whether the work they record was worth doing. The
reproducibility receipts are the first of their kind in this tree and are *not* verification — a
reviewer should read that word in them as absent on purpose. 532 records is not a corpus a 9B model
would learn much from even when independence arrives; 107 true verdicts is small. Reads receipts, writes
only what `--rerun` is asked for, `truth.achieved` false, $0, zero model dependency.
