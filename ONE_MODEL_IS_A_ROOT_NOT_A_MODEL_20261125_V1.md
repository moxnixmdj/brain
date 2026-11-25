# "Not one real model": the fragmentation measured, and the shortest way to a single system

*2026-11-25. Every number here was produced this sitting by `python3
canonical/tools/capability_fabric_v1.py` (fabric digest `4b30be2ade766931`, regenerated after the corrections in §3b) and `python3
canonical/tools/capability_enrollment_gate_v1.py` (both committed under
`canonical/capabilities/`). 0 model calls, $0.00, network 0. Nothing is typed from memory.*

## 1. The diagnosis, in numbers

| measured | value | reading |
|---|---|---|
| Python modules under `canonical/` | **5,904** | the surface |
| internal import edges | 3,479 | what is actually composed |
| connected components of the import graph | **3,533** (largest 1,422; **3,011 singletons**) | "thrown everywhere" is this number |
| distinct `SCHEMA = "…"` constants | **1,993** | 1,993 private envelopes; every one is a translation a composed edge must pay |
| runnable modules (`if __name__ == "__main__"`) | **2,689** — only **579** of them expose a `main()` | 2,689 ways in; a system has one root and N adapters |
| modules nothing in `canonical/` imports | **4,616** | three quarters of the tree is reached by hand, or not at all |
| widest import fan-out of any module | **18** | nobody in this tree composes at scale — a god-orchestrator has no precedent to imitate |
| reachability | `ISLAND` 1,448 · `TEST_ONLY` 534 · `IN_USE` 547 · `ENTRY_POINT` 565 · `TEST` 2,810 | ~2,000 non-test modules are production-unreachable |
| registry rows the brain can dispatch | **146** (all `VERIFIED_BOUND_CAPABILITY`, `incremental_spend_usd` 0) | the root already exists |
| of those, rows with `provides` / with `requires` | 146 / **90** | 56 rows can never be chained *into* |
| harness-certified capabilities reachable from the root | **1 of 9** | the strongest evidence class is not wired |

And the binding defects, all mechanical (`ENROLLMENT_GATE_V1.md`, regenerated at head `c18d19d8`):

| defect | count | meaning |
|---|---|---|
| `DANGLING_ADAPTER` | **1** | `python.task.acceptance.measured.objective.v1` → `python_measured_objective_acceptance_v1`, a file that does not exist (a near-namesake does). Two more rows point at `runtime_native_action`, which is a **declared kind** special-cased in `capability_selection_retrieval_v1.py:692` — checked before believing my own finding, and excluded |
| `MISSING_VERIFICATION_RECEIPT` | **8** | 8 rows cite `verification.receipt_path`; the files are not in the tree. The root's own second admission condition is claimed and unverifiable for them |
| `UNSATISFIABLE_REQUIRES` | **25** | 25 of 125 `requires` predicates (e.g. `manifest.json.available`, `git.repository.available`) have no provider in any row. They are ambient input facts — the bug is that "ambient" is declared nowhere that the loader reads |
| `UNENROLLED_CERTIFIED_CAPABILITY` | **8 of 9** | the four DOCX kernels, the three schedulers, and the same-identity supervisor have receipts and no dispatch row |
| `REGISTRY_VS_SNAPSHOT_DIVERGENCE` | **35** | 7 rows only in live, 8 only in snapshot, 20 differing in content (e.g. `keywords`). `load_verified_registry` merges `{**raw, **snapshot}`, so **the snapshot wins** — a newer live row is silently shadowed. The root is not single-valued |

So: **the missing thing is not a model, and not a framework — the repo already has both.** It is the
*binding* between three disjoint ledgers of truth: the harness ledger (9 measurements, 100 % on
fresh instances), the bound-capability registry (146 dispatch rows), and the frontier ownership
matrix (19 families, 7 owned). Fixing the binding is mostly data work with a check attached.

## 2. The usual ideas, in the order that is fastest here

Ordered by (evidence already exists) ÷ (wiring cost). Each has a stopping number, because "perfectly"
without one is how you get a third registry.

1. **Composition root + registry, already present — repair it before extending it.** (Usual: service
   registry / plugin manifest; here it is `load_verified_registry` with the two-condition rule and a
   CI-only attestation path, which is *better* than the usual version.) Close the 1 dangling adapter,
   the 8 lost receipts, and the 35 divergences: either restore the evidence or demote the row to
   `CANDIDATE`. *Moves:* `ENROLLMENT_GATE_V1.clean` → True. *Cost:* an afternoon per class; the gate
   tool is the checker and `--fail-on-defect` is the CI hook.
2. **Enroll what is already certified.** 8 of 9 measured kernels have no row. `ENROLLMENT_CANDIDATES_V1.json`
   carries them with everything the receipt states (entry module+function, blob, instances, pass rate,
   scope limits, the three admission blockers) and **`provides`/`requires` left `null` on purpose**: a
   predicate invented by a generator would be an unmeasured capability claim, which is the failure this
   project keeps re-measuring. Write the two predicates per kernel from its spec — 8 rows, ~15 minutes.
   *Moves:* `UNENROLLED_CERTIFIED_CAPABILITY` 8 → 0; certified coverage of non-test modules 0.517 % → ~0.65 %.
