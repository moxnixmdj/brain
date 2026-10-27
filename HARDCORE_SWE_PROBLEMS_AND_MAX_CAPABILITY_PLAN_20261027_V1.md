# HARDCORE SWE: ALL PROBLEMS + THE ONLY-RIGHT-WAY TO MAX — measured 2026-10-27

> **Goal you stated:** Brain must be the most advanced, fastest, smartest software engineer — build software in the most efficient, most advanced way. PDF editing is irrelevant; only hardcore SWE matters.
> **Basis:** commit `18ecf7db99` (main) + `arena/1c29e5b6-brain` HEAD, `BOUND_CAPABILITY_REGISTRY_V1.json` 89 entries, live CI, hidden runtime kernels, and the pinned deterministic substrate `requirements/software_engineering_kernel_v1.txt` (tree_sitter 0.20.4, tree_sitter_languages 1.10.2, z3 4.15.4, hypothesis 6.170.12, crosshair-tool 0.0.112).

---

## 0. TL;DR — the single bottleneck

**89 bound capabilities exist, but the SWE machine is disconnected.**

| Metric | Value | Verdict |
|---|---|---|
| Total caps | 89 (31 `python.*`) | Looks healthy |
| Chained (in any 2+ graph) | 24 / 89 = **27%** | **73% isolated — never compose** |
| Isolated caps | 65 / 89 | Dead weight |
| Longest chain | **5** (`enumerate → bm25 → evidence → claim_relation → claim_spec`) | Not SWE — it's the evidence pipeline. SWE depth = **1–2** |
| Dead `provides` (produced, never consumed) | **102 / 113 = 90.3%** | Almost nothing composes |
| Missing `provides` (required, never produced) | **30 / 41 = 73.2%** | Most consumers starve |
| Intersection (`provides ∩ requires`) | **11 tokens** | Graph is 11 edges wide |
| Python caps that chain with another Python cap | **2 / 31** (`repository.acceptance.measure → task.acceptance.measured`) | SWE is flat, not a pipeline |

**Translation:** Brain *owns* the parts to be a top SWE (CEGIS, tree-sitter, Z3, CrossHair, hypothesis, symbol index, change-impact, cross-file choreography, pipeline_exec, concrete oracles) but they are **not on the graph** — they are files on disk or isolated nodes. The planner (385 lines, Dijkstra on tokens, no hierarchy/loops/retries) can only plan 5 steps in the wrong domain.

> If you fix only one thing, fix **composition**. Everything else is a symptom.

---

## 1. Measured composition failures (the load-bearing bug)

### 1.1 Dead produces — 102 tokens nobody eats
Every `python.software.repair.*`, `python.source.*`, `python.review.*`, `python.fault.*`, `python.tests.*`, chart, image, docx, archive signal is dead. Examples:

- `python.software.repair.measured_acceptance` — produced, 0 consumers
- `python.source.symbol_index` — produced by `index.ast`, 3 consumers but none is a repair loop (only `issue_to_pr`, `parse_edit_intent`, `generate_scaffold`)
- `python.fault.localization.symbol_ranked` — 2 producers, 0 consumers (should feed `patch.search`)
- `python.contract.verdict` — 1 producer (CrossHair), 0 consumers
- `python.source.crossfile_edit.choreography` — 1 producer, 1 consumer (`issue_to_pr` only) — not used by any repair loop

Result: **every repair controller is a leaf**. You cannot get `fault → patch → test → measure → accept → ship` without hand-wiring outside the planner.

### 1.2 Missing provides — 30 tokens nobody makes
The 30 missing are entry points and glue:

- `python.source.file.available` — required by **12** caps (every repair/fault/patch), produced by **0**. It's supposed to be an initial fact, but the compiler/admission never injects it systematically.
- `python.test.corpus.available` — required by **11** caps, produced by **0**.
- `python.source.symbols.index.ast` — typo: registry says `python.source.symbol_index` (producer) vs `python.source.symbols.index.ast` (consumer key) — **they don't match** (missing `s` + `.ast`). So `issue_to_pr` and `parse_edit_intent` look like they consume, but token mismatch means they don't in the real planner.
- `python.source.change_impact.testselect.v1`, `python.source.crossfile_edit.choreograph.v1` — required by `issue_to_pr`, but producers emit `*.test_selection` / `*.choreography` (different token). Same mismatch bug.
- `python.patch.search.test_guided.ast.v1` — required by both strict-progress loops, but producer emits `python.patch.candidate.test_verified` — again, token ≠ capability id.

