"""Explicit professional target-instance compiler for live R1 execution.

This is integration glue over already verified Brain-owned R1 mechanisms. It
does not infer arbitrary natural-language intent. It preserves the raw task
losslessly, requires an explicit structured target instance, content-addresses
every R1 load-bearing target field, and verifies that the canonical professional
behavior still exposes the previously certified target-role semantics.

A PASS proves preservation/binding for the supplied explicit target instance.
It does not prove that the structured fields exhaust every meaning in the raw
task, nor does it grant quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import adequacy_basis_structural_completeness_gate_v1 as structural
from canonical.runtime import lossless_raw_task_contract_v1 as raw_contract
from canonical.runtime import professional_target_semantic_certificate_v1 as target_semantics

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_TARGET_INSTANCE_COMPILER_V1"
TARGET_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_TARGET_INSTANCE_V1"
BEHAVIOR_ID = target_semantics.BEHAVIOR_ID
REGISTRY_PATH = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json"
CONTRACT_SCHEMA_PATH = "canonical/governance/BEHAVIORAL_CONTRACT_SCHEMA_V1.json"
EXPECTED_CANONICAL_BEHAVIOR_SHA256 = "f6c9438aec89b442686f99bb4aaa232fb2e665e282fc0e0574695cf984254c59"

_REQUIRED_TEXT = (
    "source_id",
    "raw_task_text",
    "objective",
    "audience",
    "artifact_type",
    "target_construct",
    "claim_scope",
    "current_draft_render",
)
_REQUIRED_LISTS = (
    "source_evidence",
    "hard_constraints",
    "plausible_interpretations",
)
_ROLE_FIELDS = {
    "objective": "required_output_or_action",
    "audience": "inputs",
    "hard_constraints": "allowed_information",
    "success_semantics": "success_condition",
    "failure_semantics": "failure_condition",
    "target_construct": "success_condition",
    "claim_scope": "scope",
    "evidence_boundary": "dependency_boundary",
}


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "r1_target_step_verified": False,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return _base("FAIL_CLOSED", reason=reason, **extra)


def _string_list(value: Any, *, label: str, nonempty: bool = False) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    out: list[str] = []
    for raw in value:
        if not isinstance(raw, str) or not raw.strip():
            return None
        item = raw.strip()
        if item not in out:
            out.append(item)
    if nonempty and not out:
        return None
    return out


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve(strict=True)
    path.relative_to(root.resolve(strict=True))
    if not path.is_file() or path.is_symlink():
        raise ValueError("BOUND_FILE_INVALID:" + relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("BOUND_DOCUMENT_INVALID:" + relative)
    return value


def _canonical_behavior(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = _load_json(root, REGISTRY_PATH)
    rows = registry.get("active_contracted_residuals")
    if not isinstance(rows, list):
        raise ValueError("BEHAVIOR_REGISTRY_ROWS_INVALID")
    matches = [
        row for row in rows
        if isinstance(row, Mapping) and row.get("behavior_id") == BEHAVIOR_ID
    ]
    if len(matches) != 1:
        raise ValueError("CANONICAL_PROFESSIONAL_BEHAVIOR_NOT_UNIQUE")
    contract = deepcopy(dict(matches[0]))
    if target_semantics.digest(contract) != EXPECTED_CANONICAL_BEHAVIOR_SHA256:
        raise ValueError("CANONICAL_PROFESSIONAL_BEHAVIOR_DRIFT")
    schema = _load_json(root, CONTRACT_SCHEMA_PATH)
    return contract, schema


def _semantic_binding(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "behavior_id": BEHAVIOR_ID,
        "contract_sha256": target_semantics.digest(dict(contract)),
        "role_bindings": {
            role: {
                "source_field": field,
                "source_value_sha256": target_semantics.digest(contract[field]),
            }
            for role, field in _ROLE_FIELDS.items()
        },
        "ambiguity_policy": {
            "unique_optimum_claimed": False,
            "admissible_plan_definition": (
                "ANY_PLAN_SATISFYING_SUCCESS_AND_AVOIDING_FAILURE_WITHIN_DECLARED_SCOPE"
            ),
            "unresolved_runtime_task_ambiguity_must_remain_open": True,
        },
        "hard_nonclaims": [
            "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
            "NO_SOURCE_EXTRACTION_COMPLETENESS",
            "NO_UNIQUE_BEST_PLAN",
            "NO_GLOBAL_R1_SEMANTIC_LEAF_CLOSURE",
            "NO_GLOBAL_R1_ROOT_CLOSURE",
        ],
    }


def compile_target(
    target: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(target, Mapping):
        return _fail("TARGET_INSTANCE_NOT_OBJECT")
    if target.get("schema") != TARGET_SCHEMA:
        return _fail("TARGET_INSTANCE_SCHEMA_INVALID")

    normalized: dict[str, Any] = {"schema": TARGET_SCHEMA}
    for field in _REQUIRED_TEXT:
        value = target.get(field)
        if not isinstance(value, str) or not value.strip():
            return _fail("TARGET_TEXT_FIELD_INVALID:" + field)
        normalized[field] = value.strip()

    for field in _REQUIRED_LISTS:
        values = _string_list(
            target.get(field),
            label=field,
            nonempty=(field == "plausible_interpretations"),
        )
        if values is None:
            return _fail("TARGET_LIST_FIELD_INVALID:" + field)
        normalized[field] = values

    extra = sorted(set(target) - set(_REQUIRED_TEXT) - set(_REQUIRED_LISTS) - {"schema"})
    if extra:
        return _fail("UNMODELED_TARGET_INSTANCE_FIELDS", unmodeled_fields=extra)

    root = (
        Path(repo_root).resolve(strict=True)
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    try:
        behavior, behavior_schema = _canonical_behavior(root)
    except Exception as exc:
        return _fail("CANONICAL_BEHAVIOR_LOAD_FAILED:" + type(exc).__name__ + ":" + str(exc))

    semantics = target_semantics.certify(behavior, _semantic_binding(behavior))
    if semantics.get("pass") is not True:
        return _fail(
            "CANONICAL_TARGET_SEMANTICS_NOT_VERIFIED",
            target_semantic_receipt=semantics,
        )

    structural_receipt = structural.compile_contract_basis(behavior, behavior_schema)
    if structural_receipt.get("pass") is not True:
        return _fail(
            "CANONICAL_TARGET_STRUCTURE_NOT_VERIFIED",
            target_structural_receipt=structural_receipt,
        )

    raw = raw_contract.compile_contract(
        normalized["raw_task_text"],
        source_id=normalized["source_id"],
        routing_target_effects=[BEHAVIOR_ID],
    )
    if (
        raw.get("pass") is not True
        or raw.get("nonwhitespace_source_coverage_complete") is not True
    ):
        return _fail("RAW_TASK_LOSSLESS_BINDING_FAILED", raw_task_contract=raw)

    load_bearing = {
        "objective": normalized["objective"],
        "audience": normalized["audience"],
        "source_evidence": normalized["source_evidence"],
        "artifact_type": normalized["artifact_type"],
        "hard_constraints": normalized["hard_constraints"],
        "plausible_interpretations": normalized["plausible_interpretations"],
        "target_construct": normalized["target_construct"],
        "claim_scope": normalized["claim_scope"],
        "current_draft_render": normalized["current_draft_render"],
    }
    field_sha256 = {key: _digest(value) for key, value in load_bearing.items()}
    target_sha = _digest({
        "schema": TARGET_SCHEMA,
        "source_id": normalized["source_id"],
        "raw_task_sha256": raw["task_sha256"],
        "raw_task_contract_sha256": raw["task_contract_sha256"],
        "behavior_id": BEHAVIOR_ID,
        "canonical_behavior_sha256": EXPECTED_CANONICAL_BEHAVIOR_SHA256,
        "load_bearing_fields": load_bearing,
    })

    return _base(
        "PASS__EXPLICIT_PROFESSIONAL_TARGET_INSTANCE_BOUND",
        passed=True,
        r1_target_step_verified=True,
        behavior_id=BEHAVIOR_ID,
        target_instance_sha256=target_sha,
        raw_task_sha256=raw["task_sha256"],
        raw_task_contract_sha256=raw["task_contract_sha256"],
        raw_task_nonwhitespace_coverage_complete=True,
        canonical_behavior_sha256=EXPECTED_CANONICAL_BEHAVIOR_SHA256,
        field_sha256=field_sha256,
        normalized_target_instance=normalized,
        canonical_target_semantic_receipt=semantics,
        canonical_target_structural_receipt=structural_receipt,
        raw_task_contract=raw,
        preservation_guarantees=[
            "RAW_TASK_NONWHITESPACE_SOURCE_LOSSLESSLY_BOUND",
            "OBJECTIVE_CONTENT_ADDRESSED",
            "AUDIENCE_CONTENT_ADDRESSED",
            "SOURCE_EVIDENCE_SET_CONTENT_ADDRESSED",
            "ARTIFACT_TYPE_CONTENT_ADDRESSED",
            "HARD_CONSTRAINT_SET_CONTENT_ADDRESSED",
            "PLAUSIBLE_INTERPRETATION_SET_CONTENT_ADDRESSED",
            "TARGET_CONSTRUCT_CONTENT_ADDRESSED",
            "CLAIM_SCOPE_CONTENT_ADDRESSED",
            "CURRENT_DRAFT_OR_RENDER_REFERENCE_CONTENT_ADDRESSED",
            "CANONICAL_PROFESSIONAL_TARGET_ROLE_SEMANTICS_REVERIFIED",
            "CANONICAL_REQUIRED_BEHAVIOR_FIELDS_STRUCTURALLY_REVERIFIED",
        ],
        hard_nonclaims=[
            "NO_CLAIM_STRUCTURED_TARGET_FIELDS_WERE_INFERRED_COMPLETELY_FROM_ARBITRARY_LANGUAGE",
            "NO_CLAIM_PLAUSIBLE_INTERPRETATION_ENUMERATION_IS_OPEN_WORLD_COMPLETE",
            "NO_SOURCE_EXTRACTION_COMPLETENESS",
            "NO_UNIQUE_BEST_PLAN",
            "NO_GLOBAL_R1_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
            "NO_GLOBAL_R1_ROOT_CLOSURE",
        ],
    )


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    return compile_target(args.get("target_instance"), repo_root=args.get("repo_root"))
