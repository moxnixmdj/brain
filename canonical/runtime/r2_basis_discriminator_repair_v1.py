"""Deterministic R2 discriminator synthesis from an existing CEGAR conflict witness.

A conflict witness contains two surviving Boolean models with disjoint adequate
policy sets. Any one-atom discriminator capable of separating that pair must
differ on at least one already-declared decision-basis atom. This module proposes
only those existing atoms as candidate questions and grants them no truth,
observability, adequacy, or acceptance authority.

Downstream CEGAR must prove whether a proposed discriminator actually resolves
all surviving policy regions. If selected, the ordinary source-bound truth gate
must separately establish its value.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R2_BASIS_DISCRIMINATOR_REPAIR_V1"
SUPPORTED_ARTIFACT = "POLICY_CHANGING_DISCRIMINATOR_OR_STRONGER_ADEQUACY"
MAX_SYNTHESIZED_DISCRIMINATORS = 64


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "repair_authority": False,
        "semantic_truth_authority": False,
        "discriminator_truth_authority": False,
        "policy_adequacy_authority": False,
        "goal_satisfaction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _auto_id(atom_id: str) -> str:
    return "R2_AUTO_BASIS_ATOM::" + sha256(atom_id.encode("utf-8")).hexdigest()[:20]


def repair(
    request: Mapping[str, Any],
    next_policy_request: Mapping[str, Any] | None,
) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping):
            return _base("FAIL_CLOSED", reason="REQUEST_NOT_OBJECT")
        if not isinstance(next_policy_request, Mapping):
            return _base("NOT_APPLICABLE__NO_POLICY_REQUEST")
        if next_policy_request.get("required_artifact") != SUPPORTED_ARTIFACT:
            return _base(
                "NOT_APPLICABLE__POLICY_ARTIFACT_NOT_BASIS_DISCRIMINATOR_GAP",
                required_artifact=next_policy_request.get("required_artifact"),
            )

        search = next_policy_request.get("search_context")
        if not isinstance(search, Mapping):
            return _base("UNRESOLVED__VERIFIED_SEARCH_CONTEXT_REQUIRED")
        basis = search.get("decision_basis")
        witness = search.get("conflicting_policy_region_witness")
        if (
            not isinstance(basis, list)
            or not basis
            or any(not isinstance(x, str) or not x for x in basis)
            or len(set(basis)) != len(basis)
        ):
            return _base("UNRESOLVED__DECISION_BASIS_REQUIRED")
        if not isinstance(witness, list) or len(witness) != 2:
            return _base("UNRESOLVED__TWO_MODEL_CONFLICT_WITNESS_REQUIRED")

        valuations: list[Mapping[str, Any]] = []
        adequate_sets: list[set[str]] = []
        for row in witness:
            if not isinstance(row, Mapping):
                return _base("FAIL_CLOSED", reason="CONFLICT_WITNESS_ROW_INVALID")
            valuation = row.get("valuation")
            policies = row.get("adequate_policy_ids")
            if not isinstance(valuation, Mapping):
                return _base("FAIL_CLOSED", reason="CONFLICT_WITNESS_VALUATION_INVALID")
            if (
                not isinstance(policies, list)
                or any(not isinstance(x, str) or not x for x in policies)
            ):
                return _base("FAIL_CLOSED", reason="CONFLICT_WITNESS_POLICY_SET_INVALID")
            if any(atom not in valuation or valuation.get(atom) not in (True, False) for atom in basis):
                return _base("FAIL_CLOSED", reason="CONFLICT_WITNESS_BASIS_COVERAGE_INVALID")
            valuations.append(valuation)
            adequate_sets.append(set(policies))

        if adequate_sets[0].intersection(adequate_sets[1]):
            return _base(
                "FAIL_CLOSED",
                reason="CONFLICT_WITNESS_POLICY_SETS_NOT_DISJOINT",
            )

        differing = [
            atom for atom in basis
            if valuations[0].get(atom) != valuations[1].get(atom)
        ]
        if not differing:
            return _base(
                "FAIL_CLOSED",
                reason="CONFLICT_WITNESS_HAS_NO_DIFFERING_DECISION_BASIS_ATOM",
            )

        decision = request.get("decision_payload")
        if not isinstance(decision, Mapping):
            return _base("UNRESOLVED__DECISION_PAYLOAD_REQUIRED")
        loop = decision.get("bound_relevance_cegar_loop")
        if not isinstance(loop, Mapping):
            return _base("UNRESOLVED__CEGAR_LOOP_REQUIRED")
        problem = loop.get("cegar_problem")
        if not isinstance(problem, Mapping):
            return _base("UNRESOLVED__CEGAR_PROBLEM_REQUIRED")

        existing = problem.get("discriminators", [])
        if not isinstance(existing, list):
            return _base("FAIL_CLOSED", reason="EXISTING_DISCRIMINATORS_NOT_LIST")

        existing_ids: set[str] = set()
        existing_atoms: set[str] = set()
        for row in existing:
            if not isinstance(row, Mapping):
                return _base("FAIL_CLOSED", reason="EXISTING_DISCRIMINATOR_ROW_INVALID")
            discriminator_id = row.get("discriminator_id")
            if isinstance(discriminator_id, str) and discriminator_id:
                existing_ids.add(discriminator_id)
            formula = row.get("formula")
            if isinstance(formula, Mapping):
                if set(formula) == {"op", "id"} and formula.get("op") == "ATOM":
                    atom = formula.get("id")
                    if isinstance(atom, str) and atom:
                        existing_atoms.add(atom)
                elif set(formula) == {"op", "arg"} and formula.get("op") == "NOT":
                    arg = formula.get("arg")
                    if (
                        isinstance(arg, Mapping)
                        and set(arg) == {"op", "id"}
                        and arg.get("op") == "ATOM"
                        and isinstance(arg.get("id"), str)
                    ):
                        existing_atoms.add(str(arg["id"]))

        additions: list[dict[str, Any]] = []
        for atom in sorted(differing):
            if atom in existing_atoms:
                continue
            discriminator_id = _auto_id(atom)
            if discriminator_id in existing_ids:
                continue
            additions.append(
                {
                    "discriminator_id": discriminator_id,
                    "formula": {"op": "ATOM", "id": atom},
                }
            )
            if len(additions) >= MAX_SYNTHESIZED_DISCRIMINATORS:
                break

        if not additions:
            return _base(
                "UNRESOLVED__NO_NEW_BASIS_DISCRIMINATOR_CANDIDATE",
                differing_basis_atoms=sorted(differing),
            )

        patched_decision = deepcopy(dict(decision))
        patched_loop = patched_decision.get("bound_relevance_cegar_loop")
        if not isinstance(patched_loop, dict):
            patched_loop = deepcopy(dict(loop))
            patched_decision["bound_relevance_cegar_loop"] = patched_loop
        patched_problem = patched_loop.get("cegar_problem")
        if not isinstance(patched_problem, dict):
            patched_problem = deepcopy(dict(problem))
            patched_loop["cegar_problem"] = patched_problem
        patched_problem["discriminators"] = deepcopy(existing) + deepcopy(additions)

        return _base(
            "PASS__DECISION_BASIS_DISCRIMINATORS_PROPOSED_FOR_REVERIFICATION",
            passed=True,
            request_patch={"decision_payload": patched_decision},
            added_discriminator_ids=[row["discriminator_id"] for row in additions],
            added_basis_atoms=[
                str(row["formula"]["id"]) for row in additions
            ],
            conflicting_policy_region_witness=deepcopy(witness),
            downstream_cegar_reverification_required=True,
            downstream_truth_observation_required_if_selected=True,
            cost_note=(
                "NO_COST_ASSERTION_ADDED;DOWNSTREAM_CEGAR_EXISTING_DEFAULT_COST_"
                "CONVENTION_APPLIES_ONLY_TO_SELECTION_AMONG_GENERATED_CANDIDATES"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