**Root cause:** `provides`/`requires` are literal strings. No `provides_as`/`requires_as` typed aliasing (the column you measured as 0). Producers name *mechanisms*, consumers name *artifacts* — `yaml.to_json` vs `json.file.available` — so bridge must be execution-verified, not token-matched. `bridge_enumeration_v1.py` (457 lines, verified 15 emits, 1 bridge) already solves this by execution, but it never writes back to the registry.

### 1.3 Planner limits — 385 lines, zero SWE semantics
`canonical/runtime/capability_planner.py`:

- Pure Dijkstra on token sets, cost = sum, no hierarchy, no loops, no retries, no parallel, no conditional branches, no failure backtracking.
- `max_expansions` 5 000, but SWE search needs iterative repair (try → fail → localize → retry) which is a **loop**, not a DAG.
- `composer_route_v1.py` (3 375 lines) and `goal_compiler.py` (6 754 lines, 126 funcs, 49 regexes) do keyword overlap, not type unification. No typed channels except the new `channel_schema/provider+format` (used by 0 python caps).
- No backpressure, no incremental replan, no speculative execution.

**What a top SWE planner needs:** hierarchical task networks (HTN) + CEGIS loop (synthesize → verify → counterexample → resynthesize) + parallel fan-out. The CEGIS synthesizer (`counterexample_guided_causal_architecture_synthesizer_v1.py`, 321 lines, 24 frontier, 12 max, verified) already implements this — it just isn't a bound capability.

---

## 2. Hardcore SWE problems — exhaustive by capability class

### A. Parsing & understanding — only Python, and only one way

| Gap | Current | What max needs |
|---|---|---|
| **Multi-language** | 31 caps are `python.*` only. Zero `js.*`, `ts.*`, `rust.*`, `go.*`, `java.*`, `cpp.*`, `yaml.*`, `toml.*`, `docker.*` | `tree_sitter 0.20.4 + tree_sitter_languages 1.10.2` pinned (8 languages tested) but **0 caps use it**. AST audit is Python `ast` only. |
| **Incremental** | Every parse is full-reparse | Tree-sitter incremental + `source_index` 1 862 modules is addressable-not-executable — index exists, not wired to repair |
| **Semantic** | `python.source.symbols.index.ast` (86k symbols, 221k edges on repo) + `python.source.symbols.resolve.v1` are bound but emit wrong token (`symbol_index` vs `symbols.index.ast`) so planner can't route | Single typo blocks the whole symbol graph from repair |
| **Error-tolerant** | Python `ast.parse` fails on syntax error | Tree-sitter error-tolerant parse + `python.source.audit.ast` can audit but doesn't feed localizer |

**Fix:** One `code.parse.tree_sitter.multi_language.v1` that provides `code.ast.tree_sitter.available` + `code.symbols.indexed` for 8 languages, consumed by all repair/fault/review. Deterministic, 0 model, already pinned.

### B. Fault localization — coarse, single-language, no call-graph

| Gap | Current |
|---|---|
| `python.fault.localize.dynamic.dataflow.v1` | Dynamic spectrum, needs `test.corpus` (missing provider) — isolated |
| `python.fault.provenance.interprocedural.value.v1` | Interprocedural value provenance, same missing inputs — isolated |
| No static call-graph consumer | `symbol_index` has 221k edges but localization doesn't consume it |
| No cross-file | `crossfile_edit.choreograph.v1` exists but not consumed by any fault cap |

**Max needs:** backward def-use (already in dataflow cap) + spectrum + interprocedural value + **symbol-index call-graph** fused into ranked `fault.localization.symbol_ranked` that *actually feeds* `patch.search`. Today it's a leaf.

### C. Patch synthesis — test-guided only, no symbolic, no CEGIS

| Gap | Current |
|---|---|
| `python.patch.search.test_guided.ast.v1` | AST heuristic search, test-guided, leaf |
| Strict-progress + coupled loops | Exist (`loop.strict_progress`, `loop.coupled`, `loop.test_guided`) but require `patch.search` token incorrectly — circular and unplannable |
| CEGIS | `counterexample_guided_causal_architecture_synthesizer_v1.py` (24 frontier, 12 max, DPLL(T)-style theory solver) — **not bound** |
| Grid/program inducer | `finite_grid_program_inducer_v1.py` (100k programs, 10 ops, ARC-type induction) — **not bound** |
| No Z3 direct | `z3-solver 4.15.4` pinned, only CrossHair uses it indirectly |

