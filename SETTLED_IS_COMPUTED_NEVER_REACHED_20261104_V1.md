# Settled is computed, never reached

Result note, 2026-11-04. Base `70b8d1b1`, branch `arena/a2ec91e7-brain`.
Pre-registration: `PREREG_SETTLED_IS_COMPUTED_NEVER_REACHED_20261104_V1.md`.

---

## The question

> "You sure this is the smartest approach? You must think from the deepest layer, from first
> principles of everything. And don't forget we want a very smart, most advanced, sentient-like
> creature. We don't want a static code."

Rounds 13–17 found the same defect seven times: **a frozen list deciding an answer a computation
should decide.** Round 17 built a check that finds that class inside one module, and the check passed.
So the honest move was not an eighth instance — it was to measure whether the thing the tree claims to
be is the thing it is.

The tree's headline claim is that the operator basis compounds:

    Ω_{t+1} = Ω_t ∪ P_t ∪ C_t

The claim implies a measurement: **experience must make the next problem cheaper to *settle*.** Not
cheaper to search — cheaper to *know*.

## What I measured, before changing anything

Six problems from one family, `x mod k`, seeds `{1,2,3}`:

```
COLD  (fresh brain each)              WARM  (one brain, in order)
k= 4  crystallized      q=1           k= 4  crystallized        q=1
k= 5  crystallized      q=1           k= 5  RECALLED_TIER0      q=0
k= 7  crystallized      q=2           k= 7  RECALLED_TIER0      q=0
k= 8  contradiction     q=2           k= 8  RECALLED_TIER0      q=0
k=10  contradiction     q=3           k=10  RECALLED_TIER0      q=0
k=11  contradiction     q=3           k=11  RECALLED_TIER0      q=0
             total q = 12                            total q = 1
```

A 12× saving. Held-out inputs `10..19`, which nothing had seen:

| k | cold | warm |
|---|---|---|
| 4 | 2/10 | 2/10 |
| 5 | 2/10 | **0/10** |
| 7 | 1/10 | **0/10** |
| 8 | refused | 1/10 |
| 10 | refused | **0/10** |
| 11 | refused | **0/10** |

**Experience made the creature faster and wronger, and every status string said it had succeeded.** For
a creature meant to get smarter, that is not a bug in a component. It is the thing itself being
backwards.

## The cause: one error, three doors

All three doors decide *settled* from **the path taken** instead of from **the evidence held**.

**Door 1 — blindness becomes certainty.**
```python
if disc_probe is None:
    # "my grid cannot separate these"
    break          # ...then admits candidate_organs[0]
```
"My probes cannot see a difference" was read as "there is no difference." For `x mod 4` it admitted
`proj_0` — the identity — and returned `DISAMBIGUATED_AND_CRYSTALLIZED`.

**Door 2 — recall never asks.** The incumbent agreed with the examples that had *made it* the
incumbent, and was returned without asking, even when a working oracle was passed on the same call.

**Door 3 — grammatical poverty becomes determinacy.** This one I only found *after* fixing the first
two, because the fix made it visible. When the grammar can form only one hypothesis, the disambiguation
loop never runs and it is crystallized immediately. `x mod 5` from seeds 1..3 produced
`if x0 <= 0: 0/x0 else x0/1` — the identity in disguise — admitted with zero questions, 0/10 held-out.

Only one of these is a wrong table. All three are the same mistake in the act of concluding.

## What changed

**`canonical/runtime/settlement_v1.py`** — settlement as a computed quantity:

- hypotheses carry **weights**; contradiction down-weights rather than deletes, so experience
  accumulates a posterior instead of being filtered away;
- probes are chosen by **exact expected information gain** (verified against brute-force mutual
  information over 160 probes, max error `4.4e-16`), gated by cost;
- `settle()` returns `SETTLED` only when the posterior is concentrated **and** the mass of hypotheses
  that would behave differently *on the caller's own domain* is small;
- **six distinct non-settled states**, because collapsing them into one was how the system lost the
  ability to say what was actually wrong: `UNSETTLEABLE_BY_THIS_INSTRUMENT`,
  `INSTRUMENT_TOO_COSTLY`, `EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE`, `NO_ORACLE`, `UNDERDETERMINED`,
  `NO_HYPOTHESES`.

