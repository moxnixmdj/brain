# Hardcore-SWE problem map — measured 2026-10-28 on `main` c4128ca

Authority: **NONE**. This is a measurement, not an independent verification.
Producer: `arena/bf97adf2-brain` sandbox. Model dependency: 0. Incremental spend: $0.
Focus: advanced software-engineering capability only. PDF/DOCX/XLSX/codec/chart
capabilities are deliberately out of scope except where they are the *wrong-domain*
destination of a SWE request.

Prior work landed (so this map is current, not stale): PR #6287 wired the decisive
typed selector into `live_brain_route_admission_v1.solve` as a scoped, ambiguity-
preserving retry; #6299 fixed the resulting false-PASS with an E30 effect-consistency
gate and normalized the refactor `module` path; #6300 recorded it. All three merged
with the signed referee green. The measurements below are AFTER that work.

---

## The one-line summary

From a fresh human sentence, the machine now solves **4 of 12** real SWE tasks and
reaches a SWE capability on **7 of 12** — but **none** of those capabilities carries
independent-oracle credit, the public-runner liveness proof is non-blocking and red,
and the composition graph that should let capabilities build on each other is dead.
Speed is ~400 ms/goal with a fake cost model. Those are the hardcore problems.

---

## P0 — blocking "most advanced SWE engineer"

### P0-1. Human-sentence routing still fails 5/12, and two failures are wrong-domain
Measured `solve()` on 12 fresh human SWE sentences (clean tree each):

| task | verdict | reached |
|---|---|---|
| repair_full, fix_broken, bug_report, rename_param | **PASS** | correct SWE cap (2 via typed retry) |
| fix_short | FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN | — |
| rename_callsites | FAIL_CLOSED__NAMED_SOURCE_UNPARSEABLE | symbol index |
| write_unit_test | FAIL__LIVE_CONTROLLER_EXECUTION | **`chart.raster.axis_title_unit_binding.v1`** |
| explain_fail | FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED | — |
| find_callers, refactor_extract | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED | semantic_behavior.compile |
| type_check, lint | FAIL__RAW_GOAL_COMPILATION_GAP | — |

`write_unit_test → chart.raster` is the same class as the old `pdf.extract.ocr for a
refactor`: a different domain chosen on one word. 8 of the 10 `INV_` task families
(caller-finding, test authoring, explain-failure, lint, typecheck, git commit,
debugger, patch extraction) still have no owned adapter reachable from a sentence.
This is the "45/52 SWE capabilities never measured from a sentence" gap, and it is a
capability gap, not a routing gap.

### P0-2. No SWE capability has independent-oracle credit
`TRUE_CAPABILITY_LEDGER_V1.json`: **9 specs, 0 SWE** (all DOCX/finance/scheduling).
22 registry adapters are <=34-line stubs that read the registry and write
`verified: true`. So every SWE "PASS" is self-reported by the producer it is judging.
Until `true_capability_harness_v1` runs fresh held-out instances with >=2 independent
oracles per SWE capability, no SWE row has credit — by the project's own law.

### P0-3. The public-runner liveness proof is non-blocking and red
- Ruleset `main-lock` required checks = **only `referee/repo-integrity-guard`**.
  `heartbeat` is NOT required.
- Last 10 `live-brain-heartbeat` runs: **every one failure or cancelled**.
- 5 of 37 families short: `PYTHON_TESTS_AUDIT 38/50`, `HTTP_JSON_FETCH 39/50`,
  `KNOWLEDGE_FETCH_ASSESS_ASSERT 15/50`, `CHART_RASTER_READERS 15/50`,
  `CODEC_BSON 0/50`. `OUT_OF_SCOPE_MUST_FAIL_CLOSED 100/100`.
- Workflow comment: the full suite is >40 min against a 40-min timeout; it persists
  a partial receipt but has never finished on the public runner. Making it required
  and sharding it are **owner-only** (protected path).

### P0-4. Reachability is measured on the wrong sentences
Reachability census: `411 REACHED_AND_BOUND / 2 NOT_REACHABLE / 3 ROUTED_ELSEWHERE /
3 REACHED_BY_EXPLICIT_NAME` of 419 — but every goal is generated *from the capability's
own name*. That is the ceiling, not the reality: the same machine reaches a SWE
capability on only 7/12 human sentences. The `398/405 "reached"` number in the
inventory hides the human-sentence gap (P0-2 there).

