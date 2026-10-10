"""R2 direct end-to-end adequacy routes V1.

A direct route is admissible only when:
1. a pure exact preflight proves the raw goal belongs to a bounded semantic cell;
2. the route executes the already-verified Brain-owned capability path once;
3. an independent post-execution acceptance verifier covers every raw obligation.

Direct routes are sufficient adequacy proofs for their exact cells. They are not
general language understanding and never grant terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime import raw_goal_archive_acceptance_v1 as archive_acceptance
from canonical.runtime import raw_goal_exact_literal_acceptance_v1 as literal_acceptance
from canonical.runtime import raw_goal_literal_json_acceptance_v1 as literal_json_acceptance
from canonical.runtime import r2_structured_binary_direct_adequacy_v1 as codec_adequacy
from canonical.runtime import r2_structured_table_direct_adequacy_v1 as table_adequacy
from canonical.runtime import r2_docx_direct_adequacy_v1 as docx_adequacy
from canonical.runtime import r2_docx_json_direct_adequacy_v1 as docx_json_adequacy
from canonical.runtime import r2_typed_decision_direct_adequacy_v1 as typed_decision_adequacy
from canonical.runtime import r2_visual_code_direct_adequacy_v1 as visual_code_adequacy
from canonical.runtime import r2_markdown_pdf_direct_adequacy_v1 as markdown_pdf_adequacy
from canonical.runtime import r2_typed_json_transform_direct_adequacy_v1 as typed_json_transform_adequacy
from canonical.runtime import r2_http_json_observation_direct_adequacy_v1 as http_json_observation_adequacy
from canonical.runtime import r2_pypi_provenance_direct_adequacy_v1 as pypi_provenance_adequacy
from canonical.runtime import r2_exact_evidence_claim_support_direct_adequacy_v1 as exact_claim_support_adequacy
from canonical.runtime import r2_explicit_numeric_comparison_direct_adequacy_v1 as numeric_comparison_adequacy
from canonical.runtime import r2_unit_normalized_numeric_comparison_direct_adequacy_v1 as unit_normalized_comparison_adequacy
from canonical.runtime import r2_knowledge_consistency_direct_adequacy_v1 as knowledge_consistency_adequacy
from canonical.runtime import r2_ror_authority_identity_direct_adequacy_v1 as ror_authority_adequacy
from canonical.runtime import r2_finance_normalized_unless_direct_adequacy_v1 as finance_unless_adequacy
from canonical.runtime import r2_finance_controlled_typed_unless_direct_adequacy_v1 as finance_typed_unless_adequacy

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V1"

ARCHIVE_ROUTE_ID = "DIRECT_ADEQUACY::ARCHIVE_MANIFEST_TAR_GZ_V1"
ARCHIVE_CAPABILITY_ID = "archive.tar_gz.create_from_manifest"
EXACT_LITERAL_ROUTE_ID = "DIRECT_ADEQUACY::EXACT_LITERAL_RESPONSE_V1"
LITERAL_JSON_ROUTE_ID = "DIRECT_ADEQUACY::LITERAL_JSON_RECORDS_V1"
STRUCTURED_BINARY_CODEC_ROUTE_ID = "DIRECT_ADEQUACY::STRUCTURED_BINARY_CODEC_FAMILY_V1"
STRUCTURED_TABLE_ROUTE_ID = "DIRECT_ADEQUACY::STRUCTURED_TABLE_ARTIFACT_FAMILY_V1"
DOCX_ROUTE_ID = "DIRECT_ADEQUACY::LITERAL_DOCX_OOXML_FAMILY_V1"
DOCX_JSON_ROUTE_ID = "DIRECT_ADEQUACY::DOCX_JSON_RECORD_FAMILY_V1"
TYPED_DECISION_ROUTE_ID = "DIRECT_ADEQUACY::TYPED_EVIDENCE_DECISION_FAMILY_V1"
VISUAL_CODE_ROUTE_ID = "DIRECT_ADEQUACY::VISUAL_CODE_QR_CODE128_FAMILY_V1"
MARKDOWN_PDF_ROUTE_ID = "DIRECT_ADEQUACY::PLAIN_MARKDOWN_PDF_FAMILY_V1"
TYPED_JSON_TRANSFORM_ROUTE_ID = "DIRECT_ADEQUACY::TYPED_JSON_TRANSFORM_FAMILY_V1"
HTTP_JSON_OBSERVATION_ROUTE_ID = "DIRECT_ADEQUACY::STATE_KEYED_HTTPS_JSON_OBSERVATION_FAMILY_V1"
PYPI_PROVENANCE_ROUTE_ID = "DIRECT_ADEQUACY::PYPI_PINNED_ARTIFACT_PROVENANCE_FAMILY_V1"
EXACT_CLAIM_SUPPORT_ROUTE_ID = "DIRECT_ADEQUACY::EXACT_GROUNDED_EVIDENCE_CLAIM_SUPPORT_FAMILY_V1"
NUMERIC_COMPARISON_ROUTE_ID = "DIRECT_ADEQUACY::EXPLICIT_GROUNDED_NUMERIC_COMPARISON_FAMILY_V1"
UNIT_NORMALIZED_COMPARISON_ROUTE_ID = "DIRECT_ADEQUACY::UNIT_NORMALIZED_GROUNDED_NUMERIC_COMPARISON_FAMILY_V1"
KNOWLEDGE_CONSISTENCY_ROUTE_ID = "DIRECT_ADEQUACY::PROVENANCE_KNOWLEDGE_CONSISTENCY_FAMILY_V1"
ROR_AUTHORITY_ROUTE_ID = "DIRECT_ADEQUACY::EXACT_ROR_AUTHORITY_IDENTITY_FAMILY_V1"
FINANCE_NORMALIZED_UNLESS_ROUTE_ID = "DIRECT_ADEQUACY::FINANCE_NORMALIZED_UNLESS_BRANCH_FAMILY_V1"
FINANCE_CONTROLLED_TYPED_UNLESS_ROUTE_ID = "DIRECT_ADEQUACY::FINANCE_CONTROLLED_TYPED_UNLESS_FAMILY_V1"

ROUTES = {
    ARCHIVE_ROUTE_ID: {
        "capability_id": ARCHIVE_CAPABILITY_ID,
        "scope": "EXACT_ARCHIVE_MANIFEST_VERIFICATION_PATHS_GOAL_ONLY",
        "preflight": "raw_goal_archive_acceptance_v1.GRAMMAR.fullmatch",
        "executor": "live_integrated_brain_v1.run_raw_goal",
        "acceptance": "raw_goal_archive_acceptance_v1.verify",
    },
    EXACT_LITERAL_ROUTE_ID: {
        "capability_id": None,
        "scope": "STRICT_REPLY_OR_RESPOND_WITH_EXACTLY_LITERAL_GOAL_ONLY",
        "preflight": "raw_goal_exact_literal_acceptance_v1.preflight",
        "executor": "live_integrated_brain_v1.run_raw_goal",
        "acceptance": "raw_goal_exact_literal_acceptance_v1.verify",
    },
    LITERAL_JSON_ROUTE_ID: {
        "capability_id": None,
        "scope": "STRICT_LITERAL_JSON_RECORDS_TO_CANONICAL_REPOSITORY_PATH_ONLY",
        "preflight": "raw_goal_literal_json_acceptance_v1.preflight",
        "executor": "live_integrated_brain_v1.run_raw_goal",
        "acceptance": "raw_goal_literal_json_acceptance_v1.verify",
    },
    STRUCTURED_BINARY_CODEC_ROUTE_ID: {
        "capability_id": "DYNAMIC_VERIFIED_BOUND_CODEC",
        "scope": "EXACT_SINGLE_ACTION_JSON_TO_STRUCTURED_BINARY_GOAL_FAMILY",
        "preflight": "r2_structured_binary_direct_adequacy_v1.preflight",
        "executor": "r2_structured_binary_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_INDEPENDENT_CROSS_SUPPLIER_SEMANTIC_DECODE",
    },
    STRUCTURED_TABLE_ROUTE_ID: {
        "capability_id": "DYNAMIC_VERIFIED_BOUND_STRUCTURED_TABLE",
        "scope": "EXACT_SINGLE_ACTION_JSON_RECORDS_TO_XLSX_OR_SQLITE_GOAL_FAMILY",
        "preflight": "r2_structured_table_direct_adequacy_v1.preflight",
        "executor": "r2_structured_table_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_INDEPENDENT_SOURCE_JSON_SEMANTIC_READBACK",
    },
    DOCX_ROUTE_ID: {
        "capability_id": "docx.document.create.python_docx",
        "scope": "EXACT_TWO_CLAUSE_LITERAL_DOCX_PLUS_INDEPENDENT_OOXML_VERIFICATION_FAMILY",
        "preflight": "r2_docx_direct_adequacy_v1.preflight",
        "executor": "r2_docx_direct_adequacy_v1.run",
        "acceptance": "EXACT_INTENT_BINDING_PLUS_PRODUCER_INDEPENDENT_STDLIB_OOXML_VERIFICATION",
    },
    TYPED_DECISION_ROUTE_ID: {
        "capability_id": "decision.synthesis.typed.stdlib",
        "scope": "EXACT_REPOSITORY_LOCAL_TYPED_DECISION_PROBLEM_TO_INDEPENDENTLY_VERIFIED_DECISION_RESULT",
        "preflight": "r2_typed_decision_direct_adequacy_v1.preflight",
        "executor": "r2_typed_decision_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_INDEPENDENT_FULL_DECISION_RECOMPUTATION_PLUS_LOSSLESS_RAW_GOAL_ACCEPTANCE",
    },
    MARKDOWN_PDF_ROUTE_ID: {
        "capability_id": "document.convert.markdown_pdf.pandoc_weasyprint",
        "scope": "EXACT_REPOSITORY_LOCAL_PLAIN_SEMANTIC_MARKDOWN_TO_PDF",
        "preflight": "r2_markdown_pdf_direct_adequacy_v1.preflight",
        "executor": "r2_markdown_pdf_direct_adequacy_v1.run",
        "acceptance": "SOURCE_HASH_STABILITY_PLUS_PRODUCER_INDEPENDENT_PYPDF_VISIBLE_TEXT_READBACK",
    },
    TYPED_JSON_TRANSFORM_ROUTE_ID: {
        "capability_id": "json.query.jq",
        "scope": "EXACT_TYPED_LOCAL_JSON_ARRAY_TRANSFORMS__SELECT_EQ_SORT_BY_PROJECT_TAKE",
        "preflight": "r2_typed_json_transform_direct_adequacy_v1.preflight",
        "executor": "r2_typed_json_transform_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_INDEPENDENT_PYTHON_STDLIB_FULL_TRANSFORM_RECOMPUTATION",
    },
    HTTP_JSON_OBSERVATION_ROUTE_ID: {
        "capability_id": "http.json.fetch_from_state",
        "scope": "EXACT_STATE_KEYED_READ_ONLY_HTTPS_JSON_OBSERVATION",
        "preflight": "r2_http_json_observation_direct_adequacy_v1.preflight",
        "executor": "r2_http_json_observation_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_INDEPENDENT_CURL_REFETCH_PARSED_JSON_SEMANTIC_EQUALITY",
    },
    PYPI_PROVENANCE_ROUTE_ID: {
        "capability_id": "pypi.provenance.audit_live_artifact",
        "scope": "EXACT_CANONICAL_PYPI_PINNED_WHEEL_PROVENANCE_AUDIT",
        "preflight": "r2_pypi_provenance_direct_adequacy_v1.preflight",
        "executor": "r2_pypi_provenance_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_INDEPENDENT_CURL_METADATA_AND_WHEEL_HASH_REPRODUCTION",
    },
    EXACT_CLAIM_SUPPORT_ROUTE_ID: {
        "capability_id": "evidence.claim_relation.generic_units.stdlib",
        "scope": "EXACT_NORMALIZED_SUBSTRING_SUPPORT_OVER_INTEGRITY_CHECKED_GROUNDED_EVIDENCE_UNITS",
        "preflight": "r2_exact_evidence_claim_support_direct_adequacy_v1.preflight",
        "executor": "r2_exact_evidence_claim_support_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_INDEPENDENT_EVIDENCE_INTEGRITY_AND_EXACT_MATCH_SET_RECOMPUTATION",
    },
    NUMERIC_COMPARISON_ROUTE_ID: {
        "capability_id": "evidence.claim_spec.bind.explicit_comparison.stdlib",
        "scope": "EXPLICIT_BOUNDED_GROUNDED_NUMERIC_COMPARISON_GT_LT_GTE_LTE_EQ_NE_ABS_DIFF_LTE",
        "preflight": "r2_explicit_numeric_comparison_direct_adequacy_v1.preflight",
        "executor": "r2_explicit_numeric_comparison_direct_adequacy_v1.run",
        "acceptance": "INHERITED_VERIFIED_ROLE_BINDING_PLUS_PRODUCER_INDEPENDENT_EVIDENCE_INTEGRITY_NUMERIC_LITERAL_UNIT_AND_DECIMAL_PREDICATE_RECOMPUTATION",
    },
    UNIT_NORMALIZED_COMPARISON_ROUTE_ID: {
        "capability_id": "evidence.claim_spec.bind.explicit_comparison.stdlib",
        "scope": "EXPLICIT_MULTIPLICATIVE_UNIT_NORMALIZED_GROUNDED_NUMERIC_COMPARISON",
        "preflight": "r2_unit_normalized_numeric_comparison_direct_adequacy_v1.preflight",
        "executor": "r2_unit_normalized_numeric_comparison_direct_adequacy_v1.run",
        "acceptance": "INHERITED_VERIFIED_ROLE_BINDING_PLUS_DUAL_EXACT_RATIONAL_UNIT_CONVERSION_AND_PREDICATE_RECOMPUTATION",
    },
    KNOWLEDGE_CONSISTENCY_ROUTE_ID: {
        "capability_id": "knowledge.consistency.assess",
        "scope": "PROVENANCE_BEARING_EXTERNAL_JSON_VALUE_CONSISTENCY_OVER_DISTINCT_URL_AND_JSON_PATH_IDENTITIES",
        "preflight": "r2_knowledge_consistency_direct_adequacy_v1.preflight",
        "executor": "r2_knowledge_consistency_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_INDEPENDENT_EVIDENCE_CONTRACT_SOURCE_IDENTITY_CANONICAL_VALUE_FRESHNESS_AND_STATUS_RECOMPUTATION",
    },
    ROR_AUTHORITY_ROUTE_ID: {
        "capability_id": "source.authority.identity.ror",
        "scope": "EXACT_PUBLIC_HOST_TO_ONE_ACTIVE_ROR_ORGANIZATION_IDENTITY",
        "preflight": "r2_ror_authority_identity_direct_adequacy_v1.preflight",
        "executor": "r2_ror_authority_identity_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_ROR_BINDING_PLUS_PRODUCER_INDEPENDENT_CURL_ROR_V2_EXACT_ACTIVE_DOMAIN_RECOMPUTATION",
    },
    FINANCE_NORMALIZED_UNLESS_ROUTE_ID: {
        "capability_id": "finance.normalized_unless.branch.stdlib",
        "scope": "EXACT_NORMALIZED_SUPERVISORY_FINANCE_SINGLE_UNLESS_WITH_EXPLICIT_TYPED_EXCEPTION_TRUTH",
        "preflight": "r2_finance_normalized_unless_direct_adequacy_v1.preflight",
        "executor": "r2_finance_normalized_unless_direct_adequacy_v1.run",
        "acceptance": "SEPARATE_STDLIB_UNLESS_REPARSE_PLUS_FULL_BRANCH_AND_HASH_RECOMPUTATION",
    },
    FINANCE_CONTROLLED_TYPED_UNLESS_ROUTE_ID: {
        "capability_id": "finance.controlled_typed_unless.branch.stdlib",
        "scope": "CONTROLLED_SINGLE_UNLESS_LITERAL_TYPED_FIELD_BOOLEAN_OR_DECIMAL_CONDITION_RELATIVE_TO_TASK_BOUND_CONTENT_ADDRESSED_CONTEXT",
        "preflight": "r2_finance_controlled_typed_unless_direct_adequacy_v1.preflight",
        "executor": "r2_finance_controlled_typed_unless_direct_adequacy_v1.run",
        "acceptance": "INDEPENDENT_SCOPE_TYPED_CONTEXT_CONDITION_BRANCH_AND_HASH_RECOMPUTATION",
    },
    VISUAL_CODE_ROUTE_ID: {
        "capability_id": "DYNAMIC_VERIFIED_BOUND_VISUAL_CODE_PRODUCER",
        "scope": "EXACT_QUOTED_ASCII_PAYLOAD_TO_QR_OR_CODE128_PNG_GOAL_FAMILY",
        "preflight": "r2_visual_code_direct_adequacy_v1.preflight",
        "executor": "r2_visual_code_direct_adequacy_v1.run",
        "acceptance": "PRODUCER_INDEPENDENT_ZBARIMG_DECODE_MUST_EQUAL_EXACT_QUOTED_PAYLOAD",
    },
    DOCX_JSON_ROUTE_ID: {
        "capability_id": "docx.document.create_from_json_record",
        "scope": "EXACT_SINGLE_RECORD_JSON_TO_SEMANTICALLY_VERIFIED_DOCX_REPORT_FAMILY",
        "preflight": "r2_docx_json_direct_adequacy_v1.preflight",
        "executor": "r2_docx_json_direct_adequacy_v1.run",
        "acceptance": "EXACT_SOURCE_HASH_PLUS_INTENT_BINDING_PLUS_PRODUCER_INDEPENDENT_OOXML_SEMANTIC_REOPEN",
    },
}


def _base(status: str, *, passed: bool) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def preflight(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED", passed=False), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {
            **_base("FAIL_CLOSED", passed=False),
            "reason": "TASK_ID_AND_GOAL_REQUIRED",
        }

    match = archive_acceptance.GRAMMAR.fullmatch(goal)
    if match is not None:
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": ARCHIVE_ROUTE_ID,
            "capability_id": ARCHIVE_CAPABILITY_ID,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "bound_inputs": {
                "manifest_path": match.group("manifest"),
                "output_path": match.group("output"),
            },
            "semantic_scope": ROUTES[ARCHIVE_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    literal = literal_acceptance.preflight(goal)
    if literal.get("matched") is True:
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": EXACT_LITERAL_ROUTE_ID,
            "capability_id": None,
            "goal_sha256": literal["goal_sha256"],
            "literal_sha256": literal["literal_sha256"],
            "semantic_scope": ROUTES[EXACT_LITERAL_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    literal_json = literal_json_acceptance.preflight(goal)
    if literal_json.get("matched") is True:
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": LITERAL_JSON_ROUTE_ID,
            "capability_id": None,
            "goal_sha256": literal_json["goal_sha256"],
            "output_path": literal_json["output_path"],
            "records_sha256": literal_json["records_sha256"],
            "semantic_scope": ROUTES[LITERAL_JSON_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    ror_authority = ror_authority_adequacy.preflight(request)
    if ror_authority.get("matched") is True:
        if ror_authority.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": ROR_AUTHORITY_ROUTE_ID,
                "reason": ror_authority.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": ROR_AUTHORITY_ROUTE_ID,
            "capability_id": ror_authority.get("capability_id"),
            "policy_id": ror_authority.get("policy_id"),
            "goal_sha256": ror_authority.get("goal_sha256"),
            "input_path": ror_authority.get("input_path"),
            "candidate_host": ror_authority.get("candidate_host"),
            "output_path": ror_authority.get("output_path"),
            "semantic_scope": ROUTES[ROR_AUTHORITY_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    knowledge_consistency = knowledge_consistency_adequacy.preflight(request)
    if knowledge_consistency.get("matched") is True:
        if knowledge_consistency.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": KNOWLEDGE_CONSISTENCY_ROUTE_ID,
                "reason": knowledge_consistency.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": KNOWLEDGE_CONSISTENCY_ROUTE_ID,
            "capability_id": knowledge_consistency.get("capability_id"),
            "policy_id": knowledge_consistency.get("policy_id"),
            "goal_sha256": knowledge_consistency.get("goal_sha256"),
            "manifest_path": knowledge_consistency.get("manifest_path"),
            "evidence_paths": knowledge_consistency.get("evidence_paths"),
            "max_age_s": knowledge_consistency.get("max_age_s"),
            "output_path": knowledge_consistency.get("output_path"),
            "semantic_scope": ROUTES[KNOWLEDGE_CONSISTENCY_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    unit_normalized_comparison = unit_normalized_comparison_adequacy.preflight(request)
    if unit_normalized_comparison.get("matched") is True:
        if unit_normalized_comparison.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": UNIT_NORMALIZED_COMPARISON_ROUTE_ID,
                "reason": unit_normalized_comparison.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": UNIT_NORMALIZED_COMPARISON_ROUTE_ID,
            "capability_id": unit_normalized_comparison.get("capability_id"),
            "policy_id": unit_normalized_comparison.get("policy_id"),
            "goal_sha256": unit_normalized_comparison.get("goal_sha256"),
            "extraction_path": unit_normalized_comparison.get("extraction_path"),
            "objective": unit_normalized_comparison.get("objective"),
            "operator": unit_normalized_comparison.get("operator"),
            "expected_predicate": unit_normalized_comparison.get("expected_predicate"),
            "dimension": unit_normalized_comparison.get("dimension"),
            "output_path": unit_normalized_comparison.get("output_path"),
            "semantic_scope": ROUTES[UNIT_NORMALIZED_COMPARISON_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    numeric_comparison = numeric_comparison_adequacy.preflight(request)
    if numeric_comparison.get("matched") is True:
        if numeric_comparison.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": NUMERIC_COMPARISON_ROUTE_ID,
                "reason": numeric_comparison.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": NUMERIC_COMPARISON_ROUTE_ID,
            "capability_id": numeric_comparison.get("capability_id"),
            "policy_id": numeric_comparison.get("policy_id"),
            "goal_sha256": numeric_comparison.get("goal_sha256"),
            "extraction_path": numeric_comparison.get("extraction_path"),
            "objective": numeric_comparison.get("objective"),
            "operator": numeric_comparison.get("operator"),
            "expected_predicate": numeric_comparison.get("expected_predicate"),
            "output_path": numeric_comparison.get("output_path"),
            "semantic_scope": ROUTES[NUMERIC_COMPARISON_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    exact_claim_support = exact_claim_support_adequacy.preflight(request)
    if exact_claim_support.get("matched") is True:
        if exact_claim_support.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": EXACT_CLAIM_SUPPORT_ROUTE_ID,
                "reason": exact_claim_support.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": EXACT_CLAIM_SUPPORT_ROUTE_ID,
            "capability_id": exact_claim_support.get("capability_id"),
            "policy_id": exact_claim_support.get("policy_id"),
            "goal_sha256": exact_claim_support.get("goal_sha256"),
            "extraction_path": exact_claim_support.get("extraction_path"),
            "claim_text": exact_claim_support.get("claim_text"),
            "output_path": exact_claim_support.get("output_path"),
            "semantic_scope": ROUTES[EXACT_CLAIM_SUPPORT_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    pypi_provenance = pypi_provenance_adequacy.preflight(request)
    if pypi_provenance.get("matched") is True:
        if pypi_provenance.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": PYPI_PROVENANCE_ROUTE_ID,
                "reason": pypi_provenance.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": PYPI_PROVENANCE_ROUTE_ID,
            "capability_id": pypi_provenance.get("capability_id"),
            "policy_id": pypi_provenance.get("policy_id"),
            "goal_sha256": pypi_provenance.get("goal_sha256"),
            "selection_path": pypi_provenance.get("selection_path"),
            "metadata_path": pypi_provenance.get("metadata_path"),
            "report_path": pypi_provenance.get("report_path"),
            "semantic_scope": ROUTES[PYPI_PROVENANCE_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    http_json_observation = http_json_observation_adequacy.preflight(request)
    if http_json_observation.get("matched") is True:
        if http_json_observation.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": HTTP_JSON_OBSERVATION_ROUTE_ID,
                "reason": http_json_observation.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": HTTP_JSON_OBSERVATION_ROUTE_ID,
            "capability_id": http_json_observation.get("capability_id"),
            "policy_id": http_json_observation.get("policy_id"),
            "goal_sha256": http_json_observation.get("goal_sha256"),
            "state_path": http_json_observation.get("state_path"),
            "url_key": http_json_observation.get("url_key"),
            "output_path": http_json_observation.get("output_path"),
            "semantic_scope": ROUTES[HTTP_JSON_OBSERVATION_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    typed_json_transform = typed_json_transform_adequacy.preflight(request)
    if typed_json_transform.get("matched") is True:
        if typed_json_transform.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": TYPED_JSON_TRANSFORM_ROUTE_ID,
                "reason": typed_json_transform.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": TYPED_JSON_TRANSFORM_ROUTE_ID,
            "capability_id": typed_json_transform.get("capability_id"),
            "policy_id": typed_json_transform.get("policy_id"),
            "goal_sha256": typed_json_transform.get("goal_sha256"),
            "spec_path": typed_json_transform.get("spec_path"),
            "input_path": typed_json_transform.get("input_path"),
            "output_path": typed_json_transform.get("output_path"),
            "semantic_scope": ROUTES[TYPED_JSON_TRANSFORM_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    markdown_pdf = markdown_pdf_adequacy.preflight(request)
    if markdown_pdf.get("matched") is True:
        if markdown_pdf.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": MARKDOWN_PDF_ROUTE_ID,
                "reason": markdown_pdf.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": MARKDOWN_PDF_ROUTE_ID,
            "capability_id": markdown_pdf.get("capability_id"),
            "policy_id": markdown_pdf.get("policy_id"),
            "goal_sha256": markdown_pdf.get("goal_sha256"),
            "markdown_path": markdown_pdf.get("markdown_path"),
            "output_path": markdown_pdf.get("output_path"),
            "semantic_scope": ROUTES[MARKDOWN_PDF_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    visual_code = visual_code_adequacy.preflight(request)
    if visual_code.get("matched") is True:
        if visual_code.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": VISUAL_CODE_ROUTE_ID,
                "reason": visual_code.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": VISUAL_CODE_ROUTE_ID,
            "capability_id": visual_code.get("capability_id"),
            "policy_id": visual_code.get("policy_id"),
            "goal_sha256": visual_code.get("goal_sha256"),
            "format": visual_code.get("format"),
            "payload_sha256": visual_code.get("payload_sha256"),
            "output_path": visual_code.get("output_path"),
            "semantic_scope": ROUTES[VISUAL_CODE_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    finance_typed_unless = finance_typed_unless_adequacy.preflight(request)
    if finance_typed_unless.get("matched") is True:
        if finance_typed_unless.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": FINANCE_CONTROLLED_TYPED_UNLESS_ROUTE_ID,
                "reason": finance_typed_unless.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": FINANCE_CONTROLLED_TYPED_UNLESS_ROUTE_ID,
            "capability_id": finance_typed_unless.get("capability_id"),
            "policy_id": finance_typed_unless.get("policy_id"),
            "goal_sha256": finance_typed_unless.get("goal_sha256"),
            "input_path": finance_typed_unless.get("input_path"),
            "input_sha256": finance_typed_unless.get("input_sha256"),
            "output_path": finance_typed_unless.get("output_path"),
            "source_text_sha256": finance_typed_unless.get("source_text_sha256"),
            "typed_context_sha256": finance_typed_unless.get("typed_context_sha256"),
            "scope_id": finance_typed_unless.get("scope_id"),
            "semantic_scope": ROUTES[FINANCE_CONTROLLED_TYPED_UNLESS_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    finance_unless = finance_unless_adequacy.preflight(request)
    if finance_unless.get("matched") is True:
        if finance_unless.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": FINANCE_NORMALIZED_UNLESS_ROUTE_ID,
                "reason": finance_unless.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": FINANCE_NORMALIZED_UNLESS_ROUTE_ID,
            "capability_id": finance_unless.get("capability_id"),
            "policy_id": finance_unless.get("policy_id"),
            "goal_sha256": finance_unless.get("goal_sha256"),
            "input_path": finance_unless.get("input_path"),
            "input_sha256": finance_unless.get("input_sha256"),
            "output_path": finance_unless.get("output_path"),
            "source_text_sha256": finance_unless.get("source_text_sha256"),
            "scope_id": finance_unless.get("scope_id"),
            "semantic_scope": ROUTES[FINANCE_NORMALIZED_UNLESS_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    typed_decision = typed_decision_adequacy.preflight(request)
    if typed_decision.get("matched") is True:
        if typed_decision.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": TYPED_DECISION_ROUTE_ID,
                "reason": typed_decision.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": TYPED_DECISION_ROUTE_ID,
            "capability_id": typed_decision.get("capability_id"),
            "policy_id": typed_decision.get("policy_id"),
            "goal_sha256": typed_decision.get("goal_sha256"),
            "input_path": typed_decision.get("input_path"),
            "input_sha256": typed_decision.get("input_sha256"),
            "output_path": typed_decision.get("output_path"),
            "semantic_scope": ROUTES[TYPED_DECISION_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    table = table_adequacy.preflight(request)
    if table.get("matched") is True:
        if table.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": STRUCTURED_TABLE_ROUTE_ID,
                "reason": table.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": STRUCTURED_TABLE_ROUTE_ID,
            "capability_id": table.get("capability_id"),
            "policy_id": table.get("policy_id"),
            "goal_sha256": table.get("goal_sha256"),
            "format": table.get("format"),
            "json_path": table.get("json_path"),
            "output_path": table.get("output_path"),
            "semantic_scope": ROUTES[STRUCTURED_TABLE_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    codec = codec_adequacy.preflight(request)
    if codec.get("matched") is True:
        if codec.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": STRUCTURED_BINARY_CODEC_ROUTE_ID,
                "reason": codec.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": STRUCTURED_BINARY_CODEC_ROUTE_ID,
            "capability_id": codec.get("capability_id"),
            "policy_id": codec.get("policy_id"),
            "goal_sha256": codec.get("goal_sha256"),
            "format": codec.get("format"),
            "json_path": codec.get("json_path"),
            "output_path": codec.get("output_path"),
            "semantic_scope": ROUTES[STRUCTURED_BINARY_CODEC_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    docx = docx_adequacy.preflight(request)
    if docx.get("matched") is True:
        if docx.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": DOCX_ROUTE_ID,
                "reason": docx.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": DOCX_ROUTE_ID,
            "capability_id": docx.get("producer_capability_id"),
            "policy_id": docx.get("policy_id"),
            "goal_sha256": docx.get("goal_sha256"),
            "output_path": docx.get("output_path"),
            "intent_path": docx.get("intent_path"),
            "semantic_scope": ROUTES[DOCX_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    docx_json = docx_json_adequacy.preflight(request)
    if docx_json.get("matched") is True:
        if docx_json.get("status") == "FAIL_CLOSED":
            return {
                **_base("FAIL_CLOSED", passed=False),
                "matched": True,
                "route_id": DOCX_JSON_ROUTE_ID,
                "reason": docx_json.get("reason"),
            }
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": DOCX_JSON_ROUTE_ID,
            "capability_id": docx_json.get("capability_id"),
            "policy_id": docx_json.get("policy_id"),
            "goal_sha256": docx_json.get("goal_sha256"),
            "json_path": docx_json.get("json_path"),
            "output_path": docx_json.get("output_path"),
            "intent_path": docx_json.get("intent_path"),
            "semantic_scope": ROUTES[DOCX_JSON_ROUTE_ID]["scope"],
            "preflight_execution_authority": False,
        }

    return {
        **_base("NO_DIRECT_ADEQUACY_ROUTE", passed=False),
        "matched": False,
    }


def run(request: Mapping[str, Any]) -> dict[str, Any]:
    pf = preflight(request)
    if pf.get("matched") is not True:
        return pf

    if pf["route_id"] == ROR_AUTHORITY_ROUTE_ID:
        authority_result = ror_authority_adequacy.run(request)
        if authority_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        authority_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "ror_authority_adequacy": deepcopy(dict(authority_result)),
                "reason": authority_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": authority_result.get("capability_id"),
            "selected_policy_id": authority_result.get("selected_policy_id"),
            "goal_sha256": authority_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                authority_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": authority_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(authority_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(authority_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": authority_result.get("authority_boundary"),
        }

    if pf["route_id"] == KNOWLEDGE_CONSISTENCY_ROUTE_ID:
        consistency_result = knowledge_consistency_adequacy.run(request)
        if consistency_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        consistency_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "knowledge_consistency_adequacy": deepcopy(dict(consistency_result)),
                "reason": consistency_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": consistency_result.get("capability_id"),
            "selected_policy_id": consistency_result.get("selected_policy_id"),
            "goal_sha256": consistency_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                consistency_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": consistency_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(consistency_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(consistency_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": consistency_result.get("authority_boundary"),
        }

    if pf["route_id"] == UNIT_NORMALIZED_COMPARISON_ROUTE_ID:
        unit_result = unit_normalized_comparison_adequacy.run(request)
        if unit_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        unit_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "unit_normalized_comparison_adequacy": deepcopy(dict(unit_result)),
                "reason": unit_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": unit_result.get("capability_id"),
            "selected_policy_id": unit_result.get("selected_policy_id"),
            "goal_sha256": unit_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                unit_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": unit_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(unit_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(unit_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": unit_result.get("authority_boundary"),
        }

    if pf["route_id"] == NUMERIC_COMPARISON_ROUTE_ID:
        comparison_result = numeric_comparison_adequacy.run(request)
        if comparison_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        comparison_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "numeric_comparison_adequacy": deepcopy(dict(comparison_result)),
                "reason": comparison_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": comparison_result.get("capability_id"),
            "selected_policy_id": comparison_result.get("selected_policy_id"),
            "goal_sha256": comparison_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                comparison_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": comparison_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(comparison_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(comparison_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": comparison_result.get("authority_boundary"),
        }

    if pf["route_id"] == EXACT_CLAIM_SUPPORT_ROUTE_ID:
        claim_result = exact_claim_support_adequacy.run(request)
        if claim_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        claim_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "exact_claim_support_adequacy": deepcopy(dict(claim_result)),
                "reason": claim_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": claim_result.get("capability_id"),
            "selected_policy_id": claim_result.get("selected_policy_id"),
            "goal_sha256": claim_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                claim_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": claim_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(claim_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(claim_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": claim_result.get("authority_boundary"),
        }

    if pf["route_id"] == PYPI_PROVENANCE_ROUTE_ID:
        provenance_result = pypi_provenance_adequacy.run(request)
        if provenance_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        provenance_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "pypi_provenance_adequacy": deepcopy(dict(provenance_result)),
                "reason": provenance_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": provenance_result.get("capability_id"),
            "selected_policy_id": provenance_result.get("selected_policy_id"),
            "goal_sha256": provenance_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                provenance_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": provenance_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(provenance_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(provenance_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": provenance_result.get("authority_boundary"),
        }

    if pf["route_id"] == HTTP_JSON_OBSERVATION_ROUTE_ID:
        observation_result = http_json_observation_adequacy.run(request)
        if observation_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        observation_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "http_json_observation_adequacy": deepcopy(dict(observation_result)),
                "reason": observation_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": observation_result.get("capability_id"),
            "selected_policy_id": observation_result.get("selected_policy_id"),
            "goal_sha256": observation_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                observation_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": observation_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(observation_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(observation_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": observation_result.get("authority_boundary"),
        }

    if pf["route_id"] == TYPED_JSON_TRANSFORM_ROUTE_ID:
        transform_result = typed_json_transform_adequacy.run(request)
        if transform_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        transform_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "typed_json_transform_adequacy": deepcopy(dict(transform_result)),
                "reason": transform_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": transform_result.get("capability_id"),
            "selected_policy_id": transform_result.get("selected_policy_id"),
            "goal_sha256": transform_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                transform_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": transform_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(transform_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(transform_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": transform_result.get("authority_boundary"),
        }

    if pf["route_id"] == MARKDOWN_PDF_ROUTE_ID:
        markdown_pdf_result = markdown_pdf_adequacy.run(request)
        if markdown_pdf_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        markdown_pdf_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "markdown_pdf_adequacy": deepcopy(dict(markdown_pdf_result)),
                "reason": markdown_pdf_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": markdown_pdf_result.get("capability_id"),
            "selected_policy_id": markdown_pdf_result.get("policy_id"),
            "goal_sha256": markdown_pdf_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                markdown_pdf_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": markdown_pdf_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(dict(markdown_pdf_result)),
            "raw_result": deepcopy(dict(markdown_pdf_result.get("raw_result") or {})),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": markdown_pdf_result.get("authority_boundary"),
        }

    if pf["route_id"] == VISUAL_CODE_ROUTE_ID:
        visual_result = visual_code_adequacy.run(request)
        if visual_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        visual_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "visual_code_adequacy": deepcopy(dict(visual_result)),
                "reason": visual_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": visual_result.get("capability_id"),
            "selected_policy_id": visual_result.get("policy_id"),
            "goal_sha256": visual_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                visual_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": visual_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(dict(visual_result)),
            "raw_result": deepcopy(dict(visual_result.get("raw_result") or {})),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": visual_result.get("authority_boundary"),
        }

    if pf["route_id"] == FINANCE_CONTROLLED_TYPED_UNLESS_ROUTE_ID:
        finance_typed_result = finance_typed_unless_adequacy.run(request)
        if finance_typed_result.get("pass") is not True:
            return {
                **_base(str(finance_typed_result.get("status") or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"), passed=False),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "finance_controlled_typed_unless_adequacy": deepcopy(dict(finance_typed_result)),
                "reason": finance_typed_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": finance_typed_result.get("capability_id"),
            "selected_policy_id": finance_typed_result.get("selected_policy_id"),
            "goal_sha256": finance_typed_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(finance_typed_result.get("accepted_raw_obligation_ids") or []),
            "raw_acceptance_obligation_count": finance_typed_result.get("raw_acceptance_obligation_count"),
            "acceptance_receipt": deepcopy(dict(finance_typed_result.get("acceptance_receipt") or {})),
            "raw_result": deepcopy(dict(finance_typed_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": finance_typed_result.get("authority_boundary"),
        }

    if pf["route_id"] == FINANCE_NORMALIZED_UNLESS_ROUTE_ID:
        finance_result = finance_unless_adequacy.run(request)
        if finance_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        finance_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "finance_normalized_unless_adequacy": deepcopy(dict(finance_result)),
                "reason": finance_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": finance_result.get("capability_id"),
            "selected_policy_id": finance_result.get("selected_policy_id"),
            "goal_sha256": finance_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                finance_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": finance_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(finance_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(finance_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": finance_result.get("authority_boundary"),
        }

    if pf["route_id"] == TYPED_DECISION_ROUTE_ID:
        typed_result = typed_decision_adequacy.run(request)
        if typed_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        typed_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "typed_decision_adequacy": deepcopy(dict(typed_result)),
                "reason": typed_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": typed_result.get("capability_id"),
            "selected_policy_id": typed_result.get("selected_policy_id"),
            "goal_sha256": typed_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                typed_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": typed_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(
                dict(typed_result.get("acceptance_receipt") or {})
            ),
            "raw_result": deepcopy(dict(typed_result)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": typed_result.get("authority_boundary"),
        }

    if pf["route_id"] == STRUCTURED_TABLE_ROUTE_ID:
        table_result = table_adequacy.run(request)
        if table_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        table_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "table_adequacy": deepcopy(dict(table_result)),
                "reason": table_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": table_result.get("capability_id"),
            "selected_policy_id": table_result.get("policy_id"),
            "goal_sha256": table_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                table_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": table_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(dict(table_result)),
            "raw_result": deepcopy(dict(table_result.get("raw_result") or {})),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": table_result.get("authority_boundary"),
        }

    if pf["route_id"] == STRUCTURED_BINARY_CODEC_ROUTE_ID:
        codec_result = codec_adequacy.run(request)
        if codec_result.get("pass") is not True:
            return {
                **_base(
                    str(codec_result.get("status") or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "codec_adequacy": deepcopy(dict(codec_result)),
                "reason": codec_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": codec_result.get("capability_id"),
            "selected_policy_id": codec_result.get("policy_id"),
            "goal_sha256": codec_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                codec_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": codec_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(dict(codec_result)),
            "raw_result": deepcopy(dict(codec_result.get("raw_result") or {})),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": codec_result.get("authority_boundary"),
        }

    if pf["route_id"] == DOCX_ROUTE_ID:
        docx_result = docx_adequacy.run(request)
        if docx_result.get("pass") is not True:
            return {
                **_base(
                    str(docx_result.get("status") or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "docx_adequacy": deepcopy(dict(docx_result)),
                "reason": docx_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": docx_result.get("capability_id"),
            "selected_policy_id": docx_result.get("policy_id"),
            "goal_sha256": docx_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                docx_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": docx_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(dict(docx_result)),
            "raw_result": deepcopy(dict(docx_result.get("raw_result") or {})),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": docx_result.get("authority_boundary"),
        }

    if pf["route_id"] == DOCX_JSON_ROUTE_ID:
        docx_json_result = docx_json_adequacy.run(request)
        if docx_json_result.get("pass") is not True:
            return {
                **_base(
                    str(
                        docx_json_result.get("status")
                        or "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"
                    ),
                    passed=False,
                ),
                "matched": True,
                "route_id": pf["route_id"],
                "capability_id": pf.get("capability_id"),
                "goal_sha256": pf.get("goal_sha256"),
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "docx_json_adequacy": deepcopy(dict(docx_json_result)),
                "reason": docx_json_result.get("reason"),
            }
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": docx_json_result.get("capability_id"),
            "selected_policy_id": docx_json_result.get("policy_id"),
            "goal_sha256": docx_json_result.get("goal_sha256"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": list(
                docx_json_result.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": docx_json_result.get(
                "raw_acceptance_obligation_count"
            ),
            "acceptance_receipt": deepcopy(dict(docx_json_result)),
            "raw_result": deepcopy(dict(docx_json_result.get("raw_result") or {})),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "authority_boundary": docx_json_result.get("authority_boundary"),
        }

    raw = live_bound.run_raw_goal(request)
    if not isinstance(raw, Mapping):
        return {
            **_base("FAIL_CLOSED", passed=False),
            "reason": "DIRECT_ROUTE_EXECUTION_RESULT_NOT_OBJECT",
            "matched": True,
            "route_id": pf["route_id"],
        }

    if pf["route_id"] == ARCHIVE_ROUTE_ID:
        accepted = raw.get("raw_goal_acceptance")
        accepted_ids = raw.get("accepted_raw_obligation_ids")
        required_count = raw.get("raw_acceptance_obligation_count")
        full = (
            raw.get("pass") is True
            and raw.get("semantic_acceptance_complete") is True
            and raw.get("raw_source_coverage_complete") is True
            and raw.get("compiled_capability_id") == pf["capability_id"]
            and isinstance(accepted, Mapping)
            and accepted.get("pass") is True
            and accepted.get("semantic_acceptance_complete") is True
            and isinstance(accepted_ids, list)
            and isinstance(required_count, int)
            and not isinstance(required_count, bool)
            and required_count > 0
            and len(accepted_ids) == required_count
            and len(set(accepted_ids)) == required_count
            and raw.get("raw_goal_sha256") == pf["goal_sha256"]
        )
    elif pf["route_id"] == EXACT_LITERAL_ROUTE_ID:
        accepted = literal_acceptance.verify(goal=str(request["goal"]), raw_result=raw)
        accepted_ids = accepted.get("accepted_obligation_ids")
        required_count = accepted.get("required_obligation_count")
        full = (
            raw.get("pass") is True
            and isinstance(accepted, Mapping)
            and accepted.get("pass") is True
            and accepted.get("semantic_acceptance_complete") is True
            and accepted.get("actual_goal_satisfaction_verified") is True
            and isinstance(accepted_ids, list)
            and isinstance(required_count, int)
            and not isinstance(required_count, bool)
            and required_count > 0
            and len(accepted_ids) == required_count
            and len(set(accepted_ids)) == required_count
            and raw.get("raw_goal_sha256") == pf["goal_sha256"]
        )
    elif pf["route_id"] == LITERAL_JSON_ROUTE_ID:
        accepted = literal_json_acceptance.verify(
            goal=str(request["goal"]), raw_result=raw
        )
        accepted_ids = accepted.get("accepted_obligation_ids")
        required_count = accepted.get("required_obligation_count")
        full = (
            raw.get("pass") is True
            and isinstance(accepted, Mapping)
            and accepted.get("pass") is True
            and accepted.get("semantic_acceptance_complete") is True
            and accepted.get("actual_goal_satisfaction_verified") is True
            and accepted.get("artifact_exact") is True
            and isinstance(accepted_ids, list)
            and isinstance(required_count, int)
            and not isinstance(required_count, bool)
            and required_count > 0
            and len(accepted_ids) == required_count
            and len(set(accepted_ids)) == required_count
            and raw.get("raw_goal_sha256") == pf["goal_sha256"]
        )
    else:
        return {
            **_base("FAIL_CLOSED", passed=False),
            "reason": "DIRECT_ADEQUACY_ROUTE_ID_UNMODELED",
            "matched": True,
            "route_id": pf.get("route_id"),
        }

    if not full:
        return {
            **_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY", passed=False),
            "matched": True,
            "route_id": pf["route_id"],
            "capability_id": pf.get("capability_id"),
            "goal_sha256": pf["goal_sha256"],
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "raw_result": deepcopy(dict(raw)),
            "acceptance_receipt": deepcopy(dict(accepted)) if isinstance(accepted, Mapping) else None,
            "reason": "FULL_RAW_OBLIGATION_ACCEPTANCE_NOT_VERIFIED",
        }

    return {
        **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
        "matched": True,
        "route_id": pf["route_id"],
        "capability_id": pf.get("capability_id"),
        "selected_policy_id": pf["route_id"],
        "goal_sha256": pf["goal_sha256"],
        "semantic_scope": pf["semantic_scope"],
        "semantic_acceptance_complete": True,
        "actual_goal_satisfaction_verified": True,
        "direct_adequacy_authority": True,
        "accepted_raw_obligation_ids": list(accepted_ids),
        "raw_acceptance_obligation_count": required_count,
        "acceptance_receipt": deepcopy(dict(accepted)),
        "raw_result": deepcopy(dict(raw)),
        "execution_attempted": True,
        "retry_by_other_route_authorized": False,
        "authority_boundary": (
            "ADEQUACY_IS_PROVED_ONLY_FOR_THE_EXACT_PREFLIGHTED_CELL_AND_ONLY_AFTER_"
            "INDEPENDENT_POST_EXECUTION_ACCEPTANCE_COVERS_EVERY_RAW_OBLIGATION"
        ),
    }
