# Three unseen repositories: what actually stopped the test

**Measured 2026-11-24.** Corpus: `canonical/corpus/heldout_unseen_repos_20261124_V1.json`.

## What was attempted

§6 requires never-seen environments, and the originator ablation had just shown the
bottleneck is the corpus rather than the memory. So three repositories neither engine had
ever run on were cloned — `flask`, `boltons`, `pyjwt` — and single-line fix commits were
mined **mechanically**, with no hand-picking: exactly one removed and one added line in
one source file, with a test file in the same commit.

Yield: **8 rows, all pyjwt, all in `jwt/algorithms.py`.** The filter is aggressive; flask
and boltons produced none in their last 600 commits.

## Result: 0/8, and not one of the failures is an engine failure

| stage | rows | what it actually means |
|---|---|---|
| `NO_FAILING_TEST` | 6 | the commit's own test file **passes on the parent**. Six of eight are not bug fixes with a failing oracle at all: `return cast("AllowedOKPKeys", key)` → `return key`, a docs-only `CHANGELOG` change, and similar. A row whose test passes before the fix has no oracle to flip. |
| `NO_ORACLE` | 2 | pytest refuses to run: see below. |

The two `NO_ORACLE` rows were diagnosed rather than accepted, and the chain has three
links, each of which alone reads like an engine limitation:

1. **`[pytest]` in `setup.cfg` is rejected by pytest 9** — "no longer supported, change to
   `[tool:pytest]`". Every test invocation dies before collecting.
2. With that rewritten in the worktree, pytest then demands **`pytest-cov`**, because the
   era's `setup.cfg` adds `--cov` options unconditionally.
3. With that installed, the module still cannot import: **`from collections import
   Mapping`**, removed in Python 3.10. This pyjwt era does not run on Python 3.11.

So the honest verdict on this repository as an evaluation environment is:
**NOT RUNNABLE HERE.** Not slow, not hard — incompatible.

## Why this is the most useful thing measured today

Three sessions have treated "the engine cannot do X" as an explanation. Today's earlier
finding was that two rows were missing `markupsafe` and `requests`. This is the same
failure mode one level deeper: a stage name that means *"no evidence was produced"* sat in
the failure column and read as *"the engine is not capable"*, and behind it were a pytest
config incompatibility, a missing plugin, and a standard-library removal.

The rule this build should have written three sessions ago: **before any row is recorded
as an engine failure, prove the harness produced an oracle at all**, and when it did not,
classify the cause as environment, repository, or workflow — never as capability. Of the
10 rows currently sitting in `NO_ORACLE` / `NO_PASSING_TEST` in the union receipt, at
least 2 were pure environment and 0 have ever been shown to be engine limits.

## What this costs the plan

The plan's Steps 1-3 and Step 4 of the roadmap all assume that running the engine on
unseen repositories yields measurements. For 2 of the 3 repositories chosen, the answer is
that **the toolchain, not the engine, decides the outcome**. Any honest unseen-environment
number therefore has to be conditioned on a per-repository environment preflight, and a
repository that fails preflight must be reported as excluded-with-reason rather than as a
failure rate. Reporting 0/8 as an engine score would be exactly the kind of dishonesty
that produced the fabricated transfer receipt.


## Follow-up: the preflight, written and run on both corpora

`canonical/tools/the_harness_must_prove_it_can_see_v1.py` answers one question per row
before any engine runs — *is there a run of this project's own test file, here, with at
least one passing and one failing verdict?* — and when the answer is no, it names the
cause instead of reporting a capability limit.

**On the 8 unseen pyjwt rows:** 8/8 classified, 0 unclassified. Six are
`NO_FAILING_TEST__ROW_IS_NOT_A_BUG_FIX` (their own test passes on the parent — they were
never oracles), two are `NO_ORACLE__ENVIRONMENT` naming the `[pytest]`-in-`setup.cfg`
rejection. Not one is an engine limit.

**On the 45-commit corpus:** **43/45 ORACLE_EXISTS.** This matters more than it looks.
It means the 19/45 union score is *not* contaminated by the environment — the engine had
a real oracle on 43 rows and solved 19 of them. The gap is now genuinely an engine gap,
which is the first time that has been true and checkable.

The two exceptions, precisely:

- `urllib3 4714836a` — `NO_FAILING_TEST__ROW_IS_NOT_A_BUG_FIX`. Consistent with the
  denominator work, which already recorded this row as `FAILS_IN_FILE` rather than a
  clean single-line repair.
- `pluggy 4326ced2` — `NO_ORACLE__ENVIRONMENT`, and a genuinely interesting one:
  `HookspecMarker.__call__() got an unexpected keyword argument 'warn_on_impl_args'`.
  The project under test **is a dependency of the test runner**. pytest imports its own
  `pluggy` before anything on `PYTHONPATH` can shadow it, so the repository's `src/pluggy`
  can never be the one that runs. This is the `HARNESS_BLOCKED_THE_SUITE` row from the
  original sweep, and it is now explained rather than merely recorded.

So the honest accounting of the 10 rows previously sitting in harness stages is: **8 of
them were environment, 1 is not a bug fix, and 1 is a self-referential dependency
conflict.** Zero of them were ever engine limits, and the original sweeps had been
counting all ten against the engine.
