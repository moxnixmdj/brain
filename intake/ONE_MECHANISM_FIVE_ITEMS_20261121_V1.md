# One mechanism, five items — 29/40 → 37/40

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · 54 tests pass

| | before | after this mechanism | whole cohort now |
|---|---|---|---|
| sympy | 23/32 | 29/32 | **30/32** |
| networkx | 5/8 | 6/8 | **7/8** |
| total | 28/40 | 35/40 | **37/40** |
| cohort time | 253 s | 222 s | **221 s** |

The middle column is what *this document's* one mechanism bought. The right-hand column is the
cohort as of the latest run and includes three later items solved by other means.

New: 181, 182, 185, 188, 194. **Faster as well as better** (196 s sympy, 26 s networkx).

---

## The five were one shape, not five cases

I had classified 185/194/188 as "the meaning→name convention, not run-time derivable". That was
wrong, and measuring the actual candidates is what showed it:

| item | reference | what the prose says | what the type declares |
|---|---|---|---|
| 185 | `K.to_int(a)` | "integer representation" | `to_int` **is** a member of `FiniteField` |
| 194 | `matrix.todok()` | "dictionary-of-keys" | `todok` **is** a member of `Matrix` |
| 188 | `poly.rep.to_list()` | "internal representation" | `to_list` **is** a member of `Poly.rep` |

Every one of those members is in the **declared type's own `dir()`**. Nothing was memorised. What
was missing was *rank*, not *reach*: presented in `dir()` order, `copy` and `hash` beat `todok`
for a question about a "dictionary-of-keys representation". The rank comes from the artifact's own
naming convention — a conversion is spelled `to_X` / `as_X` — plus how many of the member's words
the prose states. 194 solved at try **1**, 188 at try **1**, 185 at try **3**.

## And a genuine construction mechanism

181/182 are not computations over an existing object; they are *constructions*, and every part of
the answer is declared:

```
return annotation        -> PinJoint                      (the constructor)
prose, verbatim          -> parent.frame.x, -child.frame.x (the argument paths)
PinJoint's own dir()     -> parent_point, child_point      (the keyword members)
```

The pairing rule is the **shared stem**: a member whose name starts with the same parameter name
and ends with the stated label receives that parameter's stated path. `parent` + `_point` ->
`parent_point=parent.frame.x`; the leading `-` in the prose is carried through.

`PinJoint` is never written into the code — the type is read from the return annotation and its
members from a live `dir()`.

### The test that decides whether this is understanding or a lookup table

`test_pairs_on_the_shared_stem_not_on_a_member_table` runs the same mechanism with a **different**
label (`_axis`) over `parent.q.x` / `-child.q.x` and requires it to work with **no new code**.
A table would fail it. It passes.

Three negative tests also hold: no fire when the paths are not parameters, when there is no
declared constructor, or when the type declares no matching member. **A mechanism that cannot
decline to fire is a lookup table.**

## What actually moved the number

Two rules, both pure derivation, no stored facts:

1. **member calls ranked by stated evidence + the `to_`/`as_` convention** — 185, 194, 188;
2. **stated calls closed by shared stem** — 181, 182.

## The remaining 5

| item | cause | verdict |
|---|---|---|
| 203 | the benchmark's prose contradicts its own test ("distinct" vs multiplicity) | **not solvable** |
| 29 | `extrema_bounding` does not exist in networkx 3.6.1 | version artifact |
| 27 | "number of communities set at 5" — the keyword is `cutoff`; prose shares no word with it | genuine vocabulary gap |
| 180 | a `subs`/`replace` with a **lambda over variable arity** and a `Max*Min` body | grammar gap, real |
| 177 | needs `legacy_matrix=False` — a behavioural keyword, stated nowhere in the prose | vocabulary gap |

**Three of the remaining five are not failures of reasoning**: one is a broken benchmark, one is a
missing function, and two are prose that does not name what it means. Only 180 is a shape the
grammar genuinely cannot yet express.

**37/40 is 92.5% of a 40-item two-library no-dependency subset, not a benchmark score.**

> **Corrected 2026-11-21.** This document was written at 35/40. Three further items were closed
> afterwards and none of them by a new mechanism: **180** by ranking a constructor out of the head
> position (see `THE_CALLEE_DOCUMENTS_THE_WORD_20261121_V1.md`), **189** by a harness budget fix,
> and **27** by reading the keyword from the callee's own docstring. The mechanism described below
> still accounts for the same five items; the table above counts the whole cohort. The
published 51–59% figures are on all 328 items across 26 libraries. `truth.achieved` remains `false`.
