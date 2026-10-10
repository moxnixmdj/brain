"""Claim-scoped professional edit causal certificate compiler.

Generalizes a verified before/after professional edit experiment into a reusable
fail-closed certificate only for the exact intervention/outcome scope proved by
its execution receipt. It does not establish global professional-quality
causality, multi-edit attribution, treatment-version invariance, or sequence
invariance.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_EDIT_CAUSAL_CERTIFICATE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_VERIFY_V1"
ADMITTED_STATUS = (
    "PASS__REAL_PROFESSIONAL_CODE_EDIT_AB__OLD_FAIL_NEW_PASS__"
    "CLAIM_SCOPED_R7_CAUSAL_INSTANCE__ZERO_TERMINAL_CREDIT"
)


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "causal_claim_authority": False,
        "global_r7_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def compile_certificate(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        return _fail("RECEIPT_NOT_OBJECT")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        return _fail("RECEIPT_SCHEMA_INVALID")
    if receipt.get("status") != ADMITTED_STATUS:
        return _fail("RECEIPT_STATUS_NOT_ADMITTED")

    scope = receipt.get("claim_scope")
    subject = receipt.get("exact_subject")
    execution = receipt.get("real_execution")
    identity = receipt.get("byte_identity")
    dispositions = receipt.get("r7_defeater_disposition")
    conclusions = receipt.get("conclusions")
    if not all(isinstance(x, Mapping) for x in (
        scope, subject, execution, identity, dispositions, conclusions
    )):
        return _fail("RECEIPT_REQUIRED_SECTION_INVALID")

    if scope.get("kind") != "EXACT_SINGLE_EDIT_PROFESSIONAL_CODE_INTERVENTION_INSTANCE":
        return _fail("ONLY_EXACT_SINGLE_EDIT_SCOPE_ADMITTED")
    if scope.get("reusable_global_design_rule_claimed") is not False:
        return _fail("GLOBAL_RULE_CLAIM_FORBIDDEN")

    if execution.get("same_test_bytes") is not True:
        return _fail("SAME_TEST_BYTES_REQUIRED")
    old = execution.get("predecessor_result")
    new = execution.get("repaired_result")
    if not isinstance(old, Mapping) or not isinstance(new, Mapping):
        return _fail("EXECUTION_RESULTS_INVALID")
    if old.get("outcome") != "FAIL" or new.get("outcome") != "PASS":
        return _fail("REQUIRED_FAIL_TO_PASS_SIGNATURE_MISSING")
    if old.get("return_code") == 0 or new.get("return_code") != 0:
        return _fail("RETURN_CODE_SIGNATURE_INVALID")

    predecessor_sha = subject.get("predecessor_runtime_git_blob_sha")
    repaired_sha = subject.get("repaired_runtime_git_blob_sha")
    test_sha = subject.get("regression_test_git_blob_sha")
    if not all(isinstance(x, str) and len(x) == 40 for x in (
        predecessor_sha, repaired_sha, test_sha
    )):
        return _fail("CONTENT_ADDRESS_INVALID")
    if predecessor_sha == repaired_sha:
        return _fail("NO_INTERVENTION_BYTE_CHANGE")

    if identity.get("predecessor_runtime_materialized_git_hash_object") != predecessor_sha:
        return _fail("PREDECESSOR_BYTE_IDENTITY_MISMATCH")
    if identity.get("repaired_runtime_materialized_git_hash_object") != repaired_sha:
        return _fail("REPAIRED_BYTE_IDENTITY_MISMATCH")
    if identity.get("predecessor_test_materialized_git_hash_object") != test_sha:
        return _fail("TEST_BYTE_IDENTITY_MISMATCH")

    expected = {
        "C28_PREDICTIVE_PRESCRIPTIVE_GAP": "DISCHARGED_FOR_THIS_EXACT_INSTANCE",
        "C30_TREATMENT_VERSION_NONINVARIANCE": "DISCHARGED_FOR_THIS_EXACT_INSTANCE",
        "C29_COMPOUND_EDIT_ATTRIBUTION": "PROVEN_IRRELEVANT_TO_THIS_CLAIM_SCOPE",
        "C31_EDIT_SEQUENCE_INTERACTION": "PROVEN_IRRELEVANT_TO_THIS_CLAIM_SCOPE",
    }
    for defeater_id, state in expected.items():
        row = dispositions.get(defeater_id)
        if not isinstance(row, Mapping) or row.get("claim_scoped_state") != state:
            return _fail("R7_DEFEATER_STATE_INVALID:" + defeater_id)

    if conclusions.get("exact_claim_scoped_professional_edit_causality_proved") is not True:
        return _fail("SOURCE_CAUSAL_CONCLUSION_NOT_PROVED")
    for forbidden_true in (
        "r7_global_root_closed",
        "domain_semantic_closure",
        "domain_execution_closure",
        "multi_edit_attribution_proved",
        "sequence_invariance_proved",
        "treatment_generalization_proved",
    ):
        if conclusions.get(forbidden_true) is True:
            return _fail("SOURCE_OVERCLAIM_FORBIDDEN:" + forbidden_true)

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_SINGLE_EDIT_CAUSAL_CERTIFICATE_COMPILED",
        "pass": True,
        "claim_scope": deepcopy(dict(scope)),
        "artifact": scope.get("artifact"),
        "intervention": scope.get("intervention"),
        "claimed_effect": scope.get("claimed_effect"),
        "predecessor_runtime_git_blob_sha": predecessor_sha,
        "repaired_runtime_git_blob_sha": repaired_sha,
        "regression_test_git_blob_sha": test_sha,
        "execution_signature": "PREDECESSOR_FAIL__REPAIRED_PASS__IDENTICAL_TEST_BYTES",
        "r7_disposition": {
            "C28_PREDICTIVE_PRESCRIPTIVE_GAP": "DISCHARGED_FOR_THIS_EXACT_INSTANCE",
            "C30_TREATMENT_VERSION_NONINVARIANCE": "DISCHARGED_FOR_THIS_EXACT_INSTANCE",
            "C29_COMPOUND_EDIT_ATTRIBUTION": "PROVEN_IRRELEVANT_TO_THIS_SINGLE_EDIT_SCOPE",
            "C31_EDIT_SEQUENCE_INTERACTION": "PROVEN_IRRELEVANT_TO_THIS_SINGLE_EDIT_SCOPE",
        },
        "reusable_mechanism": True,
        "reusable_scope": (
            "EXACT_SINGLE_EDIT_FAIL_TO_PASS_AB_EXPERIMENTS_WITH_IDENTICAL_"
            "TEST_BYTES_AND_CONTENT_ADDRESSED_SUBJECTS"
        ),
        "causal_claim_authority": True,
        "global_r7_authority": False,
        "domain_semantic_closure": False,
        "domain_execution_closure": False,
        "multi_edit_attribution_proved": False,
        "sequence_invariance_proved": False,
        "treatment_generalization_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