---

## P1 — capability depth (what "advanced" actually needs)

### P1-5. The composition graph is dead
187 distinct `provides`, **86 never consumed** by any `requires`. 41 rows declare
`requires=[]`. `orchestration.bridge_table.verified` has **0 consumers**;
`bridge_enumeration_v1` proves bridges by execution but its output never reaches
`capability_composer_v1.graph()`; `astra_runtime` implements `provides_as`/
`requires_as` aliases that nothing feeds. So "compose capabilities to build software"
is a claim, not a running mechanism. (Hidden fix: wire execution-proved bridges as
aliases — `COMPOSITION_LEVERAGE §9`: enumerate the candidate space, let execution be
the oracle.)

### P1-6. No solver-grade determinism at the type level
0 adapters import `z3`; `program_synthesis_v1` / `documentation_mining_v1` are not in
the admission path. Typed selection is deterministic but shallow (keywords + a small
E30 effect vocabulary), and `goal_compilation_benchmark_v1` still reports
`2 WRONG-CAPABILITY` (msgpack answering xlsx/sqlite). "Compiling is not selecting"
is still printed by the benchmark itself: 19/23 expected-first.

### P1-7. Fake cost model; resource-bounded law unenforced
`cost` is constant (`1`: 107 rows, `2`: 18). **0** registry rows carry timing or
bytes fields; 0 adapters expose them. So the system cannot prefer the fast/cheap
correct capability, cannot budget, and cannot honor the resource-bounded-bytes law.
Every "fastest" claim is unmeasured at the capability layer.

### P1-8. `channel_schema` on 0 SWE capabilities
7 caps have `channel_schema`; all 62 `python./code./software.` caps have none. No
typed streaming/composition channel for SWE effects.

---

## P2 — speed & consistency (the "insanely fast" requirement)

### P2-9. ~400 ms/goal and double work on failure
`fix_broken` / `bug_report` solve in 374–445 ms (mean 402 ms). The typed selector
alone is ~119 ms/goal. On a primary failure the retry re-enters the **entire** gate
chain (compile + execute + all honesty gates) a second time — correct but not fast.
No caching of the decisive typed plan across the two attempts.

### P2-10. A one-line doc edit forces a 9.4 MB model rebuild
`BRAIN_UNIFIED_MODEL_V1.json` hashes the whole tree (root `*.md`, all intents, all
runtime source). Any governance or documentation change invalidates
`ARTIFACT_INTEGRITY` and requires a full deterministic recompile. This coupling is a
real speed/consistency defect: it makes the fastest correct edit expensive.

