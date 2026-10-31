# Faster incremental indexing with context-bound reuse

2026-10-30. Local development evidence, not independent capability admission.

## Reuse, not another indexing engine

Reused the existing pinned tree-sitter substrate, incremental index adapter, row hashes/validation, language cache, conservative impact selector and patch verifier. Inspected the existing dependency-cone proof cache as a design boundary; no synthetic independent receipt or dependency-completeness claim was created to reuse it as an authorization oracle.

Installed the already-pinned `tree-sitter==0.20.4` and `tree-sitter-languages==1.10.2` into the existing local venv; they were absent before this cycle. No dependency installation runs inside tests. No protected paths, registry, capability promotion or terminal authority were changed. Work remains uncommitted on `arena/4b31f8b6-brain`.

## Three reproduced failures

New actual-parser tests failed against the pre-change implementation:

1. Changing the real extractor's definition-kind configuration reused all eleven old rows instead of executing the new extraction behavior.
2. Adding a new test file left an explicit old index acceptable to consumers, despite that index omitting the new file.
3. Lowering the reference budget was bypassed by a warm cache instead of enforcing the current limit.

Result before edits: **3 failed in 0.31 seconds**. These tests change actual inputs/configuration or add real source files; they do not substitute a fake parser or successful execution result.

## Implementation

### Context-bound reuse and consumption

`tree_sitter_swe_kernel_v1.analysis_context()` records:

- loaded kernel implementation source hash;
- Python implementation and version;
- actual installed tree-sitter package versions;
- content hashes of installed parser Python files, native extensions and grammar library;
- language mapping, definition/reference extraction policy, import regexes, ignored-directory policy and limits.

The context is serialized as a snapshot, not aliased to mutable policy dictionaries. The index stores this context and its digest. Cache reuse requires an exact context match plus row integrity, structure, language and current source content checks. Legacy or obsolete contexts cause the producer to reparse; explicit consumers refuse until the index is rebuilt.

Installed dependency hashes use a bounded process-local memo keyed by device, inode, size, mtime and ctime. Project source **never** uses metadata-only reuse: each request reads and hashes every selected source file. Installed parser files/package identity are treated as immutable during a process; observed changes require restart so new on-disk identities are not assigned to already-loaded old libraries. A subprocess test executes byte-for-byte private copies of the real packages, modifies an owned copied dependency, and verifies restart refusal without changing the installed environment.

Missing real dependencies cannot be hidden by a warm index. A real `python -I -S` subprocess tests that refusal without patching imports.

### Inventory checks at the existing consumer boundary

`read_index()` now verifies that its declared source inventory still matches the selected supported files under the source root. Added, deleted or renamed files invalidate the old index. Duplicate paths and malformed self-hashed rows refuse. Existing impact and patch adapters already call this shared reader; they now reject an index that omits a newly added test before candidate writes.

This inventory is scoped by the existing supported extensions and ignore policy. It is not a claim of complete dynamic dependency discovery or universal test-selection soundness.

### Faster discovery and parsing input reuse

The existing ignore policy is applied before descending into directories with `os.walk`, instead of traversing and sorting entire ignored trees using `rglob` and filtering afterward. Returned source ordering remains sorted; nonignored file/directory symlinks still refuse.

The producer passes the already-read source buffer to existing parsing and row validation, eliminating a second source read on a cache miss. Parsing and source hashes therefore use the same captured bytes. No test result or successful acceptance verdict is cached.

## Before/after measurements

Fixture: eleven existing source files spanning eight languages, plus **4,000 actual files** under ignored `node_modules` and `vendor` directories. Temporary projects, actual installed parsers, no mocked filesystem/parser. This deliberately stresses ignored-tree traversal; it is not a held-out production repository or an overall SWE throughput benchmark.

Three repetitions, one sequential process per implementation version. Each repetition has a fresh project/index, then warm reuse, then one modified Python source. Timing includes profiling of real source reads and `parse_bytes()` calls. Setup and fixture copying are outside the timed operation. Before measurements executed before source edits; after measurements executed the updated implementation.

