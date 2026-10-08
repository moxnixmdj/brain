"""Fail-closed registry of independently authenticated Brain-owned policy adequacy cells.

The registry does not prove that a current context belongs to any registered
region. It only makes already-proved adequacy reusable when the exact policy
condition is already part of the caller's decision basis.

A registered condition being present in the basis is not the same as the
condition being true. P3 still evaluates every surviving valuation and therefore
keeps uncovered false-membership worlds open unless upstream source constraints
prove the membership atom.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_P3_POLICY_ADEQUACY_REGISTRY_V1"
ROOT = Path(__file__).resolve().parents[2]

_REGISTRY = {
    "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1": {
        "condition": {"op": "ATOM", "id": "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1"},
        "binding_path": "canonical/governance/P2_EXPLICIT_TOP_LAW_POLICY_ADEQUACY_BINDING_20261008_V1.json",
        "binding_blob_sha": "1f3fee512979ef5346d03bd7a8bc7f0659ed90d4",
    },
    "P3_BOUND_BINARY_DECISION_GROUNDED_EXPRESSION_POLICY_V1": {
        "condition": {
            "op": "ATOM",
            "id": "P3_BOUND_BINARY_REAL_CONTEXT_GROUNDED_DECISION_TOP_LAW_V1",
        },
        "binding_path": "canonical/governance/P3_BINARY_TOP_LAW_POLICY_ADEQUACY_BINDING_20261008_V1.json",
        "binding_blob_sha": "11b468974f1f22a5298027a9e0e5f11c077d18de",
    },
    "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1": {
        "condition": {
            "op": "ATOM",
            "id": "SYNTHESIS_TYPED_VISIBLE_SUPPORT_COMMON_POLICY_TOP_LAW_V1",
        },
        "binding_path": "canonical/governance/SYNTHESIS_VISIBLE_SUPPORT_POLICY_ADEQUACY_BINDING_20261007_V1.json",
        "binding_blob_sha": "7d2322ff8205e98752c4cd2674215f93c145305c",
    },
}

_BINDING_KEYS = (
    "adequacy_certificate_path",
    "adequacy_certificate_blob_sha",
    "independent_verification_path",
    "independent_verification_blob_sha",
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "registry_authority": False,
        "membership_self_certified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _binding_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in _BINDING_KEYS}


def _load_registered_binding(
    policy_id: str,
    entry: Mapping[str, Any],
    *,
    root: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    rel = entry["binding_path"]
    path = root / rel
    if not path.is_file():
        return None, "REGISTERED_BINDING_MISSING:" + rel
    actual = _git_blob_sha(path)
    if actual != entry["binding_blob_sha"]:
        return None, "REGISTERED_BINDING_DRIFT:" + rel + ":" + actual
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, "REGISTERED_BINDING_JSON_INVALID:" + type(exc).__name__
    if not isinstance(value, Mapping):
        return None, "REGISTERED_BINDING_NOT_OBJECT"
    if value.get("schema") != "PROJECT_BRAIN_POLICY_ADEQUACY_BINDING_V1":
        return None, "REGISTERED_BINDING_SCHEMA_INVALID:" + policy_id
    if value.get("policy_id") != policy_id:
        return None, "REGISTERED_BINDING_POLICY_ID_MISMATCH:" + policy_id
    if value.get("policy_condition") != entry["condition"]:
        return None, "REGISTERED_BINDING_CONDITION_MISMATCH:" + policy_id
    projected = _binding_projection(value)
    if any(not isinstance(projected[key], str) or not projected[key] for key in _BINDING_KEYS):
        return None, "REGISTERED_BINDING_FIELDS_INVALID:" + policy_id
    return projected, None


def _condition_atoms(condition: Mapping[str, Any]) -> set[str]:
    op = condition.get("op")
    if op == "ATOM":
        atom = condition.get("id")
        return {atom} if isinstance(atom, str) and atom else set()
    if op == "NOT" and isinstance(condition.get("arg"), Mapping):
        return _condition_atoms(condition["arg"])
    atoms: set[str] = set()
    for key in ("args",):
        rows = condition.get(key)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, Mapping):
                    atoms.update(_condition_atoms(row))
    for key in ("if", "then"):
        row = condition.get(key)
        if isinstance(row, Mapping):
            atoms.update(_condition_atoms(row))
    return atoms


def augment_problem(
    problem: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_MAPPING_REQUIRED")
    basis = problem.get("decision_basis")
    if (
        not isinstance(basis, list)
        or not basis
        or any(not isinstance(x, str) or not x for x in basis)
        or len(set(basis)) != len(basis)
    ):
        return _fail("DECISION_BASIS_INVALID")

    root = Path(repo_root) if repo_root is not None else ROOT
    policies = problem.get("policy_conditions", {})
    bindings = problem.get("policy_adequacy_bindings", {})
    if not isinstance(policies, Mapping):
        return _fail("POLICY_CONDITIONS_NOT_MAPPING")
    if not isinstance(bindings, Mapping):
        return _fail("POLICY_ADEQUACY_BINDINGS_NOT_MAPPING")

    out = deepcopy(dict(problem))
    out_policies = deepcopy(dict(policies))
    out_bindings = deepcopy(dict(bindings))
    basis_set = set(basis)
    injected: list[str] = []
    reused: list[str] = []
    skipped: list[dict[str, Any]] = []

    for policy_id, entry in sorted(_REGISTRY.items()):
        condition = deepcopy(entry["condition"])
        atoms = _condition_atoms(condition)
        missing = sorted(atoms - basis_set)
        if missing:
            skipped.append(
                {
                    "policy_id": policy_id,
                    "reason": "CONDITION_ATOMS_OUTSIDE_DECISION_BASIS",
                    "missing_atoms": missing,
                }
            )
            continue

        registered_binding, error = _load_registered_binding(
            policy_id,
            entry,
            root=root,
        )
        if error is not None or registered_binding is None:
            return _fail(
                "REGISTERED_POLICY_ADEQUACY_BINDING_INVALID",
                policy_id=policy_id,
                binding_error=error,
            )

        existing_condition = out_policies.get(policy_id)
        if existing_condition is not None and existing_condition != condition:
            return _fail(
                "CALLER_POLICY_CONDITION_CONFLICTS_WITH_REGISTERED_ADEQUACY",
                policy_id=policy_id,
            )
        existing_binding = out_bindings.get(policy_id)
        if existing_binding is not None:
            if not isinstance(existing_binding, Mapping):
                return _fail(
                    "CALLER_POLICY_BINDING_INVALID",
                    policy_id=policy_id,
                )
            if _binding_projection(existing_binding) != registered_binding:
                return _fail(
                    "CALLER_POLICY_BINDING_CONFLICTS_WITH_REGISTERED_ADEQUACY",
                    policy_id=policy_id,
                )
            reused.append(policy_id)
        else:
            out_bindings[policy_id] = registered_binding
            if existing_condition is None:
                injected.append(policy_id)
            else:
                reused.append(policy_id)

        out_policies[policy_id] = condition

    out["policy_conditions"] = out_policies
    out["policy_adequacy_bindings"] = out_bindings
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__REGISTERED_POLICY_ADEQUACY_REUSED_WITHOUT_MEMBERSHIP_SELF_CERTIFICATION",
        "problem": out,
        "registered_policy_count": len(_REGISTRY),
        "basis_eligible_policy_count": len(injected) + len(reused),
        "injected_policy_ids": injected,
        "reused_policy_ids": reused,
        "skipped_registered_policies": skipped,
        "registry_authority": False,
        "membership_self_certified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "REGISTRY_REUSES_ONLY_CONTENT_ADDRESSED_ADEQUACY_BINDINGS;"
            "CONDITION_ATOMS_MUST_ALREADY_EXIST_IN_DECISION_BASIS;"
            "TRUTH_OF_MEMBERSHIP_ATOMS_REMAINS_UPSTREAM_AND_P3_EVALUATES_FALSE_WORLDS"
        ),
    }


def catalog() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "POLICY_ADEQUACY_REGISTRY_CATALOG",
        "policy_count": len(_REGISTRY),
        "policies": [
            {
                "policy_id": policy_id,
                "condition": deepcopy(entry["condition"]),
                "binding_path": entry["binding_path"],
                "binding_blob_sha": entry["binding_blob_sha"],
            }
            for policy_id, entry in sorted(_REGISTRY.items())
        ],
        "membership_self_certified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
