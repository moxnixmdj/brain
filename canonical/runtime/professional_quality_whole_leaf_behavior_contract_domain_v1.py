"""Exact whole-leaf input-domain authority for the professional V7 subject.

This module proves only domain identity and scope coverage.  It deliberately
does not prove any professional-quality leaf property.

For every professional-quality leaf, V2 claim material is bound to the same
canonical behavior and the same declared-system subject.  The exact admissible
input domain is therefore represented without shrinkage as ALL runtime
instances governed by the exact canonical behavior contract.  No success,
property, supported-format, parsed-prompt, or downstream-gate filter may narrow
that universe.

The result is a scope theorem, not a quality theorem.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_claim_scope_gate_v2 as gate
from canonical.runtime.universal_scope_closure_compiler_v1 import evaluate as evaluate_scope

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_BEHAVIOR_CONTRACT_DOMAIN_V1"
DOMAIN_SCHEMA_ID = "PROFESSIONAL_QUALITY_WHOLE_LEAF_BEHAVIOR_CONTRACT_DOMAIN_V1"

REGISTRY_PATH = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json"
REGISTRY_BLOB = "ae250d5bc5da73b23600670be354ffba31e65e53"
MANIFEST_PATH = gate.MANIFEST_PATH
MANIFEST_BLOB = gate.MANIFEST_BLOB
SUBJECT_PATH = gate.SUBJECT_PATH
SUBJECT_BLOB = gate.SUBJECT_BLOB
BEHAVIOR_ID = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"

DOMAIN_KIND = "ALL_RUNTIME_INSTANCES_GOVERNED_BY_EXACT_CANONICAL_BEHAVIOR_CONTRACT"
DOMAIN_RULE = (
    "ALL_PROFESSIONAL_QUALITY_LEAVES_EVALUATE_THE_SAME_CANONICAL_BEHAVIOR_"
    "INSTANCE_UNIVERSE__NO_ROOT_OR_LEAF_SPECIFIC_INPUT_FILTER"
)
NO_FILTER = "NONE"
PROPERTY_FILTER = "FORBIDDEN"


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _canon_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_NOT_OBJECT")
    return value


def _behavior_contract(registry: Mapping[str, Any]) -> dict[str, Any] | None:
    rows = registry.get("active_contracted_residuals")
    if not isinstance(rows, list):
        return None
    matches = [
        dict(row)
        for row in rows
        if isinstance(row, Mapping) and row.get("behavior_id") == BEHAVIOR_ID
    ]
    return matches[0] if len(matches) == 1 else None


def canonical_scope_definition(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "domain_schema_id": DOMAIN_SCHEMA_ID,
        "entire_admissible_leaf_domain": True,
        "domain_definition": {
            "domain_kind": DOMAIN_KIND,
            "behavior_id": BEHAVIOR_ID,
            "behavior_contract_registry": {
                "path": REGISTRY_PATH,
                "git_blob_sha": REGISTRY_BLOB,
            },
            "behavior_contract_sha256": _canon_sha(dict(contract)),
            "declared_system_subject": {
                "path": SUBJECT_PATH,
                "git_blob_sha": SUBJECT_BLOB,
                "subject_kind": gate.SUBJECT_KIND,
                "subject_id": gate.SUBJECT_ID,
                "subject_sha256": gate.SUBJECT_SHA256,
            },
            "leaf_input_domain_rule": DOMAIN_RULE,
            "inclusion_filter": NO_FILTER,
            "exclusion_filter": NO_FILTER,
            "success_or_property_filter": PROPERTY_FILTER,
        },
    }


def _base(pass_: bool, status: str, errors: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": pass_,
        "status": status,
        "errors": sorted(set(errors)),
        "whole_leaf_domain_equivalence_proved": pass_,
        "scope_cover_proved": False,
        "leaf_property_truth_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def verify_claim_scope_documents(
    *,
    manifest: Mapping[str, Any],
    subject: Mapping[str, Any],
    registry: Mapping[str, Any],
    claim_scope: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    leaf_id = claim_scope.get("leaf_id")
    meta = gate._manifest_leaf(manifest, leaf_id) if isinstance(leaf_id, str) else None
    if meta is None:
        errors.append("LEAF_NOT_IN_MANIFEST")

    contract = _behavior_contract(registry)
    if contract is None:
        errors.append("EXACT_BEHAVIOR_CONTRACT_NOT_UNIQUE")
        contract = {}

    components = ((subject.get("system_material") or {}).get("components") or [])
    registry_components = [
        row for row in components
        if isinstance(row, Mapping) and row.get("path") == REGISTRY_PATH
    ]
    if len(registry_components) != 1:
        errors.append("SUBJECT_BEHAVIOR_REGISTRY_COMPONENT_NOT_UNIQUE")
    elif registry_components[0].get("git_blob_sha") != REGISTRY_BLOB:
        errors.append("SUBJECT_BEHAVIOR_REGISTRY_BLOB_STALE")

    if (
        subject.get("subject_kind"),
        subject.get("subject_id"),
        subject.get("subject_sha256"),
    ) != (gate.SUBJECT_KIND, gate.SUBJECT_ID, gate.SUBJECT_SHA256):
        errors.append("SUBJECT_IDENTITY_DRIFT")

    if claim_scope.get("schema") != gate.CLAIM_SCOPE_SCHEMA:
        errors.append("CLAIM_SCOPE_SCHEMA_INVALID")
    if claim_scope.get("behavior_id") != BEHAVIOR_ID:
        errors.append("CLAIM_SCOPE_BEHAVIOR_DRIFT")
    if (
        claim_scope.get("subject_kind"),
        claim_scope.get("subject_id"),
        claim_scope.get("subject_sha256"),
    ) != (gate.SUBJECT_KIND, gate.SUBJECT_ID, gate.SUBJECT_SHA256):
        errors.append("CLAIM_SCOPE_SUBJECT_DRIFT")

    if meta is not None:
        if claim_scope.get("root_id") != meta["root_id"]:
            errors.append("CLAIM_SCOPE_ROOT_DRIFT")
        if claim_scope.get("kind") != meta["kind"]:
            errors.append("CLAIM_SCOPE_KIND_DRIFT")
        if claim_scope.get("leaf_acceptance") != meta["acceptance"]:
            errors.append("CLAIM_SCOPE_ACCEPTANCE_DRIFT")

    expected_scope = canonical_scope_definition(contract)
    if claim_scope.get("scope_definition") != expected_scope:
        errors.append("WHOLE_DOMAIN_DEFINITION_NOT_EXACT_CANONICAL_CONTRACT_UNIVERSE")

    domain = (claim_scope.get("scope_definition") or {}).get("domain_definition") or {}
    if domain.get("inclusion_filter") != NO_FILTER:
        errors.append("DOMAIN_INCLUSION_FILTER_FORBIDDEN")
    if domain.get("exclusion_filter") != NO_FILTER:
        errors.append("DOMAIN_EXCLUSION_FILTER_FORBIDDEN")
    if domain.get("success_or_property_filter") != PROPERTY_FILTER:
        errors.append("SUCCESS_OR_PROPERTY_FILTER_MUST_BE_FORBIDDEN")

    if meta is not None and not errors:
        expected_claim = gate.build_claim(
            meta,
            expected_scope,
            epoch=str(claim_scope.get("epoch") or ""),
        )
        if claim_scope.get("claim") != expected_claim:
            errors.append("CLAIM_CONTENT_ADDRESS_MISMATCH")

    passed = not errors
    return _base(
        passed,
        (
            "PASS__EXACT_CANONICAL_BEHAVIOR_CONTRACT_WHOLE_LEAF_DOMAIN"
            if passed else "FAIL_CLOSED__WHOLE_LEAF_DOMAIN_NOT_PROVED"
        ),
        errors,
        leaf_id=leaf_id,
        behavior_id=BEHAVIOR_ID,
        scope_definition_sha256=_canon_sha(expected_scope) if contract else None,
        behavior_contract_sha256=_canon_sha(contract) if contract else None,
        domain_identity_rule=(
            "THE_SCOPE_IS_DEFINITIONALLY_ALL_RUNTIME_INSTANCES_GOVERNED_BY_THE_"
            "EXACT_CANONICAL_BEHAVIOR_CONTRACT_UNDER_THE_EXACT_V7_SUBJECT__NO_"
            "DOWNSTREAM_PROPERTY_OR_SUCCESS_FILTER_IS_PRESENT"
        ),
    )


def verify_scope_certificate_documents(
    *,
    claim_scope: Mapping[str, Any],
    certificate: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    claim = claim_scope.get("claim")
    claim_id = claim.get("claim_id") if isinstance(claim, Mapping) else None
    if not isinstance(claim_id, str) or len(claim_id) != 64:
        errors.append("CLAIM_ID_INVALID")

    scope_definition = claim_scope.get("scope_definition")
    domain = scope_definition.get("domain_definition") if isinstance(scope_definition, Mapping) else None
    if not isinstance(domain, Mapping):
        errors.append("DOMAIN_DEFINITION_MISSING")
    else:
        if domain.get("domain_kind") != DOMAIN_KIND:
            errors.append("DOMAIN_KIND_DRIFT")
        if domain.get("inclusion_filter") != NO_FILTER:
            errors.append("DOMAIN_INCLUSION_FILTER_FORBIDDEN")
        if domain.get("exclusion_filter") != NO_FILTER:
            errors.append("DOMAIN_EXCLUSION_FILTER_FORBIDDEN")
        if domain.get("success_or_property_filter") != PROPERTY_FILTER:
            errors.append("SUCCESS_OR_PROPERTY_FILTER_MUST_BE_FORBIDDEN")

    scope_cert = certificate.get("scope_certificate")
    if not isinstance(scope_cert, Mapping):
        errors.append("SCOPE_CERTIFICATE_MISSING")
        scope_cert = {}
    expected_target = (
        "scope://professional-quality/whole-leaf/" + claim_id
        if isinstance(claim_id, str) else None
    )
    if scope_cert.get("target_scope_id") != expected_target:
        errors.append("TARGET_SCOPE_ID_MISMATCH")
    if scope_cert.get("claim_id") != claim_id:
        errors.append("SCOPE_CERTIFICATE_CLAIM_ID_MISMATCH")
    if scope_cert.get("basis") != "UNIVERSAL_FORMAL_SCOPE_PROOF":
        errors.append("SCOPE_BASIS_INVALID")
    if scope_cert.get("scope_relation") != "EXACT":
        errors.append("SCOPE_RELATION_MUST_BE_EXACT")
    if scope_cert.get("verified") is not True or scope_cert.get("independent") is not True:
        errors.append("VERIFIED_INDEPENDENT_REQUIRED")
    if scope_cert.get("formal_completeness") is not True:
        errors.append("FORMAL_COMPLETENESS_REQUIRED")
    if scope_cert.get("all_admissible_target_inputs_proved") is not True:
        errors.append("ALL_ADMISSIBLE_INPUTS_REQUIRED")
    expected_premise = (
        "behavior-contract-domain:" + _canon_sha(scope_definition)
        if isinstance(scope_definition, Mapping) else None
    )
    if scope_cert.get("premise_set_id") != expected_premise:
        errors.append("PREMISE_SET_ID_MISMATCH")

    scope_out = evaluate_scope(scope_cert)
    if scope_out.get("scope_complete") is not True:
        errors.append("UNIVERSAL_SCOPE_COMPILER_REJECTED")

    passed = not errors
    out = _base(
        passed,
        (
            "PASS__EXACT_BEHAVIOR_CONTRACT_DOMAIN_SCOPE_COVER"
            if passed else "FAIL_CLOSED__SCOPE_COVER_NOT_PROVED"
        ),
        errors,
        leaf_id=claim_scope.get("leaf_id"),
        claim_id=claim_id,
        scope_cover_proved=passed,
        scope_basis=scope_out.get("basis"),
        premise_set_id=expected_premise,
    )
    out["whole_leaf_domain_equivalence_proved"] = False
    return out


def verify_claim_scope_file(
    claim_scope_path: str,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    fixed = (
        (MANIFEST_PATH, MANIFEST_BLOB, "MANIFEST"),
        (SUBJECT_PATH, SUBJECT_BLOB, "SUBJECT"),
        (REGISTRY_PATH, REGISTRY_BLOB, "REGISTRY"),
    )
    errors: list[str] = []
    for rel, expected, label in fixed:
        path = root / rel
        if not path.is_file() or path.is_symlink():
            errors.append(label + "_MISSING")
        elif _git_blob(path) != expected:
            errors.append(label + "_BLOB_STALE")
    target = root / claim_scope_path
    if not target.is_file() or target.is_symlink():
        errors.append("CLAIM_SCOPE_FILE_MISSING")
    if errors:
        return _base(False, "FAIL_CLOSED__CURRENTNESS_OR_INPUT", errors)
    return verify_claim_scope_documents(
        manifest=_load(root / MANIFEST_PATH),
        subject=_load(root / SUBJECT_PATH),
        registry=_load(root / REGISTRY_PATH),
        claim_scope=_load(target),
    )
