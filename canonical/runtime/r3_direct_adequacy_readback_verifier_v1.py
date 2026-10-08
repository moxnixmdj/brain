"""Independent read-only verifier for retained durable R2 direct successes.

The producer is never invoked. The verifier recompiles the exact raw goal,
re-inspects current source/output state through the already-admitted independent
route verifier, and recomputes the candidate episode/lineage produced by the
mutable success adapter. Unsupported or non-durable routes fail closed.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.executable_skill_program_v7 import program_digest

SCHEMA = "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_READBACK_VERIFIER_V1"
VERIFICATION_KIND = "R2_DIRECT_ADEQUACY_READBACK_V1"
VERIFICATION_BASIS = (
    "EXACT_DIRECT_GOAL_RECOMPILE__CURRENT_SOURCE_IDENTITY__"
    "PRODUCER_INDEPENDENT_ARTIFACT_READBACK__NO_PRODUCER_REPLAY"
)

LITERAL_JSON_ROUTE_ID = "DIRECT_ADEQUACY::LITERAL_JSON_RECORDS_V1"
STRUCTURED_TABLE_ROUTE_ID = "DIRECT_ADEQUACY::STRUCTURED_TABLE_ARTIFACT_FAMILY_V1"
DOCX_ROUTE_ID = "DIRECT_ADEQUACY::LITERAL_DOCX_OOXML_FAMILY_V1"
DOCX_JSON_ROUTE_ID = "DIRECT_ADEQUACY::DOCX_JSON_RECORD_FAMILY_V1"
TYPED_DECISION_ROUTE_ID = "DIRECT_ADEQUACY::TYPED_EVIDENCE_DECISION_FAMILY_V1"
MARKDOWN_PDF_ROUTE_ID = "DIRECT_ADEQUACY::PLAIN_MARKDOWN_PDF_FAMILY_V1"
TYPED_JSON_TRANSFORM_ROUTE_ID = "DIRECT_ADEQUACY::TYPED_JSON_TRANSFORM_FAMILY_V1"
VISUAL_CODE_ROUTE_ID = "DIRECT_ADEQUACY::VISUAL_CODE_QR_CODE128_FAMILY_V1"

SUPPORTED_READBACK_ROUTES = frozenset({
    LITERAL_JSON_ROUTE_ID,
    STRUCTURED_TABLE_ROUTE_ID,
    DOCX_ROUTE_ID,
    DOCX_JSON_ROUTE_ID,
    TYPED_DECISION_ROUTE_ID,
    MARKDOWN_PDF_ROUTE_ID,
    TYPED_JSON_TRANSFORM_ROUTE_ID,
    VISUAL_CODE_ROUTE_ID,
})


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__R2_DIRECT_SUCCESS_NOT_REVERIFIED",
        "pass": False,
        "reason": reason,
        "execution_replayed": False,
        "terminal_authority": False,
    }


def _accepted_ids(material: Mapping[str, Any]) -> list[str]:
    raw = material.get("accepted_raw_obligation_ids")
    count = material.get("raw_acceptance_obligation_count")
    if (
        not isinstance(raw, list)
        or not raw
        or any(not isinstance(x, str) or not x for x in raw)
        or len(set(raw)) != len(raw)
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count != len(raw)
    ):
        raise ValueError("DIRECT_ACCEPTANCE_SET_INVALID")
    return list(raw)


def _sha_file(root: Path, rel: str) -> str:
    target = (root / str(rel)).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file() or target.is_symlink():
        raise ValueError("READBACK_FILE_INVALID:" + str(rel))
    return sha256(target.read_bytes()).hexdigest()


def _obligation_ids_from_contract(contract: Mapping[str, Any]) -> list[str]:
    acceptance = contract.get("acceptance_contract")
    if not isinstance(acceptance, Mapping):
        raise ValueError("RAW_ACCEPTANCE_CONTRACT_MISSING")
    ids = acceptance.get("required_obligation_ids")
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(x, str) or not x for x in ids)
        or len(set(ids)) != len(ids)
    ):
        raise ValueError("RAW_ACCEPTANCE_IDS_INVALID")
    return list(ids)


def _verify_episode_binding(
    *,
    problem: Mapping[str, Any],
    material: Mapping[str, Any],
    episode: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule_head_hash: str,
    value_capsule_head_hash: str,
) -> None:
    goal_sha = str(problem["goal_sha256"])
    route_id = str(problem["route_id"])
    capsule_sha = str(problem["proof_capsule_sha256"])
    accepted_ids = _accepted_ids(material)
    capability_id = str(material.get("capability_id") or "").strip() or None
    accepted_effect = "r2.direct.accepted.sha256:" + goal_sha
    op = capability_id or route_id
    steps = [{"index": 0, "op": op, "inputs": [], "outputs": [accepted_effect]}]
    expected_episode = {
        "episode_id": "r2-direct:" + goal_sha[:24],
        "scope_id": "r2-direct-goal-sha256:" + goal_sha,
        "steps": steps,
        "preconditions": [],
        "postconditions": [accepted_effect],
        "invalidators": [],
        "program_sha256": program_digest(
            steps=steps,
            preconditions=[],
            postconditions=[accepted_effect],
            invalidators=[],
        ),
    }
    if dict(episode) != expected_episode:
        raise ValueError("DIRECT_EPISODE_CANDIDATE_MISMATCH")
    expected_trace = [{
        "cycle": 0,
        "route_id": route_id,
        "capability_id": capability_id,
        "goal_sha256": goal_sha,
        "proof_capsule_sha256": capsule_sha,
        "accepted_effect": accepted_effect,
    }]
    if list(trace) != expected_trace:
        raise ValueError("DIRECT_EPISODE_TRACE_MISMATCH")
    expected_fact = _sha({
        "schema": "PROJECT_BRAIN_R2_DIRECT_FACT_LINEAGE_V1",
        "goal_sha256": goal_sha,
        "route_id": route_id,
        "accepted_effect": accepted_effect,
    })
    expected_value = _sha({
        "schema": "PROJECT_BRAIN_R2_DIRECT_VALUE_LINEAGE_V1",
        "proof_capsule_sha256": capsule_sha,
        "accepted_obligation_ids": accepted_ids,
    })
    if fact_capsule_head_hash != expected_fact:
        raise ValueError("DIRECT_FACT_LINEAGE_MISMATCH")
    if value_capsule_head_hash != expected_value:
        raise ValueError("DIRECT_VALUE_LINEAGE_MISMATCH")
    if problem.get("target_effects") != [accepted_effect]:
        raise ValueError("DIRECT_TARGET_EFFECT_MISMATCH")
    if problem.get("initial_facts") != []:
        raise ValueError("DIRECT_INITIAL_FACTS_MUST_BE_EMPTY")


def _verify_route(
    route_id: str,
    request: Mapping[str, Any],
    material: Mapping[str, Any],
    *,
    root: Path,
) -> list[str]:
    if route_id == LITERAL_JSON_ROUTE_ID:
        from canonical.runtime import raw_goal_literal_json_acceptance_v1 as literal_json
        pf = literal_json.preflight(str(request["goal"]), root=root)
        if pf.get("matched") is not True:
            raise ValueError("LITERAL_JSON_PREFLIGHT_NO_LONGER_MATCHES")
        artifact = (root / str(pf["output_path"])).resolve(strict=True)
        artifact.relative_to(root)
        if json.loads(artifact.read_text(encoding="utf-8")) != pf["expected_records"]:
            raise ValueError("LITERAL_JSON_CURRENT_ARTIFACT_MISMATCH")
        contract = literal_json.compile_contract(
            str(request["goal"]),
            source_id="user",
            routing_target_effects=[literal_json.ROUTING_EFFECT],
        )
        return _obligation_ids_from_contract(contract)

    if route_id == STRUCTURED_TABLE_ROUTE_ID:
        from canonical.runtime import r2_structured_table_direct_adequacy_v1 as table
        pf = table.preflight(request, repo_root=root)
        if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
            raise ValueError("TABLE_PREFLIGHT_NO_LONGER_MATCHES")
        if material.get("source_sha256") != pf.get("source_sha256"):
            raise ValueError("TABLE_SOURCE_IDENTITY_DRIFT")
        evidence = table._independent_verify(pf, repo_root=root)
        if (
            evidence.get("verified") is not True
            or evidence.get("producer_independent_verifier") is not True
        ):
            raise ValueError("TABLE_CURRENT_READBACK_DID_NOT_VERIFY")
        return [
            str(x["obligation_id"])
            for x in pf["raw_contract"]["acceptance_contract"]["obligations"]
        ]

    if route_id == DOCX_ROUTE_ID:
        from canonical.runtime import r2_docx_direct_adequacy_v1 as docx
        from canonical.runtime.bound_capabilities import docx_verify_ooxml_intent
        pf = docx.preflight(request, repo_root=root)
        if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
            raise ValueError("DOCX_PREFLIGHT_NO_LONGER_MATCHES")
        evidence = docx_verify_ooxml_intent.run({"path": pf["output_path"]}, root)
        if (
            evidence.get("verified") is not True
            or evidence.get("producer_independent_verifier") is not True
            or evidence.get("intent_source_goal") != pf.get("creation_clause")
            or evidence.get("intent_derived_expected") != pf.get("expected")
            or evidence.get("expected") != pf.get("expected")
            or evidence.get("title_ok") is not True
            or evidence.get("paragraphs_ok") is not True
            or evidence.get("table_ok") is not True
        ):
            raise ValueError("DOCX_CURRENT_READBACK_DID_NOT_VERIFY")
        return [
            str(x["obligation_id"])
            for x in pf["raw_contract"]["acceptance_contract"]["obligations"]
        ]

    if route_id == DOCX_JSON_ROUTE_ID:
        from canonical.runtime import r2_docx_json_direct_adequacy_v1 as docx_json
        pf = docx_json.preflight(request, repo_root=root)
        if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
            raise ValueError("DOCX_JSON_PREFLIGHT_NO_LONGER_MATCHES")
        if material.get("source_json_sha256") != pf.get("source_json_sha256"):
            raise ValueError("DOCX_JSON_SOURCE_IDENTITY_DRIFT")
        if material.get("expected_semantics_sha256") != pf.get("expected_semantics_sha256"):
            raise ValueError("DOCX_JSON_EXPECTED_SEMANTICS_DRIFT")
        evidence = docx_json._independent_verify(pf, repo_root=root)
        expected = evidence.get("intent_derived_expected")
        if (
            evidence.get("verified") is not True
            or evidence.get("producer_independent_verifier") is not True
            or evidence.get("source_record_verified") is not True
            or evidence.get("path") != pf["output_path"]
            or evidence.get("source_json_path") != pf["json_path"]
            or evidence.get("intent_source_goal") != pf["goal"]
            or not isinstance(expected, Mapping)
            or sha256(docx_json._canon(expected).encode("utf-8")).hexdigest()
            != pf["expected_semantics_sha256"]
        ):
            raise ValueError("DOCX_JSON_CURRENT_READBACK_DID_NOT_VERIFY")
        return [
            str(x["obligation_id"])
            for x in pf["raw_contract"]["acceptance_contract"]["obligations"]
        ]

    if route_id == TYPED_DECISION_ROUTE_ID:
        from canonical.runtime import r2_typed_decision_direct_adequacy_v1 as typed
        from canonical.runtime.bound_capabilities import evidence_decision_verify
        pf = typed.preflight(request, repo_root=root)
        if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
            raise ValueError("TYPED_DECISION_PREFLIGHT_NO_LONGER_MATCHES")
        if material.get("input_sha256") != pf.get("input_sha256"):
            raise ValueError("TYPED_DECISION_INPUT_IDENTITY_DRIFT")
        evidence = evidence_decision_verify.run(
            {"input_path": pf["input_path"], "result_path": pf["output_path"]},
            root,
        )
        if (
            evidence.get("verified") is not True
            or evidence.get("producer_independent") is not True
            or evidence.get("model_dependency_count") != 0
        ):
            raise ValueError("TYPED_DECISION_CURRENT_READBACK_DID_NOT_VERIFY")
        return list(pf["raw_acceptance_obligation_ids"])

    if route_id == MARKDOWN_PDF_ROUTE_ID:
        from canonical.runtime import r2_markdown_pdf_direct_adequacy_v1 as mdpdf
        pf = mdpdf.preflight(request, repo_root=root)
        if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
            raise ValueError("MARKDOWN_PDF_PREFLIGHT_NO_LONGER_MATCHES")
        if material.get("source_sha256") != pf.get("source_sha256"):
            raise ValueError("MARKDOWN_PDF_SOURCE_IDENTITY_DRIFT")
        evidence = mdpdf._independent_verify(pf, repo_root=root)
        if (
            evidence.get("verified") is not True
            or evidence.get("producer_independent_verifier") is not True
            or evidence.get("verifier_capability_id") != mdpdf.VERIFIER
        ):
            raise ValueError("MARKDOWN_PDF_CURRENT_READBACK_DID_NOT_VERIFY")
        return [
            str(x["obligation_id"])
            for x in pf["raw_contract"]["acceptance_contract"]["obligations"]
        ]

    if route_id == TYPED_JSON_TRANSFORM_ROUTE_ID:
        from canonical.runtime import r2_typed_json_transform_direct_adequacy_v1 as transform
        pf = transform.preflight(request, repo_root=root)
        if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
            raise ValueError("TYPED_JSON_PREFLIGHT_NO_LONGER_MATCHES")
        if material.get("spec_sha256") != pf.get("spec_sha256"):
            raise ValueError("TYPED_JSON_SPEC_IDENTITY_DRIFT")
        if material.get("input_sha256") != pf.get("input_sha256"):
            raise ValueError("TYPED_JSON_INPUT_IDENTITY_DRIFT")
        spec = json.loads((root / pf["spec_path"]).read_text(encoding="utf-8"))
        source = json.loads((root / pf["input_path"]).read_text(encoding="utf-8"))
        actual = json.loads((root / pf["output_path"]).read_text(encoding="utf-8"))
        operations = transform._validated_spec(spec)
        if operations != pf["operations"]:
            raise ValueError("TYPED_JSON_SPEC_SEMANTICS_DRIFT")
        expected = transform._reference_apply(source, operations)
        if actual != expected:
            raise ValueError("TYPED_JSON_CURRENT_SEMANTICS_MISMATCH")
        if sha256(transform._canon(actual)).hexdigest() != pf["expected_result_sha256"]:
            raise ValueError("TYPED_JSON_CURRENT_HASH_MISMATCH")
        return list(pf["raw_acceptance_obligation_ids"])

    if route_id == VISUAL_CODE_ROUTE_ID:
        from canonical.runtime import r2_visual_code_direct_adequacy_v1 as visual
        pf = visual.preflight(request, repo_root=root)
        if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
            raise ValueError("VISUAL_CODE_PREFLIGHT_NO_LONGER_MATCHES")
        retained_payload = material.get("payload_sha256")
        if retained_payload is not None and retained_payload != pf.get("payload_sha256"):
            raise ValueError("VISUAL_CODE_PAYLOAD_IDENTITY_DRIFT")
        evidence = visual._independent_decode(pf, repo_root=root)
        if (
            evidence.get("verified") is not True
            or evidence.get("producer_independent") is not True
            or evidence.get("supplier_packages_disjoint") is not True
            or evidence.get("decoded_payload") != pf["payload"]
        ):
            raise ValueError("VISUAL_CODE_CURRENT_READBACK_DID_NOT_VERIFY")
        return [
            str(x["obligation_id"])
            for x in pf["raw_contract"]["acceptance_contract"]["obligations"]
        ]

    raise ValueError("DIRECT_ROUTE_UNSUPPORTED:" + route_id)


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
        if not isinstance(problem, Mapping) or problem.get("verification_kind") != VERIFICATION_KIND:
            raise ValueError("DIRECT_VERIFICATION_KIND_INVALID")
        request = problem.get("raw_request")
        material = problem.get("retained_direct_proof")
        if not isinstance(request, Mapping) or not isinstance(material, Mapping):
            raise ValueError("DIRECT_VERIFICATION_MATERIAL_MISSING")
        if material.get("proof_kind") != VERIFICATION_KIND:
            raise ValueError("DIRECT_PROOF_KIND_INVALID")

        capsule_sha = str(problem.get("proof_capsule_sha256") or "")
        if len(capsule_sha) != 64 or _sha(material) != capsule_sha:
            raise ValueError("DIRECT_PROOF_CAPSULE_DIGEST_MISMATCH")
        goal = str(request.get("goal") or "").strip()
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if (
            not goal
            or problem.get("goal_sha256") != goal_sha
            or material.get("goal_sha256") != goal_sha
        ):
            raise ValueError("DIRECT_GOAL_HASH_MISMATCH")
        route_id = str(material.get("route_id") or "").strip()
        if route_id not in SUPPORTED_READBACK_ROUTES:
            raise ValueError("DIRECT_ROUTE_NOT_READBACK_ADMITTED:" + route_id)
        if problem.get("route_id") != route_id:
            raise ValueError("DIRECT_ROUTE_ID_DRIFT")
        retained_ids = _accepted_ids(material)

        _verify_episode_binding(
            problem=problem,
            material=material,
            episode=episode,
            trace=trace,
            fact_capsule_head_hash=fact_capsule_head_hash,
            value_capsule_head_hash=value_capsule_head_hash,
        )
        root = Path(repo_root).resolve(strict=True)
        current_ids = _verify_route(route_id, request, material, root=root)
        if current_ids != retained_ids:
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
