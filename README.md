# Project Brain — read this first

This file exists because an agent once worked from a condensed conversation summary, lost
the objective, and proposed two things the law forbids. It is the fixed minimum every human
or agent must know before acting here. It is checked by machine:

```
python3 execution_guard/agent_orientation_check_v1.py brief     # live card: objective, laws, honest state, contract sha
python3 execution_guard/agent_orientation_check_v1.py verify    # this README + the contract + the laws agree byte-for-byte
python3 execution_guard/agent_orientation_check_v1.py intent-check <intent.json>
```

The machine-readable twin is `canonical/governance/AGENT_ORIENTATION_CONTRACT_V1.json`.
Every action intent that a pull request adds must carry an `agent_orientation` block
acknowledging that contract, or the load-bearing admission gate fails the PR. The sources
cited below win on any conflict with this page.

**If you are an agent resuming from a summary: the summary is a retrieval hint, not
authority. Run `brief`, re-read the objective, then continue.**

## 1. The objective (verbatim, never rewritten by agents)

Source: `canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json`

```
BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE
```

- terminality: `OPEN_ENDED_CAPABILITY_OPTIMIZATION_NO_FINITE_FRONTIER_MODEL_OR_BENCHMARK_DEFINES_FINAL_MISSION_COMPLETION`
- Opus 5.5: `FIRST_FRONTIER_CHECKPOINT_NOT_TERMINAL_OBJECTIVE`
- spend: `ZERO_INCREMENTAL_SPEND`

Plain words: make Brain the most capable, general, reliable and cheap problem solver
possible. The mission is a direction, not a finish line; nothing is "unreachable" because
nothing is a destination. Opus 5.5 is the first yardstick, not the goal. Agents do not
rewrite, reinterpret, or offer to replace this objective. Only the owner can change it.

## 2. What Brain is

- **Theory** (`canonical/README.md`): effective intelligence = Brain-owned capability
  mechanisms + external just-in-time knowledge + general computation substrate. Knowledge
  is fetched when needed and is never counted as capability. Capability is what Brain owns
  and can still run with every outside model deleted.
- **Control plane**: this repository is the canonical, provider-independent truth (laws,
  governance JSON, pointers, receipts). CI, browsers, agent platforms and model surfaces
  are replaceable execution providers and never define truth.
- **Execution substrate**: the same-identity superworker
  (`canonical/runtime/same_identity_supervisor.py`), checkpoint/relaunch, $0 spend.
- **The solver as it exists today**: `canonical/runtime/goal_compiler.py` (deterministic
  plain-goal compiler; fails closed on unknown goals so the missing mechanism stays
  visible) + `canonical/runtime/capability_planner.py` (precondition/effect planner) +
  `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` (the bound tools: document
  create/verify, PDF text/OCR, chart reading from pixels, source ranking, a model-free
  test-guided Python repair loop, and more — `brief` prints the live count).
- **Capability acquisition engine** (laws): for each missing capability, race routes in
  the fixed order below, verify the exact Brain-owned route on untouched held-out
  instances, then minimize its persistent bytes.
- **Truth layer**: the referee `execution_guard/repo_integrity_guard_v1.py` (judged from
  `main` on every PR), the true-capability harness and ledger
  (`canonical/capabilities/true/`), and the honest test baseline
  (`canonical/verification/HONEST_SUITE_BASELINE_20261014_V1.json`).
- **Honest state**: never from memory. `brief` prints it from the canon: terminal truth
  achieved = false; ownership matrix 19 families with a status histogram; the audit that
  found 15 of 19 quoted routes contain an external model (zero credit under the law); the
  true-capability ledger (every row `MEASURED_SANDBOX`, zero credit); the honest suite
  totals (11,525 cases, 344 failing at the last baseline).

## 3. Permanent prohibitions (verbatim law text; only the owner can rescind)

