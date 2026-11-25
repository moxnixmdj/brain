# The oracle was under-queried: 44% of wrong fixes pass the target test, and the repo catches half of them

**Date:** 2026-11-24. **Authority:** NONE (producer-run sandbox).
Tools: `canonical/tools/oracle_discriminating_power_v1.py`,
`canonical/tools/oracle_strengthening_v1.py`. Receipts: `/tmp/oracle_power.json`,
`/tmp/oracle_strengthening.json`.
**Nothing here is a solve attempt.** A surviving mutant is a *wrong* edit; it is counted, never
claimed as a repair.

---

## §1 The question

Every repair arm in this tree treats the failing test as a one-bit oracle: run it, it says pass or
fail. The corpus guarantees the test fails at `before` and passes at `after`. That proves the oracle
separates those two points. It does **not** prove the oracle separates `after` from the
*neighbourhood* of `after` — and that is the property a solver actually needs, because a solver
arrives at a *candidate*, not at the truth.

If the oracle is sharp, then a search that reaches the right neighbourhood is told it is right, and
the bottleneck is **reach**. If the oracle is blunt, search is futile in a specific way: many wrong
edits look identical to the right one, so the solver reaches the neighbourhood, ships a wrong patch,
and its own check says `PASS`.

That second case is not hypothetical. It is the one result this project has from a real board: on
SWE-bench Pro V2 the engine wrote 3 patches, called all 3 `PASS` itself, and the tasks' own verifiers
scored all 3 at **0.0**.

## §2 Measurement 1 — how many wrong fixes does the target test accept?

Method: check out the fix commit, write the real fix (`after`), confirm the failing tests pass, then
mutate **only the lines the upstream fix changed** (comparison swaps, boolean flips, `and`/`or`,
`is None`/`is not None`, numeric ±1) and re-run the same failing tests.

| | |
|---|---|
| tasks well-formed | 7 (of 10 tried; 3 admitted no mutant) |
| mutants of the real fix | 36 |
| **mutants that still pass the target test** | **16** |
| **survival rate** | **44.44%** |
| tasks where no mutant survived | 2 / 7 |

**Nearly half of the wrong edits in the fix's own neighbourhood are accepted by the failing test.**
So the oracle, as the harness queries it, cannot identify the fix among its neighbours. This is the
mechanism behind the 3/3 self-`PASS` → 0/3 verifier-`PASS` result, and it is measured rather than
asserted.

## §3 Measurement 2 — is the oracle weak, or just under-queried?

For each of the 16 survivors, run the **whole test file** the target node lives in, and compare its
failure set against the real fix's. A mutant is *rejected* if it introduces a failure the real fix
does not have.

| repo | sha | survivors | rejected by whole file | accepted |
|---|---|---|---|---|
| pypa/packaging | 46167dcdb1 | 7 | **7** | 0 |
| pypa/packaging | 491af5d517 | 1 | 0 | 1 |
| pypa/packaging | a03bde12d5 | 3 | 1 | 2 |
| pypa/packaging | cd91074b05 | 3 | 0 | 3 |
| pypa/packaging | 31b2d01319 | 2 | 1 | 1 |
| **total** | | **16** | **9** | **7** |

**9 of 16 = 56.25% of the mutants that beat the target test are caught by the whole test file.**

The discriminating power was already in the repository. The harness was asking for one bit when the
repo was offering several.

**Net effect on the accepted-wrong-edit rate:** 44.44% × (1 − 0.5625) = **19.4%**. Judging with the
whole test file instead of the single target node cuts wrong-edit acceptance by **2.3×**, at zero
model calls and zero new mechanisms — it is a change to *what the harness queries*, not to the engine.

## §4 What this does and does not establish

**Does establish.** Any future arm must judge with the whole test file (or suite), not the target
node. Otherwise ~44% of the patches it accepts will be wrong even when it reaches the neighbourhood —
and its internal verification will report `PASS`, which is the most expensive possible failure because
it looks like success.

**Does not establish.** That this raises the solve rate today. In this corpus the arms produce
**0** target-test passes (`path` 0/11, `local` 1/56, `guard` 0/27, `witness` 0/79), so reach is
still the binding constraint *here*, and sharpening the oracle cannot create a pass that does not
exist. The two walls are sequential: **reach first, then precision.** On SWE-bench Verified, where 25
tasks did reach a target-test pass, precision was already binding — 18 of those 25 still did not
resolve, 16 because the whole-module run was never taken (`WHERE_THE_SWE_BENCH_LOSS_IS_20261124_V1`).
This measurement supplies the mechanism for that loss.

**Limits, stated.** n is small: 7 tasks for measurement 1, 5 tasks / 16 mutants for measurement 2,
and **every task is `pypa/packaging`** — one repo family, one test style. The 44.44% and 56.25% are
real for this sample and not yet established as corpus-wide. Extending across `tomli` and
`itsdangerous` is the obvious next run; the scripts take `--limit`/`--offset` for exactly that.

## §5 Consequence for the plan

This **supersedes the ordering in `PASTED_PLAN_VERIFICATION_20261124_V1.md`**, which named "the
repair operator" as the single bottleneck. The sharper statement is:

1. **Reach** is the binding constraint in the oracle-given corpus (0 passes of any kind).
2. **Precision** is the next wall, and it is *already measurable*: 44% of wrong fixes pass the target
   test, and the repo catches 56% of those for free.
3. Therefore the repair operator must be built **with whole-file judging from the first line**, or
   its own success signal will be wrong ~44% of the time and every measurement after it will be
   contaminated.

That last point is the reason to record this *before* building the operator rather than after: an
operator tuned against a 44%-blind oracle would be tuned to the wrong signal, and the tuning would
look like progress.
