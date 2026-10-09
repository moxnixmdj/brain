# Executable Refinement + Terminal Closure Implementation Plan

**Spec:** `docs/superpowers/specs/2026-10-09-executable-refinement-terminal-closure-design.md`

**Goal:** close the highest-dominance implementation gap by making abstract-to-concrete executable refinement a content-addressed, fail-closed dependency of verified-live runtime authority, first on a bounded representative route, without granting unrelated capability or terminal credit.

**Global constraints**
- Preserve the authoritative mission objective and current fail-closed terminal truth.
- Hard $0 incremental spend.
- Do not modify `main` directly during implementation; use an isolated branch/workspace.
- TDD for every behavior change: observe RED before implementation, then GREEN.
- Existing current-pointer/path versus immutable-blob precedence remains authoritative.
- No benchmark, family, acceptance, ownership, or terminal credit from test counts.
- Unknown schema/transition/mapping/version => fail closed.
- First implementation is bounded. No repository-wide refinement claim.
- Prefer existing exact-blob/proof-receipt patterns over new infrastructure.
- Final promotion requires fresh verification output and an independent replay of the exact bounded cone.

## Task 1: Add the fail-closed executable-refinement verifier

**Create**
- `canonical/runtime/executable_refinement_verifier_v1.py`
- `canonical/tests/test_executable_refinement_verifier_v1.py`

**Interface**
- `verify_certificate(raw: Mapping[str, Any], *, repo_root: Path | None = None) -> dict[str, Any]`
- `git_blob_sha(path: Path) -> str`
- constants:
  - `SCHEMA = "PROJECT_BRAIN_EXECUTABLE_REFINEMENT_CERTIFICATE_V1"`
  - `RECEIPT_SCHEMA = "PROJECT_BRAIN_EXECUTABLE_REFINEMENT_RECEIPT_V1"`

**Certificate fields required**
- `schema`, `subject_id`
- `abstract_spec: {path, git_blob_sha, semantic_version}`
- `concrete_implementation: [{path, git_blob_sha}]`
- `state_mapping`
- `input_binding`
- `transition_refinement`
- `observation_refinement`
- `nondeterminism_contract`
- `safety_refinement`
- `liveness_refinement`
- `proof_dependencies`
- `terminal_credit_delta`

**RED tests first**
1. `test_unknown_schema_fails_closed`
2. `test_missing_required_field_fails_closed`
3. `test_abstract_blob_drift_fails_closed`
4. `test_concrete_blob_drift_fails_closed`
5. `test_unknown_transition_class_fails_closed`
6. `test_unproved_input_binding_fails_closed`
7. `test_safety_only_certificate_rejected_when_liveness_required`
8. `test_valid_bounded_certificate_emits_content_bound_receipt`

**Implementation rule**
The verifier checks only explicit finite/bounded certificate claims and exact artifact identities. It must not infer refinement from unit-test success or source equality.

**Expected verification**
`python -m pytest -q canonical/tests/test_executable_refinement_verifier_v1.py`
=> all focused tests pass.

**Commit**
`refinement: add fail-closed executable refinement verifier`

## Task 2: Bind the deterministic router canary as a zero-credit framework proof

The existing canary is not a capability claim. It is the smallest safe object for proving the new certificate/verifier mechanics before touching a live creditable path.

**Create**
- `canonical/governance/ROUTER_DEPLOYMENT_CANARY_ABSTRACT_SPEC_20261009_V1.json`
- `canonical/governance/ROUTER_DEPLOYMENT_CANARY_EXECUTABLE_REFINEMENT_20261009_V1.json`
- `canonical/tests/test_router_deployment_canary_executable_refinement_v1.py`

**Modify only if needed**
- no runtime behavior change to `canonical/runtime/router_deployment_canary_v1.py`

**Abstract spec**
Express the complete goal-relevant behavior:
- input must be a mapping;
- canonical JSON encoding uses sorted keys and compact separators;
- output schema/status are exact;
- `payload_sha256` equals SHA-256 of canonical payload bytes;
- all capability/family/terminal deltas remain zero;
- no terminal result.

**RED/GREEN tests**
1. valid canary certificate accepted;
2. changing canary runtime bytes invalidates certificate;
3. changing abstract spec bytes invalidates certificate;
4. parser/encoding mismatch certificate rejected;
5. attempt to claim nonzero credit rejected.

**Expected verification**
Focused verifier + canary tests all pass.

**Commit**
`refinement: certify zero-credit router canary semantics`

## Task 3: Add a machine-readable terminal dependency graph and explicit lifecycle states

**Create**
- `canonical/governance/CURRENT_TERMINAL_DEPENDENCY_GRAPH_V1.json`
- `canonical/runtime/terminal_dependency_graph_guard_v1.py`
- `canonical/tests/test_terminal_dependency_graph_guard_v1.py`

