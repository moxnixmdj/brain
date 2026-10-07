"""Adequacy-basis structural completeness gate v2.

V2 preserves the independently verified v1 field-coverage checks and removes one
overconstraint: a complete candidate-policy set is not required for a positive
cover claim when one or more Brain-owned policies already have sound positive
adequacy certificates.

Completeness remains mandatory for negative/exhaustive claims such as proving no
common policy exists or claiming globally minimum information/discriminator cost.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.adequacy_basis_structural_completeness_gate_v1 import (
    verify_policy_manifest as verify_v1,
)

SCHEMA = "PROJECT_BRAIN_ADEQUACY_BASIS_STRUCTURAL_COMPLETENESS_GATE_V2"
POSITIVE = "POSITIVE_COVER"
NEGATIVE = "NEGATIVE_EXHAUSTIVE"
MINIMUM = "MINIMUM_INFORMATION_OPTIMALITY"
MODES = {POSITIVE, NEGATIVE, MINIMUM}
_MISSING_SET_CERT = "CANDIDATE_POLICY_SET_COMPLETENESS_CERTIFICATE_MISSING"


def _fail(reason: str, *, detail: Any = None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "errors": [reason],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail is not None:
        out["detail"] = detail
    return out


def verify_policy_manifest(
    contract: Any,
    contract_schema: Any,
    manifest: Any,
) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        return _fail("MANIFEST_NOT_OBJECT")

    mode = manifest.get("claim_mode")
    if mode not in MODES:
        return _fail("CLAIM_MODE_INVALID_OR_MISSING")

    base = verify_v1(contract, contract_schema, manifest)
    errors = list(base.get("errors") or [])

    if mode == POSITIVE:
        remaining = [e for e in errors if e != _MISSING_SET_CERT]
        passed = not remaining
        out = dict(base)
        out.update({
            "schema": SCHEMA,
            "pass": passed,
            "status": (
                "PASS__POSITIVE_COVER_STRUCTURAL_BASIS_COMPLETE__"
                "CANDIDATE_POLICY_SET_COMPLETENESS_NOT_REQUIRED"
                if passed else "FAIL_CLOSED"
            ),
            "errors": remaining,
            "claim_mode": mode,
            "candidate_policy_set_completeness_required": False,
            "candidate_policy_set_completeness_self_verified": False,
            "rule": (
                "POSITIVE_COVER_REQUIRES_SOUND_ADEQUACY_FOR_USED_POLICIES_ONLY;"
                "UNLISTED_POLICIES_REMAIN_UNKNOWN_AND_CANNOT_INVALIDATE_A_SOUND_POSITIVE_COVER"
            ),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        })
        return out

    out = dict(base)
    out.update({
        "schema": SCHEMA,
        "claim_mode": mode,
        "candidate_policy_set_completeness_required": True,
        "rule": (
            "NEGATIVE_OR_GLOBAL_MINIMALITY_CLAIMS_REQUIRE_POLICY_UNIVERSE_COMPLETENESS;"
            "PARTIAL_POSITIVE_ADEQUACY_CANNOT_PROVE_ABSENCE_OR_GLOBAL_MINIMALITY"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    })
    return out
