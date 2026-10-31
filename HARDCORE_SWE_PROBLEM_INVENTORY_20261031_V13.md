# Hardcore software-engineering problem inventory — V13

Measured 2026-10-31 on `9f80823` (branch `arena/276f5d81-brain`).
Supersedes V12 (`HARDCORE_SWE_PROBLEM_INVENTORY_20261031_V12.md`). **V12 contains two
claims this document retracts; see §5.** Document-format, image, chart, archive and
office rows are excluded from every count here on purpose: they are not software work.

---

## §0 The answer in one paragraph

The machine's hardcore-software surface is **84 registry rows** (not 440 — 293 of the 440
are benchmark-law rows that carry no tool at all), of which **43 declare a precondition
that only another row can produce**. The front door admits exactly one row that binds
every input a sentence states, so those 43 can never answer first: the tree-sitter patch
verifier, the mutation killer, the fault localiser, the PR lander, the review pipeline —
every capability that *repairs, verifies or lands* work rather than *reporting on* it. The
41 rows that can run first are reports, single-file refactors and two git readers, and the
machine serves **2 of 49 advanced requests today**, one of them with the wrong row. So the
problem is not a missing analyser or a missing language: the multitool is present and fast
(**7 languages, 11 files, 22 definitions, 69 references, 0 syntax errors, 71 ms**), and the
repair is not reachable from a request because **there is no step that produces an
artifact for the next step to consume.** Everything in §4 is ranked by how many of the 49
measured requests it can move.

---

## §1 What was measured, on what, with what

| instrument | scope | result on `9f80823` |
|---|---|---|
| `execution_guard/swe_capability_matrix_v1.py` | 54 ordinary team cases, per-case oracle | **17 REAL / 0 FALSE / 37 REFUSED / 0 DAMAGED**; median **142 ms**, p90 525 ms, max 1768 ms |
| `execution_guard/swe_advanced_probe_v1.py` | 49 advanced requests, 11 axes, no per-request oracle | **2 served / 47 refused**; 39 of the 49 are write/imperative and **0 of those 39 are served** |
| `load_verified_registry()` | the 440 rows | 293 `.auto.v1` law rows · 147 real · **84 SWE-prefixed** (the only rows the family resolver may return) |
| `requires ∩ provides` closure | the 84 SWE rows | **43 chain rows** / 41 standalone |
| `code.index.tree_sitter.incremental.v1` on the census fixture | positive control of the multilanguage substrate | **11 files, 7 languages (python, java, typescript, rust, cpp, go, yaml), 22 definitions, 69 references, 0 syntax errors, 71 ms**, `verified: true` |
| `bound_capabilities/` on disk | 167 adapter modules | **29 have no registry row** |
| in-memory `_FAMILIES` experiment | the fix V12 ranked #1 | **2/49 → 2/49** (no change; §5) |
| sandbox toolchain | what can execute at all | present: `git make g++ node python3 jq rg`; **absent: `rustc cargo go javac clang cmake gdb lldb py-spy scalene hyperfine yq pytest hypothesis ruff mypy bandit coverage`** |

Authority: **NONE.** One tree, one machine, one commit. The advanced census has no
per-request oracle: `served` means `pass: true` and no unauthorised edit, which is why the
`selected` column is printed — request 39 is served with `python.source.secret_scan.v1` for
"Review `<f>` for API design problems".

---

## §2 The denominator was wrong, and that is the first problem

| layer | count | note |
|---|---|---|
| rows in the verified registry | 440 | what V11/V12 counted as "capability" |
| `.auto.v1` benchmark-law rows | 293 | generated per-law rows (`canonical/runtime/livebench_*.py.auto.v1`, …); **0 of them SWE-prefixed**; they answer no request |
| real rows | **147** | what can actually be invoked |
| rows the typed family resolver can ever return | **84** | it filters on `_FAMILY_SWE_PREFIXES = (python., code., software., test., orchestration.verify., git.)` — a row like `yaml.to_json.yq`, `evidence.oracle.hypothesis_property.v1` or `json.file.write` is **structurally unreachable** by that route |

