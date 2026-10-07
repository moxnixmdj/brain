from __future__ import annotations

"""Exact minimum policy-changing discriminator over a finite semantic basis.

This module is deliberately a finite decision-region compiler, not a semantic
parser and not an adequacy certifier. It consumes:
- a sound finite over-approximation compiled by the existing monotone kernel,
- caller-declared policy adequacy conditions over that same basis, and
- the exact set of policy ids whose adequacy formulas have already been
  authenticated by an external content-addressed admission route.

It then solves exactly, over the still-possible Boolean models:
1. whether one authenticated policy is common to every model;
2. whether some possible model has no authenticated adequate policy at all;
3. otherwise, the smallest subset of observable basis atoms whose values
   partition the models into cells each having at least one common authenticated
   adequate policy.

The search is exhaustive over subsets of at most 12 basis atoms (<=4096
subsets), with deterministic tie-breaking. It grants no D_B, U-empty, or
terminal credit by itself.
"""

from itertools import combinations, product
from math import ceil, log2
from typing import Any, Mapping, Sequence

from canonical.runtime.monotone_semantic_constraint_kernel_v1 import (
    MAX_ENUM_ATOMS,
    _eval,
    _validate_formula,
    compile_state,
)

SCHEMA = "PROJECT_BRAIN_POLICY_REGION_MINIMUM_DISCRIMINATOR_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "db_admission_authorized": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _models(basis: Sequence[str], state: Mapping[str, Any]) -> list[dict[str, bool]]:
    rows: list[dict[str, bool]] = []
    for values in product((False, True), repeat=len(basis)):
        valuation = dict(zip(basis, values))
        if _eval(state, valuation):
            rows.append(valuation)
    return rows


def _bucket_key(model: Mapping[str, bool], atoms: Sequence[str]) -> tuple[bool, ...]:
    return tuple(bool(model[a]) for a in atoms)


def _adequate_sets(
    models: Sequence[Mapping[str, bool]],
    policy_conditions: Mapping[str, Mapping[str, Any]],
    authenticated_policy_ids: Sequence[str],
) -> list[frozenset[str]]:
    pids = tuple(sorted(set(authenticated_policy_ids)))
    return [
        frozenset(pid for pid in pids if _eval(policy_conditions[pid], model))
        for model in models
    ]


def _common(sets: Sequence[frozenset[str]]) -> frozenset[str]:
    if not sets:
        return frozenset()
    out = set(sets[0])
    for row in sets[1:]:
        out.intersection_update(row)
    return frozenset(out)


def _partition_witness(
    models: Sequence[Mapping[str, bool]],
    adequate: Sequence[frozenset[str]],
    atoms: Sequence[str],
) -> tuple[bool, list[dict[str, Any]]]:
    groups: dict[tuple[bool, ...], list[int]] = {}
    for index, model in enumerate(models):
        groups.setdefault(_bucket_key(model, atoms), []).append(index)

    rows: list[dict[str, Any]] = []
    for key in sorted(groups):
        idxs = groups[key]
        common = _common([adequate[i] for i in idxs])
        if not common:
            return False, []
        selected = sorted(common)[0]
        rows.append(
            {
                "observation": {atom: value for atom, value in zip(atoms, key)},
                "model_count": len(idxs),
                "common_adequate_policy_ids": sorted(common),
                "selected_policy_id": selected,
            }
        )
    return True, rows