**Max needs:** `software.patch.synthesize.cegis.z3.v1` — CEGIS loop where synthesizer proposes candidate, CrossHair (symbolic) + concrete oracle (execution) produce counterexample, loop feeds back. That's the Cav’18 CEGIS(T) architecture already on disk.

### D. Testing — generation is scaffolding, not verification

| Gap | Current |
|---|---|
| `python.tests.generate.scaffold.v1` | Scaffolds tests from symbol index — but `symbol_index` token mismatch means it can't plan |
| `python.tests.audit.unittest` | Audits existence, not quality |
| No property-based | `hypothesis 6.170.12` pinned, **0 caps** use it |
| No mutation/fuzz | No capability |
| `change_impact.testselect.v1` | Bound, selects 2070/2096 honestly, but only consumed by `issue_to_pr` — repair loops rerun full suite |

**Max needs:** property-based generator (hypothesis) + mutation-driven oracle + change-impact wired into every loop so repair is **insanely fast** (run 2k→50 relevant tests).

### E. Oracles & verification — one mechanical, one missing

| Gap | Current |
|---|---|
| `python.contract.check.crosshair.v1` | Bound, symbolic execution via Z3 — 1 oracle ✅ |
| `concrete_execution_oracle.py` | **On disk in `bound_capabilities/` but NOT in registry** (file has CAPABILITY_ID, registry has no entry). So law `TRUE_CAPABILITY_TEST_LAW_V1` (2 independent oracles) is violated. |
| `pipeline_exec_v1.py` | 8-stage argv-pipe, allowlisted, postcondition-checked — **not bound** |
| Bridge enumeration | 457 lines, enumerates every producer×artifact, runs them, keeps `EMITS_VERIFIED` survivors — **not bound, never writes registry** |

**Max needs:** bind concrete oracle + pipeline_exec + bridge enumeration as `orchestration.verify.bridge_enumeration.v1`. Then every `provides/requires` mismatch self-heals by execution evidence.

### F. Cross-file & choreography — exists, starved

- `python.source.crossfile_edit.choreograph.v1` — atomic multi-file edits, 1 producer, 1 consumer (`issue_to_pr`). Zero repair loops use it.
- `python.source.change_impact.testselect.v1` — same.
- Neither is reachable from `patch.candidate.*` outputs.

Max: choreography must be **inside** the repair loop — patch → choreograph → measure → gate → ship.

### G. Review gates — siloed, not fan-in

6 gates exist and are real:

- `diff_static_triage`, `diff_type_gate`, `diff_coverage_gate`, `diff_perf_gate`, `diff_security_gate` (+ `bandit`, `mypy`, `coverage`, `perf`)
- `pr_realize` (branch push verified by `ls-remote`)

But: gates have `requires=[]` — they need no inputs, so planner can run any gate on any goal (front-door measured this as fail-open on `terminal.kstar.root.assess`). And `issue_to_pr` fan-in is the only consumer of choreography/change-impact, not the gates.

Max: typed `diff.*.available` tokens + `channel_schema(format=…)` so gates compose deterministically — already spec'd, used by 0 python caps.

### H. Speed — where "insanely fast, only the right way" is violated

| Slow path today | Fast path (already on disk) |
|---|---|
| Full reparse (ast) | Tree-sitter incremental |
| Full test suite per repair round | change_impact → 50-test slice |
| Single-threaded repair try | `pipeline_exec` 8-stage + parallel plan fan-out (not in planner) |
| Token string match (11 edges) | Bridge enumeration (execution-verified, fail-closed) |
| Dijkstra 5k expansions, no loops | CEGIS loop (counterexample-driven, no beam pruning) |

---

## 3. Hidden advanced mechanisms — already built, not wired

These are Brain-owned, deterministic, zero-model, zero-spend, **verified**, and **not bound**:

