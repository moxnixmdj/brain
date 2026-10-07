"""Authenticated explicit-P2 top-law route.

Pipeline:
raw explicit P2 task bytes -> deterministic lossless membership proof ->
independently verified theorem-backed policy adequacy -> Brain-owned P2 solver.

No caller-provided membership boolean or policy-condition formula is accepted.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime.p2_explicit_contract_membership_v1 import compile_membership
from canonical.runtime.p2_top_law_policy_adequacy_authenticator_v1 import (
    authenticate_repository,
    MEMBERSHIP_ATOM_ID,
)
from canonical.runtime.p2_p3_information_safe_candidate_v2 import solve

SCHEMA = "BRAIN_P2_AUTHENTICATED_TOP_LAW_ROUTE_V1"


def execute(raw_source: str | bytes, *, source_id: str) -> dict[str, Any]:
    membership = compile_membership(raw_source, source_id=source_id)
    if membership.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED__P2_MEMBERSHIP_NOT_PROVED",
            "pass": False,
            "membership": membership,
            "terminal_authority": False,
        }

    adequacy = authenticate_repository()
    if adequacy.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__P2_POLICY_ADEQUACY_NOT_AUTHENTICATED",
            "pass": False,
            "membership": membership,
            "policy_adequacy": adequacy,
            "terminal_authority": False,
        }

    if adequacy.get("policy_condition") != {"op": "ATOM", "id": MEMBERSHIP_ATOM_ID}:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__POLICY_CONDITION_BINDING_MISMATCH",
            "pass": False,
            "terminal_authority": False,
        }

    result = solve(membership["public"])
    return {
        "schema": SCHEMA,
        "status": "PASS__AUTHENTICATED_P2_TOP_LAW_POLICY_SELECTED",
        "pass": True,
        "membership_atom": {"op": "ATOM", "id": MEMBERSHIP_ATOM_ID},
        "membership_receipt": membership["membership_receipt"],
        "raw_source_sha256": membership["raw_source_sha256"],
        "normalized_public_sha256": membership["normalized_public_sha256"],
        "policy_id": adequacy["policy_id"],
        "policy_adequacy": adequacy,
        "policy_result": result,
        "terminal_authority": False,
        "boundary": (
            "THIS_CERTIFIES_TOP_LAW_PLAN_SELECTION_ONLY_INSIDE_THE_STRICT_EXPLICIT_P2_SOURCE_CLASS;"
            "STRONG_VISIBLE_QUALITY_BASELINE_LAYOUT_NATIVE_MECHANICAL_AND_GLOBAL_BENCHMARK_SCOPE_REMAIN_SEPARATE"
        ),
    }
