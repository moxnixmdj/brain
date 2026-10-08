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
