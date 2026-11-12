# Two replayable fixture exercises — not two verified corpus admissions

2026-11-12 · authority NONE

## Correction to the proposed claim

This round's original hypothesis ('the corpus went from zero to two') was too strong: running
renames on existing test fixtures does not make them production work, and checking them locally does
not admit them to an independently verified corpus. This round records **two local fixture exercises**,
**zero independent verifications**, and **zero learning updates**. It does not change a registry or
`truth.achieved`.

## Executed result

`python3 corpus_run_20261112.py` invokes the existing registered adapter
`python.refactor.rename_symbol.v1` on copies of
`canonical/tests/fixtures/tree_sitter_swe/python`:

| Request | Edits | Pre-edit files saved | Local AST check | Store-only replay |
|---|---:|---:|---|---|
| `calc.py`: `add` → `add_v2` | 4 | 4 | holds | matches |
| `util.py`: `twice` → `twice_v2` | 4 | 4 | holds | matches |

The four distinct source contents are saved with the existing receipt lane's `snapshot_inputs`
helper **before** mutation. The records include relative filenames, input and output digests,
request, adapter result hash, and observed gate. This is a local exercise schema, not a standard
capability execution receipt. It does not extend `execute_and_receipt` or its independent verifier.

For replay, the edited directory is deleted and rebuilt only from the content-addressed store.
Missing or corrupt blobs refuse replay. Both result hashes and edited-file digests match for both
requests. A regression test deletes the original fixture before replay to ensure there is no fallback
to the fixture. Tests run in isolated temporary workspaces rather than writing repository records.

## Baseline and limits

The existing fixture is deliberately buggy: `add(a, b)` subtracts. A fresh subprocess running its
unittest suite measures **2 tests, 1 failure, 0 errors**, both before and after each rename. The same
failing test remains; a rename is not a repair. The runner compares test counts and failure/error IDs,
not full behavioral equivalence. The local AST check covers definitions, name/attribute references,
and from-import names in these small fixtures; it is not a general Python semantic verifier.

The adapter gate is **PASS_BLIND**, because `run_tests` is omitted. Supplying the already-red suite in
a prior local attempt produced `TESTS_RED_AFTER_EDIT` and rollback. No tolerance or gate was widened.
Records explicitly say the postcondition is local and the verifier is null. Neither repeated execution
nor a matching hash establishes independent verification.

## What remains

This demonstrates a bounded pre-edit snapshot → edit → local checks → store-only replay path. It does
not establish permanent learning, held-out generalization, sentience, arbitrary computer use, or
state-of-the-art software engineering. It does not establish that this fixture-only path is suitable
for production environments with dependencies, resources, and external state.

The useful next step is a real backlog task with a predeclared acceptance test and an external runner
that restores its captured environment and independently executes that test. Only after that should
an experience be considered for admission or learning. Adding records by itself is not learning.
