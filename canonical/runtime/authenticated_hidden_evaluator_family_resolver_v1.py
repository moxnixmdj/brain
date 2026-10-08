"""Authenticated hidden-evaluator family resolver V1.

This is a fail-closed authority wrapper around Brain's already-verified monotone
hidden-evaluator dominance ideas.

It closes exactly one seam the earlier mathematical kernels intentionally left
open: a caller may NOT obtain target-relative noninferiority merely by naming a
"material order certificate".  The actual target evaluator must be independently
bound into the claimed evaluator family, the outcome basis/material order must
be independently verified complete/sound for the comparison scope, and any
Brain/target support or distribution used by the proof must be content-addressed
and independently verified.

Two sound proof modes are exposed:

1. TARGET_FREE_TOP_SUPPORT
   If every outcome Brain can produce is >= every admissible outcome in the
   authenticated material order, Brain is noninferior for every target
   distribution and every bounded target evaluator monotone in that order.

2. MATCHED_DISTRIBUTION_COUPLING
   If authenticated target and Brain outcome distributions admit a full-mass
   dominance-preserving coupling, Brain is noninferior for every bounded target
   evaluator monotone in the authenticated order.

On an unresolved coupling, the resolver returns exact unmatched target mass and
ranks single missing dominance relations by how much each would increase the
maximum transportable mass.  This is a decision-relevant refinement witness,
not permission to invent that relation.

No mode grants benchmark acceptance, DB admission, U-empty, ownership finality,
or terminal authority by itself.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)
from canonical.runtime.hidden_evaluator_monotone_coupling_v1 import solve as coupling_solve

SCHEMA = "PROJECT_BRAIN_AUTHENTICATED_HIDDEN_EVALUATOR_FAMILY_RESOLVER_V1"

CONTRACT_SCHEMA = "PROJECT_BRAIN_HIDDEN_EVALUATOR_FAMILY_CONTRACT_V1"
CONTRACT_VERIFY_SCHEMA = "PROJECT_BRAIN_HIDDEN_EVALUATOR_FAMILY_CONTRACT_VERIFY_V1"
SUPPORT_SCHEMA = "PROJECT_BRAIN_AUTHENTICATED_OUTCOME_SUPPORT_V1"
SUPPORT_VERIFY_SCHEMA = "PROJECT_BRAIN_AUTHENTICATED_OUTCOME_SUPPORT_VERIFY_V1"
DIST_SCHEMA = "PROJECT_BRAIN_AUTHENTICATED_OUTCOME_DISTRIBUTION_V1"
DIST_VERIFY_SCHEMA = "PROJECT_BRAIN_AUTHENTICATED_OUTCOME_DISTRIBUTION_VERIFY_V1"

FAMILY = "BOUNDED_UTILITY_MONOTONE_NONDECREASING_ON_COMPLETE_MATERIAL_PARTIAL_ORDER"
MODES = {"TARGET_FREE_TOP_SUPPORT", "MATCHED_DISTRIBUTION_COUPLING"}
ROOT = Path(__file__).resolve().parents[2]


class ResolverError(ValueError):
    pass


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "universal_monotone_utility_noninferiority": False,
        "target_distribution_required": None,
        "actual_target_evaluator_family_authenticated": False,
        "db_admission_authority": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _frac(value: Any, label: str) -> Fraction:
    if isinstance(value, bool):
        raise ResolverError(label + "_BOOLEAN_FORBIDDEN")
    try:
        return Fraction(str(value))
    except Exception as exc:
        raise ResolverError(label + "_INVALID") from exc


def _resolve_pair(
    binding: Any,
    *,
    repo_root: str | Path,
    receipt_schema: str,
    verify_schema: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not isinstance(binding, Mapping):
        raise ResolverError("RECEIPT_PAIR_REQUIRED")
    rr = resolve_receipt_bytes(binding.get("receipt"), repo_root=repo_root)
    rv = resolve_receipt_bytes(binding.get("verification"), repo_root=repo_root)
    rd = rr["document"]
    vd = rv["document"]
    if rd.get("schema") != receipt_schema:
        raise ResolverError("RECEIPT_SCHEMA_INVALID:" + receipt_schema)
    if vd.get("schema") != verify_schema:
        raise ResolverError("VERIFY_SCHEMA_INVALID:" + verify_schema)
    if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
        raise ResolverError("VERIFY_SUBJECT_BLOB_MISMATCH")
    if rd.get("pass") is not True:
        raise ResolverError("RECEIPT_NOT_PASS")
    if vd.get("pass") is not True or vd.get("independent_verified") is not True:
        raise ResolverError("INDEPENDENT_VERIFICATION_NOT_PASS")
    return rd, vd, rr, rv


def _ids(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        raise ResolverError(label + "_INVALID")
    out = list(value)
    if any(not isinstance(x, str) or not x for x in out):
        raise ResolverError(label + "_ID_INVALID")
    if len(out) != len(set(out)):
        raise ResolverError(label + "_DUPLICATE")
    return out


def _order_contract(binding: Any, *, repo_root: str | Path) -> dict[str, Any]:
    rd, vd, rr, rv = _resolve_pair(
        binding,
        repo_root=repo_root,
        receipt_schema=CONTRACT_SCHEMA,
        verify_schema=CONTRACT_VERIFY_SCHEMA,
    )
    comparison_id = rd.get("comparison_id")
    evaluator_id = rd.get("evaluator_id")
    if not isinstance(comparison_id, str) or not comparison_id:
        raise ResolverError("COMPARISON_ID_INVALID")
    if not isinstance(evaluator_id, str) or not evaluator_id:
        raise ResolverError("EVALUATOR_ID_INVALID")
    if rd.get("evaluator_family") != FAMILY:
        raise ResolverError("EVALUATOR_FAMILY_INVALID")

    required_true = (
        "outcome_basis_scope_complete",
        "load_bearing_material_dimensions_complete",
        "material_order_sound",
        "actual_target_evaluator_in_family",
        "actual_target_evaluator_bounded",
        "actual_target_evaluator_monotone_nondecreasing_on_material_order",
    )
    for field in required_true:
        if rd.get(field) is not True:
            raise ResolverError("CONTRACT_PREMISE_NOT_PROVED:" + field)
        if vd.get(field) is not True:
            raise ResolverError("CONTRACT_PREMISE_NOT_INDEPENDENTLY_VERIFIED:" + field)

    for field in ("comparison_id", "evaluator_id", "evaluator_family"):
        if vd.get(field) != rd.get(field):
            raise ResolverError("CONTRACT_VERIFY_BINDING_MISMATCH:" + field)

    outcomes = _ids(rd.get("outcome_ids"), "OUTCOME_IDS")
    if vd.get("outcome_ids") != outcomes:
        raise ResolverError("OUTCOME_IDS_VERIFY_MISMATCH")
    outcome_set = set(outcomes)

    raw_edges = rd.get("dominance_edges")
    if not isinstance(raw_edges, list):
        raise ResolverError("DOMINANCE_EDGES_INVALID")
    reach: dict[str, set[str]] = {x: {x} for x in outcomes}
    normalized_edges: set[tuple[str, str]] = set()
    for i, row in enumerate(raw_edges):
        if not isinstance(row, Mapping):
            raise ResolverError(f"DOMINANCE_EDGE_INVALID:{i}")
        better = row.get("better")
        worse = row.get("worse")
        if better not in outcome_set or worse not in outcome_set:
            raise ResolverError(f"DOMINANCE_EDGE_UNKNOWN_OUTCOME:{i}")
        normalized_edges.add((str(better), str(worse)))
        reach[str(better)].add(str(worse))

    # Compute exact transitive closure, then require a partial order.
    changed = True
    while changed:
        changed = False
        for a in outcomes:
            expanded = set(reach[a])
            for b in tuple(reach[a]):
                expanded.update(reach[b])
            if expanded != reach[a]:
                reach[a] = expanded
                changed = True

    for a in outcomes:
        for b in outcomes:
            if a != b and b in reach[a] and a in reach[b]:
                raise ResolverError("MATERIAL_ORDER_NOT_ANTISYMMETRIC:" + a + ":" + b)

    canonical_closure = [
        {"better": a, "worse": b}
        for a in sorted(outcomes)
        for b in sorted(reach[a])
    ]
    if vd.get("dominance_transitive_closure") != canonical_closure:
        raise ResolverError("DOMINANCE_CLOSURE_VERIFY_MISMATCH")

    return {
        "comparison_id": comparison_id,
        "evaluator_id": evaluator_id,
        "outcomes": outcomes,
        "reach": reach,
        "closure": canonical_closure,
        "contract_receipt": {
            "path": rr["path"],
            "git_blob_sha": rr["git_blob_sha"],
            "verification_path": rv["path"],
            "verification_git_blob_sha": rv["git_blob_sha"],
        },
    }


def _support(binding: Any, *, repo_root: str | Path, contract: Mapping[str, Any]) -> list[str]:
    rd, vd, _, _ = _resolve_pair(
        binding,
        repo_root=repo_root,
        receipt_schema=SUPPORT_SCHEMA,
        verify_schema=SUPPORT_VERIFY_SCHEMA,
    )
    if rd.get("comparison_id") != contract["comparison_id"] or vd.get("comparison_id") != contract["comparison_id"]:
        raise ResolverError("SUPPORT_COMPARISON_ID_MISMATCH")
    if rd.get("role") != "BRAIN" or vd.get("role") != "BRAIN":
        raise ResolverError("SUPPORT_ROLE_MUST_BE_BRAIN")
    if rd.get("support_scope_complete") is not True or vd.get("support_scope_complete") is not True:
        raise ResolverError("BRAIN_SUPPORT_NOT_SCOPE_COMPLETE")
    if rd.get("deployed_exact") is not True or vd.get("deployed_exact") is not True:
        raise ResolverError("BRAIN_SUPPORT_NOT_DEPLOYED_EXACT")
    support = _ids(rd.get("support_ids"), "SUPPORT_IDS")
    if vd.get("support_ids") != support:
        raise ResolverError("SUPPORT_IDS_VERIFY_MISMATCH")
    if not set(support).issubset(set(contract["outcomes"])):
        raise ResolverError("SUPPORT_OUTSIDE_OUTCOME_BASIS")
    return support


def _distribution(
    binding: Any,
    *,
    repo_root: str | Path,
    contract: Mapping[str, Any],
    role: str,
) -> list[dict[str, str]]:
    rd, vd, _, _ = _resolve_pair(
        binding,
        repo_root=repo_root,
        receipt_schema=DIST_SCHEMA,
        verify_schema=DIST_VERIFY_SCHEMA,
    )
    if rd.get("comparison_id") != contract["comparison_id"] or vd.get("comparison_id") != contract["comparison_id"]:
        raise ResolverError("DISTRIBUTION_COMPARISON_ID_MISMATCH:" + role)
    if rd.get("role") != role or vd.get("role") != role:
        raise ResolverError("DISTRIBUTION_ROLE_MISMATCH:" + role)
    if rd.get("distribution_scope_complete") is not True or vd.get("distribution_scope_complete") is not True:
        raise ResolverError("DISTRIBUTION_NOT_SCOPE_COMPLETE:" + role)
    rows = rd.get("distribution")
    if not isinstance(rows, list) or not rows:
        raise ResolverError("DISTRIBUTION_ROWS_INVALID:" + role)
    if vd.get("distribution") != rows:
        raise ResolverError("DISTRIBUTION_VERIFY_MISMATCH:" + role)
    seen: set[str] = set()
    total = Fraction(0)
    normalized = []
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ResolverError(f"DISTRIBUTION_ROW_INVALID:{role}:{i}")
        oid = row.get("id")
        if not isinstance(oid, str) or not oid or oid in seen:
            raise ResolverError(f"DISTRIBUTION_ID_INVALID_OR_DUPLICATE:{role}:{i}")
        if oid not in set(contract["outcomes"]):
            raise ResolverError("DISTRIBUTION_OUTCOME_OUTSIDE_BASIS:" + role + ":" + oid)
        seen.add(oid)
        p = _frac(row.get("probability"), "PROBABILITY")
        if p < 0:
            raise ResolverError("DISTRIBUTION_NEGATIVE_PROBABILITY:" + role + ":" + oid)
        total += p
        normalized.append({"id": oid, "probability": str(p)})
    if total != 1:
        raise ResolverError("DISTRIBUTION_MUST_SUM_TO_ONE:" + role)
    return normalized


def _coupling_edges(contract: Mapping[str, Any]) -> list[dict[str, str]]:
    # Existing kernel edge orientation is {target,worse -> brain,better}.
    return [
        {"target": worse, "brain": better}
        for better in sorted(contract["reach"])
        for worse in sorted(contract["reach"][better])
    ]


def _coupled_by_target(result: Mapping[str, Any]) -> dict[str, Fraction]:
    out: dict[str, Fraction] = {}
    for row in result.get("coupling") or []:
        if not isinstance(row, Mapping):
            continue
        t = row.get("target")
        if isinstance(t, str):
            out[t] = out.get(t, Fraction(0)) + _frac(row.get("mass"), "COUPLED_MASS")
    return out


def _mass_map(rows: Sequence[Mapping[str, str]]) -> dict[str, Fraction]:
    return {str(row["id"]): _frac(row["probability"], "PROBABILITY") for row in rows}


def _run_coupling(
    *,
    contract: Mapping[str, Any],
    target: list[dict[str, str]],
    brain: list[dict[str, str]],
    extra_pair: tuple[str, str] | None = None,
) -> dict[str, Any]:
    # extra_pair = (better_brain_outcome, worse_target_outcome).
    edges = set(
        (str(row["target"]), str(row["brain"]))
        for row in _coupling_edges(contract)
    )
    if extra_pair is not None:
        better, worse = extra_pair
        edges.add((worse, better))
    return coupling_solve({
        "target_distribution": target,
        "brain_distribution": brain,
        "dominance_edges": [
            {"target": t, "brain": b} for t, b in sorted(edges)
        ],
        "material_order_certificate": "AUTHENTICATED_BY_WRAPPER",
    })


def _coupling_witness(
    *,
    contract: Mapping[str, Any],
    target: list[dict[str, str]],
    brain: list[dict[str, str]],
    base: Mapping[str, Any],
) -> dict[str, Any]:
    target_mass = _mass_map(target)
    coupled = _coupled_by_target(base)
    unmatched = [
        {
            "target_outcome_id": t,
            "unmatched_mass": str(target_mass[t] - coupled.get(t, Fraction(0))),
        }
        for t in sorted(target_mass)
        if target_mass[t] - coupled.get(t, Fraction(0)) > 0
    ]

    base_flow = _frac(base.get("max_coupled_mass"), "MAX_COUPLED_MASS")
    candidates = []
    brain_ids = sorted(_mass_map(brain))
    for item in unmatched:
        t = item["target_outcome_id"]
        for b in brain_ids:
            if t in contract["reach"][b]:
                continue
            trial = _run_coupling(contract=contract, target=target, brain=brain, extra_pair=(b, t))
            trial_flow = _frac(trial.get("max_coupled_mass"), "TRIAL_MAX_COUPLED_MASS")
            gain = trial_flow - base_flow
            if gain > 0:
                candidates.append({
                    "missing_relation": {"better": b, "worse": t},
                    "coupled_mass_gain": str(gain),
                    "post_relation_max_coupled_mass": str(trial_flow),
                    "single_relation_sufficient": trial_flow == 1,
                })
    candidates.sort(
        key=lambda row: (
            not bool(row["single_relation_sufficient"]),
            -_frac(row["coupled_mass_gain"], "GAIN"),
            row["missing_relation"]["better"],
            row["missing_relation"]["worse"],
        )
    )
    return {
        "unmatched_target_mass": unmatched,
        "decision_relevant_missing_relation_candidates": candidates,
        "witness_rule": (
            "RELATIONS_ARE_DIAGNOSTIC_ONLY__THEY_IDENTIFY_SINGLE_ORDER_FACTS_WHOSE_"
            "AUTHENTICATION_WOULD_CHANGE_THE_COUPLING_PROOF__THE_RUNTIME_NEVER_ASSERTS_THEM"
        ),
    }


def evaluate(bundle: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    try:
        if not isinstance(bundle, Mapping):
            raise ResolverError("BUNDLE_INVALID")
        mode = bundle.get("mode")
        if mode not in MODES:
            raise ResolverError("MODE_INVALID")

        contract = _order_contract(bundle.get("evaluator_contract_binding"), repo_root=repo_root)

        common = {
            "schema": SCHEMA,
            "comparison_id": contract["comparison_id"],
            "evaluator_id": contract["evaluator_id"],
            "evaluator_family": FAMILY,
            "actual_target_evaluator_family_authenticated": True,
            "outcome_basis_scope_complete": True,
            "material_order_authenticated": True,
            "db_admission_authority": False,
            "u_empty_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

        if mode == "TARGET_FREE_TOP_SUPPORT":
            support = _support(bundle.get("brain_support_binding"), repo_root=repo_root, contract=contract)
            missing = [
                {"brain_outcome_id": b, "target_outcome_id": y}
                for b in sorted(support)
                for y in sorted(contract["outcomes"])
                if y not in contract["reach"][b]
            ]
            if missing:
                return {
                    **common,
                    "pass": False,
                    "status": "UNRESOLVED__BRAIN_SUPPORT_NOT_UNIVERSAL_TOP_CLASS",
                    "universal_monotone_utility_noninferiority": False,
                    "target_distribution_required": False,
                    "brain_support_ids": sorted(support),
                    "missing_cross_support_dominance_relations": missing,
                    "next_information_rule": (
                        "DO_NOT_QUERY_TARGET_DISTRIBUTION_YET__FIRST_AUTHENTICATE_ONLY_A_"
                        "MISSING_MATERIAL_ORDER_RELATION_IF_TRUE_OR_PROVE_THE_BRAIN_SUPPORT_"
                        "CAN_BE_NARROWED_TO_A_UNIVERSAL_TOP_CLASS"
                    ),
                }
            return {
                **common,
                "pass": True,
                "status": "PASS__AUTHENTICATED_TARGET_FREE_UNIVERSAL_MONOTONE_NONINFERIORITY",
                "universal_monotone_utility_noninferiority": True,
                "target_distribution_required": False,
                "brain_support_ids": sorted(support),
                "proof_mode": "TARGET_FREE_TOP_SUPPORT",
                "acceptance_credit_delta": 0,
            }

        target = _distribution(
            bundle.get("target_distribution_binding"),
            repo_root=repo_root,
            contract=contract,
            role="TARGET",
        )
        brain = _distribution(
            bundle.get("brain_distribution_binding"),
            repo_root=repo_root,
            contract=contract,
            role="BRAIN",
        )
        result = _run_coupling(contract=contract, target=target, brain=brain)
        passed = result.get("universal_monotone_utility_noninferiority") is True
        out = {
            **common,
            "pass": passed,
            "status": (
                "PASS__AUTHENTICATED_FULL_MASS_DOMINANCE_PRESERVING_COUPLING"
                if passed
                else "UNRESOLVED__AUTHENTICATED_MONOTONE_FAMILY_BUT_NO_FULL_MASS_COUPLING"
            ),
            "universal_monotone_utility_noninferiority": passed,
            "target_distribution_required": True,
            "max_coupled_mass": result.get("max_coupled_mass"),
            "coupling": result.get("coupling"),
            "proof_mode": "MATCHED_DISTRIBUTION_COUPLING",
            "acceptance_credit_delta": 0,
        }
        if not passed:
            out.update(_coupling_witness(contract=contract, target=target, brain=brain, base=result))
        return out

    except (ResolverError, ReceiptResolutionError, ValueError, TypeError) as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def verify(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {"bundle", "repo_root"}:
        return _fail("VERIFY_PAYLOAD_INVALID")
    if proposal not in ({}, None):
        return _fail("PROPOSAL_FORBIDDEN")
    return evaluate(payload["bundle"], repo_root=payload["repo_root"])


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    args = args or {}
    return evaluate(args.get("bundle"), repo_root=args.get("repo_root", ROOT))
