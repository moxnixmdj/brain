# The representation is the bottleneck, not the search

*Round 10. 2026-11-16. Branch `arena/e7c7b049-brain`, base `9e8b043a`.*

## What round 9 left, and what this round had to answer

Round 9 measured **0 of 6 real fix commits solved** and attributed every failure to the grammar: two needed a
composite edit, two were **shape changes** (`SUBTREE_REWRITE`) that the induced template basis cannot express,
two had no firing site. Zero search failures.

`induced_edit_basis_v1` already *names* those diffs and throws them away. So this round replaced the operator
list with **one general algorithm** — anti-unification — learned the rewrite space from real repository history,
and asked the next question down:

> Can a *learned, generalised* rewrite reproduce a real fix — and a sequence of two of them?

## First: two bugs in the corpus and the instrument, found before any number was believed

1. **Round 9's corpus was a truncation artifact.** Mining was capped at 40 commits per repository. Without the
   cap the same rule yields 195 candidates and **89 tasks** that pass the execution gate. Two of round 9's three
   "not expressible" verdicts were drawn from that truncated sample. The corpus manifest is now **committed**
   (`canonical/corpus/real_fix_commits_20261116_V1.json`), so the corpus is rebuildable by anyone — round 9's
   `/tmp` paths were not.
2. **Four instrument defects, each of which would have produced a false headline:** site paths were `id()`-based
   so `deepcopy` invalidated every one of them (**no rewrite could ever install** — 1,411 rules learned, zero
   trials); the AST↔term encoding emitted tuples where `ast` requires lists; candidates were validated with
   `ast.parse` instead of `compile`, which accepts field-shape misuse; and insert/delete was overriding the task
   state instead of being reported as a flag, hiding "no rule fired" behind a plausible excuse.

## The measurement

Grammar learned **only from other repositories' diffs** (leave-one-repository-out). Every candidate executed
against **the real test from the real commit**, original bytes restored in `finally`.

| | before the round-trip gate | after it |
|---|---|---|
| tasks measured (of 89 committed) | 9 | 5 |
| solved | **0** | **0** |
| executions | 352 | 179 |
| round 9's template grammar, same sample | 0 | 0 |
| **oracle** (the commit's own diff, learned as a rule) | **1 solves · 4 need >1 edit · 4 do not fire** | 1 needs >1 edit · **4 do not fire** |

The oracle column is the one that matters, and it is why the second row is smaller and worse-looking than the
first. The **round-trip invariant** — *a rule must reproduce the diff that taught it, exactly* — is now enforced
as an admission gate. Enforcing it did not improve the score; it exposed the truth:

> **4 of 5 diffs cannot be represented by statement-level anti-unification at all.** A pattern with computed
> holes is not faithful even to the pair it came from, so it can never fire at the site that produced it.

I am reporting the unfavourable number, not the favourable one.

## What is real, what is not

**Real**
- **Verification remains free and honest:** 531 executions across both runs, `$0`, no model, byte-exact restore,
  a real test from a real commit as the only judge. That half of the asymmetry is solved and stays solved.
- **The failure is now one level deeper than round 9 located it,** and the new location is *cheap*: the
  round-trip invariant is checkable without executing anything. A grammar that fails it is not a grammar, it is
  a rumour.
- Building the generaliser by anti-unification was still the right move: it turned "the operator list decides
  everything" into a measurable property of the *representation*, which is a real diagnosis rather than a
  preference.

**Not real**
- That shape rewrites, once *learned* rather than hand-written, would close the gap. They fire (8 of 9 tasks),
  they compose (up to two), they are gated by execution — and they solve nothing, because they cannot even
  reproduce their own teaching example.
- That more search, a bigger budget, or better sampling would help. Search was never the binding constraint in
  either round 9 or round 10.

## The single bottleneck, exact

**Faithful rewrite representation.** Not vocabulary, not ranking, not budget.

The fix is prescribed by the finding, and it is not incremental: **stop computing holes.** Take the real
subtree pair from the diff and **alpha-rename** it — rename identifiers and literals positionally, keep the
structure identical — so the rule fires at its own site **by construction** and round-trip is exact rather than
hoped for. Then compose two of them, and measure on the **same 89-task committed corpus** so the comparison is
exact.

The 2026 evidence agrees with the diagnosis and shows the cost of the alternative: BIGBAG (arXiv 2606.24446,
Jun 2026) reaches 78.6% with agent-written AST transformations, and of its 86 non-fixes **72 failed because the
matching pattern was incorrect / found no call sites** — the identical representation failure measured here, paid
for with a model.

## Where the series stands

| round | organ | result |
|---|---|---|
| 1 | experience → actions | cost law; `p_correct` 0.2978 |
| 2 | differential pins | 13 drivable, 0 pins |
| 3 | structure → laws | 188 laws, 0 kills |
| 4 | instruction → contract by occurrence | site missing |
| 5 | site by intervention | 1 of 40 usable |
| 6 | permanence on real releases | 31% move, all loud; 39% never learnable |
| 7 | arguments from the environment's proofs | 1 of 41 (2.4%): lookup is capped |
| 8 | observation by the environment's own execution | 28 of 38 (73.7%) reached; 22 move, both sides recorded |
| 9 | edit synthesis from history | 0 of 6; all failures in the grammar |
| 10 | **shape rewrites learned by anti-unification** | **0 of 9, then 0 of 5 after the round-trip gate — the representation cannot reproduce its own diffs** |

Ten rounds of one continuous movement: *what can be known* → *what can be seen* → *what can be changed*. The
first two are solved, exact, and free. The third now has: a free judge, a corpus anyone can rebuild, a named
invariant, and a measured statement of exactly what its representation must satisfy.

*Reproduce:* `python canonical/swe_kernel/structural_rewrite_induction_v1.py --limit 6 --json
canonical/verification/STRUCTURAL_REWRITE_INDUCTION_20261116_V1.json`