### P2-11. Drift race + a partly-red test suite on pristine main
main advanced across 5 commits during the last session alone; every rebind of an
intent's `canonical_base_commit` and its `counterexample_receipts.git_blob_sha` goes
stale on the next fleet merge. Locally, 8 front-door/parity/consult tests fail on
**pristine** main (fleet drift from #6292's selection-rate change 23→21), and
`test_f29_a_request_that_names_nothing_fails_closed` still routes `"Run the thing."`
to `python.repository.acceptance.measure.v1` (the door does fail closed, but the
naming layer leaks). A "green" suite is not currently a trustworthy signal.

---

## P3 — governance / owner-only (agent cannot land these)

### P3-12. Protected paths
The guard, its test, the referee workflow, `frontier-state-consistency.yml`,
`CODEOWNERS`, the policy, `AGENTS.md`, the honest-baseline tool/document and the
landing script fail the referee if an agent changes them. Adding `heartbeat` to
required checks and closing the receipt/verifier blind spots require the owner to
relax the ruleset for one merge.

### P3-13. Pinned SWE kernel installed by no workflow
`requirements/software_engineering_kernel_v1.txt` exists; **0** workflows run
`pip install -r`. The heartbeat installs a generic apt/pip set instead. So the
toolchain the advanced SWE capabilities assume is not the toolchain CI measures.

### P3-14. 30 `HARDCORE_VERIFY_*` receipts are tautological
All `verified: true`, each repeats the producer's own hash, none references a
separate verifier run or a fresh instance. Independent falsification is absent at
the receipt layer, not just the capability layer.

---

## Hidden mechanisms + research ideas already in the repo (the fixes are NOT new)

The user's standing point is correct: nothing here needs a new invention. Map each
problem to an existing mechanism:

- P0-1/P0-2 → `true_capability_harness_v1` (fresh instances, >=2 oracles), placed in
  front of every new SWE adapter; `capability_type_surface_v1` (ARGV/PATH_DIR/aliases)
  + `declared_input_derivation_v1` for the derived inputs; one owned adapter per
  family, each with its E30 effect vocabulary as admission.
- P0-3 → shard heartbeat with its existing `--families`/`--jobs 4` flags; owner adds
  it to required checks.
- P1-5 → `bridge_enumeration_v1` output → `capability_composer_v1.graph()` as
  `provides_as`/`requires_as` (`astra_runtime` already implements them).
- P1-6 → `program_synthesis_v1` / `documentation_mining_v1` as the last-resort
  fallback, proved by running, not by name.
- P2-9 → `flywheel_v1` / `goal_chase_v1` persistence; cache the typed plan.
- All → `COMPOSITION_LEVERAGE_20261018_V1.md §9`: when a relation can't be derived
  from names, enumerate the candidate space and let execution be the oracle.

## Fastest correct order
1. (owner) make heartbeat required + shard it, so public-runner truth blocks merges.
2. shard the pinned kernel install; delete/implement the 22 stub caps.
3. for each of the 8 missing `INV_` families: one owned adapter + E30 effect gate +
   fresh held-out instances + 2 independent oracles via `true_capability_harness_v1`.
4. wire execution-proved bridges into the composer; add real cost/timing fields; cache
   the typed plan.
5. only then add new SWE capabilities. Adding capabilities before (1)-(3) produces
   stubs, not a more advanced engineer.

## SHIPPED 2026-10-28 — hidden-tool effect-family resolver (P0-1 partial)

The user's thesis was tested and confirmed: for the 8 failing `INV_` families the
capabilities ALREADY EXIST in the registry with the right keywords and execute
honestly — they are just buried by BM25's lexical top-8 and blocked by a narrow
SWE-verb gate. Measured root cause: "Find every caller of the function add in
`.../mod.py`" shortlists path-named and finance/chart capabilities; the correct
`python.source.symbols.index.ast` (keywords "callers, who calls, call graph")
never surfaces. Forced by name, it admits (binds every declared input) and emits
a REAL artifact: `callers_of: {"add": ["caller", "other"]}`, `call_edge_count: 2`.

Fix (REUSE of `COMPOSITION_LEVERAGE §9` — enumerate candidates, let admission be
the oracle), confined to `swe_typed_plan_v1.py`: a stated SWE effect family
authoritatively triggers a data-driven resolver that enumerates hidden
capabilities by the registry's OWN keywords, uses the existing `admit()` as the
oracle, and is decisive ONLY when exactly one candidate is admitted+specific and
names the effect. Ambiguity/zero => fail closed. No pinned selector change, no
`executed` guard relaxation, no new primitive.

Measured (fresh instances, filesystem artifact as independent oracle):
- caller-finding sentence now PASSES with `callers_of[add] == ["caller","other"]`
  (source untouched, all honesty gates clean).
- 12 fresh human SWE sentences: **4/12 -> 5/12 honest PASS, ZERO false PASS**;
  OOS/GAP still fail-closed; test-gen/lint/typecheck/extract stay honestly
  fail-closed (their capabilities are ambiguous or need inputs the sentence
  never states — NOT fabricated into a PASS).
- New suite `test_swe_typed_plan_v1.py` 17/17 (incl. real-artifact oracle,
  keyword-strip mutation, admit-as-oracle mutation, negative controls).
- Front-door/parity/consult/naming failure set byte-identical to pristine A/B
  (9 pre-existing fleet-drift failures); verifier 33/33.

This is the template for the remaining families: encode each family's OWN effect
vocabulary, enumerate its hidden capabilities, and let admission+execution judge.
