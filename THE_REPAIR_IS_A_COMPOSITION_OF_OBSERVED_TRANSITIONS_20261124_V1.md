# The repair is a composition of observed transitions, not one clever guard

Branch `arena/3fc9b5f0-brain`. No merge. This report records generated, verified repairs on five logged real failures; it is not a §6 completion claim.

## What changed

The earlier empty-payload loop found the locally correct guard for click `c53d373` but could not finish the repair: the same empty value also had to be normalized before auto-envvar resolution and serialized with its own quotes. Three independent defects were found in the generator, not in the hypothesis:

1. `normalize_candidates` inserted at the following `if`'s first token, which doubled/dropped indentation.
2. `serialize_candidates` only wrapped the interpolated expression; when the f-string supplied surrounding quotes it produced `"'...'"`. It now drops those quotes and places the helper at module scope after imports, so a generated file still imports.
3. Verification counted "no FAILED lines" as success. A syntax/import error also has no FAILED lines. Acceptance now requires a parseable candidate and at least as many passing tests as the parent baseline.

With those corrections, `multi_producer_normalization_v1.py` generated and verified the composed repair on click `c53d373` (`676 passed`) with no diff, model, network, or stored parameter.

## Other observed transitions

The same mechanism was extended from "one empty guard" to four source-derived transition families:

| observed transition | generated edit | acceptance |
|---|---|---|
| actual `None`, expected `('SRC', '')`, an empty `self.help` in the failing frame | complete an early `return None` with the tuple the same function returns later, replacing the observed empty member with `''` | click `05f6fd0`, `116 passed` |
| actual `'Bearer '`, expected `'Bearer'` | insert `.rstrip()` on the return expression whose shape matches the observed output | werkzeug `051fd66`, `124 passed` |
| two observed false flags in an `A or B` clause | append `not A and not B` to the complementary arm; two such edits compose | werkzeug `884437ae`, `150 passed` |
| a `KeyboardInterrupt` raised inside an `except` handler while writing the diagnostic | fence the call with `pass` or retry the call once | click `fc518e4`: 7/8 tests pass after composed fences; the success-exit path still fails |

Every edit is derived from a runtime-observed value, a literal comparison captured in the failing test, or the source structure of the same function. The whole relevant test file decides acceptance.

## Hard result

`canonical/verification/WIRED_FIVE_LOGGED_COMMITS_20261124_V5.json`: 1/5 verified.

`canonical/verification/MULTI_PRODUCER_NORMALIZATION_20261124_V5.json`: 1/5 verified (click only; the CLI then used one repo for all five rows, so two rows were `SOURCE_OR_TEST_NOT_FOUND` — recorded as not repaired, never as passes).

`canonical/verification/MULTI_PRODUCER_NORMALIZATION_20261124_V9.json`: **5/5 verified** — every generated candidate passed its whole test file. `canonical/verification/INDEPENDENT_REPLAY_FIVE_20261124_V1.json`: an independent replay implementation, sharing no generator code, reproduced **5/5** in fresh worktrees (676, 116, 8, 150, 124 passing tests). V5 was 1/5, V7 3/5, V8 4/5; V9 closed the remaining late-interrupt contract by enumerating pass-or-retry policies per fenced call. Zero model calls, network calls, stored parameters, or gold-patch reads in every round.

## What this refutes and what it does not

Refuted: "the mechanism cannot generate a repair for these commits". Three of five are now generated from observations and verified by the project's own runner. One more is narrowed to a single remaining behavioural contract (the intended exit code after a late interrupt).

Unseen-commit probe: 0/2. The unchanged generator was run on click `f67c2bb` (short-help abbreviation) and `7996a89` (hyphenated word wrapping); receipts `UNSEEN_COMMIT_F67C2BB_20261124_V1.json` and `UNSEEN_COMMIT_7996A89_20261124_V1.json` record zero generated proposals in both. The five-commit success is therefore a result on commits used while building these generators, not evidence of transfer.

Not established: single-experience transfer, an unseen environment, HONEST, GUI/browser, store-vs-empty and generalized-vs-raw memory ablations, or any §6 condition. The result is per-commit generation with the post-fix test file as oracle; independent verification confirms the candidates, not generality.
