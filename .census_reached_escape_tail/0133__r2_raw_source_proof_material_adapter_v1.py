"""R2 raw source-proof material adapter V1.

An information provider may supply raw policy/source text plus raw fact bytes.
The provider is not allowed to declare the selected predicate's truth. This
adapter deterministically creates both Boolean claim candidates and lets the
existing selected_semantic_truth_certificate_v1 checker decide which, if either,
is source-aligned and identity-matched.

This is proposal material only. It grants no semantic, adequacy, execution,
acceptance, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R2_RAW_SOURCE_PROOF_MATERIAL_ADAPTER_V1"
KIND = "R2_RAW_SOURCE_PROOF_MATERIAL_V1"
CLAIM_KIND = "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION"


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def adapt(
    selected_predicate_id: str,
    provided: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(selected_predicate_id, str) or not selected_predicate_id:
        return _fail("SELECTED_PREDICATE_ID_REQUIRED")
    if not isinstance(provided, Mapping):
        return _fail("PROVIDED_MATERIAL_NOT_OBJECT")
    if provided.get("kind") != KIND:
        return _fail("SOURCE_PROOF_MATERIAL_KIND_INVALID")

    allowed = {
        "kind",
        "source_text",
        "source_id",
        "fact_source",
        "fact_source_id",
    }
    extra = set(provided) - allowed
    if extra:
        return _fail("UNMODELED_SOURCE_PROOF_MATERIAL_FIELDS:" + ",".join(sorted(extra)))

    source_text = provided.get("source_text")
    source_id = provided.get("source_id")
    fact_source = provided.get("fact_source")
    fact_source_id = provided.get("fact_source_id")
    if not isinstance(source_text, str) or not source_text:
        return _fail("SOURCE_TEXT_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        return _fail("SOURCE_ID_REQUIRED")
    if not isinstance(fact_source, (str, bytes)) or not fact_source:
        return _fail("FACT_SOURCE_REQUIRED")
    if not isinstance(fact_source_id, str) or not fact_source_id.strip():
        return _fail("FACT_SOURCE_ID_REQUIRED")

    target_claim_id = "r2-selected-source-condition"
    base = {
        "predicate_id": selected_predicate_id,
        "target_claim_id": target_claim_id,
        "source_text": source_text,
        "source_id": source_id.strip(),
        "fact_source": deepcopy(fact_source),
        "fact_source_id": fact_source_id.strip(),
    }
    candidates = []
    for holds in (True, False):
        candidates.append({
            **deepcopy(base),
            "claims": [{
                "claim_id": target_claim_id,
                "kind": CLAIM_KIND,
                "condition_holds": holds,
            }],
        })
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__BOTH_BOOLEAN_SOURCE_PROOF_CANDIDATES_COMPILED",
        "selected_predicate_id": selected_predicate_id,
        "truth_payload_candidates": candidates,
        "provider_declares_truth": False,
        "provider_declares_predicate_identity": False,
        "downstream_checker_must_recompute_identity_and_truth": True,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