| id | law says (verbatim) | source |
|---|---|---|
| `NO_MODEL_PRODUCER_COGNITION` | A Brain-credited result MUST NOT depend on another model for producer cognition. | `canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md` |
| `HOSTING_DOES_NOT_LAUNDER` | Local possession, a fixed hash, zero monetary cost, open weights, or a Brain-authored wrapper does not turn another model's cognition into Brain cognition. | same |
| `ONLY_THE_OWNER_CAN_RESCIND` | Only a future explicit owner instruction that directly names this prohibition and explicitly rescinds it may change this rule. Silence, convenience, or a newer theory cannot. | same |
| `UNKNOWN_PROVENANCE_FAILS_CLOSED` | Unknown or incomplete cognition provenance fails closed exactly like a detected model dependency. | same |
| `ZERO_CREDIT_WITH_ANY_MODEL_DEPENDENCY` | Project Brain may claim capability, benchmark, acceptance, ownership, promotion, real-task, or terminal credit only when the producer cognition path has zero dependencies on another general-purpose model. | `canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10.md` |
| `K3_FORBIDDEN` | K3 runtime cognition provider: Forbidden in every Brain-credited producer path. (K1 knowledge is allowed; K2 acquisition-time donor is allowed only through the transfer gate and is deleted before qualification.) | `canonical/laws/EXTERNAL_KNOWLEDGE_CAPABILITY_TRANSFER_RUNTIME_COGNITION_BOUNDARY_LAW_V1.md` |
| `OBJECTIVE_CANNOT_BE_REPLACED` | No benchmark, model family, acceptance row, score threshold, leaderboard rank, frozen protocol, or named frontier system may replace this parent objective. | `canonical/laws/GENERAL_CAPABILITY_FIRST_DEVELOPMENT_LAW_V1.md` |
| `RED_ROW_IS_NOT_AUTHORITY` | A red benchmark row, score gap, acceptance-family gap, or rank is not by itself development authority. | same |
| `DONOR_IS_NEVER_RUNTIME` | A donor is acquisition-time evidence and causal source only. It is never a credited runtime cognition provider. | `canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V3.md` |
| `MEMORY_IS_NOT_AUTHORITY` | treat conversation memory, summaries, and prior assistant conclusions as retrieval hints only, never current authority; | `canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V4.md` |
| `NEVER_WIDEN_THE_TOLERANCE` | Never widen the tolerance to pass. | `canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md` |
| `TERMINAL_TRUTH_NOT_EDITABLE` | Terminal truth is not editable data. | `AGENTS.md` |
| `VERIFICATION_IS_SOMEONE_ELSE` | Verification means someone else ran it. | `AGENTS.md` |
| `NO_MERGE_OVER_RED_REFEREE` | Nothing merges over a red referee. | `AGENTS.md` |

In plain words: no AI model may do the thinking inside anything Brain takes credit for —
not remote, not local, not open-weight, not wrapped, not "only on hard cases", not "as one
component". Owning the weights or paying nothing changes nothing. "Allow a model" is never
an option an agent may put on a menu. If provenance is unknown, treat it as a model
dependency. Benchmarks are instruments, never the product; a red score is not a reason to
start work. When a true test fails, fix the solver or narrow the claim — never the test.

## 4. No longer true — do not repeat these

- "Underlying capability invention is forbidden" — superseded:
  `CAPABILITY_ACQUISITION_ENGINE_LAW_V8.md`: *The V7 global underlying-capability
  invention ban is superseded.* Cheap reuse precedes expensive construction as an
  optimization preference, not a ban.
- "Models may participate in credited capabilities / model independence is not
  terminal" — superseded by Substrate Law V4 and Mission Lock V10 (owner correction after
  the Qwen route, 2026-10-11).
- "The mission lock is V7 / the strategy is V7" (older orientation text and summaries) —
  stale; Mission Lock V10 and Strategy V8 are current.
- "The objective is unreachable, let's rewrite it" — category error; the objective is
  open-ended.
- "External benchmarks are the scarce limiting factor" — demoted by the owner on
  2026-10-14: *External benchmarks are no longer treated as the scarce resource of the
  project.* Brain-authored true tests replace them (`TRUE_CAPABILITY_TEST_LAW_V1.md`).

## 5. What counts as progress (and what does not)

Law: `canonical/laws/GENERAL_CAPABILITY_FIRST_DEVELOPMENT_LAW_V1.md`. Exactly these classes:

1. `VERIFIED_REUSABLE_CAPABILITY_GAIN` — Brain can now do something general it could not
   do before, verified on fresh instances by an independent oracle.
2. `VERIFIED_RELIABILITY_GENERALIZATION_OR_EFFICIENCY_GAIN` — same capability, now more
   reliable, broader or cheaper, with no capability regression.
3. `VERIFIED_INTEGRATION_OF_OWNED_CAPABILITY` — an already-owned capability becomes
   available through the live Brain.
4. `INDEPENDENT_FALSIFICATION_OF_A_FALSE_GENERAL_CLAIM` — a false claim is removed and
   the frontier causally narrowed.
5. `GOVERNANCE_GUARD_NO_PROGRESS_CLAIM` — only for `action_kind: GOVERNANCE_GUARD`; a guard
   or policy change that claims no development progress (this PR class).

Verbatim:

> Activity, benchmark score movement alone, proof bureaucracy, and repeated certification of unchanged behavior are not progress.

Measuring again what is already measured, adding receipts about unchanged code, closing
certificates, or producing more governance files is not a step and must not be presented
as one.

