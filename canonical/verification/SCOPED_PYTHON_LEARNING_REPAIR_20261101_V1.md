# Scoped Python learning repair: bounded distinct-issue transfer

## Result and scope

The frozen two-family experiment now solves **2/2 distinct held-out issues with
scoped learning enabled versus 1/2 with it disabled**, with two repetitions per
issue. This is controlled authored regression evidence on public historical bugs,
not author-blind or independent benchmark certification. No capability/ownership,
terminal, universal-learning, permanence, optimality or sentience credit follows.

One new transfer is demonstrated: teaching the historical `ichunked` insertion
fix enables repair of the different historical `chunked_even` issue. The Bits
lesson still does **not** transfer to the byte-unit issue; both arms solve that
issue through the maintained solver. Two repetitions are not four distinct tasks.

The prior merged historical report remains unchanged as the record of its earlier
failed transfer. This report describes the subsequent implementation and runs.

## Reproduced blocker and implementation

Before runtime edits, current-tree probes found:

| Case | Pattern tokens / holes | Reproduces supplied fix | Structural twin |
|---|---:|---|---|
| Bits capacity | 13 / 3 | yes | pass |
| Byte-unit mixed docstring/code change | 42 / 7 | no | fail |
| `ichunked` insertion | 27,952 / 1,882 | no | fail |
| `chunked_even` insertion | 27,989 / 1,882 | no | fail |

The existing regex hunk representation fell back to whole modules for insertions,
misrepresented Python triple strings and indentation, and could not bind a newly
referenced parameter absent from the small insertion anchor. Multiple matching
functions also require actual oracle-guided location selection.

The repair adapts existing machinery rather than replacing the learner:

- Prefer existing working legacy rules, preserving their content IDs and behavior.
- Add a versioned Python representation using the standard lexer and bounded AST
  scopes. Entry insertions bind parameters by signature category/position and
  anchor to the first executable statement. Other supported multi-hunk changes
  use one complete changed function, with identical outside context.
- Reuse the existing relational token abstraction, replacement renderer, SQLite
  store, typed project oracle, applicability/invalidation and production apply path.
- Preserve comments, opaque literals, Unicode and supported uniform CRLF windows;
  do not AST-unparse/reformat entire files. Unsupported mixed-newline windows can
  refuse. Anchors cannot match inside strings, comments or conditional subtrees.
- Content-address the new scope and parameter-binding metadata as well as tokens.
- Qualify the demonstrated transformation on an alpha-renamed source, requiring
  the expected renamed edit for new-format lessons, not merely valid Python.
  This remains structural transport, not proof of semantic correctness.
- Enumerate at most 16 candidate locations per recalled rule, behaviorally verify
  each, and preserve the live invalidation check. Reproduction/twin qualification
  considers at most 64 locations. Invalidating a rule stops its remaining locations.

Generic rename refusal is preserved. No registry capability, automatic promotion,
new external-model dependency, frontdoor learning default or parallel skill store
is introduced. Production scoped learning remains explicitly configured.

## Frozen matched experiment

`canonical/tests/fixtures/scoped_python_learning_curriculum_v1.json` was written
before runtime edits and binds the existing immutable provenance manifest. The
original four historical snapshots and selected upstream tests are unchanged.
The same solver uses 24 legacy mutations/file, two guided files/symbols and 12
pairs in both arms. Only explicit scoped retained learning is disabled in the
baseline; this is not removal of every other existing Brain learning mechanism.
Trial order alternates between arms. Expert after-source is supplied only to
teaching for the teaching issue, never in held-out apply payloads.

| Held-out issue | Baseline | Learning enabled | Median apply wall, baseline / enabled | Enabled search |
|---|---|---|---:|---:|
| `bytes2human` | 2/2 | 2/2 | 13.375s / 13.602s | 1 each |
| `chunked_even` | 0/2 | 2/2 | 23.441s / 0.747s | 0 each |

Every successful application passes the actual declared corpus and separate audit.
Failed baseline zero-consumption attempts restore source bytes and fail the audit.
Teacher code and selected tests are checked unchanged. The zero-consumption
transfer executes two memory-oracle checks: an earlier wrong location is rejected,
then the correct location passes. Only the verified patch is applied.

Median teaching is **0.423s** for Bits and **0.625s** for `ichunked`. The latter
transfer therefore takes roughly **1.372s including its teaching worker**, before
separately measured preparation/audit costs. Enabled transfer uses four observed
child launches; disabled zero-consumption attempts use 156–160. Do not call this a
speedup over a successful baseline: that baseline fails its bounded search.
No speed advantage is demonstrated for the boundary family.

## Negative controls and boundaries

- A misleading inclusive-threshold helper is a syntactic match for the Bits rule.
  Real project tests reject its incorrect mutation; fallback repairs the real
  byte-unit bug and preserves the decoy.
- The actual different pinned source revisions are declared in dependency context.
  The incompatible zero-consumption request is inapplicable to memory, executes
  zero memory-oracle calls, and falls back to the unchanged solver, which fails
  safely and leaves source unchanged. This is caller-context applicability, not
  automatic environment attestation or an interpreter-upgrade test.
