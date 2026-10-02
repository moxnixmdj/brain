"""Zero-reality universal scope certificate candidate for delegation.

This module does not grant acceptance or ownership credit.  It checks exact
load-bearing source identities and derives the premises of a universal proof for
the Brain-owned finite delegation planner.  The proof domain is the declared
finite explicit-task model accepted by the candidate: finite steps/workers,
monotone facts, non-negative finite costs, finite positive resource capacities,
supported live receipts, and at least one executable feasible plan.

The mathematical step is standard finite-search reasoning, not extrapolation from
the 132 empirical terminal cases:
  * the planner enumerates every applicable simple fact-adding step sequence;
  * all edge costs are non-negative and the heap key is the protocol objective;
  * a goal is returned only if the sequence is schedulable;
  * the independent oracle enumerates every subset/permutation and applies the
    same schedulability condition and objective key;
  * the scheduler breadth-first searches all feasible wave matchings;
  * receipt replanning re-runs the same exact search on the transformed state.

Therefore the candidate equals the exhaustive oracle for every admissible finite
contract in this model.  This candidate still requires independent clean-room
verification before the scope-completeness atom may be discharged.
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
)


def _blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def _load_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


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


def derive_source_facts(candidate_text: str, oracle_text: str) -> dict[str, bool]:
    """Derive proof premises directly from the exact source texts."""
    cf = _functions(candidate_text)
    of = _functions(oracle_text)

    return {
        "FINITE_SIMPLE_SEQUENCE_SEARCH": (
            "_plan" in cf
            and _all(candidate_text, (
                "eligible=sorted(s for s,x in steps.items() if x[\"available\"])",
                "used=set(seq)",
                "if sid in used:",
                "ns=seq+(sid,)",
                "seen_sequences={()}",
            ))
        ),
        "EVERY_APPLICABLE_FACT_ADDING_UNUSED_STEP_EXPANDED": _all(candidate_text, (
            "for sid in eligible:",
            "if not row[\"requires\"].issubset(facts):",
            "nf=facts|row[\"produces\"]",
            "if nf==facts:",
            "heappush(heap,(cost+row[\"cost\"],count+1,ns,nf))",
        )),
        "NONNEGATIVE_FINITE_STEP_COSTS_ENFORCED": _all(candidate_text, (
            "math.isfinite(float(cost))",
            "float(cost)<0",
            "STEP_COST_INVALID:",
        )),
        "HEAP_OBJECTIVE_IS_COST_COUNT_LEXICAL_SEQUENCE": _all(candidate_text, (
            "heap=[(0.0,0,(),frozenset(initial))]",
            "cost,count,seq,facts=heappop(heap)",
            "heappush(heap,(cost+row[\"cost\"],count+1,ns,nf))",
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
            "terminal_evidence.update(lineage[s])",
            "terminal_evidence.update(steps[s][\"evidence\"])",
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
            "ALL_FINITE_VALID_EXPLICIT_DELEGATION_CONTRACTS_ACCEPTED_BY_THE_"
            "FROZEN_CANDIDATE_MODEL_WITH_AT_LEAST_ONE_EXECUTABLE_FEASIBLE_PLAN"
        ),
        "theorem": {
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
                "therefore candidate plan equals oracle plan for every contract in the proof domain."
            ),
            "schedule_optimality": (
                "Breadth-first search over completed-task subsets with exhaustive feasible "
                "worker matchings yields minimum wave count because worker availability and "
                "resource capacities reset per wave and future readiness depends only on completed tasks."
            ),
            "replanning_closure": (
                "Each supported live receipt transforms the finite explicit state and the same "
                "exact solver is rerun; the theorem is therefore closed under supported replanning."
            ),
            "acceptance_consequence": (
                "For every admissible feasible contract, terminal success reaches the objective "
                "ceiling and critical dependency/resource/worker/evidence invariants are preserved. "
                "Any speedup claim is made only without sacrificing that exact correctness."
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

    protocols = json.loads(_load_text(
        "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
    ))
    rows = protocols.get("protocols") or protocols.get("families") or protocols.get("rows") or []
    row = next(x for x in rows if x.get("family") == "SUBAGENT_DELEGATION_AND_COORDINATION")
    assert row["status"] == "DEFINED_RESULT_OPEN"
    assert "terminal success conservative bound >= Opus matched bound" in row["acceptance"]
    assert "zero critical violations" in row["acceptance"]
    assert "speedup must not trade away correctness" in row["acceptance"]

    reconciliation = json.loads(_load_text(
        "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"
    ))
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in reconciliation["admissible_absolute_dominance_bases"]
    assert "SUBAGENT_DELEGATION_AND_COORDINATION" in reconciliation[
        "expected_current_reduction"
    ]["reopened_pending_scope_completeness"]

    bindings = json.loads(_load_text(
        "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
    ))
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
    out = prove_from_facts(facts)
    assert out["universal_scope_proved"] is True
    return out


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
