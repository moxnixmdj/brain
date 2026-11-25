# pytest knows the parameters; most failures have none

**Round.** `arena/3fc9b5f0-brain`, 2026-11-24. **Authority:** `NONE__PRODUCER_RUN_SANDBOX`.
Producer-run, no independent verifier. §6 is not met; no merge.

**Artifacts.** `canonical/swe_kernel/pytest_contrast_acquisition_v1.py`,
`canonical/swe_kernel/repo_native_component_mining_v1.py` (wired to the acquisition),
`canonical/verification/PYTEST_CONTRAST_ACQUISITION_20261124_V1.json`,
`canonical/tests/test_repo_native_component_mining_v1.py` (5 tests, OK).

## 0. Requirements and §2

Own model/weights/agent; zero runtime model calls; no memorized world facts in parameters; every
parameter calculated; external inspectable instant-knowledge store; one experience writes an
abstracted rule; research before building; first principles; remove parts; hardest real tests, no
leakage, no hand-solving, no borrowed outputs; one branch, one final merge only after §6. §2 stays:
forbidden = parameter fact lookup or runtime model dependency; allowed = external computed-with
store plus one-experience learning.

## 1. Research before the build

The previous round's 0/12 was blamed on contrast acquisition: `operand_invention_v1.failed_index`
reads only numeric pytest ids, and its static parametrize parser misses custom or indirect tables.
The project already had `contrastive_oracle_bootstrap_v1.py` for intervention pairs, so this build
does not invent contrast theory; it only replaces the lossy id parser with what pytest already
knows. Using `item.callspec.params` from a collection plugin is a documented pytest advanced API
[1](https://stackoverflow.com/questions/46766046/pytest-get-parametrize-values-during-setup-teardown-method)
and is already manipulated in `pytest_collection_modifyitems` [2](https://github.com/pytest-dev/pytest/issues/13217).
That is an input, not a claim that the approach will solve repair.

## 2. Minimal build

`pytest_contrast_acquisition_v1.py` runs `pytest --collect-only` with a tiny plugin that dumps
`item.callspec.params` for every node id. `contrast()` then splits values by **same test function**
and **same parameter key** into failing and passing examples. This removes two wrong behaviours:
parsing a rendered id back into a value, and mixing unrelated tests into the passing side.
`repo_native_component_mining_v1.py` now uses this acquired contrast for both the imported-module
control and the repository-mined treatment. Two implementation defects were found before the
recorded run: mining modules under `src/` named them `src.click`, and importing a worktree package
required `worktree/src` on `sys.path`, not only `worktree`.

## 3. Hard test

Fresh corpus: 12 one-source/one-test click commits unused by any earlier receipt. Result:
**0/12 verified**, 70.9 s, zero parameters/model calls/network calls. Gates FAIL (M1 false; M2–M5 true).

The acquisition itself worked: on a development probe it recovered six failing and eleven passing
sibling values from custom node ids that the old indexer could not read. On the fresh corpus:

- 9 of 12 rows had **zero** parametrized failing cases; their failing tests are plain functions, so
  pytest has no parameters to hand over.
- 3 rows had a parameter contrast (2/7, 1/2, 5/0 values), but no repository class attribute and no
  imported-module attribute separated the failing values from the passing siblings.
- 0 mined terms were admitted on any row; no guard was patched.

Rejected: parsing ids by hand (lossy and already falsified); treating unrelated parametrized tests as
passing examples (makes every predicate non-separating); adding more repository symbols before a
contrast exists (the previous round showed that supply without constraint buys zero).

## 4. Verdict and next bottleneck

Real: pytest collection exposes concrete parameters; the acquisition returns a usable contrast for
custom ids; the control/treatment harness is now fair and both arms refuse together. Failed:
pytest-parameter acquisition as a general contrast source — 9/12 failing tests have no parameters.
Unproven: runtime perturbation of captured frame values, dual-program splicing, live benchmark scores.

The next bottleneck is **a contrast source for non-parametrized failures**. The smartest minimal
route is to capture the live frame at the failing assertion (already implemented in
`the_name_is_a_hole_v1.py`), choose one concrete input value that the assertion reads, fork with
`zygote_worker_pool_v1`, perturb exactly that value in the child, and keep the pair only when the
goal judge changes. That is a manufactured contrast, not a hand-written test case. If no single
perturbation flips the judge, the row must be REFUSED__NO_CONTRAST rather than guessed.

## 5. Limits

Producer-run; one repository; 12 real commits; no independent verifier; no live SWE-bench Pro,
Terminal-Bench 4.0 or OSWorld 2.0 run. §6 remains unmet. No merge.