3. **One envelope, adapters at the boundary.** (Usual: anti-corruption layer / canonical schema.) Do not
   rewrite 1,993 private schemas — you cannot, and it buys nothing that a check cannot buy. Define one
   return shape for registry adapters (`outcome | fail_closed_reason | evidence_ref`), require it at the
   146 adapter doors, and let the 1,993 internal shapes stay internal. *Metric:* fraction of `bound_capabilities/`
   adapters returning the envelope. *Cost:* the envelope is one module; the migration is per-adapter and
   each step is independently shippable.
4. **Declare ambient preconditions instead of pretending they are capabilities.** (Usual: an ambient
   fact vocabulary / environment contract.) A tiny read-in vocabulary naming `*.available` facts, plus
   a rule that any `requires` term must be either providable or declared ambient. *Moves:*
   `UNSATISFIABLE_REQUIRES` 25 → 0 by *decision*, not by deletion — each term picks a side.
5. **Strangler fig, then prune.** (Usual: freeze the seam, route new work, retire the rest.) 1,448
   islands + 534 test-only modules are not a migration backlog; they are a *gc* queue, and the tree
   already has one (`canonical/capabilities/obsolescence/`, 105 records). Add one CI rule — **no new
   module may define a top-level `SCHEMA =` unless it is reachable from the registry lanes** — which
   stops the number growing while the pruning happens asynchronously.
6. **Single store, one format.** (Usual: shared blackboard / one memory.) This is where the benchmark
   run actually died: 44 of 51 tasks never reached an action, each carrying
   `store: STORE_FILE_ABSENT` → `FAIL_CLOSED`. Every capability reading and writing one external
   editable store is what makes "one model" true *behaviourally* — a shared state that improves with
   use — and it is the precondition for the memory-ablation arm the plan already owes.

## 3. The two ideas that are specific to this tree (and the ones I reject)

**Certify the edges, not just the nodes.** (Usual name: consumer-driven contract tests; here: metamorphic
relations at the boundary.) The harness proves a kernel is right on fresh instances. Nothing proves
that kernel A's output is a legal input to kernel B — which is exactly the gap that turns 146
admitted capabilities into 56 rows nothing can chain into. The prototype already exists: composition
legality held in **228/228** cases (measured in `canonical/`, one of the Nov rounds), and the true-capability
harness already knows how to run a generator against an oracle. What is missing is a *mode* that
generates **pairs** along a registry edge and asserts the edge relation. Start with the 90 rows that
declare `requires` — that is the whole edge set worth certifying first. *Stopping number:* certified
edges > 0, then /90.

**Route on the demand, not the signature.** The last ten ledgers keep arriving at the same
place from different directions: a site is not a production (20261124), a demonstration carries the
action but never the condition — 0 of 10 real actions at k = 1, 2, 4 (20261126), a demand read at 37
sibling productions verified 0 (20261125), and the corpus that can answer the question produced **1 verified
repair in 134 real fixes** (20261123). The capability law's arithmetic agrees: `p_correct 0.2978`,
value-bearing `0.1167`, and the only controllable lever is `check_density`. That is an argument for
making the *interface between* capabilities a witness — "what must hold afterwards, observably" — rather
than a richer type system: a witness is checkable by a machine that does not know the answer, so every
edge in item 7 becomes falsifiable, and every refusal names the gap that blocked it (the one behaviour
in the HARD-51 run that was worth something: 43 of 51 `FAIL_CLOSED` rows each carried a named gap).

Rejected, with the measurement that rejects it:

* **Distill/merge the capabilities into one trained model.** Zero-model is the law, and a distilled
  model cannot be certified by fresh-instance oracles the way `saccr_credit_kernel.py` was; the ledger's
  `determined 0.5469` is a ceiling on *any* such route, and `memory_exact 0.0481` with
  `silent_corruption 0.3114` says what happens to a "lesson" stored that way. It would also destroy
  the one thing worth having: `1.0000` fresh-instance pass rates with a receipt that names the bytes.
* **One orchestrator that imports everything.** Max fan-out in the tree is 18. The failure mode was
  never too little coupling; it is that no coupling is *checked*. A 5,901-file façade would be
  unverifiable at exactly the one point the law says to spend on.
* **Unify by renaming/reformatting** (one directory, one naming scheme, one schema linter with
  autofix). This tree has already been burned that way: `revoked_false_ownership_packages` in the
  ownership matrix are packages whose *label* claimed ownership. A relabel produces credit without
  evidence, which is the only unforgivable move here.
* **A fourth registry.** Three disjoint ledgers are the disease; a "unified capability index" written
  by hand is the same disease with better typography. Anything the root dispatches must be derived
  from a receipt, like these two tools derive their reports.

## 3b. Two corrections landed on the way, both worth recording

