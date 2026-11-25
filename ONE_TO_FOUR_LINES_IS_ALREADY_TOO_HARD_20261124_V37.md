# ONE TO FOUR LINES IS ALREADY TOO HARD

**Round V37 · 2026-11-24 · branch `arena/50c05c04-brain`**

---

## 1. The question this round asked

V36 ended with a distribution: 11 of 28 tasks need a function that exists nowhere in the file, 8 need 5–20
lines, **6 need at most 4 lines**. The operators substitute, extend or rebind what is already present, so they
are aimed at those 6.

The obvious move is to build another operator for the 11. The honest move, before adding anything, is to check
whether the family can even solve the 6 it is *supposed* to be able to reach. **It cannot. It solves 0 of 6.**

## 2. What the 6 actually are

| task | the real fix | size |
|---|---|---|
| `2aada00b` | regex quantifier `[^\s;)]*` → `[^\s;)]+` in `specifiers.py` | one character |
| `2602dd07` | regex `[^ \t]+` → `\S+` in `_tokenizer.py` | one character class |
| `8c37b047` | add a two-line guard raising `InvalidLicenseExpression` | two lines |
| `8efde605` | bind an `include_group` variable one line above its use | one line |
| `b1c439b0` | `cls.__dict__` → `Metadata.__dict__`, twice | two lines |
| `d17cfaf0` | add a three-line early return | three lines |

Every one is a **regex character change, an early-return guard, or an attribute rebinding at a site nothing
points to**. None is a substitution of an expression that already exists — which is the entire grammar the
operator family has. So the family is not merely underpowered here; it is aimed at a category of edit that
does not appear in the subset at all.

Result: **0 of 6 solved.** Candidates were produced on three of them (12 each, via `WRAP_EXCEPTION`) and every
candidate failed, because wrapping a statement in `try/except` is not the same edit as tightening a regex.

## 3. Three instrument defects found on the way

1. **`DID NOT RAISE` has two forms.** pytest writes `DID NOT RAISE <class 'X'>` for a bare expression and
   `Failed: DID NOT RAISE X` inside a `with` block. The parser matched only the first, so three of the six
   tasks reported no failure kind at all — silently, as usual.
2. **The parser returned `{}` and said nothing.** A kind of `None` was reported as *"no candidate available"*,
   which reads as a capability limit when it was a regex limit. That is the third time a silent empty result
   has been mistaken for a measurement.
3. **Python version drift.** `2602dd07` also touches a re-export block that only exists on 3.13/3.14. On 3.11
   the test passes before the source patch is even applied. The miner used the `FAILED` line rather than the
   requested node, which masked the drift. Recorded rather than fixed: the miner should compare the failing
   node against the node it asked for.

## 4. An error of mine, corrected in the same round

I classified 4 of the 11 "invents a function" tasks as easy because the invented name was a **dunder**
(`__getstate__`, `__replace__`, `__init__`). Reading the diffs killed that: `__getstate__` is 46 lines,
`__replace__` is 55 lines, and both are API redesigns.

**I was classifying by syntax instead of by difficulty.** That is the ninth comparator-of-convenience in this
project, and it is recorded as such rather than quietly dropped.

## 5. What the widened measurement now says

```
tasks mined from the repositories        28
localisation, top-1                      17   (27 within five, 0 blind)
solved by the operator family            0
of a subset whose fixes are ≤4 lines     0 of 6
```

Localisation is the one part that generalises. Generation does not, and not for want of search budget: the
attempts were made and lost.

## 6. What this changes about the next step

Building an operator for the 11 "invent a function" tasks would repeat the mistake V36 measured: adding
mechanism until a specific task falls, then reporting the fit. The evidence says the family is aimed at the
wrong category.

**The wall is that real fixes are edits of a kind no substitution grammar produces** — a quantifier flipped,
a guard inserted above a computation, a name rebound at a call site that no failure text points to. Until an
operator can express *"insert this predicate before this value is computed"*, more operators of the current
shape will keep solving zero of the tasks they are aimed at.

**Nothing here is a benchmark result. No SWE-bench, Terminal-Bench or OSWorld task has been attempted, and no
benchmark row exists or is claimed.**
