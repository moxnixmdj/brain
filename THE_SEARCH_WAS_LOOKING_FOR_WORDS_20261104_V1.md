# The Search Was Looking for Words

**2026-11-04 · round 10 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0**

Nine rounds of epistemology were built on top of a search that cannot fit a straight line.

---

## 1. The measurement that should have come first

`y = 2x + 1`. Three points. Two operations. Any first-year student answers it instantly.

```
2x+1  -> UNRESOLVED  programs=0
      why: "no body in the grammar reproduces the examples"
```

I assumed `2x` was a hard-ish case and that the machinery had been stress-tested. It had not. So I
ran nine ordinary functions through the apparatus and looked at what came back:

| task | status | programs | explanations |
|---|---|---|---|
| `x+1` | PROVISIONAL | 5 | 2 |
| `x*x` | PROVISIONAL | 4 | 3 |
| `abs` | PROVISIONAL | 7 | 5 |
| `x//2` | PROVISIONAL | 22 | 9 |
| `x+y` | DETERMINED | 5 | 1 |
| **`3x+1`** | **UNRESOLVED** | 0 | — |
| **`2**x`** | **UNRESOLVED** | 0 | — |
| `relu` | PROVISIONAL | 15 | 5, **no question available** |

Two total failures on trivially easy functions. Both worth their own diagnosis.

---

## 2. Defect one: the search accused the grammar of its own budget

`2x + 1` *is* inside the grammar. It is spelled `((x + 1) + x) / 1`. The search reaches it at weight
4 — but its candidate bank is capped at 900 entries, weight 3 fills the bank, and the sweep stops
there. The report then said **"no body in the grammar reproduces the examples"**.

That sentence is false, and it is false in the worst available direction: it is a measurement of a
`max_bank_size` constant, published as a fact about the world. Measured sweep:

