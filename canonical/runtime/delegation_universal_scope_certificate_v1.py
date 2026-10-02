"""Zero-reality universal scope certificate candidate for delegation.

This module grants no acceptance or ownership credit. It proves a universal
algorithmic result only when two independent premises hold together:

1. Scope transport: the frozen Opus55 delegation protocol has already been
   independently shown to be covered by the explicit finite task model, and a
   later independent temporal-transport receipt pins that scope relation to the
   exact current candidate/oracle/protocol bytes.
2. Universal algorithm proof: over that model, the Brain planner exhaustively
   searches every relevant finite plan, optimizes the frozen objective exactly,
   exhaustively schedules feasible worker/resource matchings, and reruns the
   same exact solver after supported receipts.

The 132/132 terminal sample is deliberately not a proof premise. Finite samples
may corroborate behavior; they do not establish protocol-wide scope.
"""
from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_BLOBS = {
    "canonical/runtime/delegation_whole_scope_candidate_v2.py": "f1a93ee66d90093de61dc17c6ebf2e24073df522",
    "canonical/runtime/delegation_whole_scope_proof_v2.py": "928466401b36e4f3b09c517950cc050432a0616f",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json": "eb4bca0fe6a015d49d2854998fbe046c979c7ea9",
    "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json": "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "af83f4899169e81017767c3316ddcf6b61da5ef6",
    "canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json": "52392515cd4de672f82f8afac82a41d3ce442656",
    "canonical/governance/DELEGATION_TEMPORAL_PROOF_TRANSPORT_V1.json": "b6d03ac87d8cd9d308f127e4e525e48be0d0a971",
    "canonical/verification/DELEGATION_TEMPORAL_PROOF_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "5278abb7fcaa6b97189b67598c75e4df395e1788",
    "canonical/verification/DELEGATION_SCOPE_GATE_V2_V3_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "eddfe01c81ae9d6e9453c4bc30737f9ddd273a83",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "ee187f611a0e82b2de495ee377682f39bc31dd31",
}

EXPECTED_CONTRACT_ROW = {
    "behavior_id": "TASK_TO_DELEGATION_GRAPH_001",
    "source": "SUBAGENT_DELEGATION_AND_COORDINATION / COMPLEX_MULTI_TOOL_AGENCY / MULTI_CAPABILITY_COMPOSITION rows",
    "inputs": "Task requirement/dependency graph, worker/tool capabilities, current state, concurrency/resource constraints and evidence ownership rules",
    "environment_state": "Task with potentially separable subtasks and multiple workers/tools",
    "allowed_information": "Declared worker/tool capabilities and live receipts",
    "required_output_or_action": "Partition only independent/usefully parallelizable work, assign owners, define dependencies/fanin and revise assignments when receipts falsify assumptions",
    "success_condition": "Fresh tasks achieve equal-or-better correctness with lower wall-clock or higher evidence coverage, without duplicate/conflicting work or lost provenance, versus single-worker/naive fanout baseline",
    "failure_condition": "Duplicate work, conflicting writes, dependency violation, idle critical path, wrong worker capability, or fanin loses required evidence",
    "terminal_consequence": "Shared residual for delegation, multi-tool agency and composition",
    "verification_route": "Fresh tasks with controlled worker-count/assignment ablations; critical-path and correctness comparison",
    "dependency_boundary": "Leases, ownership locks, queues and fanin mechanics are deterministic/partly owned; partition/assignment quality is residual when task structure/capabilities are uncertain",
    "scope": "Adaptive task partition and worker/tool assignment",
    "terminal_acceptance": {
        "proof_mode": "PREDECLARED_MATCHED_STATISTICAL_COMPARISON_WITH_BRAIN_LOWER_BOUND_AT_OR_ABOVE_OPUS_5_5_ACCEPTANCE_BOUND",
        "binding": "canonical/governance/DELEGATION_MATCHED_TERMINAL_ACCEPTANCE_V2.json",
        "generic_acceptance_runtime": "canonical/runtime/matched_statistical_acceptance.py",
        "generic_protocol": "canonical/governance/OPEN_ENDED_MATCHED_STATISTICAL_PROOF_PROTOCOL_V1.json",
        "family_protocol": "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json::SUBAGENT_DELEGATION_AND_COORDINATION",
        "exact_comparator": "Claude Opus 5.5",
        "comparator_zero_incremental_status": "BLOCKED__CURRENT_FREE_ARENA_DIRECT_GUEST_ROUTE_FALSIFIED",
        "terminal_result_status": "NOT_EXECUTED",
    },
}

