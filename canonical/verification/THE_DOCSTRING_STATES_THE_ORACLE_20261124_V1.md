# The docstring states the oracle: 1 of 45, and why it is still the right direction

**2026-11-24.** Tool: `canonical/tools/the_docstring_states_the_oracle_v1.py`.
Receipt: `canonical/verification/THE_DOCSTRING_STATES_THE_ORACLE_20261124_V1.json`.

## The distinction that matters

My Wall 1 experiment was null (0/19) because it **invented** metamorphic relations —
idempotence, round-trip, aliasing — and checked them against a *green suite*. The suite's
behaviour is already correct, so the relation fired on intentional mutation: 400
violations on click `d340b0c1`, 213 on attrs `a572c3a4`, identical at the fix.

This experiment does something different: it **harvests a relation a human already
wrote down in the source**, and checks whether reality agrees with it. The prose is the
specification; the code is the claim under test.

`packaging ba17fcea23`, shipped docstring of `is_normalized_name`:

> Check if a name is already normalized (i.e. `canonicalize_name` would
> roundtrip to the same value).

That sentence is a two-way implication. Encoded:

```
for x in valid_names:  is_normalized_name(x)  ==  (canonicalize_name(x) == x)
```

| tree | violations |
|---|---|
| `283811b` (parent) | **4** — `a--a`, `a--1`, `1--a`, `1--1` |
| `ba17fce` (fix) | **0** |

A clean fail-to-pass oracle, from a docstring, `model_calls = 0`, on the one row my
earlier originator ablation recorded as an *active regression* (`BROKE_PASSING`). The
row had no oracle at all before this.

## The rate, honestly: 1 of 45

| verdict | count |
|---|---|
| `DOCSTRING_ORACLE_DISCRIMINATES` | **1** |
| `NO_STATED_RELATION` | 32 |
| `RELATION_DOES_NOT_DISCRIMINATE` | 2 |
| `RELATION_UNRUNNABLE` | 10 |

**The 10 `UNRUNNABLE` are all false extractions, not missed opportunities.** Inspected
individually:

```
attrs         validator <-> meth        "meth" is a prose abbreviation
more-itertools notation <-> paper       a citation, not a claim
urllib3        url <-> less             "less" from 'less than'
werkzeug       get_content_type <-> mimetype
```

The adjacency heuristic takes the nearest identifier before a roundtrip phrase, and
prose contains identifiers. Of the 12 relations extracted corpus-wide, exactly **one**
was a real checkable claim.

## Why this is still the right direction, despite n=1

Because it is the only oracle source in this repository that is **neither invented nor
guessed**, and the reason it is rare is a property of the corpus, not of the mechanism:

- these 45 rows are *single-line* fixes, the smallest fixes in the corpus, and small
  fixes rarely restate a module invariant;
- the mechanism found the one row where the fix *was* a violation of a stated invariant
  — which is precisely the class of bug a docstring can catch.

A stated invariant is a specification that ships with the code. Where a project states
one, the oracle is free and exact. Where it does not, nothing here can manufacture it —
which is the same wall as everything else in this repo, now seen from a third angle.

## What I am recording as rejected

- **Loosening the prose matcher to lift the count.** Every loosening I tried raised the
  extraction count and lowered precision to zero (`notation <-> paper`). A relation that
  is not a claim is not an oracle. Precision-first, n=1, is the honest setting.
- **Treating the 10 `UNRUNNABLE` as a pipeline defect to fix.** They are not a defect;
  they are the matcher correctly reporting that it found words rather than a claim. The
  distinction is now visible in the verdicts, which is the point of having them.

## Corpus ledger

| | before | now |
|---|---|---|
| rows with a verified fail-to-pass oracle | 4 (issue prose) | **5** (+ docstring) |
| of the six-row unsolved target set, rows with an oracle | 2 | **3** (`77fa67aaf2`, `d05bd3858c`, `ba17fcea23`) |
| end-to-end solved | 20/41 | 20/41 — `ba17fcea23` has an oracle and still no generator |

`ba17fcea23`'s fix replaces a regex with `[a-z0-9]+(?:-[a-z0-9]+)*` — a
constant-refinement, the same class as `77fa67aaf2`, and the same wall. Two of the three
newly-oracled rows now stop at the same generator gap. That gap is the next thing.
