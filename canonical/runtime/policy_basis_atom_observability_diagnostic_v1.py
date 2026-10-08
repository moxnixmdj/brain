"""Policy-basis atom observability diagnostic v1.

Structural zero-credit diagnostic for one finite Boolean decision basis.

It asks the exact question induced by the observational-quotient theorem when Q
is chosen constructively from already-declared policy-basis atoms:

  under the currently authenticated/declared policy conditions, do the
  currently observable basis atoms partition every surviving abstract world
  into cells that have at least one common adequate policy?

The module does NOT authenticate policy adequacy or observation truth. It is
therefore diagnostic only. Its purpose is to return the exact uncovered
observational classes and the still-unobservable basis atoms that can split
them. No U-empty, DB, acceptance, ownership, or terminal authority is granted.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Mapping, Sequence

from canonical.runtime.monotone_semantic_constraint_kernel_v1 import (
    _eval,
    _validate_formula,
)

SCHEMA = "PROJECT_BRAIN_POLICY_BASIS_ATOM_OBSERVABILITY_DIAGNOSTIC_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "basis_atom_observational_cover_structurally_closed": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    basis = payload.get("decision_basis")
    if (
        not isinstance(basis, Sequence)
        or isinstance(basis, (str, bytes))
        or not basis
        or any(not isinstance(x, str) or not x for x in basis)
        or len(set(basis)) != len(basis)
    ):
        return _fail("DECISION_BASIS_INVALID")
    basis = list(basis)
    if len(basis) > 16:
        return _fail("DECISION_BASIS_EXCEEDS_DIAGNOSTIC_ENUMERATION_BOUND", bound=16)
    basis_set = set(basis)

    state = payload.get("state")
    errors = _validate_formula(state, basis_set)
    if errors:
        return _fail("STATE_FORMULA_INVALID", errors=errors)

    policies = payload.get("policy_conditions")
    if not isinstance(policies, Mapping) or not policies:
        return _fail("POLICY_CONDITIONS_REQUIRED")
    normalized_policies: dict[str, Mapping[str, Any]] = {}
    for pid, phi in policies.items():
        if not isinstance(pid, str) or not pid or not isinstance(phi, Mapping):
            return _fail("POLICY_CONDITION_INVALID", policy_id=str(pid))
        errs = _validate_formula(phi, basis_set)
        if errs:
            return _fail("POLICY_FORMULA_INVALID", policy_id=pid, errors=errs)
        normalized_policies[pid] = phi

    observable = payload.get("observable_atom_ids", [])
    if (
        not isinstance(observable, Sequence)
        or isinstance(observable, (str, bytes))
        or any(not isinstance(x, str) or x not in basis_set for x in observable)
    ):
        return _fail("OBSERVABLE_ATOM_IDS_INVALID")
    observable = sorted(set(observable), key=basis.index)
    hidden = [x for x in basis if x not in set(observable)]

    worlds: list[dict[str, bool]] = []
    for values in product((False, True), repeat=len(basis)):
        valuation = dict(zip(basis, values))
        if _eval(state, valuation):
            worlds.append(valuation)
    if not worlds:
        return _fail("NO_SURVIVING_ABSTRACT_WORLDS")

    def adequate(v: Mapping[str, bool]) -> tuple[str, ...]:
        return tuple(sorted(pid for pid, phi in normalized_policies.items() if _eval(phi, v)))

    rows = [{"valuation": v, "adequate_policy_ids": adequate(v)} for v in worlds]
    uncovered = [r for r in rows if not r["adequate_policy_ids"]]

    groups: dict[tuple[bool, ...], list[dict[str, Any]]] = {}
    for row in rows:
        sig = tuple(row["valuation"][a] for a in observable)
        groups.setdefault(sig, []).append(row)

    bad_classes = []
    for sig, members in groups.items():
        common = None
        for row in members:
            aset = set(row["adequate_policy_ids"])
            common = aset if common is None else common & aset
        common = common or set()
        if common:
            continue
        candidate_split_atoms = [
            atom
            for atom in hidden
            if len({m["valuation"][atom] for m in members}) > 1
        ]
        bad_classes.append({
            "observable_signature": {a: v for a, v in zip(observable, sig)},
            "world_count": len(members),
            "worlds": members,
            "common_adequate_policy_ids": [],
            "candidate_missing_split_atom_ids": candidate_split_atoms,
        })

    closed = not uncovered and not bad_classes
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__STRUCTURAL_ATOMIC_OBSERVATIONAL_POLICY_COVER_CLOSED"
            if closed
            else "OPEN__STRUCTURAL_ATOMIC_OBSERVATIONAL_POLICY_COVER"
        ),
        "decision_basis": basis,
        "surviving_world_count": len(worlds),
        "policy_count": len(normalized_policies),
        "observable_atom_ids": observable,
        "hidden_atom_ids": hidden,
        "pointwise_positive_cover": not uncovered,
        "uncovered_worlds": uncovered,
        "uncovered_world_count": len(uncovered),
        "bad_observational_classes": bad_classes,
        "bad_observational_class_count": len(bad_classes),
        "basis_atom_observational_cover_structurally_closed": closed,
        "all_basis_atoms_observable_is_sufficient_given_pointwise_positive_cover": True,
        "proof_note": (
            "WITH_ALL_BASIS_ATOMS_OBSERVABLE_EACH_BOOLEAN_VALUATION_HAS_A_UNIQUE_FULL_SIGNATURE;"
            "IF_EVERY_SURVIVING_VALUATION_HAS_AT_LEAST_ONE_ADEQUATE_POLICY_THEN_EVERY_FINAL_FULL_"
            "SIGNATURE_CLASS_HAS_A_COMMON_ADEQUATE_POLICY__PARTIAL_OBSERVABILITY_IS_EXACTLY_CHECKED_"
            "BY_THE_RETURNED_SIGNATURE_CLASSES"
        ),
        "policy_adequacy_authenticated": False,
        "observation_truth_authenticated": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "STRUCTURAL_DIAGNOSTIC_ONLY__DECLARED_POLICY_FORMULAS_AND_OBSERVABLE_ATOM_LABELS_ARE_NOT_"
            "SELF_AUTHENTICATING__NO_NEGATIVE_CAPABILITY_CLAIM_FROM_PARTIAL_POLICY_OR_OBSERVATION_BINDING"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {})
