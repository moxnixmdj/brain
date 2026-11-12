# I was wrong: they have run it 296 times

**2026-11-12.** Base `5dfc432b`. Branch `arena/7654c281-brain`. Round 16.

Last round I reported a number and drew a conclusion from it:

```
naming a run by anyone but the producer                0
TRAINING-READY EXAMPLES                                0
```

**Both are false.** Independently verified runs are not stored in `*RECEIPT.json`. They are stored in
`CAPABILITY__*__INDEPENDENT_VERIFICATION.json`, written by
`.github/workflows/capability-receipt-verification.yml` on a GitHub runner under an OIDC token whose
claims include `run_id`, `repository` and `actor`. My census globbed one pattern and reported zero while
hundreds of records sat in the same directory.

```
independent verification records                     296
  reproduced                                         296
  carrying a github_run_id                           296
  joining to a producer receipt                      296   (orphans: 0)
verifier                          github-actions:moxnixmdj/brain
TRAINING-READY EXAMPLES                              170   (105 with pass=true)
```

## The machinery was there the whole time

It is exactly what the owner keeps saying: the solution exists, under a name nobody guesses.

* `canonical/runtime/capability_receipt_lane_v1.py --verify` re-executes producer receipts **as a
  different identity** and stamps only what reproduces. Its own words: *"Same identity: not an
  independent run at all. Never count it."*
* The workflow does it on `ubuntu-latest`, mints an OIDC token, and refuses to accept a locally-written
  `github_run_id` because a local process cannot forge one.
* The lane separates the two artefacts on purpose: a receipt is what the producer observed, a
  verification record is what somebody else reproduced. I read the first and drew a conclusion about
  both.

That is not a small correction. **Round 15's headline — "the evidence base contains no verified
experience at all" — was wrong, and it was wrong in the one way this repository is built to prevent:
a conclusion drawn from an instrument that could not see the thing it was measuring.**

## What is actually true now

| | count |
|---|---|
| producer receipts | 333 distinct capabilities (532 files) |
| with a producer verdict | 172 |
| independently reproduced by CI, OIDC-attested | 296 |
| **training-ready** (verdict ∧ reproduction ∧ no model) | **170** |
| of those, pass = true | 105 |
| instances per capability | **1** |
| instance gap at 8 per capability | **2 072** |

Independence: **solved.** An outside party — a GitHub runner, a bot identity, a signed run id — has been
checking this repo's claims all along, and 296 of those checks reproduced.

Breadth: **solved.** 296 capabilities with verified execution.

Depth: **not solved, and it is now the only thing left on the data side.** Every capability has exactly
one verified instance. A held-out split needs more than one: with one instance per family there is
nothing to hold out, so generalisation cannot be measured, and a student trained on it learns 296
anecdotes.

## Which means the owner's plan was right, with one word changed

*"Give the model a try in all those new environments"* — the right idea, aimed at the wrong axis.
New *environments* add new families, and there are already 296. **New instances of the same family**
are what is missing: the same verified task, run again with fresh inputs, k times. Which is cheap,
because:

* the verifier already draws a **fresh random seed** every run — that is why it refuses to repeat
  itself, and why it is the correct instrument for producing instances;
* the CI lane already does the re-run and the attestation;
* nothing about it needs a new capability, a new model, or a new environment.

## The order

1. **Depth first.** Run the 296 verified capabilities k = 8 times each with fresh inputs, on the
   existing CI lane, keeping only what reproduces. 2 072 instances, all independently attested.
2. **Then export** with a held-out split by *instance* (not by capability — capability-level splitting
   is the mistake that makes a corpus look easy).
3. **Then the student** — offline, hindsight-distilled, admitted only on held-out improvement, never
   credited, never a grader.

## The lesson that costs the most

I built a census, pinned it with six tests, merged it, and wrote a headline on it. The tests passed
because they tested the census's own logic, not its coverage. **A measurement's tests can be green and
its population empty.** The fix is now permanent and mechanical, in two places:

* the census counts both artefact kinds, joins them, and reports `orphans` so that a verification with
  no receipt is visible rather than silent;
* the round-14 claims ledger gains the claim `independent_verification_exists`, so any future summary
  that says "no verified experience" fails a re-executed predicate instead of being typed.

## Receipts

```
python3 verified_experience_census_20261112.py
python3 round_14_claims_ledger_20261112.py
python3 -m pytest -q canonical/tests/test_verified_experience_census_v1.py \
                    canonical/tests/test_round_14_claims_ledger_v1.py     16 passed
```

## Non-claims

The census counts; it does not judge whether the work was worth doing. 170 examples is a small corpus
and 105 passing ones is smaller; depth is the gap, and this note does not claim the depth run has
happened — it names it as the next action. Nothing here is a benchmark or acceptance result,
`truth.achieved` false, $0, zero model dependency.
