# Is the fix even in the pool?

*2026-11-18 · measurement: `canonical/verification/IS_THE_FIX_EVEN_IN_THE_POOL_20261118_V1.json`
· tool: `canonical/tools/is_the_fix_even_in_the_pool_v1.py` · corpus: QuixBugs @ `4257f44b`*

## The erratum first, because it is the point

Yesterday's receipt (`THE_FAILURE_ALREADY_SAYS_WHAT_TO_WRITE`, merged) said of three published bugs:

> "the failing case is not fixed by any expression the site's own material can build, so the fix is not
> one expression at one site"

**That sentence is false.** The corpus says so plainly:

| bug | the buggy site | the published fix |
|---|---|---|
| `lis` | `longest = length + 1` | `longest = max(longest, length + 1)` |
| `next_permutation` | `if perm[j] < perm[i]:` | `if perm[i] < perm[j]:` |
| `possible_change` | `if total < 0:` | `if total < 0 or not coins:` |

Every one is **one expression at one site**, over names and operators that are already there —
`longest`, `length`, `max`, `perm`, `i`, `j`, `coins`, `not`, `or`. Nothing had to be invented. The
vocabulary was never the wall.

## What the wall actually was: two defects in my own enumerator

1. **Material was admitted by text length.** The pool took a term only if `len(text) <= 3`, so `0`, `1`,
   `[]`, `arr`, `i` were material and `length`, `longest`, `coins`, `perm` were not. A local with a
   longer name could be *offered* as a candidate and could never be *combined* into one. Every fix above
   needs such a name combined.
2. **The pool was not cumulative.** Each level's output *replaced* the material, so an atom could never
   be combined with a composite — which is the exact shape of all three fixes (`max(longest, X)`,
   `not coins` inside `or`, a swapped comparison).

Both are repaired in `force_the_value_and_see_v1.py` (material is now atoms by AST size; the pool is
cumulative and bounded; the failing case is tested first; candidates are offered smallest-first).

## What is now true, and what is still not known

With both defects repaired and **6,000 candidates offered per site** (about 1 second each — offering is
cheap, so this is not a cost excuse):

- `lis` — the published fix is **not offered**
- `next_permutation` — **not offered**
- `possible_change` — **not offered**

So the honest verdict is **UNRESOLVED**, not *impossible*. And the arithmetic says why no budget will
fix it:

```
atoms at a site              20–40
forms per pair of terms      ~45
level-2 candidates alone     160 × 160 × 45  =  1,152,000
the three fixes live at      size 5–6  (atom × composite, or composite × composite)
offered here                 6,000 per site  =  0.5% of level 2
```

Blind enumeration cannot reach an expression of size 6. Raising the budget cannot change that: the
size-6 space is larger than the number of runs the corpus can afford by many orders of magnitude.
**The search needs a goal, not more room.**

## The rule this establishes (and it applies to every future claim in this tree)

> **An insufficiency claim is a claim about the world. A failure to find something is a claim about my
> code. Before anything here may say "the site cannot build it", it must show a completeness witness:
> the published fix, fed to the same enumerator, appears among what the enumerator offers.**

This is the same discipline the tree already applies to judges (never trust an uncalibrated judge) and to
measurements (never report a hang as a cost). It now applies to *negative results about expressibility*,
which are the easiest place in this whole project to fool yourself: a defect in a generator looks
exactly like a law of nature.

## What this does to the answer about instant learning

Nothing in the last three receipts is retracted that was measured: a stored experience transfers at
1.92% precision on the pair that fires; addressability saturates at ~60%; one demonstration buys at most
`log2|Y|` bits. What changes is the **reason** the coding wall holds, and therefore what to build:

- not "the vocabulary is insufficient" (the vocabulary was there),
- not "the search is too slow" (6,000 candidates cost a second),
- but **the search has no goal.** Nothing in this tree derives *what value the site must produce*. The
  failing case supplies an expected output at the boundary; nothing propagates that demand backwards to
  the site whose value is wrong.

That is the single bottleneck, stated in the form that can be attacked:

> **Derive the demanded value — the specification of the site, not a sample of its behaviour — from the
> failing case, and the expression follows from a search that already costs a second.**

And the corollary for "experience once and own it": an experience that records an expression records a
*point* in a space of size 10⁹; an experience that records a *demanded value* records a *constraint*, and
constraints compose. The former is why memory saturates at ~1%; the latter is the only form of experience
that can be permanent, because a specification does not decay when the program changes under it.

## What was shipped

- `force_the_value_and_see_v1.py` — the two enumerator defects repaired (a long-named local is now
  material; the pool is cumulative), the failing case tested first, candidates offered smallest-first.
- `is_the_fix_even_in_the_pool_v1.py` — the completeness witness, so that no future "not expressible"
  verdict can be published without it.
- Tests: a long-named local must be combinable; the pool must survive across levels; the witness must
  say *found* when the fix is in the pool and *unresolved* when it is not.

## What happened when the defects were fixed

The repairs above were not the end of it. Fixing them exposed **three more** defects of the same family,
each one sufficient on its own to make a reachable fix unreachable:

| # | defect | what it made unwritable |
|---|--------|-------------------------|
| 3 | `_size` counted AST *context* nodes (`Load`/`Store`), so `arr` measured 2 and only constants measured 1 | every name, and therefore every composition over a name |
| 4 | the site's own sub-expressions were not admitted as material | `perm[i] < perm[j]` — the site's two operands, swapped |
| 5 | the site's own expression was excluded from its own pool | `max(longest, length + 1)` — an atom wrapped around the site |

With all five repaired, the three "inexpressible" bugs were re-run against the same corpus
(`--quixbugs /tmp/QuixBugs`, deadline 200 s/task, verify timeout 45 s):

| bug | result | expression found | is it a fix? |
|-----|--------|------------------|--------------|
| `lis` | solved, 5,368 questions, 2.2 s | `max(length + 1, longest)` | **yes** — the published fix, commuted |
| `mergesort` | solved, 385 questions, 0.9 s | `(len(arr)) <= (1)` | **yes** — the published fix |
| `get_factors` | solved, 1,860 questions, 0.8 s | `(1) + (n)` | yes |
| `kth` | solved, 34 questions, 0.3 s | `max(arr)` | yes |
| `next_permutation` | solved, 7,429 questions, 2.2 s | `(perm[j]) // (j)` | **no** — see below |
| `possible_change` | child timed out | — | unanswered |

So the retraction is stronger than the erratum first stated: **two of the three bugs this tree called
inexpressible are repaired by the published fixes themselves, in about two seconds each.** The claim was
never about the language. It was about five lines of my own code.

### The false positive, stated plainly

`next_permutation` was "solved" by `(perm[j]) // (j)`, which replaces a `<` comparison with a floor
division. It passes every published test. Run against the corpus's own `correct_python_programs`
reference on 2,000 random permutations, it **disagrees 361 times** (e.g. `[3,7,8,4,1,2]` → found
`[3,4,2,1,7,8]`, correct `[3,7,8,4,2,1]`).

The lesson is not "the corpus is bad" — it is that **solved-by-the-corpus is a weaker predicate than
correct**, and this tree's headline numbers have been counting the weaker one. The measurement to report
is: *corpus-accepted* (5 of 6) and *correct on inputs the corpus never saw* (4 of 6). Both, always.

`possible_change` remains **unanswered**, not impossible: its child process exceeded 240 s. A hang is not
a proof and it is not a cost measurement either.