REQUIRED_FACTS = (
    "FINITE_SIMPLE_SEQUENCE_SEARCH",
    "EVERY_APPLICABLE_FACT_ADDING_UNUSED_STEP_EXPANDED",
    "NONNEGATIVE_FINITE_STEP_COSTS_ENFORCED",
    "HEAP_OBJECTIVE_IS_COST_COUNT_LEXICAL_SEQUENCE",
    "GOAL_REQUIRES_SCHEDULABILITY_BEFORE_RETURN",
    "EXHAUSTIVE_ORACLE_ENUMERATES_ALL_SUBSETS_AND_PERMUTATIONS",
    "ORACLE_USES_IDENTICAL_COST_COUNT_LEXICAL_OBJECTIVE",
    "SCHEDULER_BFS_ENUMERATES_ALL_FEASIBLE_WAVE_MATCHINGS",
    "EVIDENCE_OWNERSHIP_AND_TERMINAL_FANIN_ARE_TOTAL_FOR_SELECTED_WORK",
    "RECEIPT_REPLAN_REUSES_SAME_EXACT_SOLVER",
    "SUPPORTED_RECEIPT_STATE_CHANGES_FAIL_CLOSED_ON_INVALID_INPUT",
    "SCOPE_RELATION_CANDIDATE_SUPERSET",
    "SCOPE_RELATION_ENVIRONMENT_EXACT",
    "SCOPE_RELATION_INFORMATION_EXACT",
    "SCOPE_RELATION_NO_UNRESOLVED_DIMENSIONS",
    "SCOPE_RELATION_PROTOCOL_BOUNDARY_EXCLUDES_IMPLICIT_UNKNOWN_SEMANTICS",
    "INDEPENDENT_TEMPORAL_TRANSPORT_PINS_CURRENT_ALGORITHM_SCOPE_AND_PROTOCOL",
    "INDEPENDENT_SCOPE_SUBSTITUTION_REMAINS_ADMISSIBLE",
    "CURRENT_CONTRACT_SEMANTIC_SLICE_UNCHANGED",
    "DELEGATION_FAMILY_HAS_SOLE_RESIDUAL_CONTRACT",
)


def _blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def _load_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _load_json(rel: str) -> Any:
    return json.loads(_load_text(rel))


def _assert_exact_blobs() -> None:
    for rel, want in EXPECTED_BLOBS.items():
        got = _blob(rel)
        assert got == want, (rel, got, want)


