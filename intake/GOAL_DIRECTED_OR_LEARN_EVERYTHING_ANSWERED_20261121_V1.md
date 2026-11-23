# "Goal-directed, or learn everything?" — answered with a ratio

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · 7 tests pass

The user asked this and did not know the answer. It is not a matter of taste; it is **3.0×**.

---

## The measurement

Four real environments, opaque atoms, effects learned by executing once and reading the machine's
own state. Same four requests per environment.

| environment | atoms | learn everything | goal-directed | saving | goal needs |
|---|---|---|---|---|---|
| FILESYSTEM | 5 | 10 trials | **2** | 8 | PERSIST, REPLACE, REMOVE |
| GIT | 5 | 10 | **3** | 7 | PERSIST, REMOVE, REPLACE |
| TARBALL | 4 | 8 | **4** | 4 | PERSIST, REPLACE, REMOVE |
| SQLITE | 4 | 8 | **3** | 5 | PERSIST, REPLACE, REMOVE |
| **total** | 18 | **36** | **12** | **24** | |

**3.0× cheaper**, and the saving is not a one-off: it is paid **every time the environment is
new**.

## Why the saving cannot be amortised

The obvious objection is "learn everything once and reuse it later". That is exactly what the
verdict already measured against:

> **3 of 216 names overlap** between two real hosts on the same machine (1.4%).

A fact learned about one environment's atoms is worth almost nothing in the next environment. So
"learn everything and generalise later" is not an investment with a payoff — it is a **fixed tax
in every new environment**, spent on atoms no goal in that environment ever touches.

And the tax is worse than the count suggests: **17 of 20** measured atom shapes cannot change the
state at all. Most of the budget goes on proving that something does nothing.

## What makes goal-directed possible here at all

Because the goal and the atom's effect are expressed in **the same closed, surface-neutral
vocabulary** — `PERSIST`, `REMOVE`, `REPLACE`, `APPEND`. So "what does this goal need" is
computable **before probing anything**: it is a set of target effects, and an atom is probed only
while one of those effects is still missing.

That is the difference between paying for the answer and paying for the question.

## And it is the only form that can say "not possible"

On TARBALL the goal needs `REPLACE` and **no atom produces it**. The goal-directed learner reports:

```
unsatisfiable: ["REPLACE"]   state: "IMPOSSIBLE-HERE"
```

Learning-everything cannot do this. With 18 facts and no idea which of them matter, it has no
grounds to declare an environment incapable — so it fails, slowly, at the end.

This is the same abstention the filesystem work measured as a first-class, **zero-cost** result
(`/usr/sbin` ships no gzip, and the system says so for one 48 ms scan). Abstention and goal
direction are the same mechanism seen from two sides: **knowing what you need tells you what you
have not got.**

## What generalises, then, and what does not

| generalises across environments | does not |
|---|---|
| the **effect vocabulary** (`PERSIST`/`REMOVE`/`REPLACE`/`APPEND`) | which atom produces which effect |
| the **goal**, expressed in that vocabulary | an atom's arguments |
| the **read-set** (what has been read, so it is not re-read) | any name |

So the answer to the user's question is not "save the important learning" in the sense of keeping
a curated subset of facts. It is:

> **Save the vocabulary and the read-set. Re-derive the facts, because they belong to the
> environment and die with it.**

That is goal-directed learning done properly, and it is also the smallest possible store: one
vocabulary, one read-set, and no facts at all.

`truth.achieved` remains `false`.