def solve(
    *,
    decision_basis: Sequence[str],
    formal_source_constraints: Sequence[Mapping[str, Any]],
    proposed_refinements: Sequence[Mapping[str, Any]],
    policy_conditions: Mapping[str, Mapping[str, Any]],
    authenticated_policy_ids: Sequence[str],
) -> dict[str, Any]:
    if (
        not isinstance(authenticated_policy_ids, Sequence)
        or isinstance(authenticated_policy_ids, (str, bytes))
        or not authenticated_policy_ids
        or any(not isinstance(x, str) or not x for x in authenticated_policy_ids)
    ):
        return _fail("AUTHENTICATED_POLICY_IDS_INVALID")
    if len(set(authenticated_policy_ids)) != len(authenticated_policy_ids):
        return _fail("AUTHENTICATED_POLICY_IDS_DUPLICATE")

    compiled = compile_state(
        decision_basis,
        formal_source_constraints=formal_source_constraints,
        proposed_refinements=proposed_refinements,
    )
    if compiled.get("status") == "FAIL_CLOSED":
        return _fail("SEMANTIC_STATE_FAIL_CLOSED", compiled=compiled)

    basis = list(compiled["decision_basis"])
    if len(basis) > MAX_ENUM_ATOMS:
        return _fail("DECISION_BASIS_EXCEEDS_EXACT_BOUND")

    if not isinstance(policy_conditions, Mapping) or not policy_conditions:
        return _fail("POLICY_CONDITIONS_INVALID")
    basis_set = set(basis)
    errors: list[str] = []
    for pid in authenticated_policy_ids:
        if pid not in policy_conditions:
            errors.append("AUTHENTICATED_POLICY_CONDITION_MISSING:" + pid)
            continue
        phi = policy_conditions[pid]
        for err in _validate_formula(phi, basis_set):
            errors.append("POLICY_" + pid + ":" + err)
    if errors:
        return _fail("POLICY_FORMULA_INVALID", errors=sorted(set(errors)))

    models = _models(basis, compiled["state"])
    if not models:
        return _fail("NO_STILL_POSSIBLE_MODELS")

    adequate = _adequate_sets(models, policy_conditions, authenticated_policy_ids)
    gaps = [i for i, row in enumerate(adequate) if not row]
    if gaps:
        witnesses = [
            {"model_index": i, "valuation": models[i]}
            for i in gaps[:8]
        ]
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "AUTHENTICATED_POLICY_COVER_GAP",
            "model_count": len(models),
            "uncovered_model_count": len(gaps),
            "uncovered_model_witnesses": witnesses,
            "minimum_discriminator_atom_count": None,
            "minimum_discriminator_atoms": [],
            "next_action": (
                "ADD_OR_PROVE_AN_AUTHENTICATED_ADEQUATE_POLICY_FOR_THE_WITNESS_"
                "REGION__A_DISCRIMINATOR_CANNOT_REPAIR_A_WORLD_WITH_NO_ADEQUATE_POLICY"
            ),
            "db_admission_authorized": False,
            "u_empty_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    global_common = _common(adequate)
    if global_common:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "COMMON_AUTHENTICATED_POLICY_OVER_CURRENT_SOUND_STATE",
            "model_count": len(models),
            "minimum_discriminator_atom_count": 0,
            "minimum_discriminator_atoms": [],
            "common_adequate_policy_ids": sorted(global_common),
            "selected_policy_id": sorted(global_common)[0],
            "bucket_count": 1,
            "persistent_bits_lower_bound": 0,
            "exact_over_declared_basis": True,
            "db_admission_authorized": False,
            "u_empty_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    for size in range(1, len(basis) + 1):
        for atoms in combinations(basis, size):
            ok, buckets = _partition_witness(models, adequate, atoms)
            if not ok:
                continue
            selected_policy_ids = sorted({row["selected_policy_id"] for row in buckets})
            min_bits = 0 if len(selected_policy_ids) <= 1 else ceil(log2(len(selected_policy_ids)))
            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "MINIMUM_POLICY_CHANGING_DISCRIMINATOR_FOUND",
                "model_count": len(models),
                "minimum_discriminator_atom_count": size,
                "minimum_discriminator_atoms": list(atoms),
                "bucket_count": len(buckets),
                "buckets": buckets,
                "selected_policy_ids": selected_policy_ids,
                "persistent_bits_lower_bound": min_bits,
                "exact_over_declared_basis": True,
                "tie_break": "LEXICOGRAPHIC_FIRST_MINIMUM_ATOM_SUBSET",
                "db_admission_authorized": False,
                "u_empty_authorized": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
                "boundary": (
                    "THIS_SOLVES_MINIMUM_SELECTION_INFORMATION_ONLY_OVER_THE_SOUND_"
                    "DECLARED_FINITE_BASIS_AND_EXTERNALLY_AUTHENTICATED_POLICY_FORMULAS"
                ),
            }

    return _fail("UNREACHABLE_NO_PARTITION_WITH_FULL_BASIS")