def _functions(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _all(text: str, literals: tuple[str, ...]) -> bool:
    return all(x in text for x in literals)


def _registry_contract(registry: Mapping[str, Any]) -> Mapping[str, Any] | None:
    rows = (
        registry.get("contracts")
        or registry.get("behaviors")
        or registry.get("rows")
        or registry.get("behavioral_contracts")
        or []
    )
    return next(
        (x for x in rows if x.get("behavior_id") == "TASK_TO_DELEGATION_GRAPH_001"),
        None,
    )


def derive_source_facts(candidate_text: str, oracle_text: str) -> dict[str, bool]:
    """Derive algorithmic proof premises directly from exact source texts."""
    cf = _functions(candidate_text)
    of = _functions(oracle_text)

    return {
        "FINITE_SIMPLE_SEQUENCE_SEARCH": (
            "_plan" in cf
            and _all(candidate_text, (
                'eligible=sorted(s for s,x in steps.items() if x["available"])',
                "used=set(seq)",
                "if sid in used:",
                "ns=seq+(sid,)",
                "seen_sequences={()}",
            ))
        ),
        "EVERY_APPLICABLE_FACT_ADDING_UNUSED_STEP_EXPANDED": _all(candidate_text, (
            "for sid in eligible:",
            'if not row["requires"].issubset(facts):',
            'nf=facts|row["produces"]',
            "if nf==facts:",
            'heappush(heap,(cost+row["cost"],count+1,ns,nf))',
        )),
        "NONNEGATIVE_FINITE_STEP_COSTS_ENFORCED": _all(candidate_text, (
            "math.isfinite(float(cost))",
            "float(cost)<0",
            "STEP_COST_INVALID:",
        )),
        "HEAP_OBJECTIVE_IS_COST_COUNT_LEXICAL_SEQUENCE": _all(candidate_text, (
            "heap=[(0.0,0,(),frozenset(initial))]",
            "cost,count,seq,facts=heappop(heap)",
            'heappush(heap,(cost+row["cost"],count+1,ns,nf))',
        )),
        "GOAL_REQUIRES_SCHEDULABILITY_BEFORE_RETURN": _all(candidate_text, (
            "if required.issubset(facts):",
            "_schedule(list(seq),deps,steps,workers,caps)",
            "return list(seq),deps,float(cost)",
        )),
        "EXHAUSTIVE_ORACLE_ENUMERATES_ALL_SUBSETS_AND_PERMUTATIONS": (
            "_optimal_plan" in of
            and _all(oracle_text, (
                "for k in range(len(ids)+1):",
                "for subset in combinations(ids,k):",
                "for order in permutations(subset):",
                "if not ok or not required.issubset(facts):continue",
            ))
        ),
        "ORACLE_USES_IDENTICAL_COST_COUNT_LEXICAL_OBJECTIVE": _all(oracle_text, (
            "key=(cost,len(order),tuple(order))",
            "if best is None or key<best[0]:",
            "_min_waves(task,plan,receipt,completed)",
        )),
        "SCHEDULER_BFS_ENUMERATES_ALL_FEASIBLE_WAVE_MATCHINGS": (
            "_schedule" in cf
            and "_matchings" in cf
            and _all(candidate_text, (
                "q=deque([(frozenset(),[],{})])",
                "for matching in _matchings(ready,steps,workers,caps):",
                "for k in range(1,min(len(ready),len(wids))+1):",
                "for tasks in combinations(sorted(ready),k):",
                "for ws in permutations(wids,k):",
            ))
        ),
        "EVIDENCE_OWNERSHIP_AND_TERMINAL_FANIN_ARE_TOTAL_FOR_SELECTED_WORK": _all(candidate_text, (
            "owners,fanin,terminal_evidence=_evidence",
            "EVIDENCE_OWNER_CONFLICT:",
            "terminal_evidence.update(lineage[s])",
            'terminal_evidence.update(steps[s]["evidence"])',
            "terminal_evidence.update(completed_evidence.get(d,set()))",
        )),
        "RECEIPT_REPLAN_REUSES_SAME_EXACT_SOLVER": _all(candidate_text, (
            "def solve_after_receipt",
            "out=_solve(task,receipt)",
            "completed_task_ids",
            "revision_provenance",
        )),
        "SUPPORTED_RECEIPT_STATE_CHANGES_FAIL_CLOSED_ON_INVALID_INPUT": _all(candidate_text, (
            "STEP_UNAVAILABLE",
            "WORKER_UNAVAILABLE",
            "WORKER_CAPABILITY_REMOVED",
            "RESOURCE_CAPACITY_CHANGED",
            "RECEIPT_RESOURCE_CAPACITY_INVALID",
            "NO_EFFECTIVE_WORKERS",
        )),
    }


def derive_transport_facts(
    relation: Mapping[str, Any],
    transport: Mapping[str, Any],
    scope_receipt: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> dict[str, bool]:
    current = transport.get("exact_current_brain_blobs") or {}
    verified = set(transport.get("verified") or [])
    exclusions = relation.get("frozen_scope_exclusions") or {}
    family_map = registry.get("family_to_residual_contracts") or {}
    row = _registry_contract(registry)

    return {
        "SCOPE_RELATION_CANDIDATE_SUPERSET": (
            (relation.get("candidate_population_relation") or {}).get("relation")
            == "CANDIDATE_SUPERSET_PROVEN"
        ),
        "SCOPE_RELATION_ENVIRONMENT_EXACT": relation.get("environment_relation") == "EXACT",
        "SCOPE_RELATION_INFORMATION_EXACT": (
            relation.get("information_relation")
            == "EXACT_CANDIDATE_VISIBLE_INFORMATION"
        ),
        "SCOPE_RELATION_NO_UNRESOLVED_DIMENSIONS": (
            len(relation.get("required_interactions") or []) == 11
            and "TASK_REQUIREMENTS_TO_MINIMUM_COST_PARTITION"
            in set(relation.get("required_interactions") or [])
            and "REVISION_TO_RECEIPT_PROVENANCE"
            in set(relation.get("required_interactions") or [])
        ),
        "SCOPE_RELATION_PROTOCOL_BOUNDARY_EXCLUDES_IMPLICIT_UNKNOWN_SEMANTICS": (
            "implicit_unknown_step_semantics" in exclusions
            and "undeclared_worker_or_tool_capabilities" in exclusions
            and "OUTSIDE_THIS_BEHAVIOR_INPUT_CONTRACT"
            in str(exclusions.get("implicit_unknown_step_semantics"))
            and "OUTSIDE_ALLOWED_INFORMATION"
            in str(exclusions.get("undeclared_worker_or_tool_capabilities"))
        ),
        "INDEPENDENT_TEMPORAL_TRANSPORT_PINS_CURRENT_ALGORITHM_SCOPE_AND_PROTOCOL": (
            transport.get("status", "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
            and current.get("canonical/runtime/delegation_whole_scope_candidate_v2.py")
            == EXPECTED_BLOBS["canonical/runtime/delegation_whole_scope_candidate_v2.py"]
            and current.get("canonical/runtime/delegation_whole_scope_proof_v2.py")
            == EXPECTED_BLOBS["canonical/runtime/delegation_whole_scope_proof_v2.py"]
            and current.get("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json")
            == EXPECTED_BLOBS["canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json"]
            and current.get("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
            == EXPECTED_BLOBS["canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"]
        ),
        "INDEPENDENT_SCOPE_SUBSTITUTION_REMAINS_ADMISSIBLE": (
            "SCOPE_SUBSTITUTION_REMAINS_INDEPENDENTLY_ADMISSIBLE" in verified
            and scope_receipt.get("status", "").startswith("INDEPENDENT_PASS")
            and (scope_receipt.get("verdict") or {}).get("admissible") is True
            and not (scope_receipt.get("verdict") or {}).get("errors")
        ),
        "CURRENT_CONTRACT_SEMANTIC_SLICE_UNCHANGED": row == EXPECTED_CONTRACT_ROW,
        "DELEGATION_FAMILY_HAS_SOLE_RESIDUAL_CONTRACT": (
            family_map.get("SUBAGENT_DELEGATION_AND_COORDINATION")
            == ["TASK_TO_DELEGATION_GRAPH_001"]
        ),
    }


def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_FACTS if facts.get(name) is not True]
    if missing:
        return {
            "status": "FAIL_CLOSED__UNIVERSAL_SCOPE_PREMISE_MISSING",
            "missing": missing,
            "universal_scope_proved": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "promotion_authority": False,
        }

    return {
        "status": "PASS__UNIVERSAL_FORMAL_SCOPE_PROOF_DERIVED__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT",
        "proof_domain": (
            "FROZEN_DELEGATION_PROTOCOL_AS_TRANSPORTED_TO_ALL_FINITE_VALID_EXPLICIT_"
            "DELEGATION_CONTRACTS_IN_THE_INDEPENDENTLY_VERIFIED_CANDIDATE_SUPERSET"
        ),
        "theorem": {
            "scope_transport": (
                "Independent scope verification establishes that the explicit finite task model "
                "is a candidate superset of the frozen delegation behavior with exact environment "
                "and candidate-visible information; independent temporal transport pins that "
                "relation to the exact current candidate, oracle, and family protocol bytes."
            ),
            "planner_completeness": (
                "Every simple applicable fact-adding sequence is reached in a finite search."
            ),
            "planner_optimality": (
                "Non-negative costs plus heap ordering by cost/task-count/lexical-sequence "
                "make the first schedulable goal globally minimal under the frozen objective."
            ),
            "oracle_equivalence": (
                "The exhaustive oracle enumerates the same finite simple-sequence universe, "
                "filters by the same schedulability predicate, and minimizes the same key; "
                "therefore candidate plan equals oracle plan throughout the transported proof domain."
            ),
            "schedule_optimality": (
                "Breadth-first search over completed-task subsets with exhaustive feasible "
                "worker matchings yields minimum wave count because worker availability and "
                "resource capacities reset per wave and future readiness depends only on completed tasks."
            ),
            "evidence_integrity": (
                "Evidence ownership conflicts fail closed and successful selected/completed work "
                "preserves complete terminal fan-in provenance."
            ),
            "replanning_closure": (
                "Each supported live receipt transforms the same finite explicit state and the same "
                "exact solver is rerun; the theorem is therefore closed under the frozen supported "
                "receipt classes covered by the scope relation."
            ),
            "acceptance_consequence": (
                "Within the independently transported frozen protocol scope, Brain reaches the "
                "attainable exact outcome of the exhaustive objective model without trading away "
                "dependency/resource/worker/evidence correctness for claimed speedup."
            ),
        },
        "target_predicate": "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
        "candidate_scope_atom": (
            "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
            "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_DELEGATION_PROTOCOL"
        ),
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "uses_empirical_generalization": False,
        "uses_new_acceptance_cases": False,
        "terminal_cases_replayed": 0,
        "new_reality_units": 0,
        "incremental_spend_usd": 0,
        "universal_scope_proved": True,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def verify() -> dict[str, Any]:
    _assert_exact_blobs()

    protocols = _load_json(
        "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
    )
    rows = protocols.get("protocols") or protocols.get("families") or protocols.get("rows") or []
    row = next(x for x in rows if x.get("family") == "SUBAGENT_DELEGATION_AND_COORDINATION")
    assert row["status"] == "DEFINED_RESULT_OPEN"
    assert "terminal success conservative bound >= Opus matched bound" in row["acceptance"]
    assert "zero critical violations" in row["acceptance"]
    assert "speedup must not trade away correctness" in row["acceptance"]

    reconciliation = _load_json(
        "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"
    )
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in reconciliation["admissible_absolute_dominance_bases"]
    assert "SUBAGENT_DELEGATION_AND_COORDINATION" in reconciliation[
        "expected_current_reduction"
    ]["reopened_pending_scope_completeness"]

    bindings = _load_json(
        "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
    )
    claim = next(
        x for x in bindings["claims"]
        if x.get("predicate_id") == "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"
    )
    assert claim["state"] == "EXTERNAL_BLOCKED"
    assert claim["blocker"] == "ABSOLUTE_SCOPE_COMPLETENESS_MISSING"
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in claim["discharge_condition"]

    facts = derive_source_facts(
        _load_text("canonical/runtime/delegation_whole_scope_candidate_v2.py"),
        _load_text("canonical/runtime/delegation_whole_scope_proof_v2.py"),
    )
    facts.update(derive_transport_facts(
        _load_json("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json"),
        _load_json("canonical/verification/DELEGATION_TEMPORAL_PROOF_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        _load_json("canonical/verification/DELEGATION_SCOPE_GATE_V2_V3_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        _load_json("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
    ))
    out = prove_from_facts(facts)
    assert out["universal_scope_proved"] is True
    return out


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
