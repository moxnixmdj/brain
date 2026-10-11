from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime.aa_briefcase_authority_convention_sweep_v1 import verify_review
from canonical.runtime.requirement_graph_kernel import compile_requirement_contract

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_PRE_GENERATION_CONTRACT_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_PRE_GENERATION_CONTRACT_MANIFEST_V1"


class PreGenerationError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strings(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise PreGenerationError(label + "_INVALID")
    if not allow_empty and not value:
        raise PreGenerationError(label + "_EMPTY")
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise PreGenerationError(label + "_MEMBER_INVALID")
    out = [x.strip() for x in value]
    if len(out) != len(set(out)):
        raise PreGenerationError(label + "_DUPLICATE")
    return out


def _mapping_rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise PreGenerationError(label + "_INVALID")
    if any(not isinstance(x, Mapping) for x in value):
        raise PreGenerationError(label + "_ROW_INVALID")
    return value


def _id_map(rows: list[Mapping[str, Any]], key: str, label: str) -> dict[str, Mapping[str, Any]]:
    out = {}
    for row in rows:
        rid = row.get(key)
        if not isinstance(rid, str) or not rid.strip():
            raise PreGenerationError(label + "_ID_INVALID")
        rid = rid.strip()
        if rid in out:
            raise PreGenerationError(label + "_ID_DUPLICATE:" + rid)
        out[rid] = row
    return out


def verify_pre_generation_contract(
    ingress: Mapping[str, Any],
    parse_manifest: Mapping[str, Any],
    sweep: Mapping[str, Any],
    review: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(ingress, Mapping) or ingress.get("schema") != "PROJECT_BRAIN_AA_BRIEFCASE_LOSSLESS_TASK_INGRESS_V1":
        raise PreGenerationError("INGRESS_INVALID")
    if ingress.get("all_nonempty_context_and_task_lines_preserved_exactly") is not True:
        raise PreGenerationError("TASK_CONTEXT_NOT_LOSSLESS")
    if ingress.get("all_declared_source_files_preserved_by_path_hash_and_size") is not True:
        raise PreGenerationError("SOURCE_INGRESS_NOT_LOSSLESS")

    if not isinstance(parse_manifest, Mapping) or parse_manifest.get("status") != "PASS__ALL_DECLARED_SOURCES_PARSED":
        raise PreGenerationError("PARSE_MANIFEST_INVALID")
    if parse_manifest.get("ingress_sha256") != ingress.get("ingress_sha256"):
        raise PreGenerationError("PARSE_INGRESS_BINDING_MISMATCH")
    if int(parse_manifest.get("unsupported_or_unparsed_source_count") or 0) != 0:
        raise PreGenerationError("UNPARSED_SOURCE_PRESENT")

    review_verdict = verify_review(sweep, review)
    if review_verdict.get("pass") is not True:
        raise PreGenerationError("AUTHORITY_CONVENTION_REVIEW_FAILED")

    if not isinstance(contract, Mapping) or contract.get("schema") != MANIFEST_SCHEMA:
        raise PreGenerationError("CONTRACT_SCHEMA_INVALID")
    if contract.get("ingress_sha256") != ingress.get("ingress_sha256"):
        raise PreGenerationError("CONTRACT_INGRESS_BINDING_MISMATCH")
    if contract.get("parse_manifest_sha256") != parse_manifest.get("parse_manifest_sha256"):
        raise PreGenerationError("CONTRACT_PARSE_BINDING_MISMATCH")
    if contract.get("review_verdict_sha256") != review_verdict.get("review_verdict_sha256"):
        raise PreGenerationError("CONTRACT_REVIEW_BINDING_MISMATCH")

    obligation_ids = _strings(
        [x.get("obligation_id") for x in ingress.get("obligations") or []],
        "INGRESS_OBLIGATION_IDS",
    )
    obligation_set = set(obligation_ids)
    deliverables = _strings(list(ingress.get("deliverables") or []), "INGRESS_DELIVERABLES")
    deliverable_set = set(deliverables)

    source_rows = _mapping_rows(list(ingress.get("source_files") or []), "INGRESS_SOURCE_FILES")
    source_by_path = _id_map(source_rows, "path", "SOURCE")
    source_set = set(source_by_path)

    receipts = _mapping_rows(list(parse_manifest.get("receipts") or []), "PARSE_RECEIPTS")
    receipt_by_path = _id_map(receipts, "source_path", "PARSE_RECEIPT")
    if set(receipt_by_path) != source_set:
        raise PreGenerationError("PARSE_RECEIPT_SOURCE_SET_MISMATCH")
    for path, src in source_by_path.items():
        rec = receipt_by_path[path]
        if rec.get("source_sha256") != src.get("sha256"):
            raise PreGenerationError("PARSE_RECEIPT_SOURCE_HASH_MISMATCH:" + path)

    authority_rows = _mapping_rows(contract.get("authority_sources"), "AUTHORITY_SOURCES")
    authority_by_path = _id_map(authority_rows, "source_path", "AUTHORITY_SOURCE")
    if set(authority_by_path) != source_set:
        raise PreGenerationError("AUTHORITY_SOURCE_SET_MISMATCH")
    for path, row in authority_by_path.items():
        rank = row.get("authority_rank")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 0:
            raise PreGenerationError("AUTHORITY_RANK_INVALID:" + path)
        rec = receipt_by_path[path]
        if row.get("content_sha256") != rec.get("source_sha256"):
            raise PreGenerationError("AUTHORITY_CONTENT_HASH_MISMATCH:" + path)
        if row.get("parsed_representation_sha256") != rec.get("parsed_representation_sha256"):
            raise PreGenerationError("AUTHORITY_PARSE_RECEIPT_MISMATCH:" + path)
        supersedes = _strings(list(row.get("supersedes") or []), "AUTHORITY_SUPERSEDES:" + path, allow_empty=True)
        if any(x not in source_set for x in supersedes):
            raise PreGenerationError("AUTHORITY_SUPERSEDES_UNKNOWN:" + path)

    output_rows = _mapping_rows(contract.get("outputs"), "OUTPUTS")
    output_by_id = _id_map(output_rows, "output_id", "OUTPUT")
    output_ids = set(output_by_id)
    if not output_ids:
        raise PreGenerationError("OUTPUTS_EMPTY")
    output_deliverables = set()
    for oid, row in output_by_id.items():
        path = row.get("deliverable_path")
        if path not in deliverable_set:
            raise PreGenerationError("OUTPUT_DELIVERABLE_UNKNOWN:" + oid)
        output_deliverables.add(path)
    if output_deliverables != deliverable_set:
        raise PreGenerationError("DELIVERABLE_OUTPUT_COVERAGE_MISMATCH")

    required_dim_ids = _strings(contract.get("required_dimension_ids"), "REQUIRED_DIMENSION_IDS")
    dimension_rows = _mapping_rows(contract.get("dimensions"), "DIMENSIONS")
    dimension_by_id = _id_map(dimension_rows, "dimension_id", "DIMENSION")
    if set(dimension_by_id) != set(required_dim_ids):
        raise PreGenerationError("DIMENSION_SET_MISMATCH")

    required_conv_ids = _strings(contract.get("required_convention_ids"), "REQUIRED_CONVENTION_IDS", allow_empty=True)
    convention_rows = _mapping_rows(contract.get("conventions"), "CONVENTIONS")
    convention_by_id = _id_map(convention_rows, "convention_id", "CONVENTION")
    if set(convention_by_id) != set(required_conv_ids):
        raise PreGenerationError("CONVENTION_SET_MISMATCH")

    scenario_rows = _mapping_rows(contract.get("scenario_axes"), "SCENARIO_AXES")
    scenario_by_id = _id_map(scenario_rows, "axis_id", "SCENARIO_AXIS")
    reconciliation_rows = _mapping_rows(contract.get("reconciliations"), "RECONCILIATIONS")
    reconciliation_by_id = _id_map(reconciliation_rows, "reconciliation_id", "RECONCILIATION")

    requirement_rows = _mapping_rows(contract.get("requirements"), "REQUIREMENTS")
    requirement_by_id = _id_map(requirement_rows, "id", "REQUIREMENT")
    if not requirement_by_id:
        raise PreGenerationError("REQUIREMENTS_EMPTY")
    requirement_ids = set(requirement_by_id)

    covered_obligations = set()
    semantic_source_bindings = set()
    normalized_requirements = []

    for rid, row in requirement_by_id.items():
        task_ids = _strings(list(row.get("task_obligation_ids") or []), "REQ_TASK_OBLIGATIONS:" + rid, allow_empty=True)
        srcs = _strings(list(row.get("source_paths") or []), "REQ_SOURCE_PATHS:" + rid, allow_empty=True)
        if not task_ids and not srcs:
            raise PreGenerationError("REQUIREMENT_HAS_NO_EVIDENCE:" + rid)
        unknown_task = set(task_ids) - obligation_set
        if unknown_task:
            raise PreGenerationError("REQUIREMENT_UNKNOWN_TASK_OBLIGATION:" + rid)
        unknown_sources = set(srcs) - source_set
        if unknown_sources:
            raise PreGenerationError("REQUIREMENT_UNKNOWN_SOURCE:" + rid)
        covered_obligations.update(task_ids)
        semantic_source_bindings.update(srcs)

        dims = _strings(row.get("dimension_ids"), "REQ_DIMENSIONS:" + rid)
        if any(x not in dimension_by_id for x in dims):
            raise PreGenerationError("REQUIREMENT_UNKNOWN_DIMENSION:" + rid)

        convs = _strings(list(row.get("convention_ids") or []), "REQ_CONVENTIONS:" + rid, allow_empty=True)
        if any(x not in convention_by_id for x in convs):
            raise PreGenerationError("REQUIREMENT_UNKNOWN_CONVENTION:" + rid)

        outs = _strings(row.get("output_ids"), "REQ_OUTPUTS:" + rid)
        if any(x not in output_ids for x in outs):
            raise PreGenerationError("REQUIREMENT_UNKNOWN_OUTPUT:" + rid)

        kind = row.get("kind")
        if kind not in {"STANDARD", "SCENARIO", "RECONCILIATION", "CONVENTION", "DATA"}:
            raise PreGenerationError("REQUIREMENT_KIND_INVALID:" + rid)

        axis_ids = _strings(list(row.get("scenario_axis_ids") or []), "REQ_SCENARIO_AXES:" + rid, allow_empty=True)
        recon_ids = _strings(list(row.get("reconciliation_ids") or []), "REQ_RECONCILIATIONS:" + rid, allow_empty=True)
        if any(x not in scenario_by_id for x in axis_ids):
            raise PreGenerationError("REQUIREMENT_UNKNOWN_SCENARIO_AXIS:" + rid)
        if any(x not in reconciliation_by_id for x in recon_ids):
            raise PreGenerationError("REQUIREMENT_UNKNOWN_RECONCILIATION:" + rid)
        if kind == "SCENARIO" and not axis_ids:
            raise PreGenerationError("SCENARIO_REQUIREMENT_WITHOUT_AXIS:" + rid)
        if kind == "RECONCILIATION" and not recon_ids:
            raise PreGenerationError("RECONCILIATION_REQUIREMENT_WITHOUT_RECONCILIATION:" + rid)

        normalized_requirements.append({
            "id": rid,
            "critical": bool(row.get("critical", True)),
            "dependencies": list(row.get("dependencies") or []),
            "children": list(row.get("children") or []),
            "open_questions": list(row.get("open_questions") or []),
            "clauses": list(row.get("clauses") or []),
            "scenarios": list(row.get("scenarios") or []),
        })

    if covered_obligations != obligation_set:
        raise PreGenerationError("TASK_OBLIGATION_COVERAGE_MISMATCH")

    for did, row in dimension_by_id.items():
        reqs = _strings(row.get("requirement_ids"), "DIM_REQUIREMENTS:" + did)
        if any(x not in requirement_ids for x in reqs):
            raise PreGenerationError("DIMENSION_UNKNOWN_REQUIREMENT:" + did)
        srcs = _strings(list(row.get("source_paths") or []), "DIM_SOURCES:" + did, allow_empty=True)
        tasks = _strings(list(row.get("task_obligation_ids") or []), "DIM_TASK_OBLIGATIONS:" + did, allow_empty=True)
        if not srcs and not tasks:
            raise PreGenerationError("DIMENSION_HAS_NO_EVIDENCE:" + did)
        if any(x not in source_set for x in srcs):
            raise PreGenerationError("DIMENSION_UNKNOWN_SOURCE:" + did)
        if any(x not in obligation_set for x in tasks):
            raise PreGenerationError("DIMENSION_UNKNOWN_TASK_OBLIGATION:" + did)
        if not isinstance(row.get("coverage_receipt"), str) or not row.get("coverage_receipt").strip():
            raise PreGenerationError("DIMENSION_COVERAGE_RECEIPT_MISSING:" + did)
        semantic_source_bindings.update(srcs)

    for cid, row in convention_by_id.items():
        candidates = _mapping_rows(row.get("candidates"), "CONVENTION_CANDIDATES:" + cid)
        if not candidates:
            raise PreGenerationError("CONVENTION_CANDIDATES_EMPTY:" + cid)
        effective = row.get("effective_source_path")
        if effective not in source_set:
            raise PreGenerationError("CONVENTION_EFFECTIVE_SOURCE_INVALID:" + cid)
        scored = []
        for cand in candidates:
            path = cand.get("source_path")
            if path not in source_set:
                raise PreGenerationError("CONVENTION_CANDIDATE_SOURCE_UNKNOWN:" + cid)
            rank = cand.get("authority_rank")
            if rank != authority_by_path[path].get("authority_rank"):
                raise PreGenerationError("CONVENTION_AUTHORITY_RANK_MISMATCH:" + cid)
            value_sha = cand.get("value_sha256")
            if not isinstance(value_sha, str) or len(value_sha) != 64:
                raise PreGenerationError("CONVENTION_VALUE_SHA_INVALID:" + cid)
            scored.append((rank, path, value_sha))
            semantic_source_bindings.add(path)
        best_rank = min(x[0] for x in scored)
        best = [x for x in scored if x[0] == best_rank]
        if len({x[2] for x in best}) > 1:
            raise PreGenerationError("CONVENTION_AUTHORITY_CONFLICT:" + cid)
        if effective not in {x[1] for x in best}:
            raise PreGenerationError("CONVENTION_EFFECTIVE_SOURCE_NOT_HIGHEST_AUTHORITY:" + cid)
        if not isinstance(row.get("binding_receipt"), str) or not row.get("binding_receipt").strip():
            raise PreGenerationError("CONVENTION_BINDING_RECEIPT_MISSING:" + cid)

    for aid, row in scenario_by_id.items():
        states = _strings(row.get("states"), "SCENARIO_STATES:" + aid)
        if len(states) < 2:
            raise PreGenerationError("SCENARIO_AXIS_REQUIRES_AT_LEAST_TWO_STATES:" + aid)
        reqs = _strings(row.get("requirement_ids"), "SCENARIO_REQUIREMENTS:" + aid)
        outs = _strings(row.get("output_ids"), "SCENARIO_OUTPUTS:" + aid)
        srcs = _strings(list(row.get("source_paths") or []), "SCENARIO_SOURCES:" + aid, allow_empty=True)
        tasks = _strings(list(row.get("task_obligation_ids") or []), "SCENARIO_TASK_OBLIGATIONS:" + aid, allow_empty=True)
        if any(x not in requirement_ids for x in reqs) or any(x not in output_ids for x in outs):
            raise PreGenerationError("SCENARIO_BINDING_UNKNOWN_ID:" + aid)
        if any(x not in source_set for x in srcs) or any(x not in obligation_set for x in tasks):
            raise PreGenerationError("SCENARIO_EVIDENCE_UNKNOWN:" + aid)
        if not srcs and not tasks:
            raise PreGenerationError("SCENARIO_EVIDENCE_MISSING:" + aid)
        semantic_source_bindings.update(srcs)

    for xid, row in reconciliation_by_id.items():
        methods = _strings(row.get("method_ids"), "RECONCILIATION_METHODS:" + xid)
        if len(methods) < 2:
            raise PreGenerationError("RECONCILIATION_REQUIRES_AT_LEAST_TWO_METHODS:" + xid)
        reqs = _strings(row.get("requirement_ids"), "RECONCILIATION_REQUIREMENTS:" + xid)
        if any(x not in requirement_ids for x in reqs):
            raise PreGenerationError("RECONCILIATION_UNKNOWN_REQUIREMENT:" + xid)
        oid = row.get("output_id")
        if oid not in output_ids:
            raise PreGenerationError("RECONCILIATION_OUTPUT_UNKNOWN:" + xid)
        srcs = _strings(list(row.get("source_paths") or []), "RECONCILIATION_SOURCES:" + xid, allow_empty=True)
        tasks = _strings(list(row.get("task_obligation_ids") or []), "RECONCILIATION_TASK_OBLIGATIONS:" + xid, allow_empty=True)
        if any(x not in source_set for x in srcs) or any(x not in obligation_set for x in tasks):
            raise PreGenerationError("RECONCILIATION_EVIDENCE_UNKNOWN:" + xid)
        if not srcs and not tasks:
            raise PreGenerationError("RECONCILIATION_EVIDENCE_MISSING:" + xid)
        semantic_source_bindings.update(srcs)

    if semantic_source_bindings != source_set:
        missing = sorted(source_set - semantic_source_bindings)
        raise PreGenerationError("DECLARED_SOURCE_NOT_SEMANTICALLY_BOUND:" + ",".join(missing))

    for oid, row in output_by_id.items():
        reqs = _strings(row.get("requirement_ids"), "OUTPUT_REQUIREMENTS:" + oid)
        if set(reqs) - requirement_ids:
            raise PreGenerationError("OUTPUT_UNKNOWN_REQUIREMENT:" + oid)
        expected = {rid for rid, req in requirement_by_id.items() if oid in (req.get("output_ids") or [])}
        if set(reqs) != expected:
            raise PreGenerationError("OUTPUT_REQUIREMENT_INVERSE_MISMATCH:" + oid)

    graph = compile_requirement_contract(normalized_requirements, expected_required_ids=sorted(requirement_ids))
    if graph.get("pass") is not True:
        raise PreGenerationError("REQUIREMENT_GRAPH_FAILED")

    valid_targets = {
        "AUTHORITY": source_set,
        "CONVENTION": set(convention_by_id),
        "DIMENSION": set(dimension_by_id),
        "SCENARIO_STRUCTURE": set(scenario_by_id),
        "RECONCILIATION_STRUCTURE": set(reconciliation_by_id),
        "DATA_INPUT": requirement_ids | set(dimension_by_id),
    }
    for row in review.get("rows") or []:
        action = row.get("action")
        if action == "CONTEXT_ONLY":
            continue
        targets = set(row.get("target_ids") or [])
        allowed = valid_targets.get(action)
        if allowed is None or not targets or not targets <= allowed:
            raise PreGenerationError("REVIEW_TARGET_NOT_BOUND_TO_CONTRACT:" + str(row.get("candidate_id") or ""))

    material = {
        "schema": SCHEMA,
        "status": "PASS__PRE_GENERATION_STRUCTURAL_CONTRACT_COMPLETE",
        "ingress_sha256": ingress.get("ingress_sha256"),
        "parse_manifest_sha256": parse_manifest.get("parse_manifest_sha256"),
        "review_verdict_sha256": review_verdict.get("review_verdict_sha256"),
        "requirement_count": len(requirement_by_id),
        "task_obligation_count": len(obligation_set),
        "source_count": len(source_set),
        "dimension_count": len(dimension_by_id),
        "convention_count": len(convention_by_id),
        "scenario_axis_count": len(scenario_by_id),
        "reconciliation_count": len(reconciliation_by_id),
        "output_count": len(output_by_id),
        "all_explicit_task_obligations_reach_requirement_graph": True,
        "all_declared_sources_parsed_and_structurally_bound": True,
        "authority_precedence_conflicts_fail_closed": True,
        "scenario_and_reconciliation_structure_fail_closed": True,
        "requirement_graph_pass": True,
        "pre_generation_structural_authority": True,
        "semantic_completeness_self_certified": False,
        "negative_relevance_self_certified": False,
        "hidden_rubric_information_used": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return {**material, "pre_generation_contract_sha256": _sha(_canon(material))}
