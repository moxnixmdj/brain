# The site is not where the fix comes from

*2026-11-18 · measurement: `canonical/verification/THE_SITE_IS_NOT_WHERE_THE_FIX_COMES_FROM_20261118_V1.json`
· answer in full: `THE_SITE_IS_NOT_WHERE_THE_FIX_COMES_FROM_20261118_V1.md` (repository root)
· population: 241 real single-line edits and 29 real fix commits in `requests`, `click`, `tqdm`, `httpx`*

## What was measured, and on what

Three measurements on real commit history — no QuixBugs, no synthetic corpus, no model, no network at run
time — plus the first end-to-end identification run whose oracle is a project's own post-fix tests.

| measurement | population | result |
|---|---|---|
| writability | 241 real single-line edits | 153 single in-vocabulary expressions (77.4% of the 208 code edits), 22 need a form (9.1%), 18 are statements (7.5%) |
| geometry | 136 real single-expression edits | 115 **replace** the site (84.6%), 17 widen it (12.5%), 4 narrow it (2.9%) |
| reachability | the same 136, site-rooted pool, 400 candidates | 8 contain the fix (5.9%): 50% of narrowings, 23.5% of widenings, **1.7% of replacements**; median rank 22 |

End-to-end on `click@1b0e19f505`: the parent checkout plus the post-fix test file fails
`test_missing_envvar` with `Error: Missing option '--foo' (env var: 'None').`; the human fix
`self.show_envvar and self.envvar is not None` sits at **rank 1** of the site-rooted pool because
`self.envvar` is printed one line below the guard; all 119 tests leave **2 survivors**, the human fix
among them, and the suite cannot separate `and X` from `and X is not None` because no test asks about an
empty-string envvar.

## The bottleneck

> **Candidate material is chosen from the source text. The evidence that chooses it lives in the failing
> run's values.**

Grammar (9.1%), statement form (7.5%) and pool size (median rank 22 once writable) are each smaller and
each already measured. The 84.6% of fixes that replace the site have no material source at all under a
text-indexed pool, and the failing run is the only thing in the loop that nominates it.

## The build this implies

Invert the search: instrument the failing case, record the value the site produced and the value the test
demanded, nominate material by provenance of that value, then synthesise backward from the demanded value
— one hole, sized by the value's type, not by the site's text. Keep the project's own tests as the
oracle; spend the budget on ordering, which is where the cost is (`candidates × suite latency`, ≈0.4 s per
candidate on a 119-test file).

**Falsifier, stated before the build.** On the same 136 edits, value-provenance material must put the human
fix in the pool for more than 5.9% of them and within the first 40 candidates for more than 6 edits. If it
does not beat proximity, this thesis is wrong and the next round records that.

## The end-to-end sweep, all 29 commits

| stage | commits |
|---|---:|
| `NO_ORACLE`: the post-fix tests pass on the parent | 10 |
| `MEASURED`: a real oracle, the pool ran | 7 |
| `FIX_LINE_DOES_NOT_PARSE`: a fragment or a continuation | 7 |
| `FIX_IS_NOT_A_SINGLE_EXPRESSION`: structural or multi-site | 5 |

One of the seven with a real oracle is identified (`click@1b0e19f505`, rank 1); one more has its fix in the
400-candidate pool at rank 396, outside the budget actually executed; the other five are not in the pool at
all and every one is a replacement.

## What is not claimed

The sweep's rate is a producer-run sandbox result and independent reproduction is open. Rows where the
post-fix tests pass on the parent are reported as `NO_ORACLE`, never as successes. 62 of the 241 edits are
code that spans lines and are excluded from the geometry denominator rather than reclassified.
