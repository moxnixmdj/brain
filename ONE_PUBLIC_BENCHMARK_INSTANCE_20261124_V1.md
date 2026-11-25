# One public benchmark instance, run without a gold patch

**Date:** 2026-11-24. **Status:** FAIL, 0/1. **No merge.**

## What was run

SWE-bench Lite instance `pytest-dev__pytest-8906` was reconstructed from public instance metadata mirrored on GitHub. The gold `patch` field was **never read**. Only `repo`, `base_commit`, `test_patch`, and `FAIL_TO_PASS` were used. The generated local repository has two commits: an environment-setup commit with the setuptools-generated `_pytest/_version.py` stub, and a commit applying the official test patch. Third-party pytest plugins were disabled; the repo's own `pytester` plugin was enabled.

The parent code with the official test patch produced **two** failing tests, including the official `testing/test_skipping.py::test_module_level_skip_error`. So the oracle is real, not self-solved.

## Results

| system arm | result |
|---|---|
| repo-native component mining (imported-module control) | 0/1 verified |
| repo-native component mining (mined-treatment) | 0/1 verified |
| strict manufactured contrast (input literal, same execution path, truthiness preserved) | 0/1 pairs, 0/1 verified |
| model calls / network calls during solve / stored parameters / gold patch reads | 0 / 0 / 0 / 0 |

## What this does and does not license

It licenses the statement: **on one runnable public benchmark instance, our parameter-free system did not repair the bug.** It does *not* license a benchmark score, a comparison to any frontier model, or an extrapolation to all 300/500 Lite instances. The instance was chosen because its dependencies could be made to run in this sandbox, which is selection by environment readiness; full `PASS_TO_PASS` replay (5,752 tests) was not performed because this Python environment produced one unrelated failure on the old pytest tree. A second instance (`psf__requests-863`) could not be executed: its vendored urllib3 imports `MutableMapping` from `collections`, which Python 3.11 removed. It is recorded as an environment failure, not as a system result.

This is the first ungated public-task run, not a completion of §6. GUI/browser tasks, unseen-environment transfer, and a full public benchmark remain unmet.

Receipt: `canonical/verification/PUBLIC_BENCHMARK_PROBE_20261124_V1.json`.