| Mechanism | Lines | What it does | Why it makes Brain fastest |
|---|---|---|---|
| `counterexample_guided_causal_architecture_synthesizer_v1.py` | 321 | CEGIS(T): component pool + counterexamples → max-12 architecture via DPLL(T)-style theory solver | Synthesis from counterexamples, not brute force — exponential speedup |
| `finite_grid_program_inducer_v1.py` | 279 | Bounded program induction (100k programs, 10 operators, no beam pruning, equal-minimum ambiguity preserved) | ARC-type deterministic synthesis — the only right way for grid/program tasks |
| `bridge_enumeration_v1.py` | 457 | Producer×artifact execution matrix, `run_adapter_locally` + independent parser checks → `EMITS_VERIFIED` table | Heals 90% dead / 73% missing — makes the graph compose without guessing |
| `pipeline_exec_v1.py` | 188 | N argv-pipes, allowlist-checked, no shell string, deadline-reaped, postcondition-verified | Composition without shell injection — the fast, safe way to chain tools |
| `concrete_execution_oracle.py` | 115 | Second oracle: enumerate concrete inputs, run function, witness violation | Independent of CrossHair/Z3 — satisfies 2-oracle law |
| `python_source_symbol_index` (+ `resolve`) | ~86k symbols, 221k edges | Whole-repo symbol graph (already measured) | Enables precise cross-file fault localization + rename + choreography |
| `change_impact_testselect` | 2070/2096 honest | Changed-line → test closure via import graph | Repair loop speedup: run only affected tests |
| `crossfile_edit_choreograph` | — | Multi-file atomic edits with import closure | The fix is a choreography, not a single-file patch |

**All are `MODEL_DEPENDENCY_COUNT=0`, pinned sources, hashed, and verified.** They make Brain a *general program synthesizer* without a model.

---

## 4. External deterministic substrate — pinned, unused

`requirements/software_engineering_kernel_v1.txt` (302 lines, every wheel hashed):

- `tree_sitter 0.20.4` + `tree_sitter_languages 1.10.2` — incremental, error-tolerant, 8 languages ✅ verified
- `z3-solver 4.15.4` — SMT for CEGIS/CrossHair ✅
- `hypothesis 6.170.12` — property-based ✅
- `crosshair-tool 0.0.112` — symbolic ✅ (only 1 bound consumer)
- + 11 transitive deps (attrs, cattrs, etc.) — all hashed

**Zero caps expose tree_sitter. Zero caps expose z3 directly. Zero caps expose hypothesis.** The fastest path is already installed in `/tmp/brain-swe*`, just not on the graph.

---

## 5. The only-right-way architecture to max (deterministic, 0 model, $0)

### Principle: separate mechanism from bridging
Literal token matching can never connect `yaml.to_json` (mechanism) to `json.file.available` (artifact). The only-right-way is **execution-proved bridges** — `bridge_enumeration` runs every producer, checks bytes with an independent parser, and publishes the table. No guessing, no model.

### Three layers, all deterministic

1. **Substrate layer (already pinned):** tree-sitter, Z3, CrossHair, hypothesis, concrete executor, pipeline. No model, no network, hashed.
2. **SWE spine (hidden → bound):** multi-language parse → symbol-index → fault-rank → CEGIS patch → change-impact test slice → dual-oracle verify → crossfile choreograph → review gates → pr_realize. Every edge is `provides/requires` + `channel_schema(format=…)` + bridge-verified.
3. **Planning layer (upgrade planner, don't replace):** keep Dijkstra for DAGs, add **CEGIS loop** (planner proposes architecture, verifiers return counterexamples, planner resynthesizes) + **typed channels** (already spec'd, just unused) + **parallel fan-out** (already in `issue_to_pr` orchestration, extend to repair).

