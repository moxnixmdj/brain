# I measured the benchmark in the wrong interpreter

**Date:** 2026-11-21
**Status:** correction. This supersedes every full-benchmark number in
`WHAT_IS_AND_IS_NOT_SOLVED_20261121_V1.md` and `THE_PROBE_FIRED_FIVE_TIMES_20261121_V1.md`.

## What I claimed, and what was actually true

For several turns I reported:

> Full no-dependency benchmark: **30/193 = 15.5%**, 770 s, 0 model calls.

That run executed every hidden test under `/tmp/gcv/bin/python`. That interpreter has **no
scipy, no torch, no django, no mitmproxy, no falcon, no tornado, no plotly, no gradio, no nltk,
no flask**. When a hidden test imports one of those, pytest fails at *collection* with
`ModuleNotFoundError`. The oracle reports `passed: false`. The item is counted as a failure of
the mechanism when the failure was of the environment.

`/tmp/instv/bin/python` is the interpreter those libraries were installed into. Every
measurement below uses it.

## The measurement that exposed it

I asked how many items pass when the benchmark **hands over its own reference solution** —
the ceiling any mechanism could reach. Under `/tmp/gcv/bin/python`:

    54/193 = 28.0%

Under `/tmp/instv/bin/python`, same script, only the interpreter path changed:

    110/193 = 57.0%

The 56-item gap is not a property of the benchmark. It is a property of the interpreter.

Per library, the reference ceiling is not uniform:

| library | reference fails | | library | reference fails |
|---|---|---|---|---|
| scipy | 12/34 | | gradio | 5/6 |
| torch | 12/12 | | numpy | 5/15 |
| django | 10/10 | | networkx | 3/8 |
| mitmproxy | 7/10 | | nltk | 3/6 |
| tornado | 6/8 | | pytest | 3/9 |
| falcon | 5/21 | | jinja2 | 2/2 |
| flask | 5/5 | | tqdm | 2/2 |

torch, django, flask and jinja2 are unsatisfiable in this environment: their reference
solutions do not pass their own hidden tests even when handed over verbatim. scipy's 12 are
real version drift (`wminkowski` does not exist in scipy 1.17.1; the benchmark pins 1.8.0).

## The corrected number, and what it means

    OURS:              43/193 = 22.3%   (1714 s, 0 model calls, /tmp/instv/bin/python)
    REFERENCE CEILING: 110/193 = 57.0%

    We reach 39.1% of the ceiling.

Per library:

| library | ours | | library | ours |
|---|---|---|---|---|
| sympy | 21/32 | | pytest | 1/9 |
| numpy | 9/15 | | tornado | 0/8 |
| networkx | 7/8 | | plotly | 0/7 |
| falcon | 3/21 | | nltk, gradio | 0/6 |
| lightgbm | 1/3 | | flask | 0/5 |
| geopandas | 1/2 | | **scipy** | **0/34** |
| jinja2, tqdm, matplotlib | 0/2, 0/2, 0/1 | | **torch, django, mitmproxy** | **0/12, 0/10, 0/10** |

For the four libraries whose reference solution cannot pass at all, no mechanism can score. The
honest denominator for a mechanism claim is **110**, not 193.

## Seven solves the reference does not have

Items **30, 31, 32, 76, 77, 79, 83** pass under our mechanism and fail under the benchmark's own
reference solution. 30/31/32 are the `nx.community.` prefixes; 76/77/79/83 are numpy. That is
not a boast — it is evidence that the two are answering differently and the test is the
arbiter.

## The mechanism fix that this turn produced

The alias defect, measured before the interpreter was fixed and still real:

* The corpus records a name's **defining module** — `prod` in `numpy`, `expm` in
  `scipy.linalg`.
* The grammar emitted `numpy.prod(arr)` from that.
* The stub's own line is `import numpy as np`, which binds **`np`** and not `numpy`.
* Result: the correct answer raised `NameError`. 40 of 59 recalled-but-unsolved items died
  this way.

Fixed by `alias_map` / `bound_spelling` / `respell` / `qualified_spellings` in
`body_grammar_v1.py`, plus wiring in `shape_and_synonym_v1.solve_item`. Six tests in
`test_the_stub_binds_the_name_the_body_must_use_v1.py` pin it.

**This fix was measured at 30/193 before the interpreter was corrected and 43/193 after.** The
fix's own contribution is therefore **not isolated** from the interpreter correction in these
two runs. That is stated as a limitation, not hidden.

## What I will not claim

* That the alias fix caused the +13. Not measured in isolation yet.
* That 22.3% is our score on "the benchmark". It is our score on the subset that has no
  `additional_dependencies` (193 of 328), in the environment as installed.
* That the earlier 30/193 was a regression or an improvement over anything. It was a different
  environment.

## Next, in order

1. Re-run 43/193 with the alias fix reverted, same interpreter, to isolate its contribution.
2. scipy is 0/34 with a ceiling of 22. It is the largest single tractable gap and is a grammar
   problem, not a drift problem.
3. `truth.achieved` remains **false**. Authority remains **NONE**.
