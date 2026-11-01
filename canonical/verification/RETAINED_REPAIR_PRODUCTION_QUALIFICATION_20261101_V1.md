# Integration update — current result on incoming main

The original report below is **historical**, measured on `07099b7c`. It must not
be read as the current integrated-tree result. PR #6549 integrates main at
`e529c7b7b1f589617af9df9ea1cea7a825f2e1ce` and preserves its new rule that removed
identifier names remain concrete. Generic rename lessons must fail the mutated
twin; this intentionally refuses the earlier encoding `rstrip` → `lstrip` lesson.
We did not relax that safety rule to retain the old 9/9 headline.

Current measurements: **6/9 successful learned repairs and audits versus 6/9 for
the capable disabled baseline**. All six structural transfers hit memory with
search zero. **All three encoding teachings are correctly refused**; those three
tasks remain unresolved in both arms, not counted as successful repairs.

| Family | Disabled solved + audit | Disabled median incl. audit | Learning enabled solved + audit | Enabled median incl. audit |
|---|---:|---:|---:|---:|
| floor_boundary | 3/3 | 1.473s | 3/3 | 0.806s |
| iterator_extent | 3/3 | 1.441s | 3/3 | 0.798s |
| integer_encoding | 0/3 | 4.413s | 0/3 | 4.346s |

These timings include worker startup/repair and external audit, but not the
separate teaching cost (full observations are in the JSON integration section).
Failed-task timings are not speed comparisons between correct solutions.

Integrated affected run: **160 passed, 2 inherited failures in 79.88s**, including
all **28 qualification tests** and the **5 incoming rename-safety tests**. The two
inherited legacy apply failures remain unchanged and are explained below.
The initial integrated run exposed five obsolete encoding expectations; they were
corrected openly to require refusal, not skipped or made to accept a bad rename.
Artifact restoration and invalidation controls now use the structural floor
family, require actual fallback success and passing external audits, and prove
which path ran—not that memory is necessary to solve the task. The invalidation
assertion identifies the exact original skill, so a newly taught different skill
does not hide resurrection of an invalidated one.

No 9/9 current-tree advantage, independent certification, whole-repository-green
status, universal learning or permanent mastery is claimed. Original observations
are retained below and in the JSON for chronology rather than rewritten.

---

# Bounded production repair and retained-learning qualification

2026-11-01. Base: `07099b7c5986a8864e1fc8bb2a7d14050727a77f`.
Model-assisted development and same-producer tests; **not independent certification**.
This is the first finite batch of phases 1–2 of the six-phase plan, plus a measured
Python twin-generation fix. It is not completion of the whole plan.

## What changed

- Existing production apply adapter now executes the declared test corpus with the
  maintained runner in addition to the caller command, before and after source
  application. Exact maintained-runner argv can reuse its completed observation;
  merely naming a test in another command cannot. Empty/all-skipped corpus,
  incompatible outcomes, changed selected tests, and mismatched applied bytes fail
  closed. Each test subprocess has isolated bytecode state, so same-size,
  timestamp-preserving edits cannot be hidden by an old `.pyc`.
- Explicit opt-in composes the existing scoped SQLite skill store and existing
  copied-project oracle. A retained proposal still passes live application gates;
  a miss uses the unchanged capable solver. Successful single-target repairs can
  teach a scoped skill. Corrupt memory falls back without deleting the artifact.
- Unique atomic source-write temporaries preserve mode bits and do not clobber
  fixed sibling filenames. Optional regression-generation failures roll back;
  existing deterministic regression destinations are refused before source writes.
- Initial expert crystallization failed on **all three full upstream modules**:
  regex alpha-renaming damaged Python keywords, byte-string prefixes and numeric
  exponents. Python twins now use the standard `tokenize`/`keyword` modules and a
  one-pass output assembly; non-Python behavior is unchanged. This is reuse of the
  standard lexer, not a new parser or learning architecture.

## Curriculum and comparison

Four unmodified, licensed source snapshots from boltons, more-itertools and
itsdangerous are pinned by commit and SHA256 in
`canonical/tests/fixtures/retained_repair_projects_v1/PROVENANCE.json`.
Each temporary project adds a separate caller module, three authored acceptance
tests, and three separately executed audit cases. Defects and tests are authored
here. These are **seeded repository-derived projects**, not untouched historical
bugs, complete upstream repositories, their upstream suites, or official benchmark
scores. Hidden audit inputs are not passed to the repair solver.

Each family has an expert teaching project and separate held-out variants with a
different seeded defect. Teaching and each repair arm run in distinct fresh
processes. Held-out payloads do not contain the expert-correct source. Repeat the
whole comparison three times per family, each with a fresh artifact. Disabled
learning retains exactly the same bounded search/fallback: this is not the earlier
no-fallback ablation. Authored tests remain byte-identical after successful repair.

| Family | Disabled solved+audit | Disabled median wall incl. audit | Disabled subprocesses incl. audit | Learned solved+audit | Learned median wall incl. audit | Learned subprocesses incl. audit |
|---|---:|---:|---:|---:|---:|---:|
| floor_boundary | 3/3 | 1.277s | 16 | 3/3 | 0.726s | 4 |
| iterator_extent | 3/3 | 1.315s | 11 | 3/3 | 0.702s | 4 |
| integer_encoding | 0/3 | 4.183s | 75 | 3/3 | 0.809s | 4 |

