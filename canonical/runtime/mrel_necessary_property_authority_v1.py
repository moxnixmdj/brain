"""Bounded MREL necessary-property authority V1.

Authenticates a deliberately small set of one-way semantic entailments:
    MREL -> necessary properties

All edges are source-bound to official EBA/SRB fragments. Reverse inference is
never authorized. Missing properties remain UNKNOWN, not false. No global
ontology completeness, concept identity, policy adequacy, execution, acceptance,
promotion, or terminal authority is granted.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    RECEIPT_SCHEMA as EDGE_RECEIPT_SCHEMA,
)

SCHEMA = "PROJECT_BRAIN_MREL_NECESSARY_PROPERTY_AUTHORITY_V1"
REQUEST_SCHEMA = "PROJECT_BRAIN_MREL_NECESSARY_PROPERTY_REQUEST_V1"
PACK_SCHEMA = "PROJECT_BRAIN_MREL_NECESSARY_PROPERTY_SOURCE_PACK_V1"
PACK_PATH = "canonical/evidence/MREL_NECESSARY_PROPERTY_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA = "2a78747cd4bb342572d8ee9c8e9bde370b8b9500"
SCOPE_ID = "EU_MREL_EBA_BRRD_AND_SRB_2026_V1"

MREL = "REGCAP::MREL"

RULES = {
    (MREL, "DISPOSITION::LOSS_ABSORPTION"): (
        "SRB_MREL_DASHBOARD_H2_2025_2026_07_20",
        ("MREL_LOSS_ABSORBING_CAPACITY_IN_RESOLUTION",),
    ),
    (MREL, "FUNCTION::LOSS_ABSORPTION"): (
        "EBA_MREL_CALIBRATION_QA_2019_4901",
        ("MREL_LOSS_ABSORPTION_AMOUNT",),
    ),
    (MREL, "FUNCTION::RECAPITALISATION"): (
        "EBA_MREL_CALIBRATION_QA_2019_4901",
        ("MREL_RECAPITALISATION_AMOUNT",),
    ),
    (MREL, "REGIME::RESOLUTION"): (
        "SRB_MREL_DASHBOARD_H2_2025_2026_07_20",
        ("MREL_LOSS_ABSORBING_CAPACITY_IN_RESOLUTION",),
    ),
    (MREL, "COMPOSITION::OWN_FUNDS_AND_ELIGIBLE_LIABILITIES"): (
        "EBA_MREL_CALIBRATION_QA_2019_4901",
        ("MREL_OFFICIAL_NAME",),
    ),
    (MREL, "LEGAL_FRAMEWORK::EU_BRRD_ARTICLE_45C"): (
        "EBA_MREL_CALIBRATION_QA_2019_4901",
        ("MREL_LOSS_ABSORPTION_AMOUNT", "MREL_RECAPITALISATION_AMOUNT"),
    ),
}

ROOT = Path(__file__).resolve().parents[2]


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "source_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def load_pack(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    path = (root / PACK_PATH).resolve(strict=True)
    path.relative_to(root)
    if not path.is_file() or path.is_symlink():
        raise ValueError("PACK_FILE_INVALID")
    raw = path.read_bytes()
    blob = _git_blob(raw)
    if blob != PACK_GIT_BLOB_SHA:
        raise ValueError("PACK_GIT_BLOB_DRIFT:" + blob)
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != PACK_SCHEMA:
        raise ValueError("PACK_SCHEMA_INVALID")
    if doc.get("scope_id") != SCOPE_ID:
        raise ValueError("PACK_SCOPE_INVALID")
    sources = doc.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("PACK_SOURCES_REQUIRED")

    by_id = {}
    for source in sources:
        if not isinstance(source, Mapping):
            raise ValueError("PACK_SOURCE_NOT_OBJECT")
        sid = str(source.get("source_id") or "").strip()
        if not sid or sid in by_id:
            raise ValueError("PACK_SOURCE_ID_INVALID_OR_DUPLICATE")
        by_id[sid] = dict(source)

    required_sources = {source_id for source_id, _ in RULES.values()}
    if not required_sources.issubset(by_id):
        raise ValueError("PACK_MISSING_RULE_SOURCE")

    for (concept_id, property_id), (source_id, fragment_ids) in RULES.items():
        available = {
            str(row.get("fragment_id") or "")
            for row in by_id[source_id].get("fragments") or []
            if isinstance(row, Mapping)
        }
        missing = set(fragment_ids) - available
        if missing:
            raise ValueError(
                "PACK_MISSING_RULE_FRAGMENT:"
                + concept_id
                + ":"
                + property_id
                + ":"
                + ",".join(sorted(missing))
            )

    return {
        "pack": dict(doc),
        "pack_git_blob_sha": blob,
        "sources_by_id": by_id,
    }


def verify_property_request(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    projection_verifier=verify_projection_pack,
) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping) or request.get("schema") != REQUEST_SCHEMA:
            return _base("FAIL_CLOSED", reason="REQUEST_SCHEMA_INVALID")
        allowed = {"schema", "scope_id", "concept_id", "property_id"}
        extra = set(request) - allowed
        if extra:
            return _base(
                "FAIL_CLOSED",
                reason="UNMODELED_REQUEST_FIELDS:"
                + ",".join(sorted(str(x) for x in extra)),
            )

        scope_id = str(request.get("scope_id") or "").strip()
        concept_id = str(request.get("concept_id") or "").strip()
        property_id = str(request.get("property_id") or "").strip()
        if scope_id != SCOPE_ID:
            return _base("FAIL_CLOSED", reason="SCOPE_ID_MISMATCH")
        if not concept_id or not property_id:
            return _base("FAIL_CLOSED", reason="CONCEPT_OR_PROPERTY_ID_REQUIRED")

        rule = RULES.get((concept_id, property_id))
        if rule is None:
            return _base(
                "UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE",
                concept_id=concept_id,
                property_id=property_id,
                reverse_inference_authorized=False,
                absence_means_false=False,
            )

        checked = load_pack(repo_root=repo_root)
        source_id, fragment_ids = rule
        source_pack = checked["sources_by_id"][source_id]
        source_result = projection_verifier(source_pack)
        if not isinstance(source_result, Mapping) or source_result.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED",
                concept_id=concept_id,
                property_id=property_id,
                source_result=source_result,
            )

        authenticated_ids = set(
            str(x)
            for x in source_result.get("receipt", {}).get("fragment_ids", [])
        )
        if not set(fragment_ids).issubset(authenticated_ids):
            return _base(
                "FAIL_CLOSED",
                reason="REQUIRED_SOURCE_FRAGMENT_NOT_AUTHENTICATED",
                concept_id=concept_id,
                property_id=property_id,
                required_fragment_ids=list(fragment_ids),
            )

        evidence = {
            "scope_id": SCOPE_ID,
            "concept_id": concept_id,
            "property_id": property_id,
            "pack_git_blob_sha": checked["pack_git_blob_sha"],
            "source_id": source_id,
            "source_receipt_sha256": source_result["receipt"]["receipt_sha256"],
            "fragment_ids": list(fragment_ids),
            "relation": "ENTAILS",
        }
        edge_core = {
            "pass": True,
            "schema": EDGE_RECEIPT_SCHEMA,
            "scope_id": SCOPE_ID,
            "source_id": concept_id,
            "target_id": property_id,
            "relation": "ENTAILS",
            "source_semantics_authenticated": True,
            "target_semantics_authenticated": True,
            "relation_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "evidence_sha256": _sha(evidence),
        }
        edge = dict(edge_core)
        edge["receipt_sha256"] = _sha(edge_core)

        return _base(
            "PASS__MREL_NECESSARY_PROPERTY_AUTHENTICATED",
            passed=True,
            semantic_truth_authority=True,
            source_authority=True,
            concept_id=concept_id,
            property_id=property_id,
            relation="ENTAILS",
            edge_receipt=edge,
            source_result=source_result,
            required_fragment_ids=list(fragment_ids),
            reverse_inference_authorized=False,
            exact_concept_identity_authority=False,
            open_world_ontology_complete=False,
            boundary=(
                "MREL_TO_BOUND_NECESSARY_PROPERTY_ENTAILMENT_ONLY__"
                "NO_PROPERTY_TO_MREL_REVERSE_INFERENCE__"
                "NO_TLAC_MREL_DISJOINTNESS__NO_UNLISTED_PROPERTY_NEGATION__"
                "NO_OPEN_WORLD_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