Route order for any missing capability (walk it in order and write down why each earlier
route is insufficient before taking a later one):

```
DELETE -> BYPASS -> REUSE -> ADAPT -> SUBSTITUTE -> COMPOSE -> CONFIGURE -> INTEGRATE -> SYNTHESIZE_NEW_PRIMITIVE.
```

Development loop: `UNDERSTAND -> PLAN -> COMPOSE -> ACT -> VERIFY -> LEARN -> GENERALIZE -> COMPRESS -> REUSE.`
Scheduler objective: capability gain × reuse breadth × reliability gain × causal confidence
per wall-clock × compute × memory × cost × complexity × evidence risk, with correctness and
fail-closed truth as hard constraints. Report bytes separately as B_exec / B_verify /
B_proof / B_JIT (`RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1.md`).

## 6. Which law is current

Rule: within a family the highest version number is current; lower versions are history
even when their own `Status:` line still says CANONICAL; anything whose status says
SUPERSEDED is never cited. `brief` prints the full table from the live tree. Must read
before any consequential action (also enforced per intent):

- `canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json`
- `canonical/laws/GENERAL_CAPABILITY_FIRST_DEVELOPMENT_LAW_V1.md`
- `canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md`
- `canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10.md`
- `canonical/laws/EXTERNAL_KNOWLEDGE_CAPABILITY_TRANSFER_RUNTIME_COGNITION_BOUNDARY_LAW_V1.md`
- `canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V8.md`
- `canonical/laws/CAPABILITY_INTERNALIZATION_ARBITRAGE_STRATEGY_V8.md`
- `canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V3.md`
- `canonical/laws/RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1.md`
- `canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V4.md`
- `canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md`
- `AGENTS.md`

## 7. Known traps

- Protected paths (`PROTECTED_PATHS` in `execution_guard/repo_integrity_guard_v1.py`,
  including `AGENTS.md`, the referee, its workflow, CODEOWNERS, the honest baseline) make
  any PR red; only the owner lands them.
- Several runtime kernels are byte-pinned by capability records (DOCX kernels, scheduler
  kernels). Before editing any runtime module run `git hash-object <file>` and grep that
  blob under `canonical/`; if it is pinned, measure it through a separate adapter module.
- Every PR touching `canonical/`, `execution_guard/` or workflows needs exactly one action
  intent in `canonical/action_intents/` that passes the drift guard
  (`canonical/runtime/enforce_goal_hierarchy.py`), the load-bearing gate
  (`execution_guard/enforce_load_bearing_primary_pr.py`) and this orientation contract.
- The referee forbids: stdlib attribute assignment, constant-key `sys.modules` injection,
  pin ledgers or historical git reads in tests, tautological assertions, self-merge tooling
  in `.py/.sh/.yml` files, new `pull_request_target` workflows.
- `canonical/README.md` is orientation prose, not live authority; the content-addressed
  authorities (objective JSON, highest-version laws, terminal authority) win on conflict.
- Arena/agent session memory is condensed between turns. Re-run `brief` after any
  condensation and before any plan.

## 8. Session start and the intent block

```
python3 execution_guard/agent_orientation_check_v1.py brief
python3 execution_guard/agent_orientation_check_v1.py verify
git branch --show-current && git status --short
```

Before a consequential action: state the objective verbatim and the progress class you
claim (or say honestly that the action is not progress and ask whether to do it at all);
walk the route order; name the independent oracle that will judge the result on fresh
instances; confirm zero model dependency and zero spend; then write the action intent
with this block (`brief` prints the current `contract_sha256`):

```json
"agent_orientation": {
  "contract": "canonical/governance/AGENT_ORIENTATION_CONTRACT_V1.json",
  "contract_sha256": "<from brief>",
  "objective_verbatim": "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE",
  "progress_class": "<one of the five classes above>",
  "progress_evidence_paths": ["<a path this PR changes that carries the evidence>"],
  "route_class": "<one of the route order>",
  "earlier_routes_exhausted_reason": "<required for SYNTHESIZE_NEW_PRIMITIVE>",
  "producer_cognition_model_dependency_count": 0,
  "incremental_spend_usd": 0,
  "conversation_memory_is_authority": false,
  "laws_read_this_session": ["<every path in section 6>"]
}
```

## 9. Merge rule

`AGENTS.md` rule 7 governs: nothing merges over a red referee, and the preferred route is
GitHub auto-merge, which completes only when the signed referee check is green. If your
platform forbids the auto option, do not merge unless the owner has explicitly instructed
you to; then merge only after the referee check-run conclusion is `success`, and disclose
the self-merge in your report.