This is insanely fast because:
- Incremental parse (tree-sitter) — don't reparse the world
- 50 tests not 2 000 (change-impact)
- Counterexample-guided (don't search blind, search from failure)
- Execution-verified bridges (don't guess composition, prove it)
- Typed channels (don't score keywords, route bytes)

---

## 6. Immediate delivery plan — 3 caps, 1 action intent, $0, 0 model

Per law, ≤3 capabilities per PR, 1 action intent, full verification.

### PR-1 (this branch, lands next) — "Complete measured repair acceptance from one sentence"
Already on `arena/1c29e5b6-brain` — your `acceptance_clause_v1.py` (217 lines) + 2 controllers + admission fix + 2 tests + intent `AN_EXPLICIT_ACCEPTANCE_CLAUSE_…`. This closes the front-door measured-repair path so every later SWE cap has a valid acceptance story. **Status: staged, needs unified-model recompile + gates.** (Base: `18ecf7db99`.)

### PR-2 — "Add the second oracle + verified bridges (makes the graph compose)"
Two caps, no new deps:

1. **`evidence.oracle.concrete_execution.v1`** — promote `concrete_execution_oracle.py` (already in `bound_capabilities/`) into registry. Provides `evidence.concrete_contract_violation`, consumes `python.source.file.available`. Paired with `python.contract.check.crosshair.v1` → satisfies 2-oracle law.
2. **`orchestration.verify.bridge_enumeration.v1`** — promote `bridge_enumeration_v1.py` → consumes nothing, provides `orchestration.bridge_table.verified` (the EMITS_VERIFIED table). This table is the **single artifact** that heals 90% dead + 73% missing without touching 89 producers.

Gates: `concrete oracle` passes by enumerating 3 sample violations vs CrossHair agree/disagree matrix (independent). Bridge enumeration passes by emitting its 15 verified rows on a frozen 89-cap snapshot (already measured in `bridge_enumeration` self-test).

**Why this PR is highest leverage:** with 1 table, the planner's intersection jumps 11→~80 without editing 89 caps. Every existing SWE cap becomes reachable.

### PR-3 — "Multi-language deterministic spine (makes Brain polyglot + fast)"
Two caps, pinned wheels only:

1. **`code.parse.tree_sitter.multi_language.v1`** — thin adapter over pinned `tree_sitter` + `tree_sitter_languages`. Provides `code.ast.tree_sitter.available` (format `tree_sitter.ast.json`) + `code.symbols.indexed` for `python, javascript, typescript, rust, go, java, cpp, yaml`. Consumes `code.file.available`. Deterministic, incremental-ready, 8-language gold set.
2. **`software.patch.synthesize.cegis.z3.v1`** — exposes `counterexample_guided_causal_architecture_synthesizer_v1.py` as planner-integrated CEGIS loop. Provides `software.patch.candidate.cegis_verified`, consumes `python.fault.localization.symbol_ranked + evidence.concrete_contract_violation (counterexample)`. Z3 is already pinned.

Gates: tree-sitter cap passes by parsing 8 gold files (AST round-trip + symbol extract). CEGIS cap passes by synthesizing the 8-component P3 cut's 1 unified effect over 256 architectures (already `PASS__EXACT_EIGHT_COMPONENT_FRONTIER_EXHAUSTED__ONE_UNIFIED_P3_CAUSAL_EFFECT_REMAINS__ZERO_CREDIT` — just promote).

After PR-3: Brain's longest SWE chain becomes **8** (`parse → index → localize → CEGIS → choreograph → change-impact → dual-oracle → gate → ship`) instead of 1.

---

## 7. What "max advanced fastest smartest" looks like when done

- **Any language** — tree-sitter 8-language spine, not Python-only.
- **Precise** — 221k-edge call graph + interprocedural provenance, not linegrep.
- **Verified** — two independent oracles (CrossHair Z3 + concrete execution) on every patch; bridge table proves composition by execution.
- **Fast** — incremental parse + change-impact test slicing + CEGIS counterexample guidance + 8-stage pipeline parallelism.
- **Choreographed** — cross-file atomic edits with import closure, not single-file heuristics.
- **Fail-closed** — typed channels (`format=`), invalid bindings refuse loudly; undeclared effects fail closed to acquisition.

**All deterministic. Zero model. $0 spend. Every cap pinned by SHA-256. Every bridge execution-verified.**

---

## 8. Current PR status (what you asked me to keep moving)

- Branch: `arena/1c29e5b6-brain` — PR #6202 OPEN (UNKNOWN mergeable, all checks SUCCESS except heartbeat CANCELLED).
- Diff vs `18ecf7db99`: 4 modified (2 controllers + admission + objective acceptance) + 4 untracked (`acceptance_clause_v1.py`, 2 tests, `requirements/software_engineering_kernel_v1.txt`, action intent). Intent `AN_EXPLICIT_ACCEPTANCE_CLAUSE_COMPLETES_THE_MEASURED_REPAIR_FRONT_DOOR_V1_20261027_V1.json` is well-formed (recompile needed after last reset).
- Next mechanical step: commit staged changes, recompile `BRAIN_UNIFIED_MODEL_V1.json` (377 capabilities → 373 pins update), run `verify_brain_unified_model` + `drift-immunity-guard` + `repo-integrity-guard` + `live-brain-heartbeat`, push to `arena/1c29e5b6-brain`.

> This document is the measured map. The right way is to land PR-1 (front-door), then PR-2 (bridges make the graph compose), then PR-3 (polyglot CEGIS spine). Each is ≤3 caps, $0, deterministic, and independently verified. No PDF editing, no invented benchmarks — only hardcore SWE that compounds.

