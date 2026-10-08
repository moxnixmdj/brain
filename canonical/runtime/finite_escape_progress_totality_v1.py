"""Finite structural checker for the live escape-progress-totality premise.

For a finite sound Boolean abstraction, this kernel recursively applies the
fixed-point law used by Brain's adaptive positive-cover theorem:

1. terminalize a state when one independently authenticated Brain-owned policy
   is adequate in every surviving model;
2. otherwise choose a declared discriminator that splits the surviving model
   set into two nonempty strict subsets and recurse;
3. return an exact unsplittable obstruction when neither is possible.

The structural rank is the number of surviving models, so every accepted split
strictly decreases it automatically. This module does NOT authenticate that a
discriminator is truthfully observable, safe, or resource-admissible. Therefore
a structurally closed tree is a candidate progress proof only and grants no
U-empty, ABC, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.monotone_semantic_constraint_kernel_v1 import (
    _eval,
    _validate_formula,
    _valuations,
    compile_state,
)

SCHEMA = "PROJECT_BRAIN_FINITE_ESCAPE_PROGRESS_TOTALITY_V1"
ROOT = Path(__file__).resolve().parents[2]
ADEQUACY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1"


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _condition_sha256(condition: Mapping[str, Any]) -> str:
    return sha256(_canon(condition).encode("utf-8")).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _bound_path(raw: Any, *, prefixes: tuple[str, ...]) -> Path:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise ValueError("NONCANONICAL_BINDING_PATH")
    if not any(value.startswith(prefix) for prefix in prefixes):
        raise ValueError("BINDING_PATH_OUTSIDE_ALLOWED_SCOPE")
    full = ROOT / p
    if not full.is_file():
        raise ValueError("BOUND_FILE_MISSING:" + value)
    return full


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("BOUND_JSON_NOT_OBJECT")
    return value


def _authenticate_policy_adequacy(
    policy_id: str,
    condition: Mapping[str, Any],
    binding: Mapping[str, Any] | None,
) -> tuple[bool, dict[str, Any]]:
    if not isinstance(binding, Mapping):
        return False, {"policy_id": policy_id, "reason": "ADEQUACY_BINDING_MISSING"}
    try:
        adequacy_path = _bound_path(
            binding.get("adequacy_certificate_path"),
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification_path = _bound_path(
            binding.get("independent_verification_path"),
            prefixes=("canonical/verification/",),
        )
        adequacy_blob = _git_blob_sha(adequacy_path)
        verification_blob = _git_blob_sha(verification_path)
        if binding.get("adequacy_certificate_blob_sha") != adequacy_blob:
            raise ValueError("ADEQUACY_CERTIFICATE_BLOB_DRIFT")
        if binding.get("independent_verification_blob_sha") != verification_blob:
            raise ValueError("ADEQUACY_VERIFICATION_BLOB_DRIFT")

        adequacy = _load_json(adequacy_path)
        verification = _load_json(verification_path)
        condition_sha = _condition_sha256(condition)
        if adequacy.get("schema") != ADEQUACY_SCHEMA:
            raise ValueError("ADEQUACY_CERTIFICATE_SCHEMA_INVALID")
        if adequacy.get("policy_id") != policy_id:
            raise ValueError("ADEQUACY_POLICY_ID_MISMATCH")
        if adequacy.get("policy_condition_sha256") != condition_sha:
            raise ValueError("ADEQUACY_CONDITION_MISMATCH")
        if adequacy.get("adequacy_proved") is not True:
            raise ValueError("ADEQUACY_NOT_PROVED")
        if adequacy.get("brain_owned") is not True:
            raise ValueError("POLICY_NOT_BRAIN_OWNED")
        if adequacy.get("load_bearing_constraints_preserved") is not True:
            raise ValueError("LOAD_BEARING_CONSTRAINTS_NOT_PRESERVED")

        if verification.get("schema") != VERIFY_SCHEMA:
            raise ValueError("ADEQUACY_VERIFICATION_SCHEMA_INVALID")
        if verification.get("policy_id") != policy_id:
            raise ValueError("ADEQUACY_VERIFICATION_POLICY_ID_MISMATCH")
        if verification.get("subject_git_blob_sha") != adequacy_blob:
            raise ValueError("ADEQUACY_VERIFICATION_SUBJECT_MISMATCH")
        if verification.get("pass") is not True:
            raise ValueError("ADEQUACY_INDEPENDENT_VERIFICATION_NOT_PASS")
        return True, {
            "policy_id": policy_id,
            "condition_sha256": condition_sha,
            "adequacy_certificate_path": str(adequacy_path.relative_to(ROOT)),
            "adequacy_certificate_blob_sha": adequacy_blob,
            "independent_verification_path": str(verification_path.relative_to(ROOT)),
            "independent_verification_blob_sha": verification_blob,
        }
    except Exception as exc:
        return False, {
            "policy_id": policy_id,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "progress_authority": False,
        "truthful_observation_authority": False,
        "refinement_safety_authority": False,
        "resource_authority": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _model_id(basis: Sequence[str], valuation: Mapping[str, bool]) -> str:
    return "".join("1" if valuation[x] else "0" for x in basis)


def _intersection(rows: Sequence[set[str]]) -> list[str]:
    if not rows:
        return []
    value = set(rows[0])
    for row in rows[1:]:
        value.intersection_update(row)
    return sorted(value)


def _authenticate_policies(
    conditions: Mapping[str, Mapping[str, Any]],
    bindings: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[dict[str, Mapping[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_bindings = bindings if isinstance(bindings, Mapping) else {}
    accepted: dict[str, Mapping[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for policy_id, condition in sorted(conditions.items()):
        ok, receipt = _authenticate_policy_adequacy(
            policy_id, condition, raw_bindings.get(policy_id)
        )
        if ok:
            accepted[policy_id] = condition
            receipts.append(receipt)
        else:
            rejected.append(receipt)
    return accepted, receipts, rejected


def solve(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_MAPPING_REQUIRED")

    basis = problem.get("decision_basis")
    if (
        not isinstance(basis, Sequence)
        or isinstance(basis, (str, bytes))
        or not basis
        or len(set(basis)) != len(basis)
        or any(not isinstance(x, str) or not x for x in basis)
    ):
        return _fail("DECISION_BASIS_INVALID")
    basis = list(basis)
    basis_set = set(basis)

    policies = problem.get("policy_conditions")
    if not isinstance(policies, Mapping) or not policies:
        return _fail("POLICY_CONDITIONS_REQUIRED")
    policy_errors: list[str] = []
    for policy_id, condition in policies.items():
        if not isinstance(policy_id, str) or not policy_id:
            policy_errors.append("POLICY_ID_INVALID")
            continue
        for error in _validate_formula(condition, basis_set):
            policy_errors.append(f"POLICY_{policy_id}:{error}")
    if policy_errors:
        return _fail("POLICY_CONDITIONS_INVALID", errors=sorted(set(policy_errors)))

    formal = problem.get("formal_source_constraints", [])
    refinements = problem.get("proposed_refinements", [])
    if not isinstance(formal, Sequence) or isinstance(formal, (str, bytes)):
        return _fail("FORMAL_SOURCE_CONSTRAINTS_INVALID")
    if not isinstance(refinements, Sequence) or isinstance(refinements, (str, bytes)):
        return _fail("PROPOSED_REFINEMENTS_INVALID")
    compiled = compile_state(
        basis,
        formal_source_constraints=formal,
        proposed_refinements=refinements,
    )
    if compiled.get("status") == "FAIL_CLOSED":
        return _fail("SEMANTIC_STATE_FAIL_CLOSED", semantic_state=compiled)
    state = compiled["state"]
    models = [v for v in _valuations(basis) if _eval(state, v)]
    if not models:
        return _fail("SEMANTIC_STATE_HAS_NO_MODELS", semantic_state=compiled)

    authenticated, receipts, rejected = _authenticate_policies(
        policies, problem.get("policy_adequacy_bindings")
    )
    if not authenticated:
        return _fail(
            "NO_AUTHENTICATED_POLICY_ADEQUACY",
            semantic_state=compiled,
            rejected_policy_adequacy_bindings=rejected,
        )

    model_policy_sets = [
        {
            policy_id
            for policy_id, condition in authenticated.items()
            if _eval(condition, valuation)
        }
        for valuation in models
    ]

    raw_discriminators = problem.get("discriminators", [])
    if (
        not isinstance(raw_discriminators, Sequence)
        or isinstance(raw_discriminators, (str, bytes))
    ):
        return _fail("DISCRIMINATORS_INVALID")
    discriminators: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    errors: list[str] = []
    for i, row in enumerate(raw_discriminators):
        if not isinstance(row, Mapping):
            errors.append(f"DISCRIMINATOR_{i}:NOT_OBJECT")
            continue
        did = row.get("discriminator_id")
        formula = row.get("formula")
        cost = row.get("cost_units", 1)
        if not isinstance(did, str) or not did or did in seen_ids:
            errors.append(f"DISCRIMINATOR_{i}:ID_INVALID_OR_DUPLICATE")
            continue
        seen_ids.add(did)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
            errors.append(f"DISCRIMINATOR_{did}:COST_INVALID")
            continue
        ferr = _validate_formula(formula, basis_set)
        if ferr:
            errors.extend(f"DISCRIMINATOR_{did}:{e}" for e in ferr)
            continue
        discriminators.append({
            "discriminator_id": did,
            "formula": formula,
            "cost_units": float(cost),
        })
    if errors:
        return _fail("DISCRIMINATOR_DECLARATION_INVALID", errors=sorted(set(errors)))
    discriminators.sort(key=lambda r: (r["cost_units"], r["discriminator_id"]))

    unsplittable: list[dict[str, Any]] = []
    max_depth = 0
    strict_edges = True

    def build(indices: list[int], depth: int) -> dict[str, Any]:
        nonlocal max_depth, strict_edges
        max_depth = max(max_depth, depth)
        rank = len(indices)
        common = _intersection([model_policy_sets[i] for i in indices])
        if common:
            return {
                "kind": "TERMINAL_POLICY",
                "model_count": rank,
                "rank": rank,
                "certified_common_policies": common,
                "selected_policy_id": common[0],
            }

        candidates: list[tuple[dict[str, Any], list[int], list[int]]] = []
        for row in discriminators:
            false_indices = [
                i for i in indices if not _eval(row["formula"], models[i])
            ]
            true_indices = [
                i for i in indices if _eval(row["formula"], models[i])
            ]
            if not false_indices or not true_indices:
                continue
            if len(false_indices) >= rank or len(true_indices) >= rank:
                strict_edges = False
                continue
            candidates.append((row, false_indices, true_indices))

        if not candidates:
            leaf_models = [
                {
                    "model_id": _model_id(basis, models[i]),
                    "valuation": dict(models[i]),
                }
                for i in indices
            ]
            row = {"model_count": rank, "models": leaf_models}
            unsplittable.append(row)
            return {
                "kind": "UNSPLITTABLE_OBSTRUCTION",
                "model_count": rank,
                "rank": rank,
                "models": leaf_models,
                "adequate_policy_ids_by_model": [
                    sorted(model_policy_sets[i]) for i in indices
                ],
            }

        row, false_indices, true_indices = candidates[0]
        false_node = build(false_indices, depth + 1)
        true_node = build(true_indices, depth + 1)
        return {
            "kind": "STRICT_REFINEMENT",
            "model_count": rank,
            "rank": rank,
            "discriminator_id": row["discriminator_id"],
            "formula": row["formula"],
            "cost_units": row["cost_units"],
            "branches": [
                {
                    "outcome": False,
                    "model_count": len(false_indices),
                    "strict_rank_decrease": len(false_indices) < rank,
                    "node": false_node,
                },
                {
                    "outcome": True,
                    "model_count": len(true_indices),
                    "strict_rank_decrease": len(true_indices) < rank,
                    "node": true_node,
                },
            ],
        }

    tree = build(list(range(len(models))), 0)
    closed = not unsplittable and strict_edges
    return {
        "schema": SCHEMA,
        "pass": closed,
        "status": (
            "PASS__FINITE_ESCAPE_PROGRESS_TOTALITY_STRUCTURALLY_CLOSED"
            if closed
            else "UNRESOLVED__UNSPLITTABLE_POLICY_COVER_OBSTRUCTION"
        ),
        "decision_basis": basis,
        "semantic_state": compiled,
        "root_model_count": len(models),
        "tree": tree,
        "unsplittable_leaves": unsplittable,
        "max_refinement_depth": max_depth,
        "all_refinement_edges_strictly_decrease_rank": strict_edges,
        "authenticated_policy_adequacy": receipts,
        "rejected_policy_adequacy_bindings": rejected,
        "progress_authority": False,
        "truthful_observation_authority": False,
        "refinement_safety_authority": False,
        "resource_authority": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "STRUCTURAL_FINITE_PROGRESS_TREE_ONLY__DECLARED_DISCRIMINATOR_TRUTH_"
            "SAFETY_OUTCOME_AUTHORITY_AND_RESOURCE_ADMISSIBILITY_REQUIRE_SEPARATE_"
            "CONTENT_ADDRESSED_AUTHENTICATION"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    del root
    return solve(args or {})
