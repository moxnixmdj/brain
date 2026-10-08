"""Authenticate real-context membership in the bounded P3 binary top-law cell.

This gate closes only the membership boundary. It does not mint policy adequacy,
D_B admission, U subtraction, or terminal authority.

A pass requires:
1. an independently verified, exact-byte authority-scope receipt proving the
   supplied source bundle is the complete load-bearing authority for this context;
2. lossless source-contract coverage and two-extractor semantic consensus using
   the already verified source_contract_compiler;
3. every operative semantic requirement bound to the hash of an exact structured
   P3 contract projection; and
4. the existing bounded binary grounded-expression compiler to pass on the same
   structured payload.

The source-to-structured semantic binding is represented by an exact fingerprint:
    P3_BINDING:<FIELD>:sha256:<hex>
and must be identical across independent extractors.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.source_contract_compiler import (
    atomize_source,
    validate_contract_coverage,
    validate_semantic_consensus,
)
from canonical.runtime.p3_binary_decision_grounded_expression_v1 import (
    evaluate as evaluate_expression,
)

SCHEMA = "PROJECT_BRAIN_P3_BOUND_BINARY_REAL_CONTEXT_MEMBERSHIP_V1"
AUTH_SCHEMA = "PROJECT_BRAIN_P3_AUTHORITY_SCOPE_COMPLETENESS_RECEIPT_V1"
BEHAVIOR_ID = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
ALLOWED_FIELDS = frozenset({"OBJECTIVE", "CLAIMS", "EVIDENCE", "AUDIENCE_PROFILE"})


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "selected_class_membership_authenticated": False,
        "real_context_semantic_scope_complete": False,
        "source_authorization_verified": False,
        "top_law_eligible": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _canon_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha_obj(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canon_json(value)).hexdigest()


def _sha_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _projections(objective: str, public: Mapping[str, Any]) -> dict[str, Any]:
    if set(public) != {"schema", "task"}:
        raise ValueError("V2_INPUT_TOP_LEVEL_SHAPE_NOT_EXACT")
    task = public.get("task")
    if not isinstance(task, Mapping):
        raise ValueError("TASK_REQUIRED")
    if set(task) != {"claims", "evidence", "audience_profile"}:
        raise ValueError("TASK_SHAPE_NOT_EXACT_BINARY_CELL")
    return {
        "OBJECTIVE": objective,
        "CLAIMS": task["claims"],
        "EVIDENCE": task["evidence"],
        "AUDIENCE_PROFILE": task["audience_profile"],
    }


def _authority_ok(
    ref: Mapping[str, Any],
    *,
    repo_root: str | Path,
    context_id: str,
    source_name: str,
    source_text: str,
    structured_contract_sha256: str,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    try:
        bound = resolve_receipt_bytes(ref, repo_root=repo_root)
        doc = bound["document"]
    except Exception as exc:
        return False, None, "AUTHORITY_SCOPE_RECEIPT_BINDING_INVALID:" + type(exc).__name__
    required = {
        "schema": AUTH_SCHEMA,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "context_id": context_id,
        "behavior_id": BEHAVIOR_ID,
        "source_name": source_name,
        "source_sha256": _sha_text(source_text),
        "structured_contract_sha256": structured_contract_sha256,
        "authoritative_source_set_complete": True,
        "no_external_load_bearing_authority": True,
    }
    for key, expected in required.items():
        if doc.get(key) != expected:
            return False, doc, "AUTHORITY_SCOPE_RECEIPT_INVALID:" + key
    return True, doc, None


def evaluate(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    context_id = payload.get("context_id")
    objective = payload.get("objective")
    public = payload.get("v2_input")
    source_name = payload.get("source_name")
    source_text = payload.get("source_text")
    if not isinstance(context_id, str) or not context_id.strip():
        return _fail("CONTEXT_ID_REQUIRED")
    if not isinstance(objective, str) or not objective.strip():
        return _fail("OBJECTIVE_REQUIRED")
    if not isinstance(public, Mapping):
        return _fail("V2_INPUT_REQUIRED")
    if not isinstance(source_name, str) or not source_name.strip():
        return _fail("SOURCE_NAME_REQUIRED")
    if not isinstance(source_text, str) or not source_text:
        return _fail("SOURCE_TEXT_REQUIRED")

    try:
        projections = _projections(objective, public)
        projection_hashes = {k: _sha_obj(v) for k, v in projections.items()}
        structured_contract_sha256 = _sha_obj(
            {"behavior_id": BEHAVIOR_ID, "objective": objective, "v2_input": public}
        )
    except Exception as exc:
        return _fail("STRUCTURED_CONTRACT_INVALID", detail_text=str(exc)[:200])

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    authority_ref = payload.get("authority_scope_ref")
    if not isinstance(authority_ref, Mapping):
        return _fail("AUTHORITY_SCOPE_REF_REQUIRED")
    ok, authority_doc, reason = _authority_ok(
        authority_ref,
        repo_root=root,
        context_id=context_id,
        source_name=source_name,
        source_text=source_text,
        structured_contract_sha256=structured_contract_sha256,
    )
    if not ok:
        return _fail(str(reason))

    try:
        atoms = atomize_source(source_text, source_name)
    except Exception as exc:
        return _fail("SOURCE_ATOMIZATION_FAILED", exception_type=type(exc).__name__)

    dispositions = payload.get("dispositions")
    requirements = payload.get("requirements")
    extractors = payload.get("extractor_units")
    if not isinstance(dispositions, Sequence) or isinstance(dispositions, (str, bytes)):
        return _fail("DISPOSITIONS_REQUIRED")
    if not isinstance(requirements, Sequence) or isinstance(requirements, (str, bytes)):
        return _fail("REQUIREMENTS_REQUIRED")
    if not isinstance(extractors, Mapping):
        return _fail("EXTRACTOR_UNITS_REQUIRED")

    errors = validate_contract_coverage(
        source_text=source_text,
        atoms=atoms,
        dispositions=dispositions,
        requirements=requirements,
    )
    errors += validate_semantic_consensus(
        source_text=source_text,
        atoms=atoms,
        extractor_units=extractors,
        requirements=requirements,
    )
    if errors:
        return _fail("SOURCE_CONTRACT_NOT_SCOPE_COMPLETE", errors=sorted(set(errors)))

    # After semantic consensus passes, any extractor may be used as the exact
    # consensus signature because boundaries, kind, and fingerprint are equal.
    extractor_ids = sorted(str(x) for x in extractors)
    if len(extractor_ids) < 2:
        return _fail("INDEPENDENT_SEMANTIC_EXTRACTORS_LT_2")
    reference_units = extractors[extractor_ids[0]]
    unit_fingerprint: dict[str, str] = {}
    unit_seen_count: dict[str, int] = {}
    from canonical.runtime.source_contract_compiler import semantic_unit_id

    for unit in reference_units:
        if not isinstance(unit, Mapping):
            return _fail("REFERENCE_SEMANTIC_UNIT_INVALID")
        aid = unit.get("atom_id")
        start = unit.get("start")
        end = unit.get("end")
        if not isinstance(aid, str) or type(start) is not int or type(end) is not int:
            return _fail("REFERENCE_SEMANTIC_UNIT_ID_INVALID")
        sid = semantic_unit_id(aid, start, end)
        fp = unit.get("semantic_fingerprint")
        if not isinstance(fp, str) or not fp:
            return _fail("REFERENCE_SEMANTIC_FINGERPRINT_MISSING")
        unit_fingerprint[sid] = fp
        unit_seen_count[sid] = 0

    requirement_ids: set[str] = set()
    for row in requirements:
        if not isinstance(row, Mapping):
            return _fail("REQUIREMENT_NOT_OBJECT")
        rid = row.get("id")
        if not isinstance(rid, str) or not rid or rid in requirement_ids:
            return _fail("REQUIREMENT_ID_INVALID_OR_DUPLICATE")
        requirement_ids.add(rid)
        binding = row.get("p3_binding")
        if not isinstance(binding, Mapping):
            return _fail("P3_BINDING_REQUIRED", requirement_id=rid)
        field = binding.get("field")
        declared_hash = binding.get("value_sha256")
        if field not in ALLOWED_FIELDS:
            return _fail("P3_BINDING_FIELD_OUTSIDE_BINARY_CELL", requirement_id=rid, field=field)
        expected_hash = projection_hashes[field]
        if declared_hash != expected_hash:
            return _fail(
                "P3_BINDING_VALUE_HASH_MISMATCH",
                requirement_id=rid,
                field=field,
                expected=expected_hash,
                observed=declared_hash,
            )
        refs = row.get("source_semantic_unit_ids")
        if not isinstance(refs, list) or not refs:
            return _fail("REQUIREMENT_WITHOUT_SEMANTIC_UNITS", requirement_id=rid)
        expected_fp = "P3_BINDING:" + field + ":" + expected_hash
        for sid in refs:
            if sid not in unit_fingerprint:
                return _fail("P3_BINDING_UNKNOWN_SEMANTIC_UNIT", requirement_id=rid, unit_id=sid)
            unit_seen_count[sid] += 1
            if unit_fingerprint[sid] != expected_fp:
                return _fail(
                    "P3_SEMANTIC_FINGERPRINT_BINDING_MISMATCH",
                    requirement_id=rid,
                    unit_id=sid,
                    expected=expected_fp,
                    observed=unit_fingerprint[sid],
                )

    # An operative consensus unit may not feed two different structured
    # requirements in this exact cell: that would make its semantic binding
    # ambiguous even if both extractors agreed on the span.
    duplicate_units = sorted(sid for sid, count in unit_seen_count.items() if count > 1)
    if duplicate_units:
        return _fail("SEMANTIC_UNIT_MULTI_REQUIREMENT_BINDING", unit_ids=duplicate_units)

    expression = evaluate_expression({"objective": objective, "v2_input": public})
    if expression.get("pass") is not True:
        return _fail(
            "BOUND_BINARY_EXPRESSION_CELL_REJECTED",
            expression_reason=expression.get("reason"),
        )
    if (
        expression.get("bound_cell_required_decision_coverage_complete") is not True
        or expression.get("decision_expression_covered") is not True
        or expression.get("policy_adequacy_authority") is not False
        or expression.get("terminal_authority") is not False
        or expression.get("terminal_credit_delta") != 0
    ):
        return _fail("BINARY_EXPRESSION_AUTHORITY_BOUNDARY_INVALID")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__P3_BOUND_BINARY_REAL_CONTEXT_MEMBERSHIP_AUTHENTICATED",
        "context_id": context_id,
        "behavior_id": BEHAVIOR_ID,
        "selected_class_membership_authenticated": True,
        "real_context_semantic_scope_complete": True,
        "source_authorization_verified": True,
        "top_law_eligible": True,
        "structured_contract_sha256": structured_contract_sha256,
        "projection_hashes": projection_hashes,
        "authority_scope_git_blob_sha": authority_ref.get("git_blob_sha"),
        "expression_receipt": expression,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "EXACT_AUTHORITY_CLOSED_SOURCE_BUNDLE__DUAL_SEMANTIC_CONSENSUS__"
            "EVERY_OPERATIVE_REQUIREMENT_HASH_BOUND_TO_EXACT_BINARY_P3_STRUCTURED_FIELD__"
            "EXACT_TWO_OPTIONAL_OBJECTIVE_ROLE_CLAIMS__NO_GENERAL_P3_SCOPE_CLAIM"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {}, repo_root=root)