**Graph leaf statuses allowed**
- `ENFORCED`
- `PROVED`
- `USER_AUTHORIZED`
- `ROOT`
- `UNRESOLVED`

**Lifecycle states exposed for executable routes**
- `SPECIFIED`
- `IMPLEMENTED`
- `REFINEMENT_VERIFIED`
- `VERIFIED_LIVE`

**RED tests**
1. unknown leaf status rejected;
2. `VERIFIED_LIVE` without refinement dependency rejected;
3. stale refinement receipt rejected;
4. `IMPLEMENTED` without refinement remains non-live;
5. canary may be `REFINEMENT_VERIFIED` but remains noncreditable/nonterminal.

**Implementation**
The guard validates graph structure, exact references, and anti-bypass invariants. It does not claim graph completeness merely because JSON validates.

**Commit**
`terminal: add explicit executable-refinement dependency graph`

## Task 4: Certify one current bounded live semantic route

Use the smallest current R2 route with explicit finite validation semantics:
- `canonical/runtime/brain_owned_semantic_relation_edge_authority_v1.py`
- dependency: `canonical/runtime/semantic_relation_control_v1.py`
- existing tests: `canonical/tests/test_brain_owned_semantic_relation_edge_authority_v1.py`

**Create**
- `canonical/governance/BRAIN_OWNED_SEMANTIC_EDGE_ABSTRACT_SPEC_20261009_V1.json`
- `canonical/governance/BRAIN_OWNED_SEMANTIC_EDGE_EXECUTABLE_REFINEMENT_20261009_V1.json`
- `canonical/tests/test_brain_owned_semantic_edge_executable_refinement_v1.py`

**Abstract transition classes**
The finite top-level behavior classes must include at least:
- evidence not object;
- field-set mismatch;
- schema mismatch;
- unsupported proof class;
- missing scope;
- invalid/non-distinct IDs;
- missing surfaces;
- unsupported relation;
- missing/invalid definition rows;
- semantic identity not proved;
- `NOT_ENTAILS` explicitly rejected;
- successful `ENTAILS` receipt.

**Observation contract**
For every class, the abstract spec fixes the goal-relevant fields:
- `pass`
- schema/status/reason as applicable
- relation/source/target where successful
- authority flags
- `terminal_authority`
- exact receipt/evidence digest rule on the success path.

**RED/GREEN differential tests**
1. enumerate every declared transition class with a canonical witness;
2. compare concrete output to abstract-spec evaluator/expected projection;
3. mutate one field per equivalence class and prove it either stays in the same allowed class or fails closed;
4. introduce an undeclared concrete-result class and verify certificate validation fails;
5. prove no test promotes `NOT_ENTAILS` from missing identity;
6. require exact blob identities for both the authority module and load-bearing semantic-control dependency.

This task certifies only the declared bounded transition partition. It does not claim general natural-language semantic completeness.

**Expected verification**
- existing semantic-edge tests pass;
- new differential refinement tests pass;
- relevant R2 route regression tests pass.

**Commit**
`refinement: bind bounded semantic-edge authority to abstract contract`

## Task 5: Enforce refinement at the selected-route/terminal projection boundary

**Modify**
- `canonical/runtime/certificate_gated_selected_route_runtime_entrypoint_v2.py`
- `canonical/tests/test_certificate_gated_selected_route_runtime_entrypoint_v2.py`
- `canonical/governance/CURRENT_TERMINAL_DEPENDENCY_GRAPH_V1.json`

**Registry rule**
For any row that is both:
- `admitted: true`
- `creditable: true`

require:
- `refinement_certificate_path`
- `refinement_certificate_blob_sha`
- `refinement_receipt_path` or deterministic verifier invocation over the exact certificate
- exact subject identity matching the route blob and its bound abstract spec.

Noncreditable canary behavior remains compatible and receives no credit.

**RED tests**
1. creditable row without refinement binding => `CREDITABLE_REFINEMENT_BINDING_MISSING`;
2. stale/mismatched refinement blob => fail closed;
3. refinement subject route blob mismatch => fail closed;
4. safety-only receipt when route requires liveness => fail closed;
5. noncreditable canary remains executable under existing rules;
6. valid bounded creditable fixture passes only with valid refinement receipt.

Use a test-local/temporary registry fixture for the positive creditable case. Do not invent live production credit solely for the test.

**Commit**
`runtime: require executable refinement for creditable route admission`

## Task 6: Project bounded refinement truth into current terminal authority without false closure

**Modify**
- `canonical/governance/CURRENT_TERMINAL_AUTHORITY.json`
- `canonical/tests/test_current_terminal_authority_r2_reconciliation_v1.py`

