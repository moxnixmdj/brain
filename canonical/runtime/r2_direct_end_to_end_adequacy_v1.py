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
from canonical.runtime import raw_goal_qr_acceptance_v1 as qr_acceptance

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V1"

ARCHIVE_ROUTE_ID = "DIRECT_ADEQUACY::ARCHIVE_MANIFEST_TAR_GZ_V1"
ARCHIVE_CAPABILITY_ID = "archive.tar_gz.create_from_manifest"
EXACT_LITERAL_ROUTE_ID = "DIRECT_ADEQUACY::EXACT_LITERAL_RESPONSE_V1"
LITERAL_JSON_ROUTE_ID = "DIRECT_ADEQUACY::LITERAL_JSON_RECORDS_V1"
QR_ROUTE_ID = "DIRECT_ADEQUACY::QR_EXACT_PAYLOAD_V1"
QR_CAPABILITY_ID = "image.qr.generate.qrencode"

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
    QR_ROUTE_ID: {
        "capability_id": QR_CAPABILITY_ID,
        "scope": "STRICT_QR_EXACT_PAYLOAD_TO_CANONICAL_ASTRA_TMP_PNG_ONLY",
        "preflight": "raw_goal_qr_acceptance_v1.preflight",
        "executor": "live_integrated_brain_v1.run_raw_goal",
        "acceptance": "raw_goal_qr_acceptance_v1.verify",
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

    qr = qr_acceptance.preflight(goal)
    if qr.get("matched") is True:
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": QR_ROUTE_ID,
            "capability_id": QR_CAPABILITY_ID,
            "goal_sha256": qr["goal_sha256"],
            "payload_sha256": qr["payload_sha256"],
            "output_path": qr["output_path"],
            "semantic_scope": ROUTES[QR_ROUTE_ID]["scope"],
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
    elif pf["route_id"] == QR_ROUTE_ID:
        accepted = qr_acceptance.verify(
            goal=str(request["goal"]), raw_result=raw
        )
        accepted_ids = accepted.get("accepted_obligation_ids")
        required_count = accepted.get("required_obligation_count")
        full = (
            raw.get("pass") is True
            and raw.get("compiled_capability_id") == QR_CAPABILITY_ID
            and isinstance(accepted, Mapping)
            and accepted.get("pass") is True
            and accepted.get("semantic_acceptance_complete") is True
            and accepted.get("actual_goal_satisfaction_verified") is True
            and accepted.get("decoded_payload_exact") is True
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