**P0. A registry count is not a capability count.** Any statement of the form "the brain
has N capabilities" is inflated 3× by law rows and 5× against what a software request can
reach. The number that means something is 84, and 43 of those cannot start.

---

## §3 The hardcore lattice: what exists, what can start, what serves

Row counts from the registry; "served" from the 49-request census. A domain marked
*chain-bound* has rows but no row that can be a first step.

| # | hardcore domain | rows | can start | served today | the blocker |
|---|---|---|---|---|---|
| 1 | C/C++/Rust/Go/Java/TS editing | 8 rows mention a language; **0 write one** | parse only | 0/7 | no edit synthesis for non-Python (§4 P5) |
| 2 | build systems (pyproject/Makefile/CMake) | 0 real | – | 0/5 | no row; `g++`/`make` present, unusable without one |
| 3 | CI / workflow YAML | 3 | 0 | 0/4 | `yaml.to_json.yq` parses YAML, nothing edits it |
| 4 | profiling / hot path | 1 (`diff_perf_gate`, a diff gate) | 1 | 0/4 | no profiler row; `cProfile` stdlib unused; `py-spy` absent |
| 5 | benchmarks / perf regression | 2 | 2 | 0/4 | `git.history.bisect_regression` magnet answers instead |
| 6 | concurrency / race / lock / GIL | 3 (all indirect) | 0 | 0/3 | `crossfile.choreograph` claims "race condition" and is a repair mutator |
| 7 | memory / leaks | 0 real | – | 0/3 | no row |
| 8 | test authoring (unit/regression) | 4 | 2 | 0/6 | `generate.scaffold` exists, magnet takes the sentence |
| 9 | property / fuzz testing | 2 | 2 | 0/6 | `hypothesis` absent; `pynguin` row exists but chain-bound |
| 10 | mutation testing | 7 | 1 (`mutation_score`) | 0/6 | `mutation_kill` is chain-bound on `source.file.available` + survivor set; token `mutation` matches **two** rows so the family is always ambiguous (§4 P4) |
| 11 | coverage | 5 | 2 | 0/6 | gates only review a supplied diff |
| 12 | fault localisation / debugging | 3 | 0 | 0/3 | `python.fault.localize.dynamic.dataflow.v1` chain-bound on `test.corpus.available` |
| 13 | tracing / breakpoints | 0 | – | 0/3 | `gdb`/`lldb` absent |
| 14 | git surgery (rebase/cherry-pick/bisect/worktree) | 4 | 2 | 0/5 | `git.repository.operate` selected twice and refused `NO_OBSERVED_EFFECT` on read-only ops (§4 P6) |
| 15 | packaging / release / versioning | **0** SWE rows | – | – | no row at all |
| 16 | dependency management / vendoring / pinning | 3 (none a dependency tool) | 0 | 0/5 | no row |
| 17 | static analysis / lint | 2 | 2 | 0/3 | `ruff` absent; `Triage` gates need a diff |
| 18 | type checking | 3 | 1 | 0/3 | `mypy` absent; `diff_type_gate` needs a diff |
| 19 | refactor at scale (move/split/rename-across-repo) | 12 | 8 | 0/6 | `move_function` exists and does not bind "move the function add from A into B" (§4 P3) |
| 20 | API / ABI design, ADR | 0 real | – | 0/3 | no row; `secret_scan` answers it (**wrong answer served**) |
| 21 | security review | 7 | 5 | 0/3 | gates need a diff; `secret_scan` claims the sentence |
| 22 | data / schema / SQL migration | 1 (keyword noise) | 0 | 0/7 incl. SQL | `sqlite3` module present; no migration row |
| 23 | distributed / service / RPC | **0** | – | – | no row |
| 24 | observability / logging / metrics | **0** | – | – | no row |
| 25 | docs / docstrings / changelog | 0 real | – | 0/5 | no row |
| 26 | end-to-end PR (issue → patch → land) | 5 | 1 (`pr_realize`) | 0/49 | `issue_to_pr.orchestrate` is chain-bound and its predecessors are chain-bound |

