# The alias fix is worth eight items, and it was measured against itself first

**Date:** 2026-11-21
**Status:** isolated measurement. Supersedes the "not isolated" limitation in
`I_MEASURED_THE_BENCHMARK_IN_THE_WRONG_INTERPRETER_20261121_V1.md`.

## The trap I walked into

The first attempt to isolate the alias fix reported `+0`. It was wrong: both full runs wrote
their result to the same `/tmp/full_result.json`, so the "baseline" and the "fixed" comparison
were the same run compared with itself. The per-item verdicts survived in the run logs, which
is how the number below was recovered.

## The isolated measurement

Same interpreter (`/tmp/instv/bin/python`), same 193 items, same corpus, same seed. Only
`alias_map` / `bound_spelling` / `respell` / `qualified_spellings` and their wiring differ.

| | passes |
|---|---|
| alias fix REMOVED (`6814c7ae` sources) | **35/193** |
| alias fix PRESENT | **43/193** |

    delta = +8 items, 0 regressions

The eight, and they are exactly the eight the mechanism predicts:

| item | library | body |
|---|---|---|
| 71 | numpy | `np.round(arr)` |
| 72 | numpy | `np.prod(arr)` |
| 76 | numpy | `np.round_(arr)` |
| 77 | numpy | `np.product(arr)` |
| 198 | sympy | `sympy.isprime(n)` |
| 202 | sympy | `sympy.functions.combinatorial.numbers.partition(n)` |
| 205 | sympy | `sympy.totient(n)` |
| 206 | sympy | `sympy.mobius(n)` |

Every one is a **single call to a stated name, spelled through the stub's own binding**. No
item regressed: the change only ADDS alternative spellings, and the oracle stops at the first
pass, so a wrong alternative cannot displace a right one.

## Where this leaves the honest ledger

    OURS:              43/193 = 22.3%
    REFERENCE CEILING: 110/193 = 57.0%
    WE REACH:          39.1% of what the benchmark itself can certify

The 83 items the reference cannot pass split into **version drift** (scipy 12, torch 12 — torch's
reference cannot import at all, django 10) and genuinely environment-dependent tests. For those
items no mechanism can score, so 110 is the correct denominator for any claim about mechanism.

## scipy is not drift

Measured over the 22 scipy items whose reference solution passes: **all 22 have their truth
name in the installed corpus; 0 are absent.** The earlier "scipy is version drift" reading was
wrong. scipy's zero is grammar and ranking, and it is the largest tractable gap in the
benchmark (ceiling 22, we take 0).

## Not claimed

* `truth.achieved` remains **false**. Authority remains **NONE**.
* 22.3% is not a score on "the benchmark". It is the score on the 193 no-dependency items, in
  the environment as installed.
* +8 is one mechanism, the largest single measured gain so far, and it is still 19% of the
  remaining 110-item headroom.
