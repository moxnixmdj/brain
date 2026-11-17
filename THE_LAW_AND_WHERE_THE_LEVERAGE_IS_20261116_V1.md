# The law, and why leverage is not slope

*Composed 2026-11-16 from five published receipts, each pinned by path and sha256. Instrument:
`canonical/swe_kernel/capability_law_v1.py`. Receipt: `canonical/verification/CAPABILITY_LAW_20261116_V1.json`.
No model, no network, no spend.*

## The law

```
P(correct behaviour | one action)  =  P(the action is determined)  x  P(the error is seen)
P(seen)                            =  check density  x  check strength
```

At the measured operating point on real Python work:

| term | value | receipt |
|---|---|---|
| determined (a demonstration fixes the sibling edit) | **0.5469** | `SYSTEMATIC_EDIT_SUPPLY` |
| determined, for the value itself | **0.2143** | `SYSTEMATIC_EDIT_DERIVATION` (9 of 42) |
| check density (real edits any test even names) | **0.6788** | `ORACLE_DENSITY` (python) |
| check strength (a mutant is rejected where seen) | **0.8021** | `PATCH_VERDICT_AMPLIFICATION` |
| **seen** | **0.5445** | `ORACLE_DENSITY` |
| **P(correct)** | **0.2978** | product |
| **P(correct), value-bearing action** | **0.1167** | product |
| memory: recurs later / replays exactly / silently corrupt | **0.1584 / 0.0481 / 0.3114** | `SKILL_RECURRENCE`, `ACTION_REPLAY_UNDER_CHANGE` |

## Why this is a decision and not a table

**The two slopes are equal — 0.5445 and 0.5469 — so slope alone says "spend anywhere". That is wrong.**

`P(determined)` is a property of the **trace**: one demonstration is one point, and the published ceiling
for an inducer with full AST and context machinery is **0.70** on real systematic edits (SyDIT, PLDI
2011). No amount of engineering moves it past that; the trace does not contain more.

`P(seen)` is a property of the **environment**: 0.6788 of real Python edits are even named by a test, and
that is a fact about how humans wrote their tests, not a law of nature. It is engineerable toward 1.0 by
manufacturing checks — recorded-outcome differentials, idempotence/reversibility invariants, canonical
state-projection diffs — and every manufactured check is falsifiable by mutation before it is trusted.

So leverage = slope × **controllability**:

| term | slope | controllable | leverage |
|---|---|---|---|
| check density | 0.5469 | **yes** | **0.5469** |
| check strength | 0.3712 | yes | 0.3712 |
| determinacy | 0.5445 | **no** (trace-bounded, ceiling 0.70) | **0.0** |

Every unit of effort spent making induction smarter is spent against a ceiling that the trace sets. Every
unit spent making consequences observable multiplies the whole product.

## What the ladder buys

| check density | seen | P(correct) | P(correct), value-bearing |
|---|---|---|---|
| 0.6788 (measured today) | 0.5445 | 0.2978 | 0.1167 |
| 0.80 | 0.6417 | 0.3509 | 0.1375 |
| 0.90 | 0.7219 | 0.3948 | 0.1547 |
| 1.00 (every consequence observable) | 0.8021 | **0.4387** | 0.1719 |

Note the last column: **even at full observability, one demonstration caps correctness at 0.5469.** That
is the honest answer to "is one-shot learning the solution": it is the *base* of the product and it is
capped by the trace at 0.70 for the best inducer ever published; observability is the *multiplier*, and
the multiplier is the only part still under our control.

## What this means concretely

1. **Build the check ladder, in this order** — recorded-outcome differential (for replay the intent *is*
   the recorded consequence, so no human spec is needed) → idempotence / reversibility / determinism
   invariants (need only to act twice) → existing suites → canonical state-projection diffs. Measure the
   density it reaches; that number is the project's control number.
2. **Falsify every manufactured check by mutation before trusting it.** A check a mutation does not kill
   is decoration — that is the 19.79% (naming without assertion) that the density receipt isolates.
3. **Keep memory as a cache, never a belief.** 0.1584 of work recurs, 0.0481 replays exactly, and 0.3114
   of "successful" replays are silently corrupt. Store shape + premise + postcondition; never a value.
4. **Delete the demonstration campaign as a capability engine, and delete the parameter knowledge store.**
   Weights keep the verifier's decision rule and the search policy — both computed, both kilobytes. Facts
   arrive from instant knowledge at use time.
5. **Do not quote a number without its receipt.** The law raises if a receipt is missing or has changed;
   that is deliberate, and it is the only thing keeping this document from becoming another opinion.

## Computer use is `UNMEASURED`, and the law says so

There is no check-density receipt for a desktop, because there is no test corpus there: the oracle must
be manufactured. The law prints `UNMEASURED` and refuses to print a zero it did not measure. The external
context is unambiguous — OSWorld 2.0 (2606.29537): best agent **20.6%** of 108 long-horizon workflows,
failing by losing constraints and **skipping verification**, with **under 7% of budget** spent detecting
its own errors.

What would measure it: a state-projection differential over a long-horizon workflow suite with mutated
actions — i.e. exactly the third rung of the ladder, run against OSWorld checkpoints. That is the next
receipt this project needs, and it is the one that would turn "computer use" from an assumption into a
number.

## What would falsify the law

* A population where `P(determined)` moves with effort rather than with the trace: if a second
  observation lifts an inducer above 0.70 without a check, the determinacy term is controllable and the
  leverage ordering changes. (Two-demonstration agreement has so far only raised *value* precision from
  0.214 to 0.400 while forcing abstention — it fires on 15 pairs, not 102.)
* A manufactured check that raises density without a matching collapse in strength: if 0.9 density can be
  reached with strength held near 0.80, the ladder is real. If strength falls as density rises, the
  product barely moves and the law says so before the work is done.
* Any measurement of computer-use density above zero with the agent's own manufactured oracle.

## Reproduce

```
python3 canonical/swe_kernel/capability_law_v1.py \
  --json canonical/verification/CAPABILITY_LAW_20261116_V1.json
python3 -m pytest canonical/tests/test_capability_law_v1.py -q      # 8 tests
python3 canonical/swe_kernel/capability_law_v1.py --pinned          # refuses if a receipt moved
```

The eight tests pin the terms, the product, the leverage ordering, the scenario ladder, the refusal on
computer use, and both fail-closed paths (missing receipt, changed receipt).

## What this does not claim

No capability credit, no benchmark rank, no independent verification. The product treats each term as
independent, which is a modelling choice, not a measurement: the terms were measured on different
populations (245 within-commit pairs, 691 sites, 228 replay pairs). The numbers are a description of a
population of five Python libraries, and the ceiling of 0.70 is from a 2011 system on real systematic
edits — the best published, not an impossibility proof. The claim that survives all of that is narrow and
useful: **the term to spend on is the one that multiplies, and it is the only one that is ours.**
