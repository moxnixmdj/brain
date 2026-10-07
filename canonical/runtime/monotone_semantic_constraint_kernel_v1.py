"""Monotone proof-carrying semantic constraint kernel.

This is deliberately NOT a natural-language semantic parser.

It maintains an over-approximate semantic state over a finite decision basis.
The state begins at TRUE. New semantic constraints may be admitted only when
they are present in a separately supplied formal-source constraint set.

Missing constraints leave the state broader; they cannot by themselves create
a false policy proof. The module has no terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import product
import json
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_MONOTONE_SEMANTIC_CONSTRAINT_KERNEL_V1"
MAX_ENUM_ATOMS = 12
OPS = {"TRUE", "FALSE", "ATOM", "NOT", "AND", "OR", "IMPLIES", "XOR"}


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(x: Any) -> str:
    return sha256(_canon(x).encode("utf-8")).hexdigest()


def _validate_formula(formula: Any, basis: set[str]) -> list[str]:
    if not isinstance(formula, Mapping):
        return ["FORMULA_NOT_OBJECT"]
    op = formula.get("op")
    if op not in OPS:
        return [f"FORMULA_OP_INVALID:{op}"]
    if op in {"TRUE", "FALSE"}:
        return []
    if op == "ATOM":
        atom = formula.get("id")
        if not isinstance(atom, str) or not atom:
            return ["ATOM_ID_INVALID"]
        if atom not in basis:
            return [f"ATOM_OUTSIDE_DECISION_BASIS:{atom}"]
        return []
    if op == "NOT":
        return _validate_formula(formula.get("arg"), basis)
    if op in {"AND", "OR", "XOR"}:
        args = formula.get("args")
        if not isinstance(args, Sequence) or isinstance(args, (str, bytes)) or len(args) < 2:
            return [f"{op}_ARGS_INVALID"]
        errors: list[str] = []
        for arg in args:
            errors.extend(_validate_formula(arg, basis))
        return errors
    if op == "IMPLIES":
        return (
            _validate_formula(formula.get("if"), basis)
            + _validate_formula(formula.get("then"), basis)
        )
    return ["FORMULA_INVALID"]


def _eval(formula: Mapping[str, Any], valuation: Mapping[str, bool]) -> bool:
    op = formula["op"]
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "ATOM":
        return bool(valuation[formula["id"]])
    if op == "NOT":
        return not _eval(formula["arg"], valuation)
    if op == "AND":
        return all(_eval(x, valuation) for x in formula["args"])
    if op == "OR":
        return any(_eval(x, valuation) for x in formula["args"])
    if op == "XOR":
        return sum(1 for x in formula["args"] if _eval(x, valuation)) == 1
    if op == "IMPLIES":
        return (not _eval(formula["if"], valuation)) or _eval(formula["then"], valuation)
    raise AssertionError(op)


def _and(formulas: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(formulas)
    if not rows:
        return {"op": "TRUE"}
    if len(rows) == 1:
        return dict(rows[0])
    return {"op": "AND", "args": [dict(x) for x in rows]}


def _valuations(basis: Sequence[str]):
    for values in product((False, True), repeat=len(basis)):
        yield dict(zip(basis, values))


def _models(basis: Sequence[str], formula: Mapping[str, Any]) -> list[dict[str, bool]]:
    return [v for v in _valuations(basis) if _eval(formula, v)]


def _entails(basis: Sequence[str], state: Mapping[str, Any], target: Mapping[str, Any]) -> bool:
    return not any(_eval(state, v) and not _eval(target, v) for v in _valuations(basis))


def compile_state(
    decision_basis: Sequence[str],
    *,
    formal_source_constraints: Sequence[Mapping[str, Any]] = (),
    proposed_refinements: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Compile a monotone semantic state.

    formal_source_constraints are the only authority source accepted by this
    narrow kernel. proposed_refinements must match one of those constraints
    exactly; a caller cannot self-certify a new semantic fact.
    """
    errors: list[str] = []
    if (
        not isinstance(decision_basis, Sequence)
        or isinstance(decision_basis, (str, bytes))
        or not decision_basis
        or any(not isinstance(x, str) or not x for x in decision_basis)
    ):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["DECISION_BASIS_INVALID"],
            "terminal_authority": False,
        }
    basis = list(decision_basis)
    if len(basis) != len(set(basis)):
        errors.append("DECISION_BASIS_DUPLICATE")
    if len(basis) > MAX_ENUM_ATOMS:
        errors.append(f"DECISION_BASIS_EXCEEDS_ENUMERATION_BOUND:{len(basis)}>{MAX_ENUM_ATOMS}")
    basis_set = set(basis)

    for i, c in enumerate(formal_source_constraints):
        for e in _validate_formula(c, basis_set):
            errors.append(f"FORMAL_SOURCE_CONSTRAINT_{i}:{e}")
    for i, c in enumerate(proposed_refinements):
        for e in _validate_formula(c, basis_set):
            errors.append(f"PROPOSED_REFINEMENT_{i}:{e}")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    allowed = {_canon(x): x for x in formal_source_constraints}
    accepted = []
    rejected = []
    for c in proposed_refinements:
        key = _canon(c)
        if key in allowed:
            accepted.append(dict(c))
        else:
            rejected.append({
                "constraint": dict(c),
                "reason": "UNPROVED_REFINEMENT_NOT_IN_FORMAL_SOURCE_CONSTRAINT_SET",
            })

    state = _and(accepted)
    model_count = len(_models(basis, state))
    if model_count == 0:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["SEMANTIC_STATE_INCONSISTENT__NO_MODELS"],
            "decision_basis": basis,
            "state": state,
            "state_sha256": _digest(state),
            "accepted_refinements": accepted,
            "rejected_refinements": rejected,
            "model_count": 0,
            "max_model_count": 2 ** len(basis),
            "terminal_authority": False,
        }
    return {
        "schema": SCHEMA,
        "status": "COMPILED" if not rejected else "COMPILED_WITH_REJECTED_REFINEMENTS",
        "decision_basis": basis,
        "state": state,
        "state_sha256": _digest(state),
        "accepted_refinements": accepted,
        "rejected_refinements": rejected,
        "model_count": model_count,
        "max_model_count": 2 ** len(basis),
        "monotone": True,
        "initial_state": {"op": "TRUE"},
        "terminal_authority": False,
        "soundness_boundary": (
            "OVERAPPROXIMATION_IS_SOUND_ONLY_IF_FORMAL_SOURCE_CONSTRAINTS_ARE_SOUND;"
            "THIS_KERNEL_DOES_NOT_INFER_OR_CERTIFY_RAW_LANGUAGE_SEMANTICS"
        ),
    }