**Add truth fields**
- `executable_refinement_framework_bound: true`
- `router_canary_refinement_verified: true`
- `brain_owned_semantic_edge_bounded_refinement_verified: true` only after Task 4 verification
- `repository_wide_executable_refinement_closed: false`
- `all_creditable_live_routes_refinement_verified: false` unless the graph actually proves otherwise
- `terminal_executable_refinement_gap_closed: false` unless all terminal-load-bearing live paths are covered
- `executable_refinement_missing_is_external_impossibility: false`

**Status/nonclaims**
Keep terminal false. Add explicit nonclaims against:
- repository-wide formal verification;
- attestation=>semantic correctness;
- test-pass=>refinement completeness;
- bounded semantic-edge refinement=>general semantic refinement.

Increment current pointer revision consistently with repo conventions.

**RED/GREEN**
Terminal reconciliation test must first fail when new refinement truth is absent/inconsistent, then pass after exact projection.

**Commit**
`terminal: project bounded executable-refinement truth`

## Task 7: Add the systematic terminal falsifier over the dependency graph

**Create**
- `canonical/runtime/terminal_dependency_falsifier_v1.py`
- `canonical/tests/test_terminal_dependency_falsifier_v1.py`

**Supported reusable attack families**
- `NEGATION`
- `QUANTIFIER_SWAP`
- `COMPOSITION_MISMATCH`
- `HIDDEN_STATE`
- `TIMING`
- `CONCURRENCY`
- `CRASH_RESTART`
- `ROLLBACK_FORK`
- `BYZANTINE_INPUT`
- `RESOURCE_EXHAUSTION`
- `VERSION_DRIFT`
- `REVOCATION`
- `ADAPTIVE_SELECTION`
- `PROXY_MEASUREMENT`
- `CAUSAL_CONFOUNDING`
- `NOVEL_DIMENSION`
- `IMPLEMENTATION_REFINEMENT_MISMATCH`

**Rule**
A family applies only where the dependency node declares that failure mode meaningful. Unknown applicability remains explicit rather than silently passed.

**Outputs**
- unresolved counterexample obligations;
- duplicate/covered attacks;
- highest-dominance unresolved leaf candidate;
- no terminal credit.

**Tests**
- executable-refinement mismatch is detected for an unbound `VERIFIED_LIVE` node;
- irrelevant statistical attacks are not falsely required for deterministic hash-binding leaves;
- unknown applicability is not converted to pass;
- falsifier cannot declare open-world closure on its own.

**Commit**
`assurance: add systematic terminal dependency falsifier`

## Task 8: Exact verification receipt and bounded promotion

**Create**
- `canonical/verification/EXECUTABLE_REFINEMENT_TERMINAL_CLOSURE_VERIFY_20261009_V1.json`
- optionally a narrow GitHub Actions workflow under `.github/workflows/` if a current no-cost runner is available and existing repo conventions require it.

**Verification commands**
At minimum run:
`python -m py_compile` on all new/modified Python modules.

Then run:
`python -m pytest -q canonical/tests/test_executable_refinement_verifier_v1.py canonical/tests/test_router_deployment_canary_executable_refinement_v1.py canonical/tests/test_terminal_dependency_graph_guard_v1.py canonical/tests/test_brain_owned_semantic_relation_edge_authority_v1.py canonical/tests/test_brain_owned_semantic_edge_executable_refinement_v1.py canonical/tests/test_certificate_gated_selected_route_runtime_entrypoint_v2.py canonical/tests/test_current_terminal_authority_r2_reconciliation_v1.py canonical/tests/test_terminal_dependency_falsifier_v1.py`

Also run the smallest existing R2 regression cone that imports/uses the semantic-edge authority and fixed-point front door.

**Independent replay**
Use a distinct execution carrier only if it satisfies the user's $0 incremental-spend constraint. The replay receipt must bind exact tested blobs and record the carrier. If no independent carrier is available, record that exact limitation and do not claim independent replay.

**Verification receipt must say**
- exact tests and counts;
- exact blobs;
- bounded subject only;
- repository-wide refinement remains open;
- terminal remains false unless independently proven otherwise;
- all unrelated credit deltas = 0.

**Commit**
`verify: seal bounded executable refinement closure evidence`

## Task 9: Final review and next-frontier extraction

Run a whole-branch review against the spec, with explicit focus on:
- any route that can become creditable/live without refinement;
- certificate self-certification or caller-supplied authority;
- stale blob/version acceptance;
- parser/representation bypass;
- safety/liveness conflation;
- accidental terminal-credit changes;
- dependency graph claiming completeness from enumeration.

Fix Critical/Important findings via RED→GREEN tests in one pass. Defer only genuine minor issues.

Then run the dependency falsifier on the promoted bounded graph and record the next highest-dominance `UNRESOLVED` leaf. Do not invent another primitive until that leaf survives the new-primitive test.

## Review focus

The implementation succeeds only if the concrete promotion path cannot obtain `VERIFIED_LIVE`/creditable status for the selected subject without a valid content-bound executable-refinement certificate, while every pre-existing unsupported/general scope stays explicitly open.
