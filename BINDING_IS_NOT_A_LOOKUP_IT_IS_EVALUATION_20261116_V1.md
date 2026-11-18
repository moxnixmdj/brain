# Binding is not a lookup. It is evaluation

*Round 7. 2026-11-16. Branch `arena/d68bba94-brain`, base `90e2e795`.*

## What round 6 left, and why this round exists

Round 6 measured permanence on real releases and found that the dangerous class was not *"learned and
silently wrong"* — it was *"never learnable at all"*: **30 of 76 real actions (39%)** could not be exercised,
because the arguments that would make them run are not in the environment's scalar vocabulary. You cannot
learn a behaviour you cannot run.

So round 7 asks the prior question: **can the arguments be constructed from the environment itself, with no
model?**

The 2026 field's answer is to pay a model to invent them. Plain-LLM test generation beats the classical
generators by **17.7% line** and **19.8% branch** coverage (arXiv 2601.09695), and AI-generated tests still
score only **40–55% on mutation testing** against 70–90% for human tests — *tests that run, not tests that
catch bugs.* We do not use a model, and we do not have to invent arguments, because **a real call site is a
proof that those arguments worked for somebody** — and the environment is full of them, in its source and
its own tests.

## What was built

`argument_construction_v1.py` mines every call site of the target callables from **every python file in the
tree**, and encodes each argument vector as prober tokens. A `Name` argument is resolved only from:

- a literal assignment **once** in the enclosing function (bounded local constant propagation — a
  reassigned name is not propagated);
- a **module-level literal constant** (`TAGS = [...]` is a proof the environment carries);
- a **builtin type object** (`parse_float=float` is a legal argument and cannot ride through JSON).

A call site with keywords, star-args, or an **object** argument is **refused by name**, never approximated.
An action becomes observable only if the mined call **returns and returns the same thing twice**; and then
the *same* action is run at the later release, classified by round 6's taxonomy — because an unlocked action
that is silently wrong would be worse than an unexercised one.

## The measurement, on round 6's exact denominator

| | |
|---|---|
| real actions examined | **82** |
| already exercisable with scalar witnesses | 40 |
| **round 6's unexercised set** | **41** |
| **now RUN** | **1 (2.4%)** |
| moved by the release bump | 0 |
| `REFUSED__EVERY_CALL_SITE_IS_UNENCODABLE` | **34** |
| `REFUSED__MINED_BUT_NEVER_RETURNED` | 6 |
| `REFUSED__NO_MINEABLE_CALL_SITE` | 1 |

The single unlock is real and exact: **`_cpython_abis([3, 7])` in `packaging.tags`**, mined from a genuine
call site, returns `['cp37m']` in both revisions.

## What the census says — and it is the finding

**83% of the refusals are `EVERY_CALL_SITE_IS_UNENCODABLE`.** I checked whether that was my instrument
being lazy by adding module-constant resolution: it changed **nothing**. The calls that remain refused pass
`state`, `out`, `parser`, `Signer` — **constructed objects**.

That is the whole answer, and it is a first-principles one:

> **The environment's proofs are proofs about *expressions*, not about *values*.** A call site
> `parse_key_value_pair(src, pos, out, parse_float)` proves that *something* can be passed there; it does not
> contain the something. To obtain it you must **evaluate the expression** the environment wrote — build the
> `Parser`, advance the position, allocate the accumulator — and let execution be the only judge.

So binding cannot be a lookup over literals. It is **evaluation**, and the organ that does it is a
**constructor closure**: take the argument expressions the environment itself writes, resolve them
recursively against the package's own callables and classes, and accept a construction only when the call
that consumes it actually returns.

## Two defects I found in this instrument before any number was believed

1. **Module-level call sites were invisible** — my walker only entered functions. This round's own tests
   caught it before a single corpus number existed. (It is the same class of error as round 6's
   path-keyed modules: a silent filter that quietly shrinks the denominator.)
2. **The first fixture "proved" nothing** — the action I chose returned fine for scalar witnesses, so the
   test asserting "now it can run" was satisfied by the pre-existing path. Replaced with an action that
   *raises for every scalar witness* and returns only for the mined vector, so the test can fail.

## Where the whole series now stands

| round | organ | result |
|---|---|---|
| 1 | experience → actions | cost law; `p_correct` 0.2978 |
| 2 | differential pins | 13 drivable, **0 pins** |
| 3 | structure → laws | 188 laws, **0 kills** |
| 4 | instruction → contract by occurrence | 2 of 40 compile, **0 usable**; the site is missing |
| 5 | site by intervention | **1 of 40** usable — the first real discriminating contract |
| 6 | permanence on real releases | 31% of observable actions moved, **all loud**; **39% never learnable** |
| 7 | arguments from the environment's proofs | **1 of 41 (2.4%)** unlocked; 83% need *evaluation*, not lookup |

Every round has hit the same wall from a different side, and each round has moved the wall one layer closer
to the truth: **the specification** (rounds 1–4), **the site** (round 5), **the observable** (round 6), and
now **the construction of the inputs that make an observable exist at all** (round 7).

The honest summary for the standing claim is unchanged and now sharper: instant learning is a **cost law on
already-specified, already-executable actions**. On real code, 39% of actions are not executable by
inspection, and only 2.4% of those can be recovered by reading the environment's proofs as data. The rest
require *running expressions the environment wrote* — which is the next organ, and the only remaining piece
between "13 of 42 actions verified" and all of them.

## The next organ, named

**A constructor closure over the environment's own expressions.** Not a fixture library (that is a knowledge
house), not LLM-written arguments (that is the model we refuse), but: parse the argument expressions at a
call site, resolve each against the package's own constructors and constants, recurse to a bounded depth,
and accept only what executes and returns twice. Its refusals must be named — `NO_CONSTRUCTOR_FOR_EXPRESSION`,
`CONSTRUCTION_DEPTH_EXHAUSTED`, `CONSTRUCTED_BUT_NEVER_RETURNED` — and its measurement is the same one used
here: how many of the 40 remaining actions become executable, and how many of those the next release moves.

*Reproduce:* `.venv/bin/python canonical/swe_kernel/argument_construction_v1.py --json
canonical/verification/ARGUMENT_CONSTRUCTION_20261116_V1.json`