**P1. Of 26 hardcore domains, 7 have no row at all and 12 more have rows that cannot be a
first step.** The empty seven are not oversights in the registry writer; they are domains
the tree never attempted.

---

## §4 The defect classes, ranked by how many measured requests they move

Ranks are ordered by *requests moved per unit of work*, measured where measurement was
possible and marked `est.` where it is not.

### P2 — No artifact-producing step, so 43 of 84 rows can never start (est. 20+ requests)
Advanced work is composite by nature: index → impact → patch → verify; mutation score →
kill survivors; localise → repair → accept → land. The registry already declares the graph
(`requires` names another row's `provides`) and `live_brain_route_admission_v1` already has
a composer (`_try_composed`) — **but composition only runs after a raw-goal compilation
failure, and a decisive typed plan explicitly forbids it.** Every chain row therefore
refuses with `ROUTE_ADMISSION_REJECTED` or `NO_DECISIVE_TYPED_PLAN` even when its
predecessor could be produced from the same sentence in one more step.
*Mechanism that fixes it:* walk the `requires ∩ provides` closure from the admitted row and
execute the producers in dependency order; the artifacts (`index_path`, `selection_path`,
`output_path`) are already files, already hash-verified, already content-addressed.
*Ceiling:* wiring every *standalone* row perfectly caps advanced work at 41 rows. The other
43 need this, so this is the only lever that reaches repair, verification and landing.

### P3 — Derivation holes: a row exists, the sentence cannot fill its slots (est. 6 requests)
Measured: `python.refactor.move_function.v1` returns `NO_DECISIVE_TYPED_PLAN` for "Move the
function add from `pkg/mod.py` into `pkg/calc.py` and update every caller" — the file pair
is stated and unproudced. `extract_function` refuses `REGION_INVALID` for "the loop in the
function total" (a stated region, no span). `rename_symbol` refuses
`ROUTE_ADMISSION_REJECTED` for "…across the repository" (a stated scope). `mutation_kill`
cannot fill `max_mutants`/`time_budget_s` because the row declares no default.
*Mechanism:* `declared_input_derivation_v1` already has one rule per slot shape
(`PATH_DIR_FROM_STATED_FILE_PARENT`, …); these are six new rules in the same table, and
`_execution_template` already knows how to drop adapter-defaulted slots.

### P4 — Sibling rows share an effect token, so the family is always ambiguous (est. 3 requests)
The mutation family's token is `mutation`; `python.tests.mutation_score.v1` **and**
`python.tests.advance.mutation_kill.v1` both contain it, so `_resolve_family` returns
ambiguous and the door falls back to the lexical route, which picks `mutation_score` — the
row that *measures* mutation strength — for "increase the mutation score … by adding
tests". The git family's token is `git`, which `git.history.bisect_regression.v1` also
contains, so the family can never be decisive and all five git probes fall to bisect.
*Mechanism:* the token is a discriminator by design; give each family a token that names
the effect, not the topic (`mutation_kill`, `repository.operate`). Measured caveat: doing
this alone moved the census **2/49 → 2/49** — because P3 blocks the row that would then
win. P4 is a prerequisite for P3, not a lever by itself.

### P5 — The substrate is multilingual; the editor is not (est. 7 requests, axis 0/7)
Measured, not assumed: `code.index.tree_sitter.incremental.v1` indexes
**python, java, typescript, rust, cpp, go and yaml — 11 files, 22 definitions, 69
references, 0 syntax errors, 71 ms**, against the pinned `tree_sitter 0.20.4` +
`tree_sitter_languages 1.10.2` wheel closure that the registry already verifies.
`code.patch.tree_sitter.verify.v1` already applies exact node patches and re-runs the test
oracle in any of those languages. **What does not exist is a row that produces the edit**
for anything but Python: of 84 SWE rows, zero write a non-Python file.
*Mechanism:* the patch verifier takes `edits` as data; one edit-synthesis step over the
existing index (byte spans, node types, collision refusal already implemented for Python)
turns six dead languages into six reachable ones. This is the single highest-value *new*
work and it is small because the hard part — parse, index, reference, verify — is done.

### P6 — A read-only operation is refused for "no observed effect" (2 requests)
`git.repository.operate.v1` was selected for probe 45 ("cherry-pick … onto a new branch")
and 46 ("write the changelog for the last three commits") and refused
`FAIL_CLOSED__NO_OBSERVED_EFFECT`. A diff or a changelog *has no filesystem side effect to
observe*; its effect is its returned output. The effect-observation rule is written for
mutators and applied to readers.
*Mechanism:* the row's `action_template.expect` — a reader can declare
`output_verified`/`stdout_nonempty`; the gate already honours declared expectations.

### P7 — Five magnet rows absorb 24 of 49 selections and then refuse their own inputs
`python.source.dead_code.v1` ×6, `git.history.bisect_regression.v1` ×6,
`python.tests.mutation_score.v1` ×4, `software.repair.choreograph.crossfile.v1` ×4,
`python.refactor.inline_helper.v1` ×4. `software.repair.choreograph.crossfile.v1` alone
declares 40+ keywords — `race`, `concurrency`, `thread`, `unused`, `deprecated`, `sql
injection`, `query`, `conflict`, `resolve`, `fix the code`, `are failing` — so it is a
universal magnet **by construction**: it will claim "find the race condition", "review for
SQL injection" and "optimise the query", then refuse because it is a mutator asked a
question.
*Mechanism:* the analysis-only guard (`_ANALYSIS_ONLY_TRIGGERS`) and the family/question
split already exist; magnets need the same rule at the lexical layer, where they are
currently chosen.

### P8 — A served answer can be an unrelated row, and nothing checks (1 confirmed false answer)
Probe 39: "Review `pkg/service.py` for API design problems" → `python.source.secret_scan.v1`
→ `PASS`. The census prints the row, which is how it was caught; no gate compares the row's
declared `provides` with the effect the sentence states.
*Mechanism:* `implementation_effect_error` already compares a stated implementation effect
to declared contracts; the same comparison belongs on every served answer.

### P9 — 29 adapters on disk have no registry row
Among them `python_source_tree_codec.py`, `python_test_corpus_discovery_v1.py`,
`brain_module_invoke_runner_v1.py`, `concrete_execution_oracle.py`,
`grounded_executable_composition.py`. Code exists that no sentence can reach and no
inventory counts.

### P10 — 7 hardcore domains have no row and no substrate on this machine
`rustc`, `cargo`, `go`, `javac`, `clang`, `cmake`, `gdb`, `lldb`, `py-spy`, `scalene`,
`hyperfine`, `yq`, `pytest`, `hypothesis`, `ruff`, `mypy`, `bandit` and `coverage` are all
absent. Rust/Go/Java probing, profiling, benchmarking, lint and type-check lanes **cannot
be measured here at all** — the toolchain lane in the matrix (1/7) is unmeasurable, not
failing. Wiring cannot fix this; installing a toolchain can, and any claim about those
lanes made on this machine is unfounded.

### P11 — The tree's own test suite is red (11,754 cases, 380 failed, 0 errors, 223 files)
From `canonical/verification/HONEST_SUITE_BASELINE_20261017_V1.json` (`authority: NONE`,
subject `370005ad`). A capability claim that cannot run its own suite is a claim about a
snapshot.

### P12 — Repeated derivation is not cached
Each request re-derives the same slots for the same paths. Measured median 142 ms on the
ordinary matrix; the census's slowest request is 1768 ms. Cheap to fix by memoising on
`(sentence-shape, path-hashes)` — the tree-sitter index already does exactly this for its
own artifact (`row_sha256` reuse, `incremental`).

---

## §5 Corrections to V12 (this document's predecessor)

1. **RETRACTED: "the five magnets are one `_FAMILIES` edit."** Measured in memory, twice:
   adding the 14 proposed triples moves the census **2/49 → 2/49**. Families select; they
   do not derive, and they do not compose. The magnet defect is real (§4 P7) but it is a
   *honesty* fix (wrong refusals become correct refusals), not a capability fix.
2. **RETRACTED: "whole domains have zero rows of 440."** The denominator was inflated: 293
   of the 440 are `.auto.v1` law rows. The SWE surface is 84 rows, and the correct statement
   is "43 of 84 cannot start, 7 of 26 hardcore domains have no row".
3. **CORRECTED: "C/C++/Rust/Go/Java have no substrate."** They have a complete read
   substrate — parse, incremental index, symbols, references, impact, patch verification —
   measuring 71 ms for 7 languages with zero syntax errors. They have no *writer*.
4. **ADDED: composition is the missing organ, not analysis.** V12 ranked analysis/derivation
   first. The `requires ∩ provides` measurement (43 of 84) says the organ to build is the
   chain runner.
5. **ADDED: the sandbox toolchain floor.** Prior censuses implied a failing lint/profile
   capability; the tools are simply not installed.

---

## §6 Order of work (fastest path to advanced capability)

| # | work | reaches | why first |
|---|---|---|---|
| 1 | **chain runner**: from an admitted row, walk `requires ∩ provides` and execute the producers | 43 rows, all repair/verify/land | it is the only lever that reaches the capability class the question is about; the graph and the artifacts already exist |
| 2 | **effect-named tokens** (`mutation_kill`, `repository.operate`) + the six derivation rules | 9 requests, and P3 unblocks P4 | one-line change per family, one rule per slot shape |
| 3 | **read-only effect declaration** on `git.repository.operate` | 2 requests | the row already declares `expect`; it is wrong for readers |
| 4 | **magnet containment** at the lexical layer | 24 selections → honest refusals | stops a mutator answering questions; no new capability |
| 5 | **non-Python edit synthesis** over the existing index | 7 requests, 6 languages | the substrate is measured working; only the writer is missing |
| 6 | **effect-faithfulness on every served answer** | 1 confirmed false answer, and the class | reuses `implementation_effect_error` |
| 7 | registry rows for: profiling (`cProfile`), dependency/pin/vendor, packaging, CI-YAML edit | 4 domains | the last four that are buildable here without a new toolchain |
| 8 | test-authoring rows (`scaffold`, `pynguin`) wired through the chain runner | 6 requests | they exist and are chain-bound on `source.file.available` |

Do **not** rebuild: the verified command runner, the tree-sitter index and patch verifier,
the AST editor with collision refusal, the typed selector, `declared_input_derivation_v1`,
`requires/provides`, or the acceptance chain. All six are measured working in this document.

---

## §7 Reproduction

```bash
python3 execution_guard/swe_capability_matrix_v1.py          # 17 REAL / 0 FALSE / 0 DAMAGED, 142 ms median
python3 execution_guard/swe_advanced_probe_v1.py --json /tmp/census.json   # 2 served / 47 refused
python3 - <<'PY'   # the denominator and the chain split
import sys; sys.path.insert(0,'.')
from canonical.runtime.live_brain_route_admission_v1 import load_verified_registry
from canonical.runtime.swe_typed_plan_v1 import _FAMILY_SWE_PREFIXES
reg = load_verified_registry()
real = {c:e for c,e in reg.items() if not c.endswith('.auto.v1')}
swe  = {c:e for c,e in real.items() if c.startswith(_FAMILY_SWE_PREFIXES)}
prov = {p for e in real.values() for p in (e.get('provides') or [])}
chain = [c for c,e in swe.items() if set(map(str,e.get('requires') or [])) & prov]
print(len(reg), len(real), len(swe), "chain:", len(chain), "standalone:", len(swe)-len(chain))
PY
```

Authority: NONE. A single-machine census is a finding, not a verification.
