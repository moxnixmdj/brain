# PRE-REGISTRATION — *Settled is computed, never reached*

2026-11-04, V1. Written **before** implementation, after measurement.
Base `70b8d1b1` (`feat(creature): deliberation is the organ`, PR #6625).
Branch `arena/a2ec91e7-brain`.

---

## The question the owner asked

"You sure this is the smartest approach? You must think from the deepest layer, from first principles
of everything. And don't forget we want a very smart, most advanced, sentient-like creature. We don't
want a static code."

Rounds 13–17 have been finding the same defect one instance at a time: **a frozen list deciding an
answer that a computation should decide.** Round 17 built a check that finds the class inside
`evidence_demand`, and the check passed. So the honest next move is not another instance. It is to
stop asking *which list is frozen* and ask **what makes a decision settled at all.**

## The deepest layer, as measured — not as documented

The tree's own headline claim is that the operator basis compounds:

    Ω_{t+1} = Ω_t ∪ P_t ∪ C_t

I measured the thing that claim implies and nothing else implies: **experience must make the next
problem cheaper to *settle*.** Not cheaper to search — cheaper to *know*.

Two runs, same six problems, `x mod k` for `k ∈ {4,5,7,8,10,11}` with seed inputs `{1,2,3}`:

```
COLD  (fresh brain per instance)        WARM  (one brain, in order)
k= 4  crystallized   q=1                k= 4  crystallized        q=1
k= 5  crystallized   q=1                k= 5  RECALLED_TIER0      q=0
k= 7  crystallized   q=2                k= 7  RECALLED_TIER0      q=0
k= 8  contradiction  q=2                k= 8  RECALLED_TIER0      q=0
k=10  contradiction  q=3                k=10  RECALLED_TIER0      q=0
k=11  contradiction  q=3                k=11  RECALLED_TIER0      q=0
                        total q = 12                             total q = 1
```

Warm used 1 question instead of 12 — an apparently 12× compounding win. **It is not compounding. It
is false confidence with a cost saving.**

Held-out accuracy over inputs `10..19`, which nothing had seen:

| value of k | cold: held-out correct | warm: held-out correct | warm status |
|---|---|---|---|
| 4 | 2/10 | 2/10 | crystallized |
| 5 | **2/10** | **0/10** | RECALLED_TIER0_ORGAN |
| 7 | 1/10 | **0/10** | RECALLED_TIER0_ORGAN |
| 8 | (refused) | 1/10 | RECALLED_TIER0_ORGAN |
| 10 | (refused) | **0/10** | RECALLED_TIER0_ORGAN |
| 11 | (refused) | **0/10** | RECALLED_TIER0_ORGAN |

**Experience produced a creature that asks fewer questions and is wrong more often**, and reports
success both times. For the owner's goal this is the whole ballgame: a thing that gets *faster at
being wrong* is the precise opposite of a thing that becomes smarter.

## The cause: one error with two doors

### Door 1 — blindness is converted into certainty

`meta_circular_organ_graph_v1.synthesize_or_disambiguate_skill`:

```python
while len(candidate_organs) > 1:
    disc_probe = synthesize_discriminating_input(candidate_organs, work_examples)
    if disc_probe is None:
        # All surviving hypotheses are observationally equivalent across the entire probe grid!
        break          #  <-- then falls through to: winner = candidate_organs[0]
```

`disc_probe is None` means **"my frozen grid cannot separate these."** The comment reads that as *"they
are equivalent."* Those are different statements, and the code takes the second. It then admits
`candidate_organs[0]` — which for `k=4` is `proj_0`, i.e. the function `x` — and returns
`DISAMBIGUATED_AND_CRYSTALLIZED`.

Measured at `k=4`: three hypotheses survive (`proj_0`, `observational_eq`, `exact_affine`); the grid
does find a probe `(5,)`; after one query the survivor set still cannot be separated **by the grid**,
so the loop breaks and `x` is admitted. Held-out 2/10.

### Door 2 — recall never asks, even when the oracle is present

The Tier-0 path returns the incumbent when it is consistent with the *given* examples, without
requesting a new observation — although the caller passed a working `oracle` on the same call. That
is what produces `q=0` above.

### Why these are one error

Both decide "settled" from **the path taken** instead of from **the evidence held**. Door 1 infers
equivalence from the absence of a *visible* counterexample. Door 2 infers correctness from the absence
of an *attempted* refutation. One error, two doors.

### And the freeze underneath both

`synthesize_discriminating_input` scores probes by **unweighted** Shannon entropy over the surviving
set and searches `_candidate_probe_inputs` — a frozen integer grid whose largest literal is `11 + slot`.
Consequences measured today:

- **`k=6` returns `CONTRADICTORY_ORACLE_OR_OUT_OF_GRAMMAR`** — the system blamed the *world* for a
  contradiction that does not exist. `x % 6` is perfectly consistent; the grammars `mod 4` and
  `mod 6` are separated only at inputs the grid omits.
- **`k=15` cannot be expressed at all** — the hypothesis needs a literal the grammar never emits.

Naming the world as the liar when the instrument is blind is the same defect as the twelve-entry
constant menu: **a frozen table deciding what is true.**

## What I will build (and why this is not another patch)

Add one module, `canonical/runtime/settlement_v1.py`, and wire the organ graph to it.

1. **`VersionSpace`** — hypotheses carry weights, not just membership. Every observation multiplies
   weights by a real likelihood; a hypothesis that contradicts an observation is *down-weighted*, not
   deleted-and-forgotten. Experience therefore accumulates a posterior instead of a filter.

2. **`select_probe`** — chooses the probe maximizing **expected information gain**, via the existing
   `deterministic_decision_primitives.expected_information_gain`, gated by **cost**. A question is
   asked only if its expected reduction in uncertainty exceeds its price. This is where "smart" lives:
   a smart creature does not ask more questions, it asks the questions that buy the most.

3. **`settled()`** — the load-bearing primitive. Returns `SETTLED` only if the posterior mass on a
   single hypothesis exceeds a stated confidence **and** the mass of hypotheses that would behave
   differently on the *user's own* domain is below a stated bound. Crucially, `settled()` must return
   **`UNSETTLEABLE_BY_THIS_INSTRUMENT`** — never `SETTLED` — when no probe in the reachable space has
   nonzero expected information gain. Blindness becomes a *named refusal*, not a silent verdict.

4. **`probe_space.derive(hypotheses, examples)`** — the reachable probe set is derived from the
   hypotheses' own literals and the observed domain, so a grammar's own blindness cannot silently
   define equivalence.

5. **Wire `synthesize_or_disambiguate_skill`**: the Tier-0 recall must pass through `settled()` with an
   oracle available, and the `disc_probe is None` branch must return the refusal instead of admitting
   `candidate_organs[0]`.

## Predictions — stated so they can fail

- **P1 (the headline).** Warm experience must never be *less accurate* than cold. On the six `x mod k`
  instances, warm held-out accuracy ≥ cold held-out accuracy, instance by instance.
  *Falsified if any k is worse warm than cold.*
- **P2 (compounding is real, not cosmetic).** Warm total oracle queries < cold total, **while P1
  holds**. If P1 fails, the query saving is not a win and must not be reported as one.
- **P3 (blindness is refused, not converted).** `k=4` and `k=15` return an explicit not-settled status
  with an accountable reason and admit **no** organ. *Falsified if any organ is crystallized on a
  set the instrument could not separate.*
- **P4 (the world is not blamed).** `k=6` no longer reports `CONTRADICTORY_ORACLE_OR_OUT_OF_GRAMMAR`.
- **P5 (no collapse to timidity).** Genuinely determined problems (the two-operand product, the
  `7x-2y+12` affine, the composed `2(x+1)`) still crystallize. *Falsified if refusing becomes
  universal — a creature that refuses everything is trivially never wrong and perfectly useless.*
- **P6 (cost gate is load-bearing).** With a probe cost above the value of the remaining ambiguity,
  `select_probe` declines to ask and `settled()` reports not-settled. *Falsified if it asks anyway.*

P5 exists because it is the obvious cheap way to "pass" P1–P4. I am naming it in advance.

## What this does NOT claim

- It does not make the creature sentient, and I will not say it does.
- `SETTLED` means *settled with respect to the reachable probe space and the stated confidence*. It is
  never truth. A hypothesis no reachable probe can distinguish remains unknown forever, and the system
  must say so.
- No neural weights, no external model calls, no dynamic code execution in result-bearing paths. $0.
- `truth.achieved` stays false.
- The existing pre-registered failures from earlier rounds stay failures; I am not touching them.

## Why this is the deepest available layer

Every previous round repaired *a* frozen table. This repairs **the act of deciding that a table is no
longer needed** — turning "settled" from a fact about the search path into a computed quantity with a
price, a confidence, and an explicit refusal. That is the difference between a program that searches
and a creature that knows what it does not know — and it is the only change that makes experience
*monotonically* valuable rather than merely faster.
