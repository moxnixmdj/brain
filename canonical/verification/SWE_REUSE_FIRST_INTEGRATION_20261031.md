# Reuse-first SWE integration bundle — producer-run engineering evidence

Date: 2026-10-31. Upstream base: `34124aa5` (PR6504).
External agent-assisted implementation, no Brain capability/benchmark/ownership/
promotion/terminal credit. This is not independent verification or a claim that
all advanced software-engineering gaps have been closed.

## Combined delivery and reuse

The owner authorized fastest correct reuse and merging all local work. This bundle
includes the two prior local integrations, preserved without relabeling their
measurements:

* Source-scoped fault evidence: `SWE_SOURCE_SCOPED_LOCALIZATION_20261031.md`.
* Scope-aware security import aliases: `SWE_SECURITY_IMPORT_ALIASES_20261031.md`.

Original per-change intents are preserved as `*_ORIGINAL_INTENT.json` in this
verification directory. One combined active intent represents the single delivery
transaction, as the existing admission gate requires. No protected guard, policy,
workflow, truth ledger, capability registration or assertion bypass is introduced.

Fresh upstream already supplied tree-keyed sibling index reuse, certificate scope
handling and routing/substrate improvements. Those are integrated, not rebuilt.
The generated model's merge conflict is resolved by the official compiler.

## Reproduced source-deletion defect and repair

An ancestor output directory passed the old scaffold check, which only rejected
outputs equal to or underneath source. Recursive recreation then deleted the
source and unrelated fixture files; SOURCE_TREE_MUTATED was raised afterward.

Use the existing resolved `Path.parents` boundary in both directions. Validate
both output destinations before even creating the temporary index. Equal, parent,
child, repository-root and resolved symlink-overlap cases now refuse before writes.
No new path framework. This is not a symlink-swap/race sandbox or a general promise
that executing arbitrary subject tests cannot mutate source.

Also reuse the AST's existing positional-only argument partition: generate those
arguments positionally, while preserving keyword arguments for other parameters.
An actual generated test now executes a mixed positional-only/keyword-only function.
Async synthesis and semantic test-oracle expansion are not claimed.

## Reproduced forged-cache defect and repair

Changing a persisted index definition while leaving source unchanged previously
returned output_verified=True with zero modules parsed. Recomputing the row hash
does not make fabricated derived semantics authentic.

Retain existing SHA256, real index derivation and tree-keyed sibling discovery.
A bounded process-local map of 128 path/digest attestations remembers only exact
artifact bytes this producer actually derived. Known outputs can be reused after
source hashes match; unknown, altered or new-process artifacts are rederived.
Unknown sibling files are skipped before reading their contents. Existing output
bytes are checked again before the unchanged-output shortcut is accepted.

The external cached-index validator additionally requires an authenticated artifact
or exact equality with a fresh source derivation. It still checks membership and
source hashes first. Fabricated definitions, symbols, callers and totals refuse.
This is process-local provenance, not a persisted signature or cross-process trust
claim, filesystem snapshot, adversarial in-process Python sandbox or concurrent
source-write isolation. A fresh process deliberately loses the warm parse shortcut.

## Failure-first controls and neighboring suites

New file: `canonical/tests/test_swe_safe_reuse_integration_v1.py`.
Before the two runtime repairs: **14 failed, 3 passed**, 1.77 s.
After: **17 passed** (also included in the focused suite below).
Controls use real disposable directories, source bytes, symlinks, test execution,
cache files and child interpreters. No loader/subprocess-result replacements.

One incoming test previously required a fabricated sibling row (all-zero source
hash and no producer provenance) to be returned. It is openly corrected to require
no reuse of that untrusted metadata. Real producer/sibling reuse has separate
positive controls. No protected harness change or historical-file test loader.

Focused suite: **122 passed**, 4.85 s. Covers new controls, incoming tree-cache
controls, existing scaffold and multiline-import controls, plus all prior new
security and localization controls.

Broader selected suite: **211 passed, 3 failed**, 4 warnings, 19.06 s. The same
three identities were already observed before this repair in the previous audit:

1. root3 process inventory: symbol index ProcessPoolExecutor is not mediated;
2. fault-localizer shared-vs-failing-only scoring: 1.0 vs 2.707106781187;
3. cross-file registry exact contract expects one effect, registry advertises two.

These assertions are unchanged. This is not a green whole-repository suite. The
full repository suite was not run. The selected broad run includes incoming
certificate/substrate controls, repair/choreography, security/localization,
scaffold/index and acceptance-boundary controls. Final model/compiler, admission,
integrity and remote checks are recorded after this indexed report is finalized.

## Measured cost

Python 3.11.2, synthetic 32-module/320-function tree, nine samples, median full
adapter/validator perf_counter_ns duration (imports excluded):

| Route | Median |
|---|---:|
| Warm index, zero modules parsed | 2.034 ms |
| Altered/untrusted artifact, 32 modules rederived | 9.193 ms |
| Known producer artifact validation | 2.556 ms |
| Unknown valid artifact validation, fresh derivation | 9.957 ms |

These are bounded sandbox observations, not randomized production comparisons,
confidence bounds, a universal speedup or global-optimality proof. Cache integrity
has an explicit cold/new-process cost; existing warm reuse remains available.

## Discovery and publication boundaries

Inspected native scaffold/index/transaction path handling and fresh upstream.
Official stdlib source: https://github.com/python/cpython/blob/3.11/Lib/pathlib.py.
The prior integration reports record qualified-name/CPython compiler discovery.
No donor package, replacement security analyzer or new runtime dependency added;
no exhaustive research-paper survey or globally best-route claim.

Publication is authorized, but main admission still requires actual green signed
checks and an explicit PR-number merge. No self-signed remote check or bypass is
permitted. Open engineering gaps remain open after this bounded delivery.

## Remote falsifier follow-up: explicit application/test directory roles

The first PR6506 head passed the signed referee and other verification gates, but
its surface census correctly failed **27/28** on localization. This was not bypassed,
rerun as a flaky result or addressed by lowering the floor. Reproduction showed
`declared_input_derivation` binding the test package (its `__init__.py` counted as
code) instead of the separately stated application directory. The strict
localizer then correctly refused: NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN.

Reuse existing stated-directory, witness-directory and test-discovery evidence.
For a test-consuming contract, a unique explicitly stated non-witness/non-test
directory binds source_root before test-owner inference. Multiple such directories
remain ambiguous, rather than arbitrarily selecting one. No localizer score,
source-membership filter, acceptance assertion or census floor changed.

New source/test-role controls: **5 failed, 1 passed -> 6 passed**. Existing declared
input controls plus those six: **13 passed**, 1.06 s. Actual full surface census
with the unchanged floor: **28/28**, including real localization output.

Seven-module follow-up neighbors: **143 passed, 1 failed**, 6.21 s. The failure is
`EffectFamilyEnumerationTests::test_caller_family_passes_with_a_real_callers_of_artifact`
with ANSWER_SCOPE_UNPROVEN. Openly reversing only this binding patch reproduced
that same failure (**1 failed**, 0.54 s), then the patch was reapplied. This is an
additional observed pre-existing residual, not hidden or attributed to this fix.
