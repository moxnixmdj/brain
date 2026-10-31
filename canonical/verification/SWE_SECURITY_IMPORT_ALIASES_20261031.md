# Bounded security import qualification — local integration evidence

Date: 2026-10-31. Canonical upstream base: `1f2f1605f084aee80c729e35b2dc763182e604ba`.
Prior local integration: `1c34639c` (source-scoped localization, not reimplemented).
Scope: existing AST security fallback and regression controls. No new package,
capability registration, finding-policy expansion or protected-harness edit.

## Observed failure and reuse

The scanner flagged `os.system(command)` but missed equivalent imported names,
such as `import os as ops; ops.system(command)` and
`from os import system as launch; launch(command)`. One global alias dictionary
would leak unrelated imports across scopes and misclassify shadowed parameters.

Reused, rather than replacing the analyzer:

* Brain's `root3_runtime_process_universe_v2._aliases` and `_qname` for qualified
  import spelling. Feed only selected import statements to `_aliases`, not the
  whole module with nested imports.
* Native CPython `symtable` for lexical global/local/free classification, plus
  its child tables for function, lambda and comprehension scopes.
* Existing security row shape, rule IDs/messages, severity/confidence, hash
  exemption, secrets, ordering and changed-line blocking/advisory policy.

Only stable absolute imports directly in the module body introduce new
qualification. Conflicting/relative/conditional rebinding, module assignment,
explicit global writes from nested scopes and star imports prevent expansion.
Local imports are not inferred. Function parameters, closure bindings and
comprehension targets do not inherit module aliases. Defaults, annotations,
decorators, bases and the first comprehension iterable use their enclosing
scope. Methods skip class-local bindings as the compiler specifies; class-body
alias expansion itself is deliberately unsupported. When new qualification is
unavailable, the legacy direct-spelling heuristic remains, including its known
potential false positives for a locally shadowed literal `os.system`.

Identity mappings (ordinary `import os`, for example) bypass the extra compiler
parse/scope walk. Child tables are indexed once per parent, with queues for
same-line anonymous scopes instead of repeatedly searching all sibling tables.

YAML's exemption now recognizes the qualified names `yaml.SafeLoader` and
`yaml.CSafeLoader`, including supported aliases, not arbitrary expressions
containing the substring `Safe`. Shadowed loader aliases do not grant an
exemption. This remains a static name heuristic, not proof of runtime values.

## Failure-first and real-path checks

`canonical/tests/test_security_import_aliases_v1.py` has **61 controls**: imported
modules/functions; builtin eval/exec aliases; functions, async functions,
closures, lambdas and all comprehension kinds; default/decorator/annotation
scope; ambiguous/relative/star/local bindings; YAML loader controls; weak-hash
exemption; direct legacy rules, secrets, row stability and no subject execution.

Same-line anonymous scopes have distinct expected messages, not just a count
that could pass after swapping two scopes. This exposed an intermediate bug:
CPython's dictionary-comprehension symbol-table pass visits the value before
the key, unlike runtime evaluation order. The implementation follows the
compiler's traversal, including argument annotations, rather than guessing.

Three controls call the actual security adapter through an actual isolated
stdlib virtual environment, without Bandit. They assert the `brain-ast-security-v1`
route, block an aliased B605 on a changed call line, retain a preexisting B605
as advisory, and accept a shadowed parameter without a B605 finding. No import
loader, tool probe or subprocess result is replaced. Subjects are parsed, never
imported or executed by the scanner.

Same six-module comparison, unchanged tests on both versions:

* Baseline: **37 failed, 66 passed, 14 skipped**, 4 warnings, 12.62 s.
* Patched: **1 failed, 102 passed, 14 skipped**, 4 warnings, 11.23 s.
* Programmatically compared JUnit failure identities: **36 removed, 0 introduced**.

Modules: the new security controls, existing diff-security/static-triage/type
adapters, `test_hardcore_swe_capabilities_20261031_v1.py`, and
`test_hardcore_swe_capabilities_and_speed_v1.py`. For the baseline, openly
reversed only our runtime-file patch in the working tree, ran the unchanged
tests and timings, then reapplied it. No historical-file test infrastructure.

## Honest residual and unsupported scope

The unchanged residual is
`HardcoreSWECapabilitiesTests::test_root3_process_universe_has_zero_unmediated_sites`:
`python_source_symbol_index.py::_collect_index_parts`, line 428, uses
`concurrent.futures.ProcessPoolExecutor` outside that inventory's mediation.
It fails before and after; its assertion was not changed. Skips in the selected
neighboring modules remain visible. The complete repository suite was not run.
The earlier fault-localizer scoring defect is also not addressed by this patch.

This is **not Bandit equivalence**, complete Python binding/dataflow analysis,
a runtime-value proof, or security certification. Dynamic import, reflective
mutation, temporal alias reassignment, attribute monkeypatching, function-local
import inference, class-body qualification and arbitrary alias assignments are
outside the supported expansion boundary. Ambiguity can intentionally leave
false negatives. Native compiler-scope behavior and controls were measured on
Python **3.11.2**, not every Python release. A PASS from the existing gate is
not a guarantee that a program is secure; this patch does not revise its
inherited `complete`/`verified` vocabulary.

## Cost, not a universal speedup

Nine batches of 20 scans per fixture/version, median per-scan `perf_counter_ns`
time; module import excluded. Baseline and patch ran sequentially in the same
sandbox, with the runtime edit exposed/reapplied as above. No confidence bounds
or randomized production performance claim.

| Fixture | Baseline ms | Patched ms | Baseline → patched findings |
|---|---:|---:|---:|
| Small clean, no import | 0.025890 | 0.021400 | 0 → 0 |
| Small direct `os.system` | 0.023321 | 0.021809 | 1 → 1 |
| Small imported function alias | 0.022472 | 0.090843 | 0 → 1 |
| 100 clean functions, ordinary `import os` | 2.508907 | 2.140010 | 0 → 0 |
| 100 functions, `import os as ops` | 1.787550 | 3.306586 | 0 → 100 |

New qualification costs approximately 0.068 ms on the small alias fixture and
1.519 ms on the 100-function alias fixture. Previously missed findings are
not comparable work, and the clean differences are noisy observations, not
proof of a speedup. No globally optimal/fastest route has been established.

## Discovery, provenance and integration

Official sources inspected through GitHub:

* https://github.com/python/cpython/blob/main/Lib/symtable.py — symbol predicates.
* https://github.com/python/cpython/blob/3.11/Python/symtable.c — actual traversal
  order for compiler child scopes; no donor code copied or package installed.
* https://api.github.com/search/repositories?q=python+static+analysis+import+alias+symtable&per_page=2
  — discovery request produced no candidate rows; no qualified external supplier
  or broad literature survey is claimed.

Incoming upstream PR6495 contained an engineering inventory and generated-model
changes, not an overlapping security fix. Its generated-artifact merge conflict
is resolved by the official compiler, not hand-merging model hashes.

This is externally agent-assisted implementation and producer-run regression
measurement, **not independent verification or proof that Brain autonomously
produced this repair**. No benchmark/family, ownership, promotion, capability or
terminal credit. No push/PR/main merge is implied. Final compiler/verifier and
local integrity/admission results are checked after this indexed report is
finalized to avoid recursively invalidating its own model digest.