Times above include worker startup/imports, actual repair/verification and external
audit, but exclude the separate expert-teaching cost below. A failed baseline's
runtime is **not** a speed comparison between equally correct solutions.

| Family | Median teaching worker wall | Median teaching + learned repair + external audit |
|---|---:|---:|
| floor_boundary | 0.174s | 0.893s |
| iterator_extent | 0.218s | 0.924s |
| integer_encoding | 0.180s | 0.989s |

Teaching executes two oracle subprocesses per trial; learned repair executes three
and its external audit one. Every learned transfer hits a scoped verified skill
and calls fallback search zero times. The two successful disabled families require
15 and 10 repair subprocesses respectively, plus one external audit. The encoding
baseline exhausts its configured bound after 74 repair subprocesses and fails its
external audit; no successful-source-write claim is made for it.

The raw nine observations, source hashes, worker/child CPU, separate audit costs,
per-worker RSS and largest-child RSS are in the adjacent JSON. `elapsed_s` starts
after worker imports; `process_wall_s` includes worker startup. CPU includes worker
and waited-for children only when both fields are summed. RSS is **not aggregate
process-tree peak**. Source download, fixture construction and human/expert
acquisition effort are not measured; neither a global compute-cost nor optimality
claim follows from these results. Three repetitions on one machine do not provide
statistical certification across environments.

## Refusal, restoration and real-boundary checks

The 28-case new qualification module uses actual processes/files, not patched
loaders, subprocesses or pathlib. It checks actual-corpus disagreement, empty and
all-skipped suites, changed selected tests, stale bytecode in both directions,
post-apply wrong-patch rollback, source hashes/modes, optional regression creation
and destination collision, retained invalidation, incompatible applicability,
artifact removal/restoration, automatic teaching, corrupt-memory fallback, root
projects, source snapshot integrity, Python lexical twins, and the real
`astra_runtime._invoke_bound_capability` dispatcher teaching then recalling with
search zero. Artifact removal causes actual fallback search (and failure for the
bounded encoding case); restoring the artifact restores successful transfer.

## Configuration and trust boundary

Learning is **off by default**. The existing apply API / explicit bound invocation
accepts, for example, the following alongside normal source/test/output arguments:

```json
{
  "source_root": "project",
  "test_paths": ["project/test_engine.py"],
  "output_path": "repair.json",
  "retained_learning": {
    "enabled": true,
    "db_path": "memory/repairs.sqlite",
    "target_path": "project/src/engine.py",
    "contract": {
      "schema_version": 1,
      "scope_id": "example/engine-contract/v1",
      "verification_kind": "TEST_SUITE",
      "dependencies": {"python_major": 3},
      "preconditions": {"operation": "finite-floor"}
    },
    "context": {
      "dependencies": {"python_major": 3},
      "preconditions": {"operation": "finite-floor"}
    }
  }
}
```

Use your actual contract/dependencies/preconditions; copying these declarations
is not evidence that they hold. Context remains trusted caller input, **not an
automatic environment attestation**. The target must be a contained Python source
inside the source root. The SQLite path must be repository-contained, outside
`.git`, with `.sqlite`/`.sqlite3` suffix; it may be inside the execution root.
Copied-project verification retains its manifest/file/byte bounds, so large or
unsupported projects can refuse retained qualification without proving general
inapplicability. Ordinary search remains available. Typed teaching requires actual
positive `TEST_SUITE` evidence; legacy plain-assert scripts with unknown counts
do not become typed evidence merely because their command exits zero.

This does not modify frozen registry action templates or automatically enable
learning in natural-language planners. The tested production dispatcher accepts
explicit retained arguments; broader frontdoor configuration is not claimed.
Tests, commands and explicit context are trusted inputs. Copied-tree execution is
**not an OS sandbox**. Protection/restoration covers selected declared test files
and planned source writes, not every possible external filesystem side effect.
Rollback on observed failures is not a power-loss-atomic transaction. Ordinary
source mode bits are covered, not ownership, ACLs or extended attributes. Concurrent
invalidation across a filesystem application, crash recovery, upgrades, large
inventories and full restoration campaigns remain unqualified here.

## Validation and remaining work

Affected suites: **155 passed, 2 failed in 68.73s**, including all **28 new
qualification cases passing**. Both failures were reproduced on the original base
before editing (original apply suite: 11 passed, 2 failed):

1. `test_a_patch_that_fails_in_place_is_rolled_back_byte_for_byte` supplies a
   three-argument fake for the already-four-argument `_run_test`.
2. `test_no_bounded_repair_means_no_write` expects no repair where the inherited
   live-trace synthesis now produces a constant that satisfies its single stated
   test. That test pass is not a complete semantic correctness claim.

These tests are not weakened, skipped or rewritten. The affected set includes the
existing scoped restart, durable/general lesson, lesson transport/shipping,
measured/objective/semantic acceptance, repository measurement, test-guided search
and apply suites. This is not a whole-repository-green claim. The official model
compiler/verifier and existing admission/integrity/model suites are separate
acceptance steps; their command outcomes are reported with this change, not
inferred from this document. No independent/terminal/ownership promotion follows.

Next: harder actual historical repository bugs and multi-file procedural repairs,
then crash/concurrency/migration/inventory stress and broader reversible autonomy.
Passing these finite tests proves neither universally optimal engineering,
permanent mastery, arbitrary-environment one-shot learning nor sentience.