**My own numbers were wrong, twice, in the same direction.** "578 ways in" counted `def main(`; the
tree has **2,689** modules with a `__main__` guard — the census understated the entry-point problem by
~4.6x. The cause was a regex anchored to end-of-line, so a guard carrying a trailing comment was
missed. It surfaced only because the new test counts guards by *parsing each file with `ast`* while the
tool matches text: two implementations, one number, which is the only way a census is checkable at
all. (Likewise "3,530 components" reads 3,533 once my own files are in the tree — the number is a
function of the commit, which is exactly why the digest is printed next to it.)

**Run `45676020414` found a second harness bug with the identical shape.** The backslash fix worked: for
the first time all 18 shards published reports — and all 18 said `COLLECT_FAILED`, listed in
`incomplete_shards`, with `arms: {}` and `run_produced_number: false`. Running the CLI by hand put the
reason in plain sight: `error: unrecognized arguments: --note …`. The `--note` *handling* existed in
`main`'s collect branch and in the `collect(notes=…)` **function**; the `--note` *flag* had never been
declared on the collect **subparser**. Every unit test called the function directly and stayed green
while the call shape CI actually uses was broken. So:

- `build_parser()` is now a real function, and
  `canonical/tests/test_eval_workflow_shell_invocations_are_well_formed_v1.py` extracts the flags the
  workflow passes to each subcommand and checks them against what that subcommand's own `--help` says it
  accepts — with a probe assertion proving the comparison discriminates;
- the collect step writes stdout+stderr to a published `*.collect.log`, the `COLLECT_FAILED` marker
  embeds `collector_output_tail`, and the aggregate surfaces `collector_last_line` per incomplete shard,
  so "the collector failed" can never again be the whole sentence;
- the exact CLI invocation is covered by a subprocess round-trip test asserting the notes land in
  `conditions`, ints kept ints.

Both bugs teach one rule: **the CI surface is an interface, and an interface with no test on the real
call shape is uncovered**, however many tests the underlying function has.

## 4. The stopping rule, because "perfectly" needs one

The system is unified when all four of these hold, and each is a check, not a feeling:

1. `capability_enrollment_gate_v1.py --fail-on-defect` exits **0** — no row without resolvable code and
   evidence, no unsatisfied predicate left undeclared, root single-valued.
2. **9 of 9** certified capabilities are dispatchable rows, each with a receipt whose blob still
   matches HEAD (this check caught a stale binding today — `SAME_IDENTITY_SUPERVISOR_V1`, measured
   against `ce869c9a…` while HEAD shipped `ae66843e…`; re-measured 2000/2000 and rebound).
3. Every `requires` edge of the 90 declaring rows has a **certified composition test** or a declared
   ambient fact — so the planner never plans through a hole.
4. `capability_fabric_v1.py --check` passes. It gates the **dispatch surface** — the certified manifest
   must match the receipts — and deliberately only *prints* the graph counts: a check that fires on
   ordinary tree growth gets deleted rather than obeyed. That is what keeps the fabric from rotting the
   way the October prose counts did (`5_OF_19_ACCEPTED` vs `acceptance_truth: 7`).

That is a week of shippable, individually-verifiable work — not a rewrite. What it does **not** buy is a
benchmark score: rows 1–4 of the frontier comparison (SWE-bench Pro 61.5 %, Terminal-Bench 64.85 %, METR
39 h) are not closed by tidier composition, and our own 0/51 says the bottleneck is store admission and
check density, not wiring. The unification is what makes the *next* capability arrive admitted instead of
islanded; the capability itself is still the expensive part.

## 5. What this turn changed in the tree

`canonical/tools/capability_fabric_v1.py` (import graph + certified manifest + `--check`),
`canonical/tools/capability_enrollment_gate_v1.py` (5 defect classes + `--emit-candidates` +
`--fail-on-defect`), their outputs `canonical/capabilities/CAPABILITY_FABRIC_V1.{json,md}`,
`ENROLLMENT_GATE_V1.{json,md}`, `ENROLLMENT_CANDIDATES_V1.json`;
`canonical/tests/test_capability_enrollment_gate_counts_the_missing_binding_v1.py` (6 tests: two fixture
mutations proving the gate bites, one proving it is satisfiable);
`canonical/tests/test_capability_fabric_census_gates_the_dispatch_surface_v1.py` (4 tests, including the
independent `ast` recount that caught the understated entry-point number); and on the CI surface,
7 tests in `test_eval_workflow_shell_invocations_are_well_formed_v1.py` (flag-vs-parser check, the CLI
`--note` round trip, the collect-log publishing) plus 7 in
`test_capability_inventory_refuses_stale_and_broken_claims_v1.py`, whose report-refusal test is now
data-driven instead of pinned to one run's verdict — it went stale the moment CI overwrote
`swe-pro-v2-hard51-latest.json` with a void report, which is itself the lesson about pinning numbers in
tests. **56 passed** across the six files that touch this work. `capability_fabric_v1.py --check` passes.
HARD-51 re-armed (`RUN_SWE_PRO_V2`, 6 shards, 240 s engine budget) against the fixed collector CLI.
