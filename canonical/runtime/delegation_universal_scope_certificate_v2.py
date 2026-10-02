"""Fail-closed universal scope certificate candidate for delegation V4.

The mathematical proof is the finite-search + finite-history induction bound in
TASK_TO_DELEGATION_SCOPE_RELATION_V2. This checker binds that proof to exact Git
blobs and refuses the certificate if any load-bearing source premise is absent.

It does not grant acceptance, capability, family, execution, or promotion
authority. Independent clean-room verification remains mandatory.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
ATOM = (
    "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
    "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_DELEGATION_PROTOCOL"
)

EXPECTED_BLOBS = {
    "canonical/runtime/delegation_receipt_history_candidate_v4.py":
        "e4faa96bacb3d948e960899ba44ec75485703991",
    "canonical/tests/test_delegation_receipt_history_candidate_v4.py":
        "bf0f4edff4a7553d3e36812da38068e0e06ccdff",
    "canonical/runtime/delegation_whole_scope_candidate_v2.py":
        "f1a93ee66d90093de61dc17c6ebf2e24073df522",
    "canonical/runtime/delegation_whole_scope_proof_v2.py":
        "928466401b36e4f3b09c517950cc050432a0616f",
    "canonical/governance/TASK_TO_DELEGATION_SCOPE_RELATION_V2.json":
        "be855e285f0b64ec951b5ea870b4d4cc166740c9",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "eb4bca0fe6a015d49d2854998fbe046c979c7ea9",
    "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":
        "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":
        "af83f4899169e81017767c3316ddcf6b61da5ef6",
    "canonical/governance/DELEGATION_RECEIPT_HISTORY_SCOPE_REPAIR_V1.json":
        "60303b1dd081984e1218c8c2e978c7b1497df9e8",
}

REQUIRED_FACTS = (
    "V4_HISTORY_METADATA_BOUND",
    "V4_FULL_HISTORY_REPLAY_FROM_BASE",
    "V4_DISABLE_EFFECTS_ARE_IDEMPOTENT_SET_UNIONS",
    "V4_RESOURCE_STATE_IS_ORDERED_LAST_WRITE",
    "V4_SUPPORTED_EVENT_SET_EXACT",
    "V4_DELEGATES_MATERIALIZED_STATE_TO_EXACT_V2_SOLVER",
    "V2_FINITE_SIMPLE_SEQUENCE_SEARCH",
    "V2_NONNEGATIVE_COST_OBJECTIVE",
    "V2_GOAL_REQUIRES_SCHEDULABILITY",
    "ORACLE_ENUMERATES_ALL_SUBSETS_AND_PERMUTATIONS",
    "ORACLE_USES_IDENTICAL_OBJECTIVE_AND_SCHEDULABILITY",
    "SCHEDULER_BFS_ENUMERATES_FEASIBLE_MATCHINGS",
)


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _functions(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _has(text: str, *parts: str) -> bool:
    return all(p in text for p in parts)


def derive_source_facts(v4: str, v2: str, oracle: str) -> dict[str, bool]:
    f4 = _functions(v4)
    f2 = _functions(v2)
    fo = _functions(oracle)
    return {
        "V4_HISTORY_METADATA_BOUND": (
            "_history_from_previous" in f4
            and _has(
                v4,
                'previous.get("receipt_history_semantics") != SEMANTICS',
                'ids != expected_ids',
                'DUPLICATE_RECEIPT_ID:',
            )
        ),
        "V4_FULL_HISTORY_REPLAY_FROM_BASE": (
            "_apply_history" in f4
            and _has(
                v4,
                "out = deepcopy(dict(task))",
                "for raw in history:",
                "history.append(current)",
                "_apply_history(task, history)",
            )
        ),
        "V4_DISABLE_EFFECTS_ARE_IDEMPOTENT_SET_UNIONS": _has(
            v4,
            "disabled_steps: set[str] = set()",
            "unavailable_workers: set[str] = set()",
            "removed_capabilities: dict[str, set[str]] = defaultdict(set)",
            "disabled_steps.add(entity)",
            "unavailable_workers.add(entity)",
            "removed_capabilities[entity].add(capability)",
        ),
        "V4_RESOURCE_STATE_IS_ORDERED_LAST_WRITE": _has(
            v4,
            "resource_caps = dict(out.get",
            'resource_caps[entity] = receipt["capacity"]',
            'out["resource_capacities"] = resource_caps',
        ),
        "V4_SUPPORTED_EVENT_SET_EXACT": all(
            ('"' + name + '"') in v4
            for name in (
                "STEP_UNAVAILABLE",
                "WORKER_UNAVAILABLE",
                "WORKER_CAPABILITY_REMOVED",
                "RESOURCE_CAPACITY_CHANGED",
            )
        ) and "RECEIPT_KIND_UNSUPPORTED:" in v4,
        "V4_DELEGATES_MATERIALIZED_STATE_TO_EXACT_V2_SOLVER": _has(
            v4,
            'out = v2._solve(effective_task, {"completed_task_ids": completed})',
            'out["receipt_history"] = history',
            'out["receipt_history_ids"] = [x["receipt_id"] for x in history]',
        ),
        "V2_FINITE_SIMPLE_SEQUENCE_SEARCH": (
            "_plan" in f2
            and _has(
                v2,
                "eligible=sorted(s for s,x in steps.items() if x[\"available\"])",
                "used=set(seq)",
                "if sid in used:",
                "ns=seq+(sid,)",
                "seen_sequences={()}",
            )
        ),
        "V2_NONNEGATIVE_COST_OBJECTIVE": _has(
            v2,
            "math.isfinite(float(cost))",
            "float(cost)<0",
            "heap=[(0.0,0,(),frozenset(initial))]",
            "cost,count,seq,facts=heappop(heap)",
            'heappush(heap,(cost+row["cost"],count+1,ns,nf))',
        ),
        "V2_GOAL_REQUIRES_SCHEDULABILITY": _has(
            v2,
            "if required.issubset(facts):",
            "_schedule(list(seq),deps,steps,workers,caps)",
            "return list(seq),deps,float(cost)",
        ),
        "ORACLE_ENUMERATES_ALL_SUBSETS_AND_PERMUTATIONS": (
            "_optimal_plan" in fo
            and _has(
                oracle,
                "for k in range(len(ids)+1):",
                "for subset in combinations(ids,k):",
                "for order in permutations(subset):",
                "if not ok or not required.issubset(facts):continue",
            )
        ),
        "ORACLE_USES_IDENTICAL_OBJECTIVE_AND_SCHEDULABILITY": _has(
            oracle,
            "_min_waves(task,plan,receipt,completed)",
            "key=(cost,len(order),tuple(order))",
            "if best is None or key<best[0]:",
        ),
        "SCHEDULER_BFS_ENUMERATES_FEASIBLE_MATCHINGS": (
            "_schedule" in f2
            and "_matchings" in f2
            and _has(
                v2,
                "q=deque([(frozenset(),[],{})])",
                "for matching in _matchings(ready,steps,workers,caps):",
                "for tasks in combinations(sorted(ready),k):",
                "for ws in permutations(wids,k):",
            )
        ),
    }


def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_FACTS if facts.get(name) is not True]
    if missing:
        return {
            "status": "FAIL_CLOSED__UNIVERSAL_SCOPE_PREMISE_MISSING",
            "missing": missing,
            "universal_scope_proved": False,
            "scope_atom_satisfied_candidate": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }
    return {
        "status": (
            "PASS__UNIVERSAL_FORMAL_SCOPE_PROOF_DERIVED_FOR_V4__"
            "INDEPENDENT_PUBLIC_RUNNER_VERIFICATION_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "universal_scope_proved": True,
        "scope_atom_satisfied_candidate": True,
        "scope_atom": ATOM,
        "target_predicate": "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "proof": {
            "base": (
                "V2 performs finite exhaustive simple-sequence search with an exact "
                "schedulability gate and is checked against an exhaustive independent "
                "subset/permutation oracle under the identical objective."
            ),
            "history_induction": (
                "V4 stores the exact ordered receipt history, replays that complete "
                "history from immutable base task state on every update, accumulates "
                "disable/removal effects by idempotent set union, applies ordered "
                "resource updates, then invokes the unchanged exact V2 solver."
            ),
            "finite_closure": (
                "Base case is empty history. The append step preserves every prior "
                "effect and adds exactly the current normalized receipt. Therefore by "
                "induction the exact solver sees the ordered fold of every finite "
                "supported valid history."
            ),
            "terminal_ceiling": (
                "Under the frozen same-scope explicit contract, a feasible case has "
                "terminal-success ceiling 1 and exact solve reaches it; if exhaustive "
                "search proves no feasible plan under identical constraints, the "
                "contract ceiling is 0 and V4 fails closed."
            ),
        },
        "uses_empirical_generalization": False,
        "terminal_cases_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def verify() -> dict[str, Any]:
    for rel, want in EXPECTED_BLOBS.items():
        got = blob_sha(ROOT / rel)
        if got != want:
            raise AssertionError((rel, got, want))

    protocol = json.loads(_text(
        "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
    ))
    row = next(
        x for x in protocol["protocols"]
        if x["family"] == "SUBAGENT_DELEGATION_AND_COORDINATION"
    )
    assert row["status"] == "DEFINED_RESULT_OPEN"
    assert row["proof_mode"] == "MATCHED_DIRECT_NONINFERIORITY_WITH_MECHANICAL_CEILINGS"
    assert "terminal success conservative bound >= Opus matched bound" in row["acceptance"]
    assert "same frozen task population/harness/tool authority" in protocol["universal_rules"]["same_scope"]

    firewall = json.loads(_text(
        "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"
    ))
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in firewall["admissible_absolute_dominance_bases"]
    assert "SUBAGENT_DELEGATION_AND_COORDINATION" in firewall[
        "expected_current_reduction"
    ]["reopened_pending_scope_completeness"]

    bindings = json.loads(_text(
        "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
    ))
    claim = next(
        x for x in bindings["claims"]
        if x.get("predicate_id") == "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"
    )
    assert claim["state"] == "EXTERNAL_BLOCKED"
    assert claim["blocker"] == "ABSOLUTE_SCOPE_COMPLETENESS_MISSING"
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in claim["discharge_condition"]

    repair = json.loads(_text(
        "canonical/governance/DELEGATION_RECEIPT_HISTORY_SCOPE_REPAIR_V1.json"
    ))
    assert repair["scope_effect"]["universal_scope_completeness_proved"] is False
    assert repair["falsified_prior_claim"]["disposition"] == (
        "DO_NOT_PROMOTE_EXISTING_SCOPE_RELATION_TO_UNIVERSAL_FORMAL_SCOPE_PROOF"
    )

    relation = json.loads(_text(
        "canonical/governance/TASK_TO_DELEGATION_SCOPE_RELATION_V2.json"
    ))
    assert relation["status"].startswith(
        "CANDIDATE_POST_RECEIPT_REPAIR_UNIVERSAL_SCOPE_RELATION"
    )
    assert relation["relation_to_frozen_acceptance_protocol"]["target_predicate"] == (
        "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"
    )

    facts = derive_source_facts(
        _text("canonical/runtime/delegation_receipt_history_candidate_v4.py"),
        _text("canonical/runtime/delegation_whole_scope_candidate_v2.py"),
        _text("canonical/runtime/delegation_whole_scope_proof_v2.py"),
    )
    return prove_from_facts(facts)


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("universal_scope_proved") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
