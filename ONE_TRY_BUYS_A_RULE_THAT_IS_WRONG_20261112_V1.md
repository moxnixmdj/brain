# One try buys a rule that is wrong

**2026-11-12.** Base `e3f6075f`. Branch `arena/2356f2b6-brain`. Round 2 of the owner's question.

The owner asked again, and the fair reading of asking three times is that the previous answers were
arguments, not evidence. So this round does not argue. It measures his sentence inside this tree's
own settlement machinery:

> *"After he does them at least once, he would learn all of those permanently."*

Authority **NONE**. Constructed experiment, one machine, no independent verifier, $0, zero model
dependency. `truth.achieved` stays `false`. No capability registered.

---

## 1. The measurement

`one_shot_identifiability_probe_20261112.py` — 47 hand-authored unary integer programs; 10 targets,
each a member of that space (checked; the probe fails closed if not); scored on inputs **10..21**,
which appear in no demonstration. Everything runs through `canonical/runtime/settlement_v1.py`
(`VersionSpace`, `settle`, exact information gain), not through a re-implementation.

| target | programs still fitting after **1** demo | leader right on held-out | after **3** demos | leader right | one demo + **chosen questions** |
|---|---|---|---|---|---|
| `affine:-1:2` | 16 | 1.00 | 1 | 1.00 | 2 q → 1.00 |
| `affine:2:1` | 3 | 0.00 | 1 | 1.00 | 1 q → 1.00 |
| `const:0` | 14 | 0.00 | 7 | 1.00 | 2 q → 1.00 |
| `floordiv:2` | 14 | 0.00 | 2 | 1.00 | 2 q → 1.00 |
| `floordiv:3` | 14 | 0.00 | 1 | 1.00 | 2 q → 1.00 |
| `mod:3` | 16 | 0.00 | 1 | 1.00 | 2 q → 1.00 |
| `mod:5` | 16 | 0.00 | **7** | **0.00** | 2 q → 1.00 |
| `mod:7` | 16 | 0.00 | **7** | **0.00** | 2 q → 1.00 |
| `square` | 16 | 0.00 | 1 | 1.00 | 2 q → 1.00 |
| `threshold:0` | 16 | 0.00 | 3 | 1.00 | 3 q → 1.00 |

```
after ONE demonstration:      14.1 of 47 programs still fit
                              leader right on 10% of held-out inputs
                              0 of 10 targets exactly identified
after THREE demonstrations:    3.1 fit;  leader right 80%;  5 of 10 exactly identified
one demo + chosen questions:   2.0 queries;  leader right 100%;  10 of 10 settled
one demo + a narrow prior:     leader right 100%
```

Two things to notice, because both are load-bearing.

**One demonstration leaves 14 programs standing, and the one you would pick is wrong on 90% of the
inputs the caller actually cares about.** That is "learn it once": not a rule, a guess with a
justification. It is not an implementation defect — every one of those 14 programs genuinely agrees
with the observation. They disagree about the next input.

**Three demonstrations do not rescue it.** `mod:5` and `mod:7` still have seven candidates and are
still 0% right after seeing `1, 2, 3` — because those three points cannot distinguish period 5
from period 7 from several affine readings. This is the same insufficiency the tree already found
for period 4 from three seeds, reproduced in 40 lines. More exposure is not the missing thing;
*informative* exposure is.

**Two chosen questions take it to 100%, 10 times out of 10.** That is the honest form of "instant
learning": not one shot, but ~2 bits of *chosen* evidence. `settlement_v1` picks those questions by
exact expected information gain, and this run is the first place its whole loop — observe, choose,
settle, refuse — is scored end to end on held-out inputs.

**And the counterfactual names where the generalising happens.** The last line is the same single
observation as the first, against a space that already contains only two candidates. It is right on
all ten targets. **The example did not change. Only the space did.** That is the entire argument,
measured rather than asserted: the prior generalises, the example only selects.

## 2. What this does *not* say — and it matters, because here the owner is right

The owner is not wrong everywhere. There is a regime where one try genuinely is enough, and this
tree already lives in it:

- **`environment_fit_v1`** reads a repository's own declarations (CI workflow → `package.json` →
  `Makefile` → `pyproject`) and applies ADAPT → PROVISION → FOLLOW to repositories never seen
  before. One shot, and it works.
- **A one-shot taught repair** reaches 5/5 syntactic shapes *under apply-time narrowing with a real
  suite*, versus 1/5 without it.
- The industry's best 2026 result — Agent S4 — gets 3.8× by evolving **interfaces**, with held-out
  validation choosing which repository survives.

What do those have in common? **A stable, declared, programmatic interface, plus a mechanical
verifier.** In that regime the interface *is* the prior: `npm test` means the same thing in ten
thousand repositories, so a lesson expressed against it transfers without any induction at all.
That is why "give it a stable action interface" is right — not because actions teach the system,
but because **a typed interface is a pre-loaded hypothesis space**, and code against it is a lesson
that needs no generalisation.

Outside that regime — pixels, untyped state, goals whose acceptance is a judgement — there is no
shared interface, and the measurement above applies unchanged: 14 candidates, 10% right.

So the correct form of the owner's sentence is:

> **One try is enough exactly when the interface and the verifier already do the generalising.**

That is not a technicality. It is a design rule, and it says where to spend the next month: not on
more environments, but on **widening the interface regime** — making more of computer use into code
against a declared interface with a mechanical check, which is precisely the move that produced the
only large 2026 gain.

## 3. Why "more environments" still fails outside it

Same probe, different question: does meeting more *kinds* shrink the space for the next kind? No —
measured twice in this tree (`cold_acts=1525 grown_acts=1525`, byte-identical; learning-to-learn
beat a coin flip 3/10). A per-kind store is 47 hypotheses partitioned into 10 boxes of 47. The
boxes do not talk, so `mod:5` learns nothing from `mod:3`.

The fix is not a bigger store. It is a **shared** space, which is what §2's interface regime gives
you for free and what hand-authored grammars give you only where a person wrote the shape.

## 4. What to do with this

1. **Make the interface/verifier regime the default.** Every capability that can be expressed as
   code against a declared interface with a mechanical check gets one-shot transfer for free. Count
   how much of the current surface is in that regime; that count is the real capability number.
2. **Where it cannot, spend questions, not examples.** Two chosen probes beat three demonstrations
   10-to-0 in the table above, and cost less. `settlement_v1` already chooses them; the rule store
   still does not ask.
3. **Then, and only then, the donor-distilled prior** (`THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md`
   §6, B1): harvest candidate hypothesis spaces, delete the donor, verify at zero model. That is the
   only route to a shared space that no person wrote.

## 5. Receipts

```
python3 one_shot_identifiability_probe_20261112.py
canonical/tests/test_one_shot_identifiability_probe_v1.py    8 tests, all passing
```

The tests pin the properties, not the prose: every target is a member of the space; survivors never
grow; no target is exactly identified by one demonstration; the message and the probe pool are
disjoint from the scorer; the run is deterministic; and the same observation under a two-hypothesis
space is right on all ten targets where the full space is wrong on nine.

## 6. Non-claims

The hypothesis space is hand-authored — that is the finding, not a caveat. Numbers are specific to
this space; the invariant is that the version space after one observation is large for any
non-trivial space, not that it is exactly 14.1. Constructed experiment, one machine, no independent
verifier, no GUI, no unbounded computer use, $0, zero model dependency. Authority NONE.
