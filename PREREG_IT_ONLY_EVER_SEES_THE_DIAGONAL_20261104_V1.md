# PRE-REGISTRATION — *It only ever sees the diagonal, and it crashes on anything unhashable*

2026-11-04, V1, round 25. Written **before** implementation, after measuring.
Base: current working tree on `arena/b0d725c0-brain`. `truth.achieved` false, `authority: NONE`, $0.

*(Note on history: `main` has been rewound — it no longer contains my rounds 20-23. The trees are
substantively identical, so this round builds on the working tree and reports against commit hashes that
exist locally. Recorded so the receipts are honest about what they point at.)*

---

## The measurement

Four rounds optimised **inference**: reachability, expression breadth, cost, composition. All of them
measured `f: int -> number`. This round asked a different question — *what can this thing perceive?* — and
the answer is narrower than any of those rounds assumed.

### 1. It crashes on any input it cannot hash

```
list -> len      CRASH TypeError
list -> sorted   CRASH TypeError
dict -> len      CRASH TypeError
tuple -> len     DISAMBIGUATED_AND_CRYSTALLIZED
```

Cause, exact:

```
settlement_v1.derive_probe_space
    seen.add(tuple(ex_in))        # TypeError: unhashable type: 'list'
```

The creature does not reason about lists. It **raises** on them. Every door I opened in rounds 21-24
routes into a function that dies on the first list-shaped input, and no test ever caught it because no
test ever passed a list.

### 2. Multi-argument tasks are only ever probed on the diagonal

```
x+y     -> observational_eq, exact        (2x on the diagonal)
x*y+1   -> NO_CONSISTENT_HYPOTHESIS
block[x%3]+y -> NO_CONSISTENT_HYPOTHESIS
```

Cause, exact:

```
settlement_v1.derive_probe_space
    probe = tuple([x] * arity)
```

Every probe is one number repeated `arity` times. For two arguments the creature only ever sees
`f(n,n)`. `x+y` happens to be affine on that diagonal; `x*y+1` is not affine there, so **no amount of
search improvement can reach it** — the evidence never separates it from a line. This is a perception
limit, not an inference limit, which is why four rounds of inference work could not touch it.

### 3. The cost constant is a real ceiling, and it is measurable

```
P=5  : 25 questions    floor 2P = 10    4P = 20
P=7  : 35 questions    floor 2P = 14    4P = 28
P=11 : 55 questions    floor 2P = 22    4P = 44
```

Two separate leaks: the evidence constant `4P` is 2× the information floor, and the loop overshoots even
that (25 for a 20 budget, 55 for 44). Any P where the budget bites becomes a refusal — this is the same
class of defect as a frozen menu, applied to *questions per structure*.

## The thesis

> The last four rounds made the creature better at **answering**, while its **senses** were fixed. A
> reasoner that crashes on a list and only ever sees `(n, n)` cannot become smart by reasoning harder;
> broadening the input it can perceive broadens every task it can attempt at once.

## What I will build

**A perceptual widening, in the data path rather than the inference path.**

1. **Hashable identity for any value.** A canonical key for lists, dicts, sets, nested structures — so
   `derive_probe_space` measures reachability of *any* input instead of raising. Behaviour unchanged for
   values that already hash.
2. **Non-diagonal probes.** For arity > 1, the probe space must contain points where the arguments
   **differ** — deliberately derived (offsets between slots), not a fixed grid. This is what makes
   `x*y+1` separable from a line at all.
3. **The cost constant becomes derived, not declared.** `table_evidence_requirement` must stop being
   `4P`, and the collection loop must not overshoot the budget it was given. Target: at or near `2P`,
   with the overshoot gone. I will state the new number and its justification *before* claiming it.

## Predictions — stated so they can fail

- **P1 (no crash).** `list -> len`, `list -> sorted` and `dict -> len` return a decision — an answer or a
  refusal — and never raise. A refusal is acceptable; a crash is not.
- **P2 (the diagonal is broken).** `x*y+1` and `block[x%3]+y` become reachable, exact on held-out pairs
  never shown. *Falsified if they still refuse*, which would mean the defect is deeper than probing.
- **P3 (nothing that worked breaks).** Every task solved before this change is still solved, exactly.
  `x+y` must still be exactly right — the risk of non-diagonal probes is that they add noise.
- **P4 (no new false claims).** The adversarial battery stays at zero false positives, and now also
  covers list/dict shapes.
- **P5 (cost actually falls).** Questions for a period-P structure fall toward `2P` and the overshoot
  disappears. I will report the measured numbers whatever they are; if the constant cannot be tightened
  without losing accuracy, that is the result and I will say so.

**Explicitly NOT predicted:** that this makes the creature generally capable, or smart in any human
sense. Widening perception widens the set of problems it can *attempt*; it does not create understanding,
and nothing here compounds across separate problems.

## Non-claims

- A canonical hash is plumbing, not cognition. Calling it "perception" is a description of where it sits
  in the pipeline, not a claim about experience.
- Non-diagonal probing is a **derivation**, not a learned policy. The creature still does not choose
  which question to ask because it would discriminate; it asks a broader set.
- `truth.achieved` false. `authority: NONE`. $0. No external models, no neural weights, no dynamic code
  execution in result-bearing modules. No sentience claim.

## Why this is deeper than round 24

Rounds 21-24 each widened **what it can say**. This widens **what it can be shown**, and the crash proves
the difference: a list input does not produce a wrong answer, it produces an exception — the creature has
never been able to look at one at all. Making inference better is bounded by the evidence it gets. This
changes the evidence.
