from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Mapping

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAPPING_REL = "canonical/governance/OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V1.json"
PROTOCOL_REL = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
FIRST_PARTY_REL = "canonical/governance/OPUS55_FIRST_PARTY_OBSERVABLE_SURFACE_COVERAGE_AUDIT_20261005_V1.json"
META_REL = "canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V5.json"

EXPECTED_SURFACES = {
    "CYBERSECURITY",
    "BIOLOGY_RESEARCH_AND_DEVELOPMENT",
    "AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT",
    "HEALTHCARE",
    "MATHEMATICAL_REASONING_ARXIVMATH",
}
FIRST_PARTY_SURFACES = {
    "CYBERSECURITY",
    "BIOLOGY_RESEARCH_AND_DEVELOPMENT",
    "AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT",
}
EXTERNAL_REVALIDATION_SURFACES = {
    "HEALTHCARE",
    "MATHEMATICAL_REASONING_ARXIVMATH",
}


class MappingError(RuntimeError):
    pass


def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _require(cond: bool, code: str) -> None:
    if not cond:
        raise MappingError(code)


def verify_mapping(mapping: Mapping, protocols: Mapping, first_party: Mapping, meta: Mapping) -> dict:
    _require(mapping.get("schema") == "PROJECT_BRAIN_OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V1", "MAPPING_SCHEMA")
    rules = mapping.get("global_rules") or {}
    _require(rules.get("knowledge_external_jit") is True, "KNOWLEDGE_NOT_JIT")
    _require(rules.get("domain_label_alone_is_not_a_capability") is True, "DOMAIN_LABEL_RULE_MISSING")
    _require(rules.get("mapping_does_not_imply_acceptance") is True, "ACCEPTANCE_FIREWALL_MISSING")
    _require(rules.get("new_family_only_on_constructive_unmapped_transform") is True, "NEW_FAMILY_RULE_MISSING")

    family_rows = protocols.get("protocols") or []
    families = {str(x.get("family")) for x in family_rows if isinstance(x, dict) and x.get("family")}
    _require(len(families) == 19, "CANONICAL_FAMILY_COUNT_NOT_19")

    frontier = set(meta.get("family_mapping_frontier") or [])
    _require(frontier == EXPECTED_SURFACES, "META_FRONTIER_DRIFT")

    source_rows = first_party.get("candidate_mappings") or []
    source_surfaces = {str(x.get("surface")) for x in source_rows if isinstance(x, dict)}
    _require(FIRST_PARTY_SURFACES.issubset(source_surfaces), "FIRST_PARTY_SURFACE_BINDING_MISSING")

    rows = mapping.get("mappings")
    _require(isinstance(rows, list), "MAPPINGS_NOT_LIST")
    by_surface = {}
    for row in rows:
        _require(isinstance(row, dict), "MAPPING_ROW_INVALID")
        surface = str(row.get("surface") or "")
        _require(surface and surface not in by_surface, "SURFACE_EMPTY_OR_DUPLICATE")
        by_surface[surface] = row
    _require(set(by_surface) == EXPECTED_SURFACES, "SURFACE_SET_DRIFT")

    for surface, row in by_surface.items():
        union = row.get("existing_family_union")
        _require(isinstance(union, list) and union, "EMPTY_FAMILY_UNION:" + surface)
        _require(len(union) == len(set(union)), "DUPLICATE_FAMILY:" + surface)
        unknown = sorted(set(union) - families)
        _require(not unknown, "UNKNOWN_FAMILY:" + surface + ":" + ",".join(unknown))
        decomp = row.get("behavioral_decomposition")
        _require(isinstance(decomp, list) and decomp and len(decomp) == len(set(decomp)), "BEHAVIOR_DECOMPOSITION_INVALID:" + surface)
        _require(row.get("new_family_required") is False, "UNJUSTIFIED_NEW_FAMILY:" + surface)
        transfer = str(row.get("terminal_transfer") or "")
        _require(transfer.startswith("REQUIRES_"), "TERMINAL_TRANSFER_NOT_FAIL_CLOSED:" + surface)
        _require("CLOSED" not in transfer and "PROVED" not in transfer, "TRANSFER_OVERCLAIM:" + surface)
        if surface in EXTERNAL_REVALIDATION_SURFACES:
            _require(row.get("external_source_revalidation_required") is True, "EXTERNAL_REVALIDATION_NOT_PRESERVED:" + surface)

    math = by_surface["MATHEMATICAL_REASONING_ARXIVMATH"]
    _require(math.get("acceptance_scope_bridge_required") is True, "ARXIVMATH_SCOPE_BRIDGE_NOT_REQUIRED")
    _require("NO_HLE_ONLY_INHERITANCE" in str(math.get("terminal_transfer")), "ARXIVMATH_HLE_FIREWALL_MISSING")

    result = mapping.get("mapping_result") or {}
    _require(result.get("surface_count") == 5, "RESULT_SURFACE_COUNT")
    _require(result.get("mapped_to_existing_family_union_count") == 5, "RESULT_MAPPED_COUNT")
    _require(result.get("constructive_unmapped_transform_count") == 0, "RESULT_UNMAPPED_COUNT")
    _require(result.get("positive_root1_gap_delta") == 0, "ROOT1_GAP_OVERCLAIM")
    _require(result.get("semantic_mapping_independent_verification_required") is True, "SEMANTIC_VERIFICATION_GATE_MISSING")
    _require(result.get("terminal_acceptance_credit_delta") == 0, "TERMINAL_CREDIT_FORBIDDEN")

    return {
        "schema": "PROJECT_BRAIN_OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_VERDICT_V1",
        "status": "PASS",
        "primitive_mapping_structurally_total": True,
        "mapped_surface_count": 5,
        "canonical_family_count": 19,
        "new_family_required_count": 0,
        "domain_acceptance_parity_proved": False,
        "semantic_mapping_independent_verification_required": True,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def verify_repository(root: pathlib.Path = ROOT) -> dict:
    mapping = json.loads((root / MAPPING_REL).read_text(encoding="utf-8"))
    protocols = json.loads((root / PROTOCOL_REL).read_text(encoding="utf-8"))
    first_party = json.loads((root / FIRST_PARTY_REL).read_text(encoding="utf-8"))
    meta = json.loads((root / META_REL).read_text(encoding="utf-8"))
    authorities = mapping.get("authorities") or {}
    expected = {
        "terminal_protocols": (PROTOCOL_REL, git_blob_sha(root / PROTOCOL_REL)),
        "first_party_surface_audit": (FIRST_PARTY_REL, git_blob_sha(root / FIRST_PARTY_REL)),
        "meta_envelope_v5": (META_REL, git_blob_sha(root / META_REL)),
    }
    for key, (path, actual) in expected.items():
        row = authorities.get(key) or {}
        _require(row.get("path") == path, "AUTHORITY_PATH_DRIFT:" + key)
        _require(row.get("git_blob_sha") == actual, "AUTHORITY_BLOB_DRIFT:" + key)
    out = verify_mapping(mapping, protocols, first_party, meta)
    out["repository_bindings_status"] = "PASS"
    out["mapping_git_blob_sha"] = git_blob_sha(root / MAPPING_REL)
    return out


if __name__ == "__main__":
    try:
        print(json.dumps(verify_repository(), indent=2, sort_keys=True))
    except Exception as exc:
        print(json.dumps({
            "schema": "PROJECT_BRAIN_OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }, indent=2, sort_keys=True))
        raise
