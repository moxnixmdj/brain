"""Authenticated symbolic policy-cover fixed point.

Positive-only proof kernel for policy adequacy.

Security boundary:
- caller data may name a Brain-owned verifier, but may not assert semantic truth;
- policy adequacy conditions come only from an in-process trusted verifier;
- discriminator predicates come only from an in-process trusted verifier;
- the initial belief state is TRUE unless a trusted constraint verifier proves a
  narrowing formula;
- inline receipt/pass/verified/adequacy booleans are rejected as input fields.

The kernel proves only a bounded symbolic winning strategy over the supplied
finite Boolean decision basis. It never grants U-empty or terminal authority.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import product
import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AUTHENTICATED_SYMBOLIC_POLICY_COVER_FIXED_POINT_V1"
MAX_BASIS_ATOMS = 12
OPS = {"TRUE", "FALSE", "ATOM", "NOT", "AND", "OR", "IMPLIES", "XOR"}

_TOP_FIELDS = frozenset({"decision_basis", "constraint_checks", "policies", "discriminators"})
_POLICY_FIELDS = frozenset({"policy_id", "verifier_id", "cost_units"})
_DISCRIMINATOR_FIELDS = frozenset({"discriminator_id", "verifier_id", "cost_units"})
_CONSTRAINT_FIELDS = frozenset({"constraint_id", "verifier_id", "input"})


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "winning_strategy_proved": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _valid_cost(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value >= 0
        and math.isfinite(float(value))
    )


def _validate_formula(formula: Any, basis: set[str]) -> bool:
    if not isinstance(formula, Mapping):
        return False
    op = formula.get("op")
    if op not in OPS:
        return False
    if op in {"TRUE", "FALSE"}:
        return set(formula) == {"op"}
    if op == "ATOM":
        return (
            set(formula) == {"op", "id"}
            and isinstance(formula.get("id"), str)
            and formula["id"] in basis
        )
    if op == "NOT":
        return set(formula) == {"op", "arg"} and _validate_formula(formula["arg"], basis)
    if op in {"AND", "OR", "XOR"}:
        args = formula.get("args")
        return (
            set(formula) == {"op", "args"}
            and isinstance(args, Sequence)
            and not isinstance(args, (str, bytes))
            and len(args) >= 2
            and all(_validate_formula(x, basis) for x in args)
        )
    if op == "IMPLIES":
        return (
            set(formula) == {"op", "if", "then"}
            and _validate_formula(formula["if"], basis)
            and _validate_formula(formula["then"], basis)
        )
    return False


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


def _and(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    return {"op": "AND", "args": [dict(a), dict(b)]}


def _not(a: Mapping[str, Any]) -> dict[str, Any]:
    return {"op": "NOT", "arg": dict(a)}


def _constraint_verifier(
    verifier_id: str,
    constraint_id: str,
    verifier_input: Any,
) -> dict[str, Any]:
    if verifier_id == "SELECTED_SEMANTIC_TRUTH_OBSERVATION_V1":
        if not isinstance(verifier_input, Mapping) or set(verifier_input) != {
            "source_text", "source_id", "fact_source", "fact_source_id"
        }:
            return {
                "pass": False,
                "reason": "SELECTED_SEMANTIC_OBSERVATION_INPUT_INVALID",
                "verifier_id": verifier_id,
                "constraint_id": constraint_id,
            }
        from canonical.runtime.selected_semantic_discriminator_dispatch_v1 import evaluate as dispatch
        payload = {
            "predicate_id": constraint_id,
            "target_claim_id": "selected",
            "source_text": verifier_input.get("source_text"),
            "source_id": verifier_input.get("source_id"),
            "claims": [{
                "claim_id": "selected",
                "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
            }],
            "fact_source": verifier_input.get("fact_source"),
            "fact_source_id": verifier_input.get("fact_source_id"),
        }
        out = dispatch(payload, {"TRUE": "__OBS_TRUE__", "FALSE": "__OBS_FALSE__"})
        if out.get("pass") is not True:
            return {
                "pass": False,
                "reason": "SELECTED_SEMANTIC_OBSERVATION_NOT_PROVED",
                "verifier_id": verifier_id,
                "constraint_id": constraint_id,
                "raw_status": out.get("status"),
                "raw_reason": out.get("reason"),
            }
        if out.get("predicate_id") != constraint_id:
            return {
                "pass": False,
                "reason": "SELECTED_SEMANTIC_PREDICATE_ID_MISMATCH",
                "verifier_id": verifier_id,
                "constraint_id": constraint_id,
                "verified_predicate_id": out.get("predicate_id"),
            }
        truth = out.get("predicate_truth")
        atom = {"op": "ATOM", "id": constraint_id}
        if truth == "TRUE":
            formula = atom
        elif truth == "FALSE":
            formula = {"op": "NOT", "arg": atom}
        else:
            return {
                "pass": False,
                "reason": "SELECTED_SEMANTIC_OBSERVATION_UNKNOWN",
                "verifier_id": verifier_id,
                "constraint_id": constraint_id,
            }
        return {
            "pass": True,
            "constraint_id": constraint_id,
            "constraint_formula": formula,
            "proof_digest": out.get("input_binding_sha256"),
            "verifier_id": verifier_id,
            "predicate_truth": truth,
            "source_sha256": (out.get("input_binding") or {}).get("source_sha256"),
            "fact_source_sha256": (out.get("input_binding") or {}).get("fact_source_sha256"),
        }

    if verifier_id == "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1":
        if constraint_id != "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1":
            return {
                "pass": False,
                "reason": "P2_CONSTRAINT_ID_MISMATCH",
                "verifier_id": verifier_id,
                "constraint_id": constraint_id,
            }
        if not isinstance(verifier_input, Mapping) or set(verifier_input) != {"raw_source", "source_id"}:
            return {
                "pass": False,
                "reason": "P2_CONSTRAINT_INPUT_INVALID",
                "verifier_id": verifier_id,
                "constraint_id": constraint_id,
            }
        from canonical.runtime.p2_explicit_contract_membership_v1 import compile_membership
        out = compile_membership(
            verifier_input.get("raw_source"),
            source_id=verifier_input.get("source_id"),
        )
        if out.get("pass") is not True:
            return {
                "pass": False,
                "reason": "P2_EXPLICIT_MEMBERSHIP_REJECTED",
                "verifier_id": verifier_id,
                "constraint_id": constraint_id,
                "raw_status": out.get("status"),
                "errors": out.get("errors", []),
            }
        return {
            "pass": True,
            "constraint_id": constraint_id,
            "constraint_formula": {"op": "ATOM", "id": "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1"},
            "proof_digest": out.get("membership_receipt"),
            "verifier_id": verifier_id,
            "raw_source_sha256": out.get("raw_source_sha256"),
        }
    return {
        "pass": False,
        "reason": "TRUSTED_CONSTRAINT_VERIFIER_NOT_REGISTERED",
        "verifier_id": verifier_id,
        "constraint_id": constraint_id,
    }


def _policy_verifier(verifier_id: str, policy_id: str) -> dict[str, Any]:
    if verifier_id == "P2_TOP_LAW_POLICY_ADEQUACY_AUTHENTICATOR_V1":
        from canonical.runtime.p2_top_law_policy_adequacy_authenticator_v1 import (
            authenticate_repository,
        )
        out = authenticate_repository()
        if out.get("pass") is not True or out.get("policy_id") != policy_id:
            return {
                "pass": False,
                "reason": "P2_POLICY_AUTHENTICATOR_REJECTED",
                "raw_status": out.get("status"),
            }
        return {
            "pass": True,
            "policy_id": policy_id,
            "policy_condition": out.get("policy_condition"),
            "adequacy_proved": out.get("adequacy_proved") is True,
            "brain_owned": out.get("brain_owned") is True,
            "proof_digest": out.get("proof_digest"),
            "verifier_id": verifier_id,
        }
    return {
        "pass": False,
        "reason": "TRUSTED_POLICY_VERIFIER_NOT_REGISTERED",
        "verifier_id": verifier_id,
        "policy_id": policy_id,
    }


def _discriminator_verifier(verifier_id: str, discriminator_id: str) -> dict[str, Any]:
    # Deliberately empty until a verifier proves truth/safety/totality over a
    # symbolic belief region rather than merely accepting receipt-shaped flags.
    return {
        "pass": False,
        "reason": "TRUSTED_DISCRIMINATOR_VERIFIER_NOT_REGISTERED",
        "verifier_id": verifier_id,
        "discriminator_id": discriminator_id,
    }


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    if set(payload) != _TOP_FIELDS:
        return _fail("TOP_FIELDS_INVALID")

    basis = payload.get("decision_basis")
    if (
        not isinstance(basis, Sequence)
        or isinstance(basis, (str, bytes))
        or not basis
        or len(basis) > MAX_BASIS_ATOMS
        or any(not isinstance(x, str) or not x for x in basis)
        or len(set(basis)) != len(basis)
    ):
        return _fail("DECISION_BASIS_INVALID")
    basis = list(basis)
    basis_set = set(basis)

    valuations = [
        dict(zip(basis, bits))
        for bits in product((False, True), repeat=len(basis))
    ]
    root_formula: dict[str, Any] = {"op": "TRUE"}

    constraints = payload.get("constraint_checks")
    if not isinstance(constraints, Sequence) or isinstance(constraints, (str, bytes)):
        return _fail("CONSTRAINT_CHECKS_INVALID")
    accepted_constraints = []
    for i, row in enumerate(constraints):
        if not isinstance(row, Mapping) or set(row) != _CONSTRAINT_FIELDS:
            return _fail("CONSTRAINT_FIELDS_INVALID", index=i)
        cid = row.get("constraint_id")
        vid = row.get("verifier_id")
        if not isinstance(cid, str) or not cid or not isinstance(vid, str) or not vid:
            return _fail("CONSTRAINT_ID_OR_VERIFIER_INVALID", index=i)
        proof = _constraint_verifier(vid, cid, row.get("input"))
        if proof.get("pass") is not True:
            return _fail("TRUSTED_CONSTRAINT_VERIFICATION_FAILED", index=i, verifier_id=vid)
        phi = proof.get("constraint_formula")
        if not _validate_formula(phi, basis_set):
            return _fail("TRUSTED_CONSTRAINT_FORMULA_INVALID", index=i)
        root_formula = _and(root_formula, phi)
        accepted_constraints.append({
            "constraint_id": cid,
            "verifier_id": vid,
            "proof_digest": proof.get("proof_digest"),
        })

    root_models = frozenset(
        i for i, valuation in enumerate(valuations) if _eval(root_formula, valuation)
    )
    if not root_models:
        return _fail("TRUSTED_CONSTRAINTS_MAKE_ROOT_INCONSISTENT")

    policies = payload.get("policies")
    if not isinstance(policies, Sequence) or isinstance(policies, (str, bytes)):
        return _fail("POLICIES_INVALID")
    policy_conditions: dict[str, Mapping[str, Any]] = {}
    policy_costs: dict[str, float] = {}
    policy_proofs: dict[str, dict[str, Any]] = {}
    rejected_policies: list[dict[str, Any]] = []
    seen_policy_ids: set[str] = set()
    for i, row in enumerate(policies):
        if not isinstance(row, Mapping) or set(row) != _POLICY_FIELDS:
            rejected_policies.append({"index": i, "reason": "POLICY_FIELDS_INVALID"})
            continue
        pid = row.get("policy_id")
        vid = row.get("verifier_id")
        cost = row.get("cost_units")
        if (
            not isinstance(pid, str) or not pid
            or not isinstance(vid, str) or not vid
        ):
            rejected_policies.append({"index": i, "policy_id": pid, "reason": "POLICY_ID_OR_VERIFIER_INVALID"})
            continue
        if pid in seen_policy_ids:
            rejected_policies.append({"index": i, "policy_id": pid, "reason": "POLICY_ID_DUPLICATE"})
            continue
        seen_policy_ids.add(pid)
        if not _valid_cost(cost):
            rejected_policies.append({"index": i, "policy_id": pid, "reason": "POLICY_COST_INVALID"})
            continue
        proof = _policy_verifier(vid, pid)
        if proof.get("pass") is not True:
            rejected_policies.append({
                "index": i, "policy_id": pid, "verifier_id": vid,
                "reason": "TRUSTED_POLICY_VERIFICATION_FAILED",
            })
            continue
        if (
            proof.get("adequacy_proved") is not True
            or proof.get("brain_owned") is not True
            or proof.get("policy_id") != pid
        ):
            rejected_policies.append({
                "index": i, "policy_id": pid,
                "reason": "TRUSTED_POLICY_PROOF_SEMANTICS_INVALID",
            })
            continue
        phi = proof.get("policy_condition")
        if not _validate_formula(phi, basis_set):
            rejected_policies.append({
                "index": i, "policy_id": pid,
                "reason": "TRUSTED_POLICY_CONDITION_INVALID",
            })
            continue
        policy_conditions[pid] = phi
        policy_costs[pid] = float(cost)
        policy_proofs[pid] = {
            "verifier_id": vid,
            "proof_digest": proof.get("proof_digest"),
        }

    discriminators = payload.get("discriminators")
    if not isinstance(discriminators, Sequence) or isinstance(discriminators, (str, bytes)):
        return _fail("DISCRIMINATORS_INVALID")
    discriminator_formulas: dict[str, Mapping[str, Any]] = {}
    discriminator_costs: dict[str, float] = {}
    discriminator_proofs: dict[str, dict[str, Any]] = {}
    rejected_discriminators: list[dict[str, Any]] = []
    seen_discriminator_ids: set[str] = set()
    for i, row in enumerate(discriminators):
        if not isinstance(row, Mapping) or set(row) != _DISCRIMINATOR_FIELDS:
            rejected_discriminators.append({"index": i, "reason": "DISCRIMINATOR_FIELDS_INVALID"})
            continue
        did = row.get("discriminator_id")
        vid = row.get("verifier_id")
        cost = row.get("cost_units")
        if (
            not isinstance(did, str) or not did
            or not isinstance(vid, str) or not vid
        ):
            rejected_discriminators.append({
                "index": i, "discriminator_id": did,
                "reason": "DISCRIMINATOR_ID_OR_VERIFIER_INVALID",
            })
            continue
        if did in seen_discriminator_ids:
            rejected_discriminators.append({
                "index": i, "discriminator_id": did,
                "reason": "DISCRIMINATOR_ID_DUPLICATE",
            })
            continue
        seen_discriminator_ids.add(did)
        if not _valid_cost(cost):
            rejected_discriminators.append({
                "index": i, "discriminator_id": did,
                "reason": "DISCRIMINATOR_COST_INVALID",
            })
            continue
        proof = _discriminator_verifier(vid, did)
        if proof.get("pass") is not True:
            rejected_discriminators.append({
                "index": i, "discriminator_id": did, "verifier_id": vid,
                "reason": "TRUSTED_DISCRIMINATOR_VERIFICATION_FAILED",
            })
            continue
        if (
            proof.get("truthful") is not True
            or proof.get("safe") is not True
            or proof.get("total_over_basis") is not True
            or proof.get("discriminator_id") != did
        ):
            rejected_discriminators.append({
                "index": i, "discriminator_id": did,
                "reason": "TRUSTED_DISCRIMINATOR_PROOF_SEMANTICS_INVALID",
            })
            continue
        phi = proof.get("predicate_formula")
        if not _validate_formula(phi, basis_set):
            rejected_discriminators.append({
                "index": i, "discriminator_id": did,
                "reason": "TRUSTED_DISCRIMINATOR_FORMULA_INVALID",
            })
            continue
        discriminator_formulas[did] = phi
        discriminator_costs[did] = float(cost)
        discriminator_proofs[did] = {
            "verifier_id": vid,
            "proof_digest": proof.get("proof_digest"),
        }

    def condition_models(phi: Mapping[str, Any]) -> frozenset[int]:
        return frozenset(i for i, valuation in enumerate(valuations) if _eval(phi, valuation))

    policy_regions = {pid: condition_models(phi) for pid, phi in policy_conditions.items()}
    discriminator_true = {did: condition_models(phi) for did, phi in discriminator_formulas.items()}

    def common_policies(state: frozenset[int]) -> tuple[str, ...]:
        return tuple(sorted(pid for pid, region in policy_regions.items() if state.issubset(region)))

    @lru_cache(maxsize=None)
    def solve(state: frozenset[int]):
        best = None
        covers = common_policies(state)
        if covers:
            pid = min(covers, key=lambda x: (policy_costs[x], x))
            best = {
                "possible": True,
                "worst_cost": policy_costs[pid],
                "policy_id": pid,
                "discriminator_id": None,
                "children": (),
            }

        for did in sorted(discriminator_formulas):
            yes = state.intersection(discriminator_true[did])
            no = state.difference(discriminator_true[did])
            if not yes or not no or yes == state or no == state:
                continue
            children = [solve(frozenset(no)), solve(frozenset(yes))]
            if not all(c["possible"] for c in children):
                continue
            cost = discriminator_costs[did] + max(c["worst_cost"] for c in children)
            candidate = {
                "possible": True,
                "worst_cost": cost,
                "policy_id": None,
                "discriminator_id": did,
                "children": ((False, frozenset(no), children[0]), (True, frozenset(yes), children[1])),
            }
            if (
                best is None
                or candidate["worst_cost"] < best["worst_cost"]
                or (
                    candidate["worst_cost"] == best["worst_cost"]
                    and best["discriminator_id"] is not None
                    and did < best["discriminator_id"]
                )
            ):
                best = candidate

        return best or {
            "possible": False,
            "worst_cost": float("inf"),
            "policy_id": None,
            "discriminator_id": None,
            "children": (),
        }

    root = solve(root_models)

    def serialize(node):
        if node["policy_id"] is not None:
            pid = node["policy_id"]
            return {
                "terminal_policy_id": pid,
                "policy_verifier": policy_proofs[pid],
                "worst_case_remaining_cost_units": node["worst_cost"],
            }
        did = node["discriminator_id"]
        return {
            "discriminator_id": did,
            "discriminator_verifier": discriminator_proofs[did],
            "worst_case_remaining_cost_units": node["worst_cost"],
            "branches": [
                {
                    "outcome": outcome,
                    "remaining_model_count": len(models),
                    "next": serialize(child),
                }
                for outcome, models, child in node["children"]
            ],
        }

    if not root["possible"]:
        # Return the exact root belief size, not a false impossibility claim.
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNRESOLVED__NO_AUTHENTICATED_SYMBOLIC_WINNING_STRATEGY",
            "winning_strategy_proved": False,
            "root_model_count": len(root_models),
            "accepted_constraint_proofs": accepted_constraints,
            "authenticated_policy_count": len(policy_conditions),
            "authenticated_discriminator_count": len(discriminator_formulas),
            "rejected_policy_candidates": rejected_policies,
            "rejected_discriminator_candidates": rejected_discriminators,
            "negative_impossibility_authorized": False,
            "u_empty_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "FAILURE_MEANS_ONLY_CURRENT_TRUSTED_VERIFIER_SET_DOES_NOT_PROVE_A_WIN;"
                "NO_COMPLETE_DISCRIMINATOR_OR_POLICY_SET_IS_ASSUMED"
            ),
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__AUTHENTICATED_SYMBOLIC_WINNING_STRATEGY",
        "winning_strategy_proved": True,
        "root_model_count": len(root_models),
        "accepted_constraint_proofs": accepted_constraints,
        "authenticated_policy_count": len(policy_conditions),
        "authenticated_discriminator_count": len(discriminator_formulas),
        "rejected_policy_candidates": rejected_policies,
        "rejected_discriminator_candidates": rejected_discriminators,
        "minimum_worst_case_resource_bound_units": root["worst_cost"],
        "decision_tree": serialize(root),
        "caller_semantic_flags_accepted": False,
        "complete_discriminator_library_required": False,
        "exact_true_world_enumeration_required": False,
        "negative_impossibility_authorized": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
