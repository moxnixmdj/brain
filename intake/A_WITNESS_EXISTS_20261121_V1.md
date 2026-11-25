# The witness exists. The refusal was instrumental.

Date 2026-11-21. Schema `BRAIN_A_NAME_GETS_ITS_VALUE_FROM_THE_RUN_V1`.
Receipts `intake/RECEIPT_A_NAME_FROM_THE_RUN_*_20261121_V1.json`,
`intake/RECEIPT_A_NAME_FROM_THE_RUN_ACROSS_REPOS_20261121_V2.json`.

## The claim this replaces

`every_call_site_v1` refused **65 of 127** packaging sites on a bare `Name` -- a name with
no value at parse time. The open question was whether that refusal was fundamental (a name
has no value until something runs) or instrumental (we could not observe the value).

It is instrumental. The value is there at runtime, and a suite that passes 26,852 tests is
already producing it. Nothing about Python prevents the observation. Five different ways of
trying to observe it produced a clean number while measuring nothing.

## Five instruments that failed, and what each one taught

| # | Instrument | What it reported | What was actually happening |
|---|---|---|---|
| 1 | `exec` each test file | 11 files ran, 0 completed | every `from x import y` breaks; not one test executed |
| 2 | run pytest under the current `sys.executable` | OK, 19 pairs | that interpreter had no pytest; exit 1, and import-time frames were counted as witnesses |
| 3 | `sys.settrace` around `subprocess.run([..., "-m", "pytest"])` | **hits: 0**, 26,852 passed | a trace cannot cross a process boundary |
| 4 | pytest without `src/` first on `PYTHONPATH` | 0 converted, clean | pytest imported the INSTALLED `packaging` from site-packages, so the tree under study never ran |
| 5 | `sitecustomize` | 0 witnessed, 26,852 passed | imported before pytest exists; pytest replaces the trace during collection |

The working instrument is a **pytest plugin** loaded with `-p`, which installs the trace from
`pytest_runtest_setup` and removes it at teardown. It runs in the same process as the tests.

## Two performance findings that are part of the design

Tracing every frame turned a 20 s suite into **>900 s**, twice. Two changes fixed it:

- the trace is on only while a test body runs, not during collection, and
- the frame filter is **name-first and cached per code object**. A path resolution per frame
  is the whole cost; the first check is one set-membership test.

Suite time with the witness on: **36.96 s** against a 19.20 s un-witnessed baseline.

## The bug that produced a wrong number

The first working run reported **23 of 59** conversions by matching the *identifier* the
caller wrote against the callee's parameter name. That is wrong: the caller says `raw` and
the callee calls it `value`. Only sites where both sides happened to choose the same word
were counted, so the number was an accident of naming.

Matching by **argument position** changed the answer in both directions, which is why it is
the only version reported:

- packaging went **23 -> 40** (name matching had missed 17 real ones),
- itsdangerous went **4 -> 0** (all four had been name coincidences).

A witness that agrees with itself is not a witness. The itsdangerous result is the evidence
that the positional rule refuses things it could have claimed.

## Result

`entered_and_single_typed` means the callee was entered during the suite and the argument
had exactly one type. `settled_by_a_value` additionally requires the value to be
JSON-encodable, i.e. usable as a prober token.

| repo | blocked sites | entered + single-typed | settled by a value |
|---|---|---|---|
| pypa/packaging 24.0 | 59 | 40 (67.8%) | **14 (23.7%)** |
| pallets/itsdangerous 2.1.2 | 10 | 0 | **0** |
| total | 69 | 40 | **14** |

## What that is worth in executability

Re-mining each tree with the witnessed literals available at each blocked position:

| repo | call sites | parse only | with witness |
|---|---|---|---|
| pypa/packaging | 112 | 22 (19.6%) | **36 (32.1%)**, +14 |
| pallets/itsdangerous | 12 | 2 (16.7%) | 2 (16.7%), +0 |

The gain equals the number of settled values, which is the only encouraging thing in the
table: the mechanism does not inflate.

## What must be said against this result

**A witness is a recording, not a derivation.** `_get_config_var(warn)` was witnessed as
`False` because the suite happened to pass `False`. That does not settle the parameter; it
records one caller. A generator that used this token would be checking its own probe against
a value copied from the test suite -- circular in exactly the way this project forbids. The
honest use is as a **typed seed that must then be falsified by a probe**, never as an oracle.

**The yield is corpus-dependent and thin.** 14 sites out of 69, concentrated in one
repository, and zero in the other. itsdangerous refused correctly: `coerce_str|ref` was seen
as both `bytes` and `str`, and `want_bytes|s` as both. A name with two types is not settled,
and the instrument refuses it rather than picking the commoner one.

**A witness adds no coverage.** An argument value observed during a passing suite is a value
the suite's own caller produced. It proves the callee tolerates it, nothing about inputs the
suite never made.

## Why this is still worth keeping

It closes a refusal that was recorded as fundamental and was not: the values exist, and the
instrument that reads them costs 17.8 s of suite time. It also removes three named failure
modes from the toolkit -- installed-package shadowing, cross-process tracing, and
name-identity matching -- each of which silently produced a plausible number first.

The remaining 55 of 69 blocked sites need something a witness cannot supply: a value from
someone who is not the test suite. That is the prober's job, and this receipt says nothing
about it.