- Unit regressions cover literal/comment opacity, parameter-role mismatch,
  non-generator mismatch, conditional-anchor exclusion, metadata identity,
  expected-twin mismatch, Unicode/outside-byte preservation, CRLF, a 16-location
  budget and live invalidation stopping alternative locations.

These are exact target-module historical projects with selected upstream test
bodies, authored consumers and audits, not complete upstream repositories. The
zero-consumption pair changes different functions in the same library file;
actual multi-source-file patch qualification remains open. Experimental databases
are isolated temporary stores, deliberately not promoted into global/shipped
memory. Permanent availability or validity of lessons is not established here.

## Costs and validation

The adjacent JSON contains full receipts, source hashes at run start, frozen
curriculum identity, phase costs, worker/child CPU, source/test integrity evidence,
audits and refusals. The final campaign took **146.577s wall / 145.030s own plus
waited-descendant CPU**, across **25 fresh workers** and **822 worker-observed
subprocess launches** (worker launches are additional).

The run timer covers local discovery/provenance verification, fixture construction,
teaching, both arms, verification, audits, negative controls and cleanup. It excludes
initial interpreter imports and final JSON output serialization. Existing upstream
acquisition is reused sunk work, not zero acquisition effort. Earlier exploratory
runs, environment setup, integration/model/safety tests and model-assisted reasoning
or provider costs are separate; complete all-in development-cost optimality is not
claimed. RSS receipts describe individual peaks, not aggregate process-tree peak.

Current-tree validation before model/merge gates:

- **224 integration tests passed / 211.75s**, including the historical matrix,
  production corpus/rollback, scoped restart/transport, rename safety, coupled
  search, provenance/localization and the prior cache-freshness regression.
- **15 focused new tests passed / 1.17s**. An initial unit-test assumption requiring
  a new-format label was corrected: working legacy rules are intentionally preferred;
  the contract is exact behavior, not forcing a representation. No behavioral
  success assertion, typed verification or negative control was removed.
- The final metered campaign separately reran the frozen comparison and both
  controls after the implementation fixes. Producer file hashes bind that run.

Official compiler/verifier, admission, integrity and PR CI are subsequent gates.
Their actual command/check outcomes govern merge, not this document. This is not
whole-repository-green or independent-certification evidence.

Reproduce:

```sh
.venv/bin/python -m pytest -q canonical/tests/test_python_scoped_edit_learning_v1.py \
  canonical/tests/test_historical_repair_transfer_v1.py \
  canonical/tests/test_scoped_skill_verification_and_restart_v1.py \
  canonical/tests/test_retained_repair_production_qualification_v1.py \
  canonical/tests/test_a_learned_rename_is_not_a_shape_v1.py
.venv/bin/python -m canonical.tests.scoped_python_learning_campaign_v1 /tmp/scoped-learning.json
.venv/bin/python canonical/runtime/compile_brain_unified_model_v1.py
.venv/bin/python canonical/runtime/verify_brain_unified_model_v1.py
```

## Decision

Keep this bounded representation/verification improvement. Continue using failed
or unsupported lessons as explicit refusals, not evidence of perfect learning.
The next frontier is distinct new repository tasks and genuine multi-source-file
edits, followed by broader migration/concurrency/crash/inventory stress. Do not
expand the claim to arbitrary computer use or sentience.

## Post-report gate results

Official verifier: **33/33**. Model/goal-compiler tests: **137 + 911 subtests
passed / 33.29s**. Admission/orientation/integrity tests: **50 passed / 27.47s**.
Existing invalid-escape deprecation warnings remain. Intent check: `ok: true`.
The official projection is regenerated after this documentation update; actual
GitHub CI and signed referee checks must pass before the authorized merge.

## Incoming-main integration and final acceptance

Main through `6f7401105c699585086ac04fee2384596b33493c` added a stronger multi-step
repair fallback and bytecode cleanup. Those changes were preserved. The full
matched campaign was rerun against that stronger solver, producing the table and
146.577s qualification measurements above. The baseline still fails the
zero-consumption task despite 156–160 observed child launches. No fallback was
disabled to manufacture the retained-transfer result. Combined-tree integration
including the incoming solver tests passed **232 tests / 291.93s**. Prior
pre-integration measurements remain in the JSON and Git history.

Main subsequently advanced to `573e735bd73fab444f608d9e8f762a6a3012472e`, changing
child bytecode-write policy rather than the learner. It is integrated and affected
tests are rerun before merge. The timing table is from the fully metered run at
6f740110, not a claim of identical timings on all later environments. Integration
tests ran concurrently with that campaign; timing observations are descriptive,
not isolated-load statistical evidence. The exact-base guard correctly blocked
the initial PR as main advanced. Metadata is refreshed, not the guard relaxed.
Only generated projection conflicts were resolved, using the official compiler.

After the bytecode-policy integration, **69 affected checks passed / 166.79s**,
including the full historical matrix/negatives, scoped unit/restart/rename safety
and incoming bytecode-policy regressions. Main then advanced to
`c34c150f2e19692e321025a1d5cb3e8655c76cd7` with scope-aware rename input routing
changes only; no measured learning/project-repair producer files changed. Those
changes are preserved and their routing/model paths are revalidated separately.
