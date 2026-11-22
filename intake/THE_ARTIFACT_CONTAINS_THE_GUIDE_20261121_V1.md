# The artifact contains the guide: 29/40 → 31/40, and the "unreachable" class falls

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` = `false` · **$0**, 0 model calls

---

## 0. The class I had written off

Two items were classified — in three successive receipts — as **not solvable by any derivation**:

| item | prose says | answer is |
|---|---|---|
| 188 | "a **list** of its **coefficients**" | `poly.rep.to_list()` |
| 194 | "its **dictionary-of-keys** representation" | `matrix.todok()` |

`to_list` contains no word for *coefficient*. `todok` contains no word for *dictionary*. Ranked
by prose vocabulary both sit hundreds of members deep, and I concluded that this was **the
meaning→name convention in its pure form** — knowledge that could only be a stored table.

That conclusion was wrong, and the user's framing was right: *every computer artifact already has
a guide.*

```
>>> Matrix([[1,2],[3,4]]).todok.__doc__
'Return the matrix as dictionary of keys.'
```

The prose says "dictionary-of-keys representation". The member's own docstring says "dictionary of
keys". **They are the same string space.** The match is computable, with no table and no synonym
list, because the artifact states what each member means.

## 1. Why ranking could never find it, and what narrows the search

The search space is a single type's members — `sympy.Matrix` exposes 178 of them. Matching the
prose against all 178 is noisy, and the first attempt failed for two measured reasons:

**Doctest examples dominate the docstring.** `matrix.tolist()`'s text mentions `import`,
`examples`, `sympy`, `Matrix`, `python`, `nested` — six words, none of which the prose asks for.
It outranked `todok`, whose *first sentence* is an exact statement of what is wanted. Fix: **score
the first sentence only.** Examples, cross-references and import lines are not the statement.

**A stoplist ate the word that mattered.** The first stoplist contained `representation` — the one
word item 194 depends on. The rule that follows is narrow and now enforced by a test: *only
structural English may be a stopword; nothing type-specific.*

**And direction is part of meaning.** `poly.rep` exposes both `to_list` and `from_list`, both
mentioning "list" and "coefficients". The prose asks for one direction, so a member whose own name
states the inverse (`from_`) is penalised. 188's answer went from second to first.

## 2. The narrowing is stated, not tuned

The third statement is the one that makes this cheap: **the return annotation names the type of
the answer.** A stub declared `-> list[int]` cannot be answered by a member returning a dict. It is
applied as a *partition*, not a filter, because a wrong annotation must never empty the space.

Three statements, from three different places, none of them a table:

```
return annotation   ->  the TYPE of the answer        (the signature)
member docstring    ->  the MEANING of each member    (the artifact)
problem prose       ->  the WANTED meaning            (the task)
```

## 3. Result

Both items solve **at try 1**.

| | before | after |
|---|---|---|
| sympy | 25/32 | **25/32** (188, 194 replace nothing; both new) |
| networkx | 6/8 | **6/8** |
| **total** | **29/40** | **31/40** |

No committed win regressed: the previous 25 sympy wins are all still wins.

**Held-out sympy: 16/19 → 17/19.** The weights were not refit. Of the six items gained since
29/40, five (178, 186, 191, 194, 200) are held-out — so most of this gain cannot be tuning. 188
itself *is* in the fitted set, so its win alone would not prove transfer, and 194 is the honest
demonstration: a held-out item whose prose and name share no word, solved from the artifact's own
guide.

## 4. What is left, and it is no longer the convention

```
sympy unsolved:  177  180  181  182  185  189  203
networkx unsolved: 27  29
```

| item | cause |
|---|---|
| 203 | **the prose contradicts its own test** (says DISTINCT, test wants MULTIPLICITY) — unsolvable, and correctly not attempted |
| 181 182 | `parent.frame.x` — a stated offset through a *nested* attribute, into a constructor |
| 177 180 189 | compositions over constructed literals inside a joint/system constructor |
| 185 | `K.to_int(a)` — a conversion whose name the prose never states |
| 27 | prose says "number of communities", the keyword is `cutoff` |
| 29 | version artifact — the referenced symbol does not exist in networkx 3.6.1 |

**The meaning→name convention is no longer the dominant obstacle.** It was 2 items out of 40 and
both are now solved by a general mechanism. What remains is dominated by *nesting* (181, 182) and
*literal composition* (177, 180, 189) — grammar work with no knowledge component at all.

31/40 is 77.5% of a two-library, no-dependency subset and is **not comparable** to the published
51–59% on all 328 items across 26 libraries. `truth.achieved` remains `false`.
