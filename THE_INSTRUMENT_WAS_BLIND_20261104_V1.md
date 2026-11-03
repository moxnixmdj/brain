# The Instrument Was Blind

**2026-11-04 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0 spent**

Yesterday's document said the concept library buys compactness but **not reach**, and I ranked
"explain the held-out 1/2" as the most informative next move on the grounds that an unaccounted
result is worth more than a accounted one. That was right, and the explanation is worse than a
gap in the data:

> **The reach was there. My measuring instrument had three bugs, each of which independently
> suppressed it.**

I had written *"I do not have an explanation for this that I trust, so I am not going to write
one."* Writing none was the correct call. The explanation, once found, was not about the creature
at all — it was about the ruler.

---

## 1. What was actually wrong

I built `canonical/runtime/generalization_check_v1.py` to fix the first thing I noticed: the
benchmark counted a *non-`None` body* as a solve. Reading one of those bodies showed why that is
worthless —

```python
if not lo2:
    return ((s + 2) / hi2)
return ((s - lo2) / 1)
```

— which reproduces three teaching examples and is not the target function. The new checker holds
points back, synthesizes on the rest, and requires agreement on the withheld points. Counting
honestly turned "1/2 solved" into "0 genuinely solved".

Then the checker itself failed on bodies that *were* correct. Three separate faults:

| # | bug | effect |
|---|---|---|
| 1 | `synthesize_python_function_body` returns concept helpers already materialised (a `def concept_…` block followed by the real `return`); my compiler wrapped *every* line in one function | a correct body compiled into a nested-def nonsense, scored OVERFIT |
| 2 | `exec(src, globals, locals)` put the helper `def` in locals while the body resolved names in globals | `NameError` → scored OVERFIT |
| 3 | two of my benchmark's own expected values were wrong (I typed `0.75` and `2.0` for inputs whose true values are `1.2` and `1.5`) | correct outputs scored as failures |

Bug 3 is the same error I have now made four times in this project: **the first instrument always
flatters the hypothesis I already believe.** Here it flattered the pessimistic hypothesis, which is
why it survived a round — I was not looking for a reason to distrust a negative result.

Every expected value is now *computed from the reference function*, never typed.

---

## 2. The corrected result

Concept: a clamped normalisation, absent from the synthesizer's bank. Taught from 16 example
programs. Held-out problems apply the concept and then compose it with something new. Withheld
points are never shown to the synthesizer.

| form | empty library | after invention |
|---|---|---|
| `c + 0.5` | OVERFIT | **SOLVED** |
| `c − 0.5` | OVERFIT | **SOLVED** |
| `c * 2.0` | OVERFIT | **SOLVED** |
| `c / 0.5` | OVERFIT | **SOLVED** |
| `0.5 − c` | OVERFIT | OVERFIT |
| `max(c, 0.5)` | OVERFIT | SOLVED *(with 6 training examples)* |
| `1.0 − c` | UNREACHED | UNREACHED |
| `c ** 2` | UNREACHED | UNREACHED |
| `2c + 0.5` | UNREACHED | UNREACHED |

Aggregate, three problems with a `+0.5` / `×2` / `1−c` split: **0/3 → 2/3 generalising solves**,
stable at `max_weight` 3 through 6. The bodies returned are exactly right:

```python
return (concept_640d4492(v, l, h) + 0.5)
```

That is composition of an invented concept with a new constant, generalising to four unseen
points. It is the first honest reach gain this project has measured, and yesterday's document
denied it.

---

## 3. The real limit, which is more interesting than the false one

`0.5 − c` **overfits** rather than being unreachable. With three training points the search
returned `-((2 / h))` — a formula that fits the examples and means nothing. `max(c, 0.5)` came back
as `c or 0.5`, then became the correct `max(concept_(v,l,h), 0.5)` once six examples were supplied.

So the synthesizer **returns the first body that fits its examples**. With few examples "fits" is
cheap, and an interpolation wins before the correct composition is ever reached. The limit is not
the concept, and not the grammar — it is that *fitting is not generalising*, and the search has no
notion of the difference. It will confidently return nonsense when the evidence is thin.

`1.0 − c` and `c ** 2` stay unreachable because the combiner only joins a weight-2 concept with a
weight-1 term: there is no binary operation node that takes the concept and a constant as a squaring
or a subtraction-from-one, and no unary-node-application path. A concept can be *combined*, not
*transformed*. That is a grammar boundary, and it is the next thing worth widening.

---

## 4. What the join was worth, restated

The semantic join from the previous document is unaffected and its role is now sharper. With the
honest counter:

- empty library: **0 generalising solves**
- concept taught on a single-spelling corpus: **1**
- concept taught on a two-spelling corpus: **1**
- concept taught on a corpus repaired through a semantic correspondence: **1**

The join does not add reach. It recovers the *admission* that re-spelling cost (2 concepts vs 1 at
a thin corpus, fully restoring the single-spelling count) and it makes one concept cover a corpus
written two ways. The reach gain comes from the concept existing at all. Two mechanisms, two
different jobs, and conflating them is how yesterday's document went wrong in the first place.

---

## 5. What this says about a creature

The honest reading is that the creature can now do something it could not do before: **notice that
many solved problems share a sub-idea, name it, and then use that name as a building block in a
function it has never seen.** That is compositional reuse — a real cognitive primitive, not a
benchmark artefact.

And the same experiment exposes the thing it cannot do, in a way that is more diagnostic than any
list of failures: **it cannot tell when its own explanation is wrong.** When evidence is thin it
returns `c or 0.5` and has no internal signal that this is not `max(c, 0.5)`. It has no equivalent
of "this answer is convenient and I should double-check it." Every bug in this document — three in
the ruler, four across the project — is that same absence, in me, reproduced in the machinery. A
creature that generalises but cannot audit its own generalisation will be confidently wrong at
exactly the moments confidence matters.

**Non-claims.** No sentience. Pure Python over small numeric tuples; no I/O, no host execution, no
GUI; nothing here bears on reaching a shell or browser, which remain gated. "SOLVED" means agreement
on four withheld points, not proof of the function. `truth.achieved` stays false. $0 spent.

---

## 6. Ranked next moves

1. **Widen the combiner.** `1.0 − c` and `c ** 2` fail for a structural reason: a concept can be
   joined with a weight-1 term but not transformed by a unary operator or squared. Adding a
   unary-application path over learned concepts is a small, falsifiable change with a pre-registered
   expectation: those two forms move from UNREACHED to SOLVED or OVERFIT.
2. **A self-audit gate.** The synthesizer returns the first fit. A cheap second pass that rejects a
   body whose withheld-point agreement is worse than a simpler body's would attack the `c or 0.5`
   failure directly. This is the capability that matters most, and it is where the creature analogy
   actually bites.
3. **Composition of invented concepts** — concept built from concept. Still untested. Two-away
   problems are the only route to compounding-on-compounding.
4. Concept invention on the primary path (still behind a cognitive-core buffer, not the front door).
5. Backlog. Last.
