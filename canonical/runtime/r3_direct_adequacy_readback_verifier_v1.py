"""Read-only independent verifier for retained R2 direct-adequacy successes.

The original producer is never executed. The verifier recompiles the exact
preflight and independently reinspects current outputs/source bindings using
the verifier already admitted for the matched direct family.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct
from canonical.runtime import raw_goal_archive_acceptance_v1 as archive_acceptance
from canonical.runtime import raw_goal_exact_literal_acceptance_v1 as literal_acceptance
from canonical.runtime import raw_goal_literal_json_acceptance_v1 as literal_json_acceptance
from canonical.runtime import r2_structured_binary_direct_adequacy_v1 as codec
from canonical.runtime import r2_structured_table_direct_adequacy_v1 as table
from canonical.runtime import r2_docx_direct_adequacy_v1 as docx
from canonical.runtime import r2_docx_json_direct_adequacy_v1 as docx_json
from canonical.runtime import r2_typed_decision_direct_adequacy_v1 as typed
from canonical.runtime.bound_capabilities import docx_verify_ooxml_intent
from canonical.runtime.bound_capabilities import evidence_decision_verify

SCHEMA = "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_READBACK_VERIFIER_V1"
VERIFICATION_BASIS = "EXACT_DIRECT_PREFLIGHT_PLUS_PRODUCER_INDEPENDENT_CURRENT_ARTIFACT_READBACK"


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__R2_DIRECT_SUCCESS_NOT_REVERIFIED",
        "pass": False,
        "reason": reason,
        "execution_replayed": False,
        "terminal_authority": False,
    }


def _sha_file(root: Path, relative: str) -> str:
    p = (root / relative).resolve(strict=True)
    p.relative_to(root)
    if not p.is_file() or p.is_symlink():
        raise ValueError("READBACK_FILE_INVALID:" + relative)
    return sha256(p.read_bytes()).hexdigest()


def _accepted_ids(material: Mapping[str, Any]) -> list[str]:
    raw = material.get("accepted_raw_obligation_ids")
    if not isinstance(raw, list) or not raw or any(not isinstance(x, str) or not x for x in raw):
        raise ValueError("ACCEPTED_OBLIGATION_IDS_INVALID")
    if len(set(raw)) != len(raw):
        raise ValueError("ACCEPTED_OBLIGATION_IDS_DUPLICATE")
    if material.get("raw_acceptance_obligation_count") != len(raw):
        raise ValueError("ACCEPTED_OBLIGATION_COUNT_MISMATCH")
    return list(raw)


def verify_material(
    *,
    problem: Mapping[str, Any],
    episode: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule_head_hash: str,
    value_capsule_head_hash: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        from canonical.runtime.r3_direct_adequacy_success_adapter_v1 import VERIFICATION_KIND
        if problem.get("verification_kind") != VERIFICATION_KIND:
            raise ValueError("VERIFICATION_KIND_INVALID")
        request = problem.get("raw_request")
        material = problem.get("retained_direct_proof")
        if not isinstance(request, Mapping) or not isinstance(material, Mapping):
            raise ValueError("DIRECT_PROOF_MATERIAL_MISSING")
        root = Path(repo_root).resolve(strict=True)
        goal = str(request.get("goal") or "").strip()
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if not goal or problem.get("goal_sha256") != goal_sha or material.get("goal_sha256") != goal_sha:
            raise ValueError("GOAL_HASH_MISMATCH")
        pf = direct.preflight(request)
        if pf.get("matched") is not True:
            raise ValueError("DIRECT_PREFLIGHT_NO_LONGER_MATCHES")
        route_id = str(material.get("route_id") or "")
        if pf.get("route_id") != route_id or problem.get("route_id") != route_id:
            raise ValueError("DIRECT_ROUTE_ID_DRIFT")
        retained_ids = _accepted_ids(material)
        raw_result = material.get("raw_result")
        evidence: Mapping[str, Any]

        if route_id == direct.EXACT_LITERAL_ROUTE_ID:
            if not isinstance(raw_result, Mapping):
                raise ValueError("EXACT_LITERAL_RAW_RESULT_MISSING")
            evidence = literal_acceptance.verify(goal=goal, raw_result=raw_result)
            ids = evidence.get("accepted_obligation_ids")
            ok = (
                evidence.get("pass") is True
                and evidence.get("semantic_acceptance_complete") is True
                and evidence.get("actual_goal_satisfaction_verified") is True
            )
        elif route_id == direct.LITERAL_JSON_ROUTE_ID:
            if not isinstance(raw_result, Mapping):
                raise ValueError("LITERAL_JSON_RAW_RESULT_MISSING")
            evidence = literal_json_acceptance.verify(goal=goal, raw_result=raw_result)
            ids = evidence.get("accepted_obligation_ids")
            ok = (
                evidence.get("pass") is True
                and evidence.get("semantic_acceptance_complete") is True
                and evidence.get("actual_goal_satisfaction_verified") is True
                and evidence.get("artifact_exact") is True
            )
        elif route_id == direct.ARCHIVE_ROUTE_ID:
            retained = material.get("acceptance_receipt")
            if not isinstance(retained, Mapping) or retained.get("pass") is not True:
                raise ValueError("ARCHIVE_ACCEPTANCE_RECEIPT_MISSING")
            output_sha = str(retained.get("verified_output_sha256") or "")
            output_rel = str((pf.get("bound_inputs") or {}).get("output_path") or "")
            if len(output_sha) != 64 or _sha_file(root, output_rel) != output_sha:
                raise ValueError("ARCHIVE_OUTPUT_READBACK_MISMATCH")
            evidence = retained
            ids = retained.get("accepted_obligation_ids")
            ok = retained.get("semantic_acceptance_complete") is True
        elif route_id == direct.STRUCTURED_BINARY_CODEC_ROUTE_ID:
            cp = codec.preflight(request, repo_root=root)
            evidence = codec._independent_verify(cp, repo_root=root)
            ids = retained_ids
            ok = (
                evidence.get("verified") is True
                and evidence.get("producer_independent") is True
                and (
                    evidence.get("dependency_independent") is True
                    or (
                        evidence.get("implementation_independent") is True
                        and evidence.get("supplier_class_independent") is True
                    )
                )
            )
        elif route_id == direct.STRUCTURED_TABLE_ROUTE_ID:
            tp = table.preflight(request, repo_root=root)
            if tp.get("source_sha256") != _sha_file(root, str(tp.get("json_path") or "")):
                raise ValueError("TABLE_SOURCE_HASH_DRIFT")
            evidence = table._independent_verify(tp, repo_root=root)
            ids = retained_ids
            ok = evidence.get("verified") is True and evidence.get("producer_independent_verifier") is True
        elif route_id == direct.DOCX_ROUTE_ID:
            dp = docx.preflight(request, repo_root=root)
            evidence = docx_verify_ooxml_intent.run({"path": dp["output_path"]}, root)
            ids = retained_ids
            ok = (
                evidence.get("verified") is True
                and evidence.get("producer_independent_verifier") is True
                and evidence.get("intent_source_goal") == dp.get("creation_clause")
                and evidence.get("intent_derived_expected") == dp.get("expected")
            )
        elif route_id == direct.DOCX_JSON_ROUTE_ID:
            dp = docx_json.preflight(request, repo_root=root)
            evidence = docx_json._independent_verify(dp, repo_root=root)
            ids = retained_ids
            ok = (
                evidence.get("verified") is True
                and evidence.get("producer_independent_verifier") is True
                and evidence.get("intent_source_goal") == dp.get("goal")
            )
        elif route_id == direct.TYPED_DECISION_ROUTE_ID:
            tp = typed.preflight(request, repo_root=root)
            if tp.get("input_sha256") != _sha_file(root, str(tp.get("input_path") or "")):
                raise ValueError("TYPED_DECISION_INPUT_HASH_DRIFT")
            evidence = evidence_decision_verify.run(
                {"input_path": tp["input_path"], "result_path": tp["output_path"]},
                root,
            )
            ids = retained_ids
            ok = evidence.get("verified") is True and evidence.get("producer_independent") is True
        else:
            raise ValueError("DIRECT_ROUTE_UNSUPPORTED:" + route_id)

        if not ok:
            raise ValueError("DIRECT_CURRENT_READBACK_DID_NOT_VERIFY")
        if isinstance(ids, list) and ids and list(ids) != retained_ids:
            raise ValueError("DIRECT_ACCEPTANCE_OBLIGATION_SET_DRIFT")
        return {
            "schema": SCHEMA,
            "status": "PASS__R2_DIRECT_SUCCESS_REVERIFIED_READ_ONLY",
            "pass": True,
            "verification_basis": VERIFICATION_BASIS,
            "route_id": route_id,
            "goal_sha256": goal_sha,
            "accepted_raw_obligation_ids": retained_ids,
            "execution_replayed": False,
            "producer_independent_readback": True,
            "terminal_authority": False,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