def resolve_common_policy(
    decision_basis: Sequence[str],
    policy_conditions: Mapping[str, Mapping[str, Any]],
    *,
    formal_source_constraints: Sequence[Mapping[str, Any]] = (),
    proposed_refinements: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    compiled = compile_state(
        decision_basis,
        formal_source_constraints=formal_source_constraints,
        proposed_refinements=proposed_refinements,
    )
    if compiled["status"] == "FAIL_CLOSED":
        return compiled

    basis = list(compiled["decision_basis"])
    basis_set = set(basis)
    errors: list[str] = []
    if not isinstance(policy_conditions, Mapping) or not policy_conditions:
        errors.append("POLICY_CONDITIONS_INVALID_OR_EMPTY")
    else:
        for pid, phi in policy_conditions.items():
            if not isinstance(pid, str) or not pid:
                errors.append("POLICY_ID_INVALID")
                continue
            for e in _validate_formula(phi, basis_set):
                errors.append(f"POLICY_{pid}:{e}")
    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    state = compiled["state"]
    adequate = sorted(
        pid for pid, phi in policy_conditions.items()
        if _entails(basis, state, phi)
    )
    result = dict(compiled)
    result.update({
        "status": "COMMON_POLICY_CERTIFIED" if adequate else "UNRESOLVED",
        "certified_common_policies": adequate,
        "rule": (
            "A_POLICY_IS_RETURNED_ONLY_IF_EVERY_MODEL_OF_THE_CURRENT_UNDERSPECIFIED_STATE"
            "_SATISFIES_ITS_DECLARED_ADEQUACY_CONDITION"
        ),
    })
    return result
