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
`canonical/tools/capability_enrollment_gate_v1.py` (4 defect classes + 1 fact + `--emit-candidates` +
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
tests. **56 passed** across the six files at that point; the count after section 6 is 65 across eight.
`capability_fabric_v1.py --check` passed then on digest `4b30be2ade766931`, and after section 6 on `7e9412f672577beb`.
HARD-51 re-armed (`RUN_SWE_PRO_V2`, 6 shards, 240 s engine budget) against the fixed collector CLI.

## 6. Execution: the enrollment, and what the instruments said back

Plan item 2 was carried out for all nine measured capabilities, and item 1 turned out to need
corrections rather than repairs. `canonical/tools/capability_enroll_certified_v1.py` (`--write`,
`--check`) derives, for each capability, five artifacts and refuses to author any of their contents:

| artifact | count | what it is |
|---|---|---|
| `canonical/runtime/bound_capabilities/truecap_*.py` | 9 | thin `run(args, root)` adapters; the measured kernel is the whole implementation, and the adapter's only logic is resolving an instance |
| `canonical/capabilities/true/instances/*.json` | 9 | the instance the edge was measured on, committed, because a capability that can only be called with an in-memory dict cannot be re-run by anyone else |
| `canonical/astra_runtime/pending_bindings/TRUECAP-ENROLL-*.json` | 9 | `registry_entry` + fixture digest + result path, in the shape `auto_pypi_library_acquisition.py` already uses for acquired capabilities |
| `canonical/capabilities/COMPOSITION_EDGES_V1.json` | 9 edges | 34 oracle verdicts executed against real output: 102 passes, 0 failures, 0 oracle errors; 1 published canary passed; 0 model calls, $0.00 |
| a `truecap.*` row in `AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json` | 9 | registration in the one file `capability_receipt_lane_v1.discover()` reads, in the same dialect as `brain.module.function.invoke` — the only prior example of a bound-capability adapter registered for receipting |

That last artifact is what turns "documented" into "reachable". `autonomous_capability_inventory_v1` scans `canonical/**/*.py` and *excludes* `canonical/runtime/bound_capabilities/**`, so an adapter is invisible to the inventory by design; the curated bound registry is the other door, and that is exactly the file where a status may not be self-granted. The extended registry is the seam in between — a row there is not an admission claim (`_receipt_admits` ignores `status` entirely and reads evidence), it is a declaration that the lane should look. Measured consequence: `lane.discover(".")` returns 816 candidates including all nine `truecap.*` ids as `("contract", "run")`, so the workflow that mints producer receipts will execute these adapters with no CI edit. Registering them also freezes the file, which is the point of the generator's own guard: `main()` raises "Refusing to overwrite promoted entries" if any row is not `UNVERIFIED_INVENTORY`, so a declared capability cannot be re-derived away by the next inventory run.

The gate now counts the *other* capability class too, because "every advanced capability" is not only the
nine kernels. `OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json` holds 19 families; 4 of them name a Python
module as their `verified_route` (`matched_agency_stateful_case_v2.py`, `delegation_whole_scope_candidate_v2.py`,
`tool_discovery_information_safe_candidate.py`, `trajectory_failure_typed_ir_candidate_v7.py`), and the gate grades
each against evidence rather than against a label: 1 has a producer receipt but no independent verification
(`RECEIPTED__NO_INDEPENDENT_VERIFICATION`), 3 are `INVENTORY_ONLY__NOT_DISPATCH_SHAPE` — an `.auto.v1`
inventory row exists, which means the file was *seen*, and none of the four speaks `run(args, root)`, so
`lane.discover()` cannot execute them and nothing can be admitted about them. **0 of 4 admitted.** That is
the remaining half of the answer to "is everything in one model", and it is not closed by wrapping those four
in adapters: they have no generator and no oracles, so a wrapper would be an envelope around an unmeasured
claim — exactly the shape this repo keeps re-measuring as its own failure. What closes them is one spec per
family under `canonical/capabilities/true/specs/` (falsifiable claim, instance generator, independent oracles,
mutation test), after which the enrollment tool picks them up with no new machinery. The gate prints the
verdict ladder on every run so the number cannot be quietly forgotten, and one test refuses to pass if a
family route ever appears ADMITTED while its evidence still says otherwise.

One property worth naming, found by regenerating the fixtures: all nine generators are seed-stable in
structure, but the four DOCX instances embed zip-member timestamps, so their bytes differ per process. The
committed fixture, not the seed, is what makes those edges re-runnable by a verifier that runs tomorrow —
which is the reason the fixture exists as an artifact at all.

Three instrument bugs were caught before anything was committed. Each one would have become a quoted
number, which is what makes them worth writing down rather than fixing silently:

1. an oracle's `check(inst, out, solve)` returns `(ok, detail)`, per the harness's own contract; treating
   it as a bool made every one of the 34 checks read `0/3`. A green-looking tool reporting total failure
   is the friendlier version of this bug, and it is still a lie.
2. the first `action_template` asserted `field_equals status == "None"`, because statuses were collected
   with `str(out.get("status"))` and four of the nine kernels return no `status` key at all. That is a
   binding no result can ever satisfy — published, dispatchable in principle, permanently failing. The
   expectation is now derived from whether the kernel uses the field, and falls back to
   `field_nonempty capability_id` when it does not (the envelope always carries it).
3. enrollment was traced by substring over the merged rows, which made all nine look `registry_bound` —
   the extended inventory has a row for nearly every module in the tree, so "mentions the kernel's name"
   matched everything. Binding is now decided by artifact identity (the file a row dispatches to *is* the
   measured kernel or forwards to it, or the row cites the capability's own spec), and it is graded:
   **registry-bound 9**, **pending-binding-only 0**, **unenrolled 0** — and the grading was written *before* the registration, so the intermediate state (bound 1, queued 8) is what `git log -p` shows, which is the right order for a claim meant to be checkable.

Corrections to §1 and §3b, in the same spirit: the root was understated, not missing.

- `load_verified_registry` merges **four** sources — curated live (145 rows), curated snapshot (146),
  the extended inventory (2,310) and the receipt projection (305 entries) — and admits **447** rows today
  (153 with `include_extended=False`). The claim "there is already one registry" is therefore stronger
  than the draft said, and it comes with a second admission route (`_receipt_admits`) that a measurement
  can actually use. The 1,993-schema sprawl is real; the dispatch surface is already unified.
- `REGISTRY_VS_SNAPSHOT_DIVERGENCE` (35) was defect class 5 and is now a reported fact. The loader's own
  comment is the reason: "A PROJECTION MAY ADD OR UPDATE A ROW; IT MAY NEVER DELETE ONE. The snapshot is
  therefore the FLOOR." The merge is a union, so divergence cannot lose a row — it is drift to read, not
  something to block on. A gate that fires on ordinary growth is a gate that gets deleted, and this one
  would have been deleted for a stylistic objection.
- `DANGLING_ADAPTER` was 1, and the 1 was my error, not the registry's.
  `python.task.acceptance.measured.objective.v1` resolves through `source.adapter_path` →
  `canonical/runtime/python_measured_objective_acceptance_v1.py` (present, 7,999 bytes), which is exactly
  the convention `capability_receipt_lane_v1.py:587` uses. Under the corrected rule the count is 0. Same
  class of mistake as the `runtime_native_action` exclusion one section earlier: applying one file's
  schema to a corpus admitted through another route.

The stopping rule, item by item, as of this commit:

1. *gate `--fail-on-defect` exits 0* — **not met**, and not met for reasons this change did not create: 8
   curated rows cite absent `canonical/verification/HARDCORE_VERIFY_*.json` receipts, and 25 `requires`
   predicates have no provider. Those are plan items 1 and 4, still open, still named in
   `ENROLLMENT_GATE_V1.md` with every id listed.
2. *9/9 dispatchable, with the measured blob equal to HEAD* — **met**. `git hash-object` equals the
   ledger's `solver_git_blob_sha` for all nine kernels (so the certifications describe the code that is
   in the tree right now, not a copy of it), and every adapter was executed with the lane's own argument
   shape and met its derived expectation.
3. *every `requires` edge certified or declared ambient* — **met for the nine**: `requires: []`, with the
   fixture named under `ambient_preconditions` and sha256-pinned by the queue entry. The remaining 25
   belong to pre-existing rows and are item 4.
4. *`capability_fabric_v1.py --check` passes* — **met**, digest `7e9412f672577beb`: 5,915 modules,
   3,544 components, 3,022 singletons, 2,690 runnable entry points of which 580 expose a `main()`.

**67 tests pass** across the eight files that cover this work, 10 of them new: 9 in
`test_measured_capabilities_are_enrolled_into_the_one_registry_v1.py` — including one that calls the receipt
lane's own `discover()` and one that runs `git hash-object` against the certified blob — plus the family-route
census test, whose bite is that an ADMITTED verdict may not appear unless the evidence files say so.

What "100 % sure" means here, stated so it can be refuted. It means: every advanced capability the repo
measures now has exactly one row-shape in the one queue the root consumes; the row's predicates came
from executing the composition, not from a person typing them; the adapters were run, not inspected; the
kernels are byte-identical to what was certified; and `--check` plus the tests fail if code, queue and
registration disagree. It does **not** mean the nine are admitted — `load_verified_registry` still answers
**447** rows and none of them is `truecap.*`. The queue entries carry
`BOUND_PENDING_INDEPENDENT_VERIFICATION` / `AWAITING_RECEIPT_AND_INDEPENDENT_VERIFICATION` and a
`verification` block that deliberately names no receipt path, because `_receipt_admits` demands
a producer receipt at the adapter's content hash *and* an independent verification record whose run
reference carries a platform-attested `github_run_id`, and only
`.github/workflows/capability-receipt-verification.yml` can mint that. Writing it from this sandbox would
be the `SESSION_E0A256F8` failure mode the root exists to prevent ("produced 464 self-verified
receipts"), and a unification bought by laundering a status is worse than the sprawl: the sprawl at least
told the truth. The root's own gate is stricter than a promise could be anyway:
`run_reference_is_attested` accepts only claims signed by `token.actions.githubusercontent.com`, so "I ran it"
is not something a sandbox can type. So the gap is named rather than closed, and the last mile has been reduced
to the workflow that already exists: it discovers these nine rows, mints producer receipts at the adapter
hashes, and its OIDC-attested reproduction turns them into projection entries — at which point `truecap.*`
appears in `load_verified_registry()` (447 → 456) without anything in this document needing to be rewritten.

