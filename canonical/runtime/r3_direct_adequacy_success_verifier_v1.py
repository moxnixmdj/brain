"""Independent read-only verifier for R2 direct-adequacy success episodes.

No producer is replayed. The verifier recompiles the route preflight, re-reads the
current source/artifact bytes with the route's existing independent acceptance
mechanism, checks the retained semantic evidence, and then verifies the R3 episode
lineage. It grants no execution, capability, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.executable_skill_program_v7 import program_digest
from canonical.runtime.r3_direct_adequacy_success_adapter_v1 import VERIFICATION_KIND

SCHEMA = "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_SUCCESS_VERIFIER_V1"
VERIFICATION_BASIS = "R2_DIRECT_ROUTE_PRODUCER_INDEPENDENT_READBACK_V1"

STRUCTURED_BINARY_CODEC_ROUTE_ID = "DIRECT_ADEQUACY::STRUCTURED_BINARY_CODEC_FAMILY_V1"
STRUCTURED_TABLE_ROUTE_ID = "DIRECT_ADEQUACY::STRUCTURED_TABLE_ARTIFACT_FAMILY_V1"
DOCX_ROUTE_ID = "DIRECT_ADEQUACY::LITERAL_DOCX_OOXML_FAMILY_V1"
DOCX_JSON_ROUTE_ID = "DIRECT_ADEQUACY::DOCX_JSON_RECORD_FAMILY_V1"
TYPED_DECISION_ROUTE_ID = "DIRECT_ADEQUACY::TYPED_EVIDENCE_DECISION_FAMILY_V1"
VISUAL_CODE_ROUTE_ID = "DIRECT_ADEQUACY::VISUAL_CODE_QR_CODE128_FAMILY_V1"
MARKDOWN_PDF_ROUTE_ID = "DIRECT_ADEQUACY::PLAIN_MARKDOWN_PDF_FAMILY_V1"
TYPED_JSON_TRANSFORM_ROUTE_ID = "DIRECT_ADEQUACY::TYPED_JSON_TRANSFORM_FAMILY_V1"


class DirectAdequacyVerificationError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _safe(root: Path, relative: str) -> Path:
    rel = Path(str(relative or "").strip())
    if not rel.as_posix() or rel.is_absolute() or ".." in rel.parts:
        raise DirectAdequacyVerificationError("REPOSITORY_PATH_INVALID")
    target = (root / rel).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file() or target.is_symlink():
        raise DirectAdequacyVerificationError("REPOSITORY_FILE_REQUIRED:" + rel.as_posix())
    return target


def _accepted_ids(pf: Mapping[str, Any]) -> list[str]:
    raw = pf.get("raw_acceptance_obligation_ids")
    if isinstance(raw, list) and raw:
        return [str(x) for x in raw]
    contract = pf.get("raw_contract")
    acceptance = contract.get("acceptance_contract") if isinstance(contract, Mapping) else None
    obligations = acceptance.get("obligations") if isinstance(acceptance, Mapping) else None
    if isinstance(obligations, list) and obligations:
        out = []
        for row in obligations:
            if not isinstance(row, Mapping) or not str(row.get("obligation_id") or ""):
                raise DirectAdequacyVerificationError("RAW_ACCEPTANCE_OBLIGATION_INVALID")
            out.append(str(row["obligation_id"]))
        return out
    required = acceptance.get("required_obligation_ids") if isinstance(acceptance, Mapping) else None
    if isinstance(required, list) and required:
        return [str(x) for x in required]
    raise DirectAdequacyVerificationError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")


def _typed_transform_verify(
    typed_transform: Any,
    pf: Mapping[str, Any],
    root: Path,
) -> Mapping[str, Any]:
    spec_path = _safe(root, str(pf["spec_path"]))
    input_path = _safe(root, str(pf["input_path"]))
    output_path = _safe(root, str(pf["output_path"]))
    if typed_transform._sha_file(spec_path) != pf["spec_sha256"]:
        raise DirectAdequacyVerificationError("TRANSFORM_SPEC_SHA_DRIFT")
    if typed_transform._sha_file(input_path) != pf["input_sha256"]:
        raise DirectAdequacyVerificationError("TRANSFORM_INPUT_SHA_DRIFT")
    source = json.loads(input_path.read_text(encoding="utf-8"))
    spec_raw = json.loads(spec_path.read_text(encoding="utf-8"))
    operations = typed_transform._validated_spec(spec_raw)
    if operations != pf["operations"]:
        raise DirectAdequacyVerificationError("TRANSFORM_SPEC_SEMANTICS_DRIFT")
    expected = typed_transform._reference_apply(source, operations)
    actual = json.loads(output_path.read_text(encoding="utf-8"))
    if actual != expected:
        raise DirectAdequacyVerificationError("TRANSFORM_SEMANTIC_READBACK_MISMATCH")
    actual_semantic_sha = sha256(typed_transform._canon(actual)).hexdigest()
    if actual_semantic_sha != pf["expected_result_sha256"]:
        raise DirectAdequacyVerificationError("TRANSFORM_RESULT_SHA_MISMATCH")
    return {
        "verified": True,
        "producer_independent": True,
        "verifier": "python_stdlib_reference_transform",
        "expected_result_sha256": pf["expected_result_sha256"],
        "actual_semantic_result_sha256": actual_semantic_sha,
        "source_immutability_verified": True,
        "spec_immutability_verified": True,
    }


def _route_readback(
    route_id: str,
    raw_request: Mapping[str, Any],
    *,
    root: Path,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    # Route modules are deliberately lazy-loaded. R3 verifier import must not
    # inherit every direct producer's dependency graph.
    if route_id == STRUCTURED_BINARY_CODEC_ROUTE_ID:
        from canonical.runtime import r2_structured_binary_direct_adequacy_v1 as codec
        pf = codec.preflight(raw_request, repo_root=root)
        evidence = codec._independent_verify(pf, repo_root=root)
        independent = (
            isinstance(evidence, Mapping)
            and evidence.get("verified") is True
            and evidence.get("producer_independent") is True
            and (
                evidence.get("dependency_independent") is True
                or (
                    evidence.get("implementation_independent") is True
                    and evidence.get("supplier_class_independent") is True
                )
            )
        )
        if not independent:
            raise DirectAdequacyVerificationError("CODEC_READBACK_NOT_INDEPENDENT")
        return pf, evidence

    if route_id == STRUCTURED_TABLE_ROUTE_ID:
        from canonical.runtime import r2_structured_table_direct_adequacy_v1 as table
        pf = table.preflight(raw_request, repo_root=root)
        evidence = table._independent_verify(pf, repo_root=root)
        if not (
            isinstance(evidence, Mapping)
            and evidence.get("verified") is True
            and evidence.get("producer_independent_verifier") is True
        ):
            raise DirectAdequacyVerificationError("TABLE_READBACK_NOT_VERIFIED")
        return pf, evidence

    if route_id == DOCX_ROUTE_ID:
        from canonical.runtime import r2_docx_direct_adequacy_v1 as docx
        pf = docx.preflight(raw_request, repo_root=root)
        evidence = docx.docx_verify_ooxml_intent.run({"path": pf["output_path"]}, root)
        if not (
            isinstance(evidence, Mapping)
            and evidence.get("verified") is True
            and evidence.get("producer_independent_verifier") is True
            and evidence.get("intent_source_goal") == pf["creation_clause"]
            and evidence.get("intent_derived_expected") == pf["expected"]
            and evidence.get("expected") == pf["expected"]
            and evidence.get("title_ok") is True
            and evidence.get("paragraphs_ok") is True
            and evidence.get("table_ok") is True
        ):
            raise DirectAdequacyVerificationError("DOCX_READBACK_NOT_VERIFIED")
        return pf, evidence

    if route_id == DOCX_JSON_ROUTE_ID:
        from canonical.runtime import r2_docx_json_direct_adequacy_v1 as docx_json
        pf = docx_json.preflight(raw_request, repo_root=root)
        evidence = docx_json._independent_verify(pf, repo_root=root)
        expected = evidence.get("intent_derived_expected") if isinstance(evidence, Mapping) else None
        if not (
            isinstance(evidence, Mapping)
            and evidence.get("verified") is True
            and evidence.get("producer_independent_verifier") is True
            and evidence.get("source_record_verified") is True
            and evidence.get("path") == pf["output_path"]
            and evidence.get("source_json_path") == pf["json_path"]
            and evidence.get("intent_source_goal") == pf["goal"]
            and isinstance(expected, Mapping)
            and sha256(docx_json._canon(expected).encode("utf-8")).hexdigest()
            == pf["expected_semantics_sha256"]
        ):
            raise DirectAdequacyVerificationError("DOCX_JSON_READBACK_NOT_VERIFIED")
        return pf, evidence

    if route_id == TYPED_DECISION_ROUTE_ID:
        from canonical.runtime import r2_typed_decision_direct_adequacy_v1 as typed_decision
        pf = typed_decision.preflight(raw_request, repo_root=root)
        input_path = _safe(root, str(pf["input_path"]))
        evidence = typed_decision.verifier.run(
            {"input_path": pf["input_path"], "result_path": pf["output_path"]},
            root,
        )
        if not (
            isinstance(evidence, Mapping)
            and evidence.get("verified") is True
            and evidence.get("producer_independent") is True
            and evidence.get("model_dependency_count") == 0
            and typed_decision._sha_file(input_path) == pf["input_sha256"]
        ):
            raise DirectAdequacyVerificationError("TYPED_DECISION_READBACK_NOT_VERIFIED")
        return pf, evidence

    if route_id == VISUAL_CODE_ROUTE_ID:
        from canonical.runtime import r2_visual_code_direct_adequacy_v1 as visual
        pf = visual.preflight(raw_request, repo_root=root)
        evidence = visual._independent_decode(pf, repo_root=root)
        if not (
            isinstance(evidence, Mapping)
            and evidence.get("verified") is True
            and evidence.get("producer_independent") is True
            and evidence.get("supplier_packages_disjoint") is not False
            and evidence.get("decoded_payload") == pf["payload"]
        ):
            raise DirectAdequacyVerificationError("VISUAL_CODE_READBACK_NOT_VERIFIED")
        return pf, evidence

    if route_id == MARKDOWN_PDF_ROUTE_ID:
        from canonical.runtime import r2_markdown_pdf_direct_adequacy_v1 as markdown_pdf
        pf = markdown_pdf.preflight(raw_request, repo_root=root)
        evidence = markdown_pdf._independent_verify(pf, repo_root=root)
        if not (
            isinstance(evidence, Mapping)
            and evidence.get("verified") is True
            and evidence.get("producer_independent_verifier") is True
            and evidence.get("verifier_capability_id") == markdown_pdf.VERIFIER
        ):
            raise DirectAdequacyVerificationError("MARKDOWN_PDF_READBACK_NOT_VERIFIED")
        return pf, evidence

    if route_id == TYPED_JSON_TRANSFORM_ROUTE_ID:
        from canonical.runtime import r2_typed_json_transform_direct_adequacy_v1 as typed_transform
        pf = typed_transform.preflight(raw_request, repo_root=root)
        evidence = _typed_transform_verify(typed_transform, pf, root)
        return pf, evidence

    raise DirectAdequacyVerificationError("DIRECT_ROUTE_NOT_ADMITTED:" + route_id)

def _binding_check(proof: Mapping[str, Any], pf: Mapping[str, Any], root: Path) -> None:
    bindings = proof.get("route_bindings")
    if not isinstance(bindings, Mapping):
        raise DirectAdequacyVerificationError("DIRECT_ROUTE_BINDINGS_MISSING")
    for key, retained in bindings.items():
        if key == "output_sha256":
            output_path = str(bindings.get("output_path") or pf.get("output_path") or "")
            current = sha256(_safe(root, output_path).read_bytes()).hexdigest()
            if current != retained:
                raise DirectAdequacyVerificationError("DIRECT_OUTPUT_SHA_DRIFT")
            continue
        if key in pf and pf.get(key) != retained:
            raise DirectAdequacyVerificationError("DIRECT_PREFLIGHT_BINDING_DRIFT:" + str(key))


def verify_material(
    *,
    problem: Mapping[str, Any],
    episode: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule_head_hash: str,
    value_capsule_head_hash: str,
    repo_root,
) -> dict[str, Any]:
    try:
        if problem.get("verification_kind") != VERIFICATION_KIND:
            raise DirectAdequacyVerificationError("VERIFICATION_KIND_INVALID")
        root = Path(repo_root).resolve(strict=True)
        raw_request = problem.get("raw_request")
        proof = problem.get("direct_proof")
        if not isinstance(raw_request, Mapping) or not isinstance(proof, Mapping):
            raise DirectAdequacyVerificationError("DIRECT_PROOF_MATERIAL_MISSING")

        goal = str(raw_request.get("goal") or "")
        route_id = str(problem.get("route_id") or "")
        capability_id = str(problem.get("capability_id") or "")
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if not goal or goal_sha != problem.get("goal_sha256"):
            raise DirectAdequacyVerificationError("DIRECT_GOAL_HASH_MISMATCH")
        if proof.get("goal_sha256") != goal_sha or proof.get("route_id") != route_id:
            raise DirectAdequacyVerificationError("DIRECT_PROOF_ROUTE_OR_GOAL_MISMATCH")
        if proof.get("capability_id") != capability_id:
            raise DirectAdequacyVerificationError("DIRECT_PROOF_CAPABILITY_MISMATCH")

        pf, evidence = _route_readback(route_id, raw_request, root=root)
        if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
            raise DirectAdequacyVerificationError("ROUTE_PREFLIGHT_NOT_ADMISSIBLE")
        if pf.get("goal_sha256") != goal_sha:
            raise DirectAdequacyVerificationError("ROUTE_GOAL_HASH_MISMATCH")
        if pf.get("capability_id") not in {None, capability_id}:
            raise DirectAdequacyVerificationError("ROUTE_CAPABILITY_MISMATCH")

        _binding_check(proof, pf, root)
        retained_evidence_sha = str(
            proof.get("independent_acceptance_sha256") or ""
        )
        if len(retained_evidence_sha) != 64:
            raise DirectAdequacyVerificationError(
                "RETAINED_INDEPENDENT_ACCEPTANCE_SHA_MISSING"
            )
        if _sha(dict(evidence)) != retained_evidence_sha:
            raise DirectAdequacyVerificationError(
                "INDEPENDENT_ACCEPTANCE_EVIDENCE_DRIFT"
            )

        accepted_ids = _accepted_ids(pf)
        if accepted_ids != list(problem.get("accepted_raw_obligation_ids") or []):
            raise DirectAdequacyVerificationError("RAW_ACCEPTANCE_SET_MISMATCH")
        if int(problem.get("raw_acceptance_obligation_count") or 0) != len(accepted_ids):
            raise DirectAdequacyVerificationError("RAW_ACCEPTANCE_COUNT_MISMATCH")

        accepted_effect = "r2.direct_adequacy.accepted.sha256:" + goal_sha
        expected_steps = [{
            "index": 0,
            "op": capability_id,
            "inputs": [],
            "outputs": [accepted_effect],
        }]
        if list(episode.get("steps") or []) != expected_steps:
            raise DirectAdequacyVerificationError("EPISODE_STEPS_MISMATCH")
        if list(episode.get("preconditions") or []) != []:
            raise DirectAdequacyVerificationError("EPISODE_PRECONDITIONS_MISMATCH")
        if list(episode.get("postconditions") or []) != [accepted_effect]:
            raise DirectAdequacyVerificationError("EPISODE_POSTCONDITIONS_MISMATCH")
        if list(episode.get("invalidators") or []) != []:
            raise DirectAdequacyVerificationError("EPISODE_INVALIDATORS_NOT_EMPTY")
        expected_program = program_digest(
            steps=expected_steps,
            preconditions=[],
            postconditions=[accepted_effect],
            invalidators=[],
        )
        if episode.get("program_sha256") != expected_program:
            raise DirectAdequacyVerificationError("EPISODE_PROGRAM_DIGEST_MISMATCH")

        proof_sha = _sha(dict(proof))
        expected_trace = [{
            "cycle": 0,
            "capability_id": capability_id,
            "route_id": route_id,
            "selected_policy_id": problem.get("selected_policy_id"),
            "goal_sha256": goal_sha,
            "accepted_effect": accepted_effect,
            "direct_proof_sha256": proof_sha,
        }]
        if _canon(list(trace)) != _canon(expected_trace):
            raise DirectAdequacyVerificationError("EPISODE_TRACE_MISMATCH")
        expected_fact = _sha({
            "schema": "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_FACT_LINEAGE_V1",
            "route_id": route_id,
            "goal_sha256": goal_sha,
            "accepted_effect": accepted_effect,
            "trace": expected_trace,
        })
        expected_value = _sha({
            "schema": "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_VALUE_LINEAGE_V1",
            "direct_proof_sha256": proof_sha,
            "accepted_raw_obligation_ids": accepted_ids,
            "raw_acceptance_obligation_count": len(accepted_ids),
        })
        if fact_capsule_head_hash != expected_fact:
            raise DirectAdequacyVerificationError("FACT_LINEAGE_HEAD_MISMATCH")
        if value_capsule_head_hash != expected_value:
            raise DirectAdequacyVerificationError("VALUE_LINEAGE_HEAD_MISMATCH")

        return {
            "schema": SCHEMA,
            "status": "PASS__R2_DIRECT_ADEQUACY_SUCCESS_REVERIFIED_READ_ONLY",
            "pass": True,
            "verification_basis": VERIFICATION_BASIS,
            "route_id": route_id,
            "capability_id": capability_id,
            "semantic_acceptance_reverified": True,
            "artifact_readback_reverified": True,
            "trace_reverified": True,
            "execution_replayed": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__R2_DIRECT_ADEQUACY_SUCCESS_NOT_REVERIFIED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "execution_replayed": False,
            "terminal_authority": False,
        }
