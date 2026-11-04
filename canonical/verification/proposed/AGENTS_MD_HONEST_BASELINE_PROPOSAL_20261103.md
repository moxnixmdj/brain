# Rules for agents working in this repository

These rules are enforced by `execution_guard/repo_integrity_guard_v1.py` (run by the referee
workflow on every pull request — always the version on `main` — and inside the test suite). They exist because a previous session made the
test suite green by feeding tests historical copies of files, and declared the project's
terminal goal achieved by editing numbers. Read
`canonical/governance/REPO_INTEGRITY_POLICY_V1.json` for the full policy.

## Hard rules (the guard fails your PR if you break them)

1. **Tests run against the tree as it is.** No `conftest.py` that patches `pathlib`,
   `builtins.open`, the import loader, `urllib`, `http.client` or `subprocess`; no pin
   ledgers; no `git cat-file`/`git show` in test infrastructure; no `sudo`/`pip`/`apt`
   from tests; no fake `docker`/`sqlite3`/`cadquery`. If a test fails, the test or the
   code is wrong — fix one of them in the open, or delete the test with a reason.
2. **Terminal truth is not editable data.** `truth.achieved` stays `false` until the
   owner edits the guard's countersign constant in person. Mirrors (pointer, scoreboard,
   ownership files, manifest, hierarchy projection) must equal what the authority derives.
3. **A family flips to PASS only with new evidence** that resolves to real files, at most
   two families per PR, at most +4 atomic predicates per PR. Fail-closed records
   (`acceptance_calibration`, `current_machine_verdict`, blockers, quarantines, ledgers)
   may change value but may never be deleted or emptied.
4. **Verification means someone else ran it.** A document that says `independent_verified`
   or `INDEPENDENT_PASS` must name a verifier different from the producer and carry a run
   reference. A VERIFY that repeats its RECEIPT's hash is not verification. A "proof" with
   no numeric measurement is not a proof. At most 40 new receipt files per PR.
5. **No self-promotion.** No capability may register itself; at most 3 new capabilities
   per PR; no `singularity`/`omega`/`ultimate`/`sovereign` naming.
6. **No tautologies, no weakening floods.** `assertIn(x, {.., x})`, `assert True`,
   swallowed assertions, and more than 10 exact→loose assertion changes per PR fail.
7. **Nothing merges over a red referee.** Every pull request is judged by the referee
   workflow *as it exists on `main`* (`pull_request_target`); your copy of the referee is never
   run. The verdict is a check signed by the Brain Referee app and required by the branch
   ruleset with an empty bypass list. `gh pr merge --auto` is fine — GitHub completes it only
   when that check is green. No plain `gh pr merge`, no `--admin`, no force-push to `main`,
   no `git push … main`, no workflow that touches the `referee` environment, the referee app
   secrets or the check-run API, no new `pull_request_target` workflow. Carriers that need to
   land results on `main` call `.github/scripts/land_on_main.sh`.
8. **Protected paths** (the guard, its test, the referee workflow, `frontier-state-consistency.yml`,
   `CODEOWNERS`, the policy, this file, the honest-baseline tool and document, the landing
   script) fail the referee when changed; only the owner, by relaxing the ruleset in the web
   UI for that one merge, can land such a change. Say in the PR why it is needed and stop.

## If you believe a rule is wrong

Say so in the PR description and stop. Do not work around it. The owner changes the guard;
agents do not.

## Honest status reporting

Report the real test count, including failures. "All green" produced by any mechanism in
rule 1 is a defect, not a result.

The honest state of the suite is re-measured, never carried forward. The current measurement is
**`canonical/verification/HONEST_SUITE_BASELINE_20261103_V1.json`** (2026-11-03, `407cc3c`):
**16,361 cases — 15,255 passed, 984 failed, 42 error, 80 skipped; 344 of 2,279 files with
failures**. It supersedes the 2026-10-14 (11,525 cases / 344 failed) and 2026-10-17 (11,754 /
380) documents, which described a suite a third smaller.

**Those numbers are not all the same kind of thing, and the difference decides what to work on.**
`canonical/verification/SUITE_BACKLOG_SPLIT_20261103_V1.json` splits them: **48 are environment
failures** (a missing module or network — the machine, not the tree), **642 are regressions**
against the 2026-10-17 baseline (the file was clean then), and **336 are standing debt**. See
`P2_HONEST_SUITE_MEASURED_20261103_V1.md`.

Three rules that follow, and supersede "those failures are the real backlog":

1. **Before believing a red, check the machine.** Run
   `python3 scripts/restore_substrate_v1.py --check`. Measured 2026-11-03: it reported **1 of 10**
   declared modules present, and an uninstalled `cv2` prints the same `F` as a broken invariant.
   A missing-module failure is not a backlog item; it is `pip install` (the split document names
   the package for each absence).
2. **Fix runtime code, or correct governance documents in the open. Never touch the harness.**
   Unchanged, and it is why rule 1 matters rather than being a loophole.
3. **Report the whole table, and say how it was taken.** A single-session run emits no junit at
   all when one test hangs (measured: killed at 8%, nothing written), so 2026-11-03 used a
   per-file sweep — which cannot share cross-file fixtures and therefore biases toward *more*
   failures. Numbers from a sweep and from one session are not interchangeable; say which you used.

Re-measure with `python3 execution_guard/honest_suite_baseline_v1.py --junit <pytest junit xml> ...`
and report the new numbers; do not edit the baseline document by hand. Measurement documents carry
no authority — they are sandbox observations, not receipts.
