"""Fail-closed pre-promotion falsification gate.

This gate never grants acceptance, family, capability, ownership, execution, or
promotion credit. It only decides whether a candidate proof package is eligible
to enter a separate target-specific reduction.

The purpose is to prevent a theorem/certificate from changing canonical truth
before exact subject binding, quantified-domain binding, adversarial
counterexample search, boundary/metamorphic search, and independent replay have
all been content-addressed. Risk-specific obligations close failure modes that
already occurred in the terminal program (exact floating-point semantics,
opaque identifier totality, accepted-string totality, and transitive dependency
closure).
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PREPROMOTION_FALSIFICATION_GATE_V1"

BASE_REQUIRED = (
    "SUBJECT_BYTES_BOUND",
    "QUANTIFIED_DOMAIN_BOUND",
    "COUNTEREXAMPLE_SEARCH_PASS",
    "BOUNDARY_SEARCH_PASS",
    "METAMORPHIC_SEARCH_PASS",
    "INDEPENDENT_REPLAY_PASS",
    "SEPARATE_REDUCTION_PRECOMMIT",
)

RISK_REQUIREMENTS = {
    "uses_floating_point": "EXACT_FLOAT_SEMANTICS_BOUND",
    "uses_opaque_identifiers": "IDENTIFIER_TOTALITY_PROVED",
    "accepts_open_string_domain": "STRING_DOMAIN_TOTALITY_PROVED",
    "has_transitive_runtime_dependencies": "TRANSITIVE_DEPENDENCY_CLOSURE_BOUND",
}

_HEX = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def _fail(errors: list[str], required: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "eligible_for_separate_reduction": False,
        "errors": errors,
        "required_obligations": required,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _valid_receipt(name: str, receipt: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, Mapping):
        return [f"MISSING_OR_INVALID_RECEIPT:{name}"]
    if receipt.get("status") != "PASS":
        errors.append(f"RECEIPT_NOT_PASS:{name}")
    if receipt.get("content_addressed") is not True:
        errors.append(f"RECEIPT_NOT_CONTENT_ADDRESSED:{name}")
    sha = receipt.get("receipt_sha")
    if not isinstance(sha, str) or not _HEX.fullmatch(sha):
        errors.append(f"INVALID_RECEIPT_SHA:{name}")
    if name == "INDEPENDENT_REPLAY_PASS" and receipt.get("independent") is not True:
        errors.append("INDEPENDENT_REPLAY_NOT_INDEPENDENT")
    return errors


def evaluate(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        return _fail(["SPEC_NOT_MAPPING"], list(BASE_REQUIRED))

    candidate_id = spec.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        return _fail(["INVALID_CANDIDATE_ID"], list(BASE_REQUIRED))

    claim_type = spec.get("claim_type")
    if claim_type not in {
        "UNIVERSAL_FORMAL",
        "FINITE_EXHAUSTIVE",
        "STRONGER_PROOF_CERTIFICATE",
    }:
        return _fail(["INVALID_CLAIM_TYPE"], list(BASE_REQUIRED))

    risks = spec.get("risk_features", {})
    if not isinstance(risks, Mapping):
        return _fail(["RISK_FEATURES_NOT_MAPPING"], list(BASE_REQUIRED))

    required = list(BASE_REQUIRED)
    for flag, obligation in RISK_REQUIREMENTS.items():
        value = risks.get(flag, False)
        if not isinstance(value, bool):
            return _fail([f"RISK_FLAG_NOT_BOOL:{flag}"], required)
        if value:
            required.append(obligation)

    receipts = spec.get("receipts")
    if not isinstance(receipts, Mapping):
        return _fail(["RECEIPTS_NOT_MAPPING"], required)

    errors: list[str] = []
    for name in required:
        errors.extend(_valid_receipt(name, receipts.get(name)))

    counterexamples = spec.get("known_counterexamples", [])
    if not isinstance(counterexamples, list):
        errors.append("KNOWN_COUNTEREXAMPLES_NOT_LIST")
    elif counterexamples:
        errors.append("KNOWN_COUNTEREXAMPLE_REMAINS_OPEN")

    if spec.get("post_outcome_rule_change") is True:
        errors.append("POST_OUTCOME_RULE_CHANGE_FORBIDDEN")

    if errors:
        return _fail(errors, required)

    return {
        "schema": SCHEMA,
        "status": "PASS__PREPROMOTION_FALSIFICATION_PRECONDITIONS_ONLY",
        "candidate_id": candidate_id,
        "claim_type": claim_type,
        "eligible_for_separate_reduction": True,
        "required_obligations": required,
        "validated_receipt_count": len(required),
        "known_counterexample_count": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "execution_authority": False,
        "promotion_authority": False,
        "hard_nonclaim": (
            "PASS_ONLY_MEANS_THE_CANDIDATE_MAY_ENTER_A_SEPARATE_TARGET_SPECIFIC_"
            "REDUCTION__IT_DOES_NOT_PROVE_THE_CLAIM"
        ),
    }


def run(args=None, root=None):
    return evaluate(args or {})