| Operation | Before samples (ms) | After samples (ms) | Before median | After median |
|---|---|---|---:|---:|
| Cold project index | 91.223, 83.138, 70.907 | 102.340, 11.828, 14.709 | 83.138 ms | 14.709 ms |
| Warm index | 72.602, 72.152, 82.808 | 10.544, 10.405, 12.539 | 72.602 ms | 10.544 ms |
| One changed file | 72.775, 72.300, 82.963 | 11.283, 11.140, 14.658 | 72.775 ms | 11.283 ms |

Warm median latency is **85.48% lower**; one-change median latency is **84.50% lower** on this fixture.

**Startup trade-off:** the first process call is slower, **91.223 → 102.340 ms**. The new implementation hashes approximately 83 MB of installed parser/native grammar files once per process. The cold-project median includes this first sample and two later projects benefiting from dependency-digest reuse; it is **not** a fresh-process startup speedup. An isolated context probe measured roughly 74.2 ms initially and 1.0 ms median on ten subsequent calls. Small projects without large ignored trees may see a net overhead; no universal latency claim is made.

Actual work counts in every repetition:

| Operation | Parser calls before → after | Source reads before → after | Reused rows |
|---|---:|---:|---:|
| Cold project | 11 → 11 | 22 → 11 | 0 |
| Warm | 0 → 0 | 11 → 11 | 11 |
| One changed file | 1 → 1 | 12 → 11 | 10 |

Before and after file-row hashes match exactly:

- cold/warm: `f20cea3ca5983cc8c58809bc7be33e31fa2b16f33d28f976da741f79ea1d8d3e`;
- one changed: `26f414a15d46573f199e47b9051ada294ffeb1a01afb6b45ff2205dced2cfd9f`.

The full artifact deliberately changes to add context metadata. Within the updated implementation, an unchanged warm artifact remains byte-identical, as checked by the existing test.

Reproducer:

```sh
.venv/bin/python -m canonical.experiments.benchmark_tree_sitter_cache_v1
```

It prints JSON and removes temporary projects. A separate rerun of that checked-in reproducer gave medians **13.100 / 11.215 / 12.512 ms** for cold-project / warm / one-change, with the same row hashes and work counts. Those later values are not substituted into the paired table above.

## Validation

- Existing tree-sitter suite before changes: **11 passed in 0.56 s**.
- New cache-context module: **29 cases**. Together with the unchanged existing tree-sitter suite: **40 passed in 1.62 s**.
- Coverage includes real extractor configuration changes, actual installed dependency hashes/versions, private real-parser dependency modification, absent substrate, legacy cache migration, malformed self-hashed rows, changed inventory, consumer refusal before writes, strict current limits, symlink refusal, observed ignored-tree pruning, actual source-read counts and actual parser-call counts.
- Adjacent ten-module selection: **161 passed, 3 failed in 32.09 s**. Failures were not weakened:
  - source-symbol registry test expects an exact `provides` list without its current additional alias;
  - change-impact registry test similarly expects a list without its additional alias;
  - apply-verified missing-test-path test expects refusal while the adapter intentionally discovers tests.
- Separate twelve-module repair/measurement/confinement regression: **150 passed in 111.68 s**.
- The two regression selections ran in parallel pytest processes; these timings are not the sequential benchmark above.
- Integrity guard against base `c79a8f544fe47b1d7250b1c64889b958237db4f3`: **17 rules, 0 violations, PASS**. `git diff --check`: clean.

No full-suite/CI-green claim, independent semantic oracle credit, promotion, commit or push.

## Boundaries

Context/row hashes provide consistency and invalidation, not authentication of a cache supplied by a hostile writer. This is not a sandbox, hostile filesystem defense, complete supply-chain attestation, detection of arbitrary in-memory monkeypatching, or a continuously atomic repository snapshot. Source can change after indexing; consumers revalidate inventory and content before use. Dynamic imports, unsupported file types and ignored paths remain outside a universal dependency-completeness claim. Cache publication remains the existing mutable artifact writer; concurrent publication/atomic cache replacement was not redesigned in this cycle.

The earlier public-entry intermittent report-preservation failure and previously reported broader-suite failures are not claimed fixed by this work.

Prior work: [shared repair rendering and report publication](SWE_SHARED_RENDERING_AND_PUBLICATION_20261030.md).
