"""Bridge independently authenticated policy-cover authority into reached-state V2.

This adapter is deliberately bounded. It accepts one exact finite reached state
only when the same state is represented by an independently authenticated
observable-policy-cover problem whose totality gate proves:
- complete policy-relevant world scope,
- adequate + hard-constraint-safe Brain-owned policies,
- truthful/safe/complete discriminators,
- finite resource bounds, and
- terminal-or-strict-refinement totality.

It then derives the exact per-row V2 authority receipts from that already
authenticated problem. Caller booleans never create authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import certified_reached_escape_state_constructor_v2 as reached_v2
from canonical.runtime import observable_policy_cover_executor_v1 as cover_executor
from canonical.runtime import observable_policy_cover_totality_gate_v1 as cover_gate
from canonical.runtime import reached_escape_state_kernel_v1 as kernel

SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_POLICY_COVER_AUTHORITY_BRIDGE_V1"
RESOURCE_UNIT = "POLICY_COVER_COST_UNIT"


class ReachedPolicyCoverAuthorityError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _sid(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReachedPolicyCoverAuthorityError(label + "_INVALID")
    return value.strip()


def _seq(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ReachedPolicyCoverAuthorityError(label + "_INVALID")
    return list(value)


def _cost(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReachedPolicyCoverAuthorityError(label + "_INVALID")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise ReachedPolicyCoverAuthorityError(label + "_INVALID")
    return out


def _candidate_core(state: Mapping[str, Any]) -> dict[str, Any]:
    state_id, regions, policies, discriminators = reached_v2._prepare_candidate(state)
    return {
        "schema": kernel.STATE_SCHEMA,
        "state_id": state_id,
        "regions": [{"region_id": rid} for rid in regions],
        "policies": deepcopy(policies),
        "discriminators": deepcopy(discriminators),
    }


def _problem_projection(problem: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(problem, Mapping):
        raise ReachedPolicyCoverAuthorityError("POLICY_COVER_PROBLEM_REQUIRED")
    state_id = _sid(problem.get("state_id"), "STATE_ID")

    region_ids: list[str] = []
    seen_regions: set[str] = set()
    for row in _seq(problem.get("worlds"), "WORLDS"):
        if not isinstance(row, Mapping):
            raise ReachedPolicyCoverAuthorityError("WORLD_ROW_INVALID")
        rid = _sid(row.get("world_id"), "WORLD_ID")
        if rid in seen_regions:
            raise ReachedPolicyCoverAuthorityError("DUPLICATE_WORLD_ID:" + rid)
        seen_regions.add(rid)
        region_ids.append(rid)
    if not region_ids:
        raise ReachedPolicyCoverAuthorityError("WORLD_SET_EMPTY")
    region_ids.sort()
    region_set = set(region_ids)

    policy_map: dict[str, dict[str, Any]] = {}
    policies: list[dict[str, Any]] = []
    for row in _seq(problem.get("policies"), "POLICIES"):
        if not isinstance(row, Mapping):
            raise ReachedPolicyCoverAuthorityError("POLICY_ROW_INVALID")
        pid = _sid(row.get("policy_id"), "POLICY_ID")
        if pid in policy_map:
            raise ReachedPolicyCoverAuthorityError("DUPLICATE_POLICY_ID:" + pid)
        covers = sorted({_sid(x, "POLICY_WORLD_ID") for x in _seq(row.get("adequate_world_ids"), "POLICY_WORLD_IDS")})
        if not covers or not set(covers).issubset(region_set):
            raise ReachedPolicyCoverAuthorityError("POLICY_WORLD_SET_INVALID:" + pid)
        cost = _cost(row.get("cost_units"), "POLICY_COST:" + pid)
        receipt = row.get("adequacy_receipt")
        if not isinstance(receipt, Mapping):
            raise ReachedPolicyCoverAuthorityError("POLICY_ADEQUACY_RECEIPT_REQUIRED:" + pid)
        for key in (
            "independent_verified",
            "exact_byte_bound",
            "policy_adequate_on_every_listed_world",
            "policy_safe_on_every_listed_world",
            "hard_constraint_scope_complete",
            "brain_owned",
            "deployed_exact",
            "resource_bound_proved",
        ):
            if receipt.get(key) is not True:
                raise ReachedPolicyCoverAuthorityError("POLICY_AUTHORITY_PREMISE_UNPROVED:" + pid + ":" + key)
        if receipt.get("policy_id") != pid:
            raise ReachedPolicyCoverAuthorityError("POLICY_RECEIPT_ID_MISMATCH:" + pid)
        policy_map[pid] = {
            "policy_id": pid,
            "adequate_region_ids": covers,
            "cost_units": cost,
        }
        policies.append({"policy_id": pid, "adequate_region_ids": covers})
    policies.sort(key=lambda row: row["policy_id"])

    discriminator_map: dict[str, dict[str, Any]] = {}
    discriminators: list[dict[str, Any]] = []
    for row in _seq(problem.get("discriminators", []), "DISCRIMINATORS"):
        if not isinstance(row, Mapping):
            raise ReachedPolicyCoverAuthorityError("DISCRIMINATOR_ROW_INVALID")
        did = _sid(row.get("discriminator_id"), "DISCRIMINATOR_ID")
        if did in discriminator_map:
            raise ReachedPolicyCoverAuthorityError("DUPLICATE_DISCRIMINATOR_ID:" + did)
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, Mapping) or set(outcomes) != region_set:
            raise ReachedPolicyCoverAuthorityError("DISCRIMINATOR_OUTCOME_DOMAIN_INVALID:" + did)
        normalized_outcomes = {rid: deepcopy(outcomes[rid]) for rid in region_ids}
        _canon(normalized_outcomes)
        cost = _cost(row.get("cost_units"), "DISCRIMINATOR_COST:" + did)
        receipt = row.get("truth_safety_receipt")
        if not isinstance(receipt, Mapping):
            raise ReachedPolicyCoverAuthorityError("DISCRIMINATOR_RECEIPT_REQUIRED:" + did)
        for key in (
            "independent_verified",
            "exact_byte_bound",
            "outcome_map_complete",
            "truth_preserving",
            "safe_on_entire_state",
            "resource_bound_proved",
        ):
            if receipt.get(key) is not True:
                raise ReachedPolicyCoverAuthorityError("DISCRIMINATOR_AUTHORITY_PREMISE_UNPROVED:" + did + ":" + key)
        if receipt.get("discriminator_id") != did:
            raise ReachedPolicyCoverAuthorityError("DISCRIMINATOR_RECEIPT_ID_MISMATCH:" + did)
        discriminator_map[did] = {
            "discriminator_id": did,
            "outcomes": normalized_outcomes,
            "cost_units": cost,
        }
        discriminators.append({"discriminator_id": did, "outcomes": normalized_outcomes})
    discriminators.sort(key=lambda row: row["discriminator_id"])

    core = {
        "schema": kernel.STATE_SCHEMA,
        "state_id": state_id,
        "regions": [{"region_id": rid} for rid in region_ids],
        "policies": policies,
        "discriminators": discriminators,
    }
    return core, policy_map, discriminator_map


def _receipt(claim: Mapping[str, Any], *, kind: str, authority_id: str, verified: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "schema": reached_v2.RECEIPT_SCHEMA,
        "pass": True,
        "claim_sha256": reached_v2._digest(claim),
        "candidate_state_sha256": claim.get("candidate_state_sha256"),
        "authority_kind": kind,
        "authority_id": authority_id,
        "verification_authority_mutated": False,
        "verified": deepcopy(dict(verified)),
    }
    return {**core, "receipt_sha256": reached_v2._digest(core)}


def construct(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    base = {
        "schema": SCHEMA,
        "pass": False,
        "policy_cover_authority_bound": False,
        "global_escape_progress_totality_proved": False,
        "global_repair_acquirability_proved": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    try:
        if not isinstance(payload, Mapping):
            raise ReachedPolicyCoverAuthorityError("PAYLOAD_MAPPING_REQUIRED")
        state = payload.get("state")
        problem = payload.get("policy_cover_problem")
        binding = payload.get("cover_binding")
        if not isinstance(state, Mapping):
            raise ReachedPolicyCoverAuthorityError("STATE_REQUIRED")
        if not isinstance(problem, Mapping):
            raise ReachedPolicyCoverAuthorityError("POLICY_COVER_PROBLEM_REQUIRED")
        if not isinstance(binding, Mapping):
            raise ReachedPolicyCoverAuthorityError("POLICY_COVER_BINDING_REQUIRED")

        candidate_core = _candidate_core(state)
        problem_core, policy_map, discriminator_map = _problem_projection(problem)
        candidate_sha = _digest(candidate_core)
        if _digest(problem_core) != candidate_sha:
            raise ReachedPolicyCoverAuthorityError("STATE_POLICY_COVER_PROJECTION_MISMATCH")

        root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
        cover_auth = cover_executor._authenticate_cover_binding(
            binding,
            problem=problem,
            repo_root=root,
        )
        if cover_auth.get("pass") is not True:
            raise ReachedPolicyCoverAuthorityError(
                "POLICY_COVER_BINDING_NOT_AUTHENTICATED:"
                + str(cover_auth.get("status") or cover_auth.get("reason") or "UNKNOWN")
            )

        cover = cover_gate.evaluate(problem)
        if (
            cover.get("pass") is not True
            or cover.get("bound_state_totality_proved") is not True
            or cover.get("policy_safety_coverage_proved") is not True
        ):
            raise ReachedPolicyCoverAuthorityError(
                "POLICY_COVER_TOTALITY_NOT_PROVED:"
                + str(cover.get("reason") or cover.get("status") or "UNKNOWN")
            )

        authority_id = str(cover_auth.get("independent_verifier_id") or "").strip()
        if not authority_id:
            raise ReachedPolicyCoverAuthorityError("POLICY_COVER_VERIFIER_ID_REQUIRED")

        def policy_verifier(claim: Mapping[str, Any]) -> Mapping[str, Any] | None:
            if (
                claim.get("claim_type") != "POLICY_ADEQUACY_SAFETY_AND_RESOURCE"
                or claim.get("candidate_state_sha256") != candidate_sha
                or claim.get("state_id") != candidate_core["state_id"]
                or sorted(claim.get("region_ids") or []) != [row["region_id"] for row in candidate_core["regions"]]
            ):
                return None
            row = policy_map.get(str(claim.get("policy_id") or ""))
            if row is None or sorted(claim.get("adequate_region_ids") or []) != row["adequate_region_ids"]:
                return None
            return _receipt(
                claim,
                kind="POLICY_ADEQUACY_SAFETY_AND_RESOURCE",
                authority_id=authority_id,
                verified={
                    "safe": True,
                    "adequate_region_ids": row["adequate_region_ids"],
                    "resource_bound": {
                        "amount": row["cost_units"],
                        "unit": RESOURCE_UNIT,
                    },
                },
            )

        def discriminator_verifier(claim: Mapping[str, Any]) -> Mapping[str, Any] | None:
            if (
                claim.get("claim_type") != "DISCRIMINATOR_TRUTH_SAFETY_COMPLETENESS_AND_RESOURCE"
                or claim.get("candidate_state_sha256") != candidate_sha
                or claim.get("state_id") != candidate_core["state_id"]
                or sorted(claim.get("region_ids") or []) != [row["region_id"] for row in candidate_core["regions"]]
            ):
                return None
            row = discriminator_map.get(str(claim.get("discriminator_id") or ""))
            if row is None or _digest(claim.get("outcomes")) != _digest(row["outcomes"]):
                return None
            return _receipt(
                claim,
                kind="DISCRIMINATOR_TRUTH_SAFETY_COMPLETENESS_AND_RESOURCE",
                authority_id=authority_id,
                verified={
                    "safe": True,
                    "truthful": True,
                    "complete": True,
                    "outcomes": row["outcomes"],
                    "resource_bound": {
                        "amount": row["cost_units"],
                        "unit": RESOURCE_UNIT,
                    },
                },
            )

        reached = reached_v2.construct(
            state,
            policy_authority_verifier=policy_verifier,
            discriminator_authority_verifier=discriminator_verifier,
        )
        if reached.get("pass") is not True:
            raise ReachedPolicyCoverAuthorityError(
                "V2_REACHED_STATE_REJECTED_AUTHENTICATED_POSITIVE_COVER:"
                + str(reached.get("reason") or reached.get("status") or "UNKNOWN")
            )

        return {
            **deepcopy(dict(reached)),
            "schema": SCHEMA,
            "policy_cover_authority_bound": True,
            "policy_cover_problem_sha256": _digest(problem),
            "policy_cover_binding": deepcopy(cover_auth),
            "policy_cover_totality": deepcopy(cover),
            "policy_cover_minimum_worst_case_resource_bound_units": cover.get(
                "minimum_worst_case_resource_bound_units"
            ),
            "bounded_reached_state_totality_proved": True,
            "global_escape_progress_totality_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            **base,
            "status": "FAIL_CLOSED__REACHED_ESCAPE_POLICY_COVER_AUTHORITY",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return construct(args or {})
