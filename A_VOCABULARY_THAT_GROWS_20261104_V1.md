# A Vocabulary That Grows

**2026-11-04 · round 12 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0**

Eleven rounds improved the reasoning. None of them touched the thing being reasoned about.

---

## 1. The measurement that should have come first

Two facts, both true at the same moment, before this round:

```
mod 2 as STRINGS : PROVISIONAL — 75 programs, one of them  ((x / 1) % 2)
mod 2 as CLASSES : ONTOLOGY_EXHAUSTED
```

`%` is in the string search's operator inventory. "Remainder" is not in the hypothesis inventory.
**The written vocabulary and the thought vocabulary were disjoint**, and every round of work had gone
into making the written side's bookkeeping more careful.

And the reason it stayed that way:

```
FAMILIES = {Affine, Power, Constant}     three Python classes, typed by hand
```

A fourth kind of hypothesis entered the ontology only when **I** edited source. Everything about
*which primitives are available* was mine, permanently. No amount of epistemics can move that, which
is why the thing kept being describable as static code no matter how much machinery was hung on it.

Third measurement, same theme: a refutation was discarded when the call returned. `mod 2` was
declared `ONTOLOGY_EXHAUSTED` twice, identically, with no record of having been asked. **A verdict
that cannot change under any experience is not a belief — it is a constant.**

---

## 2. The recovery

Round 11 ended by writing: *"`mod 2` remains unexplained by everything in this repository; next round
should make it the target."* A static toolkit cannot take a target and come back with a new
primitive. So I made that sentence the test.

**The survivors are evidence.** When a sweep overflows its bank, the programs that remain *fit*. A
program that reproduces every observation is wrong-maybe but never arbitrary, so the vocabulary it
draws on is a sample of what the target is made of. For `mod 2`:

```
binop vocabulary   : {'Mod': 3, 'Div': 3, 'USub': 1}
constant vocabulary: {'2': 3, '1': 3}
```

`%` is there. `+` is not. The operator that creates partitions is in the admissible set, and the
target's structure becomes findable — not because I said "look for periods", but because the fitting
programs use `%` and nothing else structural.

Regenerating from that vocabulary and testing partitions exactly:

```
mod 2   INDUCED   value repeats every 2 inputs
    _r = int(x) % 2
    if _r == 0:  return 0
    elif _r == 1:  return 1
```

**The name is read off the parameters** (`period=2`), not matched against a word I supplied. On
period-3 data the same pathway returns `value repeats every 3 inputs`. That is what S3 existed to
check: change the data's period and the name changes with it.

---

## 3. Two things this proved that I did not expect

**It works where the search cannot spell the function.** `x % 3` is *not* in the string grammar — the
right operand comes from the seed constants and 3 is not among them. So `mod 3` yields **zero**
admissible programs at a complete sweep. The partition test still recovers period 3, from six points,
because a partition is a property of the observations rather than of the syntax. The evidence gate
turned out to be an accelerator, not a requirement.

**And it immediately tried to lie.** Given only the observations, six *unrelated* points were
"explained" by **period 6**: six residues, one value each, a perfect partition carrying no
information. That is the identical failure to `mod 2` composing into two memorised constants last
round — *as many parameters as observations*. So a residue class must now be witnessed at least
twice. Six noise points: refused. Eight quadratic points: refused.

That constraint is doing more work than the induction itself, and it was found by running the thing
on data I expected to fail and watching it succeed.

---

## 4. A lifetime

Same inputs, twice, one process, no code change in between:

```
before learning : ONTOLOGY_EXHAUSTED
first encounter : INDUCED (value repeats every 2 inputs)
second encounter: RECOGNISED
```

Refutations are kept too, so a repeat encounter reports what was already ruled out instead of
re-testing from nothing. Recognition is an **exact re-check** against the induced body, not a
remembered verdict: applying a table of previously-seen values and calling it recognition is the
error the whole arc is about, and there is a test asserting it declines.

This is the first thing in twelve rounds whose answer depends on something that happened before.
Every previous module was a pure function of its arguments, which is precisely why the creature read
as static code no matter how good the reasoning was.

---

## 5. Honest scoreboard

| target | string search | class layer | induced |
|---|---|---|---|
| `2x`, `3x+1` | 0 bodies / 12 programs | **affine, exact** | — |
| `relu`, regime change | 15/50 programs | refuses | — (composition covers these) |
| **`mod 2`** | 75 programs, `PROVISIONAL` | **exhausted** | **`value repeats every 2 inputs`** |
| **`mod 3`** | **0 bodies** — unspellable | exhausted | **`value repeats every 3 inputs`** |
| six random points | 0 bodies | exhausted | refused |
| quadratic | fits by family | `power` | refused |

**What is still not general, stated plainly.** One new kind was recovered: periodic. The pathway that
recovered it is a *partition test* — the right test for that kind. It is not a general engine that
discovers arbitrary primitives; it discovers primitives that the fitting programs' vocabulary
corroborates and that a known structural test can verify. `mod 3` induced from observations alone
because I had already written the partition test. It is honest to say: **the recovery of a kind
becomes possible when a test for that kind exists**, and writing the test is still my job.

What genuinely changed is not that the ontology is self-extending in general. It is that (a) the
ontology now grows *without a new class per kind*, from evidence rather than from an edit, and (b) the
creature's verdicts now accumulate, so it can be wrong and then be less wrong.

**Non-claims.** No sentience. `INDUCED` does not mean true — a period-2 table reproduces six points
and could still be wrong at seven. The vocabulary gate depends on the search finding at least one
admissible body, and `x % 3` shows that gate can be empty while the structure is still there. Two
kinds total now (curve, periodic). `truth.achieved` false. $0.

---

## 6. Ranked next moves

1. **Make the test, not the kind, the thing that is discovered.** Right now each new structural kind
   needs a test written by me. The general move is to derive a candidate test from the vocabulary
   (a partition, an ordering, a monotone run) and let the data refute it — which is the same
   "constraint enforces honesty" pattern that just worked twice.
2. **Persist the ontology across processes.** It is in memory; a restart forgets everything, and a
   memory that dies with the process is a demonstration rather than a creature.
3. **Feed the induced body back into `demand_evidence` and the refutation loop**, which still only
   speak to the string search — S8 was predicted and is not yet wired.
4. Domain tracking; the front door.
