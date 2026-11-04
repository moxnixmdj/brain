# First principles, pass eleven — it repaired with an edit it never performed

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

Pass ten moved the ceiling with a generator I wrote, and said so: *"I wrote it; the creature did
not learn it."* The falsifier was therefore mine to answer:

> Can the creature derive an edit class from its own successes — without being told what a class is
> — and apply it in a context it has never edited?

**Yes. Measured on the real loop.**

## 1. The mechanism, entire

    a successful repair is (before, after)
    tokenize both; if exactly one token differs, that is a substitution the creature performed
    substitutions form a graph whose nodes are tokens the creature itself changed
    transitive closure over that graph is the inferred edit class
    proposal = apply every observed and inferred pair at every real occurrence of its left token

No family table. No node kinds. No model. The only authored content is "a single-token
substitution is an edit worth generalising", which is the definition of the experiment rather than
a hint about arithmetic.

## 2. The result

Two lives, both BinOp worlds it could already repair:

    life 1:  return a * b   ->   return a + b      observed  * -> +
    life 2:  return a + b   ->   return a - b      observed  + -> -
    inferred (never performed):                    * -> -

Held-out world `return a * b` where the answer is `a - b`:

    candidates proposed: 2      passing: [1]      patch: return a - b

**It repaired the world with a substitution it had never performed, derived from two it had.** That
is the difference between a system that accumulates and one that is static, and it happened without
a teacher, without a family table, and without a model.

## 3. The part that actually matters: the class grows

Exercising it on four operators — never told which operators belong together:

| seen | observed | inferred (never performed) |
|---|---|---|
| 4 ops (`*->/ +->* -->+ /->//`) | 4 | **6**: `*->// +->/ +->// -->* -->/ -->//` |

Give it `- -> +` and `+ -> *` and it derives `- -> *`. Give it a chain and it derives the chain's
composition. **The hand-written family table is recoverable from experience alone**, which means the
table in `operator_family_rewrite_v1` is not knowledge the creature lacks — it is knowledge the
creature can earn, given successes to observe.

## 4. Where it is still blind, stated plainly

- **The class is closed.** Learning `- -> +` produces no cross-family edges, because there are none
  in its experience. A world whose operator never appeared anywhere gets **zero attempts**. Coverage
  is live, not monolithic: it grows with what the creature has done and is silent about the rest.
- **Augmented operators do not compose for free.** `-=` is a single token, so a token-comparing
  learner cannot derive `-= -> +=` from `- -> +`. It carried that edit only because it had observed
  exactly that pair, from its own augassign repair. That is observation, not inference, and the
  difference is worth keeping straight.
- **Not wired into the live path.** It is a validated mechanism with a falsifier passed, not a
  shipped producer. Wiring it now would double-propose what the hand-written generator already
  covers. The measurement that would justify wiring — does the derived class *beat* the hand table
  on held-out shapes, including ones the table omits — has not been run.

## 5. What this changes about the whole effort

For ten passes the question was "how does the creature use what it remembers", and every answer
was bounded by search it could not bootstrap. The actual answer was underneath that:

> The creature was never missing a memory. It was missing the **abstraction step** — nothing in the
> system ever turned a success into a reusable claim.

`operator_family_rewrite_v1` proved the ceiling moves when an edit class exists.
`derived_edit_classes_v1` proves the creature can build one from its own history.

## 6. The next falsifier, stated so it can fail

**S7.** Delete the hand-written family table. Let the derived class be the *only* source of
operator-family proposals, warm-started from nothing. Measure on the twelve-shape screen:

- If it reaches the hand table's coverage (10-11 of 12) by the end of the run, the abstraction is
  real and the table should be deleted permanently.
- If it covers materially less, then inference buys generality at the cost of reach, and the honest
  design is both: a hand-seeded class for what is known, the derived class for what grows.

Either outcome is a real answer. The thing that would make this effort meaningless is leaving the
mechanism validated but unwired, and calling that progress.

## 7. Standing bar

Different at the end of a run than at its start: **yes, for the first time, in a measured sense** —
two lives produced an edit the creature had never performed, and that edit repaired a world it had
never seen. It is one mechanism, on one family of defects, validated outside the live path. That is
not sentience and it is not general. It is the first time this system has been non-static on
measurement rather than on description.
