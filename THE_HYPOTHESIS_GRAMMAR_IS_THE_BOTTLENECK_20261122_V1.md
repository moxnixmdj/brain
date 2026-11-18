# The hypothesis grammar is the bottleneck

*`canonical/tools/the_space_is_the_artifact_v1.py` · `semantic_site` · 24 tests · receipt `canonical/verification/THE_HYPOTHESIS_GRAMMAR_IS_THE_BOTTLENECK_20261122_V1.json` · 30 real commits · 83.6 s · 0 parameters*

---

## The question this round had to answer

Last round ended with a number and a plan: *150,000 candidates offered per row, none admissible* — so the shortage is the **shape** of the hypothesis, and the next step was to admit shape. This round builds the measurement that says **which** shape, and it falsifies the answer I expected.

## The grammar of 30 real fixes, in the population's own words

Both revisions of each changed file go through `ast.unparse`, which deletes formatting, comments and continuation lines. What differs afterwards is what the program actually underwent. Each exclusion now carries that fact instead of the hunk's line count:

| AST fact about the fix | rows |
|---|---|
| **more than one change region** — the value is produced in one place and consumed in another, or a statement moved | **8** |
| more than one statement changed | 3 |
| the change inserts or deletes whole statements — a guard or a definition is added, nothing is replaced | 2 |
| the changed expression spans several lines and the patcher addresses one line | 1 |
| *addressed by the instrument* (`diff_hunk` 12 + `semantic_ast` 1) | 13 |

And of the 13 addressed: 1 verified, 5 searched-and-empty, 6 refused at the demand, 1 never ran. Accusations: **0**.

## The hypothesis I had to falsify

The census first looked like good news. Four of the fifteen rows excluded as `MULTI_LINE_EDIT` were, at the semantic level, one statement replaced — so "the instrument excludes real work because of formatting" was a plausible, attractive claim, and the fix would be to read the site from the ASTs.

That is now built (`semantic_site`), and the claim is **false on real material**:

- jinja `8931077058` and click `4fd2fea0db` **move a statement** — two real regions, no replacement anywhere (`MORE_THAN_ONE_CHANGE_REGION`);
- click `b7e5fd4cc7` changes a string literal **and** deletes a branch — two regions;
- jinja `b512058270` is genuinely one statement, and the patcher cannot address it because the expression spans four source lines.

So formatting reformatting is **not** what hides the population. Exactly **one** row was recovered (`jinja eec0db8642`, now searched and refused at its demand). Handling formatting is worth 1/30, not 4/30 — and I would have believed 4/30 if I had not executed the claim.

## What this means for the claim that one experience is enough

The instrument is the smallest complete thing that can turn one execution into a verified rule: it reads a demand from the artifact, enumerates a space, and lets the project's own tests decide. It verifies **1 of 30** real historical fixes, and the reasons are now mechanical rather than rhetorical:

- **13 of 30** are expressible as an expression at one addressable site — the instrument's whole hypothesis class. It converts 1 of them into a verified repair.
- **17 of 30** are not, and 8 of those are *compositions*: a value produced in one place, consumed in another. That is not a search problem, a speed problem, or a memory problem. It is a **grammar** problem: the hypothesis language has one production (`replace this expression`) and the fixes use four.

That is the same conclusion the 2026 literature reaches from the other direction: multi-hunk repair degrades with divergence and dispersion, and the hardest class is definition-or-setup followed by use [3](https://dl.acm.org/doi/full/10.1145/3660828) — exactly the "more than one change region" bucket here. No amount of replay, retention or instant learning changes a hypothesis language.

## What was nearly hidden — and is now impossible to repeat

The first run of this round reported **15 of 30 rows as `NO_FAILING_TEST`** — a claim about the commits. Nothing was wrong with the commits: a missing pytest plugin aborted collection, the harness produced no verdicts, and the tool reported silence as a fact. It now says `TESTS_DID_NOT_RUN` and carries the pytest tail. A harness failure must never be able to wear a fact's name; the same rule that killed the false `verified` row last round.

## Honest accounting

Declared acceptance: at least **1 verified repair whose human fix is multi-line**. **Not met — 0.** Accusations 0: met. No verified row preserving 0 passing values: met.

## Next step, with the acceptance stated before the build

The grammar has four productions and the instrument has one. The next build is the **absolute-offset patcher** plus the **composition production**: a hypothesis may produce a value at one site and consume it at another, with the suite as the only judge. Declared acceptance: **1 verified repair whose AST fact is `MORE_THAN_ONE_CHANGE_REGION`** — if that fails, the conclusion is that the remaining capability needs a different hypothesis language entirely, and it will be recorded as the falsification of the composition production rather than as another round of tuning.