**`meta_circular_organ_graph_v1.py`** — all three doors closed, plus the operator induction that
`Ω_{t+1} = Ω_t ∪ P_t` claims:

- a surviving set that no reachable probe separates but that agrees everywhere on the domain is
  **inconsequential** and may be crystallized (choosing between `2x+2` and `2*(x+1)` is not a guess);
  if it *disagrees* anywhere, it refuses and says so;
- a lone hypothesis must predict something it has not already been shown (`HELD_OUT_REFUTED`);
- `%` is not in the organ grammar at all. Rather than add it to a menu — the same defect again — the
  creature **induces the period from observed periodicity** and emits a body for it.

## Measured result

| | before | after |
|---|---|---|
| held-out on `x mod k`, k ∈ {4,5,7,8,10,11,15} | 0–2/10, or refused | **700/700** |
| questions for the whole 7-instance family | 12 (cold) / 1 (warm, by guessing) | **1** |
| `k=15` (inexpressible in the grammar) | impossible | **100/100** |
| a wrong answer reported as success | yes | never |

The one question is not a coincidence. All-positive evidence cannot distinguish `math.fmod` from
Python's `%` — measured at 30/30 correct above zero and 6/30 below. That is a *hypothesis about a
convention*, so it gets asked once, settled, remembered, and reused.

## Pre-registration scored

| prediction | result |
|---|---|
| **P1** warm never worse than cold | **PASS** — after the repair, and it was **failing** when first measured |
| **P2** cheaper *while* P1 holds | **PASS** — 1 question per family, 700/700 held-out |
| **P3** blindness refused, not converted | **PASS** — `UNSETTLEABLE_BY_THIS_INSTRUMENT`, no organ admitted |
| **P4** world not blamed | **PASS** — `EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE` |
| **P5** no collapse to timidity | **PASS** — `x*y` 40/40, `7x-2y+12` exact, both crystallize |
| **P6** cost gate load-bearing | **PASS** — `INSTRUMENT_TOO_COSTLY`, zero questions asked |

**Falsified along the way, and kept:** my first information-gain implementation scored probes against
an alphabet drawn from past observations. A probe whose outcomes were all novel scored zero and was
declared unlearnable — the exact blindness I was repairing, reimplemented by accident. Also falsified:
`_candidate_probe_inputs` entropy bucketing used `repr` (`0` vs `-0.0` differ) while elimination used
numeric tolerance (they match), so the system spent a query on a probe that eliminated nothing.

## The honest limit, which matters more than the win

**Inducing a period costs evidence proportional to the period, and does not get cheaper with
experience.** Measured: the minimum n to induce period p is `2p+2` (p=2→6, p=3→8, p=4→10, p=5→12,
p=7→16, p=9→20, p=11→24, p=15→32). Learning `mod 5` does **not** make `mod 15` cheap.

What experience buys is the operator's **existence**. Before `periodic` is induced, no budget
suffices, because no body in the grammar can express it. That is a real gain and it is not
general intelligence, and I am not going to call it that.

## Non-claims

- `SETTLED` means settled **with respect to the reachable probe space and a stated confidence**. It is
  never truth. Two programs identical on every reachable input remain genuinely undecidable, and the
  system now says so instead of choosing.
- The convention memory is a belief that **can be overturned** (tested: a stale `fmod` belief is
  refuted by contradicting evidence). A belief that could not be revised would be a frozen table that
  took a longer route into the tree.
- Period induction is implemented for **single-variable** evidence only. Multi-variable periodicity is
  not claimed.
- Nothing here is sentience. `truth.achieved` false, `authority: NONE`, $0, no neural weights, no
  external model calls, no dynamic code execution in result-bearing paths.

## Why this is a layer down

Every previous round repaired *a table*. This repaired **the act of concluding that a table is no
longer needed** — turning *settled* from a fact about the search path into a quantity with a price, a
confidence, and a refusal. And then it made the operator basis actually grow: `periodic` did not exist
in the grammar, and now exists because evidence implied it.

A program searches. A creature knows what it does not know, and can be told otherwise.