| task | bank 900 | bank 5 000 | bank 50 000 |
|---|---|---|---|
| `2x+1` | **0** | 21 | 32 |
| `x*x+1` | **0** | 18 | 20 |
| `x+1` | 21 | 38 | 73 |
| `2x` (this session's case) | 12 | 12 | 12 |

The last row is the one that matters for honesty about my own work: **the `2x` conclusions are
stable across a 60× budget change.** The grouping, the three explanations, the interrogation — none
of it was an artifact. The epistemics were sound and were sitting on a search that lies about *why*
it found nothing.

Both are fixed. Completeness is now decidable from state the search already keeps — the bank either
filled or it did not — so an empty result is reported as `SEARCH_TRUNCATED` (a statement about the
budget) or `UNRESOLVED` (a statement about the grammar), and never confused. Every grouping now
carries its basis. And notice what that flag revealed: **the `2x` enumeration was never certified
complete either.** Its numbers are robust, but "these are all the explanations" was never justified
— only observed to be stable.

---

## 3. Defect two: the ontology had no slots

The deeper problem has nothing to do with budgets. The creature's hypothesis vocabulary is *closed
expressions over the inputs and a frozen constant list* `[0, 1, 2, -1, 100, ...]`. Slope 1 and
offset 1 are spellable. Slope 3 is not spellable at any affordable budget, because `(x+x)+x` costs
three operations and so does every other spelling of it.

So the creature cannot say `a·x + b`. It can only write sentences about specific numbers and then
count the sentences. **Every one of the twelve programs for `2x` is a spelling of the same linear
function**, and nine rounds of apparatus — grouping, probe ranges, witnesses, refutation — existed to
work out, by probing, something a slot would have said outright.

`hypothesis_classes_v1` adds the missing kind of object: a template with free parameters and an
exact solver.

```
3x+1        DETERMINED  affine {a: 3, b: 1}       <- the search could not do this at ANY budget
2x          DETERMINED  affine {a: 2, b: 0}       <- one explanation, not three
x*x         DETERMINED  power  {a: 1, k: 2}
piecewise   UNRESOLVED  (nothing fits, correctly)
```

Three properties the string search structurally cannot have:

**The evidence requirement is computed from the class, not discovered by trial.** Two parameters,
two points. The third point is a *test*, not new information — the report says `surplus: 1`. A
creature that cannot make that distinction cannot know when it has enough evidence; it can only know
when it has stopped finding new matches.

**The question is formed before the answer exists.** The string search asks which of its survivors
disagree — a question it can only form once survivors exist. A family knows what would pin it while
it is still unpinned: *any unused input*. That is anticipating a gap instead of reacting to one.

**Grouping is algebraic where a class applies.** Same family, same parameters → same explanation,
exactly, no probe range and no caveat. The probe-range caveat survives only for bodies belonging to
no class.

**And it hands the fit back to the search.** A family that fits is a hypothesis, not a program. So
the fit is compiled to source — `return 3 * x + 1` — and verified by the same checker the search
uses. Without that step this would be a parallel ontology proving nothing about the creature's
reach, which is precisely the criticism every earlier round deserved.

---

## 4. Bugs in my own new code, and what they have in common

**Silent signature mismatch.** `determine` takes flat `(x, y)` pairs, `reach` takes the project's
`((args,), value)` form. `reach` passed one to the other, every fit came back `UNSUPPORTED`, and it
reported *"no family in this ontology explains the observations"* for data it had just fitted
correctly. A non-result that looks exactly like a mechanism saying no. Same family as the stale
collection last round, and the `repr` signature before that: **one module substituting a value of the
wrong shape for the one it was asked about.**

**A crash on every fractional fit.** Parameters are reported as int or as `"n/d"` strings. The
compiler compared them numerically — `b >= 0` — so an entire class of *correct* answers raised
`TypeError`. Found only by trying a third, an offset, and a constant in the same sweep.

**An unreadable correct answer.** Fitting to float `1/3` yields
`3333333333333333/10000000000000000` — exactly right, since the float genuinely is not `1/3`, and
useless as an answer. Rational reconstruction now reports `(2 / 3) * x + (1 / 3)`, and the fit
carries `reconstructed: true` so the reconstruction is visible rather than assumed. My first test of
this was wrong: it asserted `sqrt(2)` came back unchanged, but a continued-fraction convergent
*is* within 10⁻¹² of it. The honest property is that an irrational never reconstructs to something
small enough to look like a clean result.

---

## 5. What this says about the asking

Nine rounds answered *"how should a creature behave when its evidence is thin?"* — carefully,
correctly, and at length. The answer kept being about how to count and interrogate a set of
candidate sentences, because the candidate sentences were the only representations available.

The tenth question was different: **what kind of thing should a hypothesis be?** Once a hypothesis
can have a slot, "how many explanations does this data permit" stops being a search-and-probe
question and becomes division. The probe range, the grouping, the witnesses — none of it was wrong,
and all of it was a workaround for a missing primitive.

That is the pattern to carry forward, and it is not flattering: the machinery improved steadily
while the thing it reasoned about stayed fixed, and every apparent advance was an improvement in
*bookkeeping about a fixed vocabulary*. The vocabulary was the bottleneck for three rounds of
increasingly clever work that never once asked whether `a·x + b` was sayable.

---

## 6. Where each mechanism still fails

Honest scoreboard, because a new primitive makes it tempting to declare the old one obsolete:

| input | family | string search |
|---|---|---|
| `3x+1` | fits exactly | `SEARCH_TRUNCATED` at 900, **0 bodies at any budget tested** |
| `2x` from 3 points | **1** explanation | 12 programs / 3 explanations |
| piecewise | **refuses** | 50 programs, all interchangeable |
| `x+1` then `2x` | **refuses** | 16 programs |
| `mod 2` | **refuses** | 107 programs |

The family is devastatingly right where a class applies and useless where none does — and it is
*only* those two classes so far. The string search is the opposite: it always produces something and
cannot tell when the something is noise (107 programs for `mod 2`). Neither subsumes the other. The
obvious next primitive is to let the search **compose** fitted families into piecewise bodies, which
is the same "repair instead of delete" that the refutation round asked for, now with something to
compose.

**Non-claims.** No sentience. A fitted family is a guess that fits — `a=2, b=0` is not true because
it is simple. Reconstruction is stated per fit, not assumed globally. Two classes only; one input
only; no composition. `3x+1` is reachable *by the family*, not by the string search. The oracle in
last round's measurements remains a lambda. `truth.achieved` false. $0.

---

## 7. Ranked next moves

1. **Compose.** Give the search families to instantiate inside piecewise bodies; `mod 2` and
   piecewise are where both current mechanisms fail, and both fail by refusing to have a second kind
   of object.
2. **Coverage as a first-class argument.** Every claim from every module should carry the budget it
   was measured under. `2x` was never certified complete and nobody noticed for eight rounds.
3. **Let the family ask its question of the real oracle** — it can form one before seeing anything,
   which the string search cannot.
4. Domain tracking; the front door.
