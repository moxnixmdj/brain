"""Professional whole-leaf property-truth frontier V1.

This is a zero-credit localization layer after the independently verified 24/24
whole-leaf scope batch. It does not prove property truth. It projects current
known-defeater coverage and the R10 execution guard into one shared property
frontier, while preserving the explicit fact that unknown-defeater/detection
completeness is unproved.

The Coverage Closure mapping is diagnostic only. It does not mutate or reuse the
single active canonical coverage claim.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_PROPERTY_TRUTH_FRONTIER_V1"

PINS = {
    "scope_batch_activation": (
        "canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_ACTIVATION_20261010_V1.json",
        "d40188f87818d9c6a4507a043380a753ca563e18",
    ),
    "scope_batch_verify": (
        "canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json",
        "4c2d40a262f18f34bb35f94b59660d60972d45ef",
    ),
    "manifest": (
        "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json",
        "a7cad32c9fd969ff2c3857bb924c7bd746237ec2",
    ),
    "catalog": (
        "canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json",
        "8b92e5cf76f767054f55414b87014e03d43460b8",
    ),
    "known_defeater_verify": (
        "canonical/verification/PROFESSIONAL_QUALITY_80_DEFEATER_UVCK_REPLAY_VERIFY_20261009_V1.json",
        "c054e9362ce382889e9cca62bdb69e11cea19644",
    ),
    "r10_execution_guard_verify": (
        "canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_GUARD_VERIFY_20261010_V1.json",
        "7a29d67c77c8961b238e7f9b3bf74d278984452e",
    ),
}

def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "property_truth_ready_count": 0,
        "property_truth_closed_count": 0,
        "new_primitive_required": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }

def _status_pass(doc: Mapping[str, Any]) -> bool:
    return isinstance(doc.get("status"), str) and str(doc["status"]).startswith("PASS__")

def project_documents(
    manifest: Mapping[str, Any],
    catalog: Mapping[str, Any],
    scope_verify: Mapping[str, Any],
    known_verify: Mapping[str, Any],
    r10_verify: Mapping[str, Any],
) -> dict[str, Any]:
    if not _status_pass(scope_verify):
        return _fail("SCOPE_BATCH_NOT_VERIFIED")
    replay = scope_verify.get("independent_replay") or {}
    if (
        replay.get("leaf_count") != 24
        or replay.get("scope_complete_count") != 24
        or replay.get("property_truth_count") != 0
    ):
        return _fail("SCOPE_BATCH_COUNTS_INVALID")

    roots = manifest.get("roots")
    if not isinstance(roots, list) or len(roots) != 12:
        return _fail("LEAF_MANIFEST_ROOT_SET_INVALID")
    root_ids = [r.get("root_id") for r in roots if isinstance(r, Mapping)]
    if len(root_ids) != 12 or len(set(root_ids)) != 12 or any(not isinstance(x, str) for x in root_ids):
        return _fail("LEAF_MANIFEST_ROOT_IDS_INVALID")

    challenges = catalog.get("challenges")
    if catalog.get("challenge_count") != 80 or not isinstance(challenges, list) or len(challenges) != 80:
        return _fail("DEFEATER_CATALOG_COUNT_INVALID")
    if "NO_CLAIM_DEFEATER_SET_COMPLETE" not in set(catalog.get("hard_nonclaims") or []):
        return _fail("DEFEATER_COMPLETENESS_NONCLAIM_MISSING")

    counts = {rid: 0 for rid in root_ids}
    ids: set[str] = set()
    for row in challenges:
        if not isinstance(row, Mapping):
            return _fail("DEFEATER_ROW_INVALID")
        cid = row.get("id")
        refs = row.get("root_ids")
        if not isinstance(cid, str) or not cid or cid in ids:
            return _fail("DEFEATER_ID_INVALID")
        ids.add(cid)
        if not isinstance(refs, list) or not refs:
            return _fail("DEFEATER_ROOT_MAPPING_INVALID", defeater_id=cid)
        for rid in refs:
            if rid not in counts:
                return _fail("DEFEATER_ROOT_UNKNOWN", defeater_id=cid, root_id=rid)
            counts[rid] += 1
    if any(v <= 0 for v in counts.values()):
        return _fail("ROOT_WITHOUT_KNOWN_DEFEATER")

    if not _status_pass(known_verify) or "80_OF_80_KNOWN_DEFEATERS_BOUND" not in str(known_verify.get("status")):
        return _fail("KNOWN_DEFEATER_BINDING_NOT_VERIFIED")
    if "NO_ADVERSARIAL_COMPLETENESS_OF_UNKNOWN_ATTACKS" not in set(known_verify.get("hard_nonclaims") or []):
        return _fail("KNOWN_DEFEATER_VERIFY_COMPLETENESS_NONCLAIM_MISSING")

    if not _status_pass(r10_verify):
        return _fail("R10_EXECUTION_GUARD_NOT_VERIFIED")
    open_r10 = r10_verify.get("open_residual") or {}
    if open_r10.get("detection_completeness_proved") is not False:
        return _fail("R10_DETECTION_COMPLETENESS_OVERCLAIM")
    if open_r10.get("whole_leaf_property_truth_proved") is not False:
        return _fail("R10_PROPERTY_TRUTH_OVERCLAIM")

    rows: list[dict[str, Any]] = []
    for root in roots:
        rid = root["root_id"]
        for kind, field in (("SEMANTIC", "semantic_leaf"), ("EXECUTION", "execution_leaf")):
            leaf = root.get(field)
            if not isinstance(leaf, Mapping) or not isinstance(leaf.get("id"), str):
                return _fail("LEAF_DEFINITION_INVALID", root_id=rid, leaf_kind=kind)
            leaf_id = leaf["id"]
            if kind == "SEMANTIC":
                residual = "DOMAIN_SEMANTIC_GROUNDING_PLUS_UNKNOWN_DEFEATER_COMPLETENESS"
                enforcement = False
            elif rid == "R10_ANALYSIS_DECISION":
                residual = "DEFEATER_DETECTION_AND_REQUIRED_PROOF_SLOT_COMPLETENESS"
                enforcement = True
            else:
                residual = "ROOT_SPECIFIC_PROPERTY_EXECUTION_PLUS_DETECTION_COMPLETENESS"
                enforcement = False
            rows.append({
                "root_id": rid,
                "leaf_id": leaf_id,
                "leaf_kind": kind,
                "whole_leaf_scope_complete": True,
                "known_root_defeater_count": counts[rid],
                "known_defeater_binding_verified": True,
                "known_defeater_set_complete_proved": False,
                "detection_completeness_proved": False,
                "root_specific_enforcement_verified": enforcement,
                "whole_leaf_property_truth_proved": False,
                "property_truth_ready": False,
                "exact_residual": residual,
            })

    if len(rows) != 24 or len({r["leaf_id"] for r in rows}) != 24:
        return _fail("PROPERTY_FRONTIER_LEAF_SET_INVALID")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__24_SCOPE_COMPLETE_PROPERTY_LEAVES_LOCALIZED__80_KNOWN_DEFEATERS_BOUND__UNKNOWN_DEFEATER_AND_DETECTION_COMPLETENESS_OPEN__ZERO_PROPERTY_CREDIT",
        "leaf_count": 24,
        "scope_complete_count": 24,
        "known_defeater_count": 80,
        "known_defeater_root_counts": {k: counts[k] for k in sorted(counts)},
        "known_defeater_binding_verified": True,
        "known_defeater_set_complete_proved": False,
        "unknown_defeater_completeness_proved": False,
        "property_truth_ready_count": 0,
        "property_truth_closed_count": 0,
        "rows": sorted(rows, key=lambda r: r["leaf_id"]),
        "coverage_closure_projection": {
            "claim_scope": "PROFESSIONAL_WHOLE_LEAF_PROPERTY_FALSE_CERTIFICATION_COVERAGE__DIAGNOSTIC_ONLY",
            "CC_R1_REALITY_CONTAINMENT": "OPEN__NO_PROOF_ALL_REAL_PROPERTY_FALSE_CERTIFICATION_MODES_ENTER_CURRENT_DETECTOR_OR_CHALLENGE_BASIS",
            "CC_R2_MISSION_SOUNDNESS": "PARTIAL__KNOWN_DEFEATER_ACTIVATION_IS_FAIL_CLOSED_BUT_NO_GLOBAL_WHOLE_PROPERTY_VERIFIER_BOUND",
            "CC_R3_TERMINAL_CLOSURE": "PARTIAL__80_KNOWN_DEFEATERS_BOUND_TO_EXISTING_UVCK_ROOTS_BUT_DETECTION_TOTALITY_AND_ROOT_EXECUTION_CLOSURE_OPEN",
            "CC_R4_PROOF_AUTHORITY": "OPEN__NO_CLAIM_SCOPED_COVERAGE_ROOT_CERTIFICATES_EXIST_FOR_THIS_PROPERTY_CLAIM",
            "canonical_coverage_registry_mutated": False,
        },
        "shared_next": [
            "FREEZE_ONE_CLAIM_SCOPED_PROFESSIONAL_PROPERTY_DETECTION_COMPLETENESS_CLAIM_USING_EXISTING_COVERAGE_CLOSURE_MACHINERY",
            "ATTACK_CC_R1_REALITY_CONTAINMENT_FIRST__PROVE_OBSERVATION_AND_DETECTION_COVERAGE_OR_PRODUCE_ONE_EFFECT_DISTINGUISHING_FALSE_CERTIFICATION_COUNTEREXAMPLE",
            "REUSE_80_KNOWN_DEFEATER_BINDING_AND_ROOT_SPECIFIC_GUARDS_FOR_CC_R2_CC_R3__DO_NOT_REBUILD_THE_UVCK_ONTOLOGY",
            "RUN_LEAF_PROPERTY_EXECUTION_ONLY_AFTER_SHARED_DETECTION_COMPLETENESS_OR_A_LEAF_SPECIFIC_STRONGER_PROOF",
        ],
        "new_primitive_required": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

def verify(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    docs: dict[str, Any] = {}
    for key, (rel, expected) in PINS.items():
        path = root / rel
        if not path.is_file() or path.is_symlink():
            return _fail(key.upper() + "_MISSING")
        if _blob(path) != expected:
            return _fail(key.upper() + "_BLOB_STALE")
        try:
            docs[key] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return _fail(key.upper() + "_JSON_INVALID")
    return project_documents(
        docs["manifest"],
        docs["catalog"],
        docs["scope_batch_verify"],
        docs["known_defeater_verify"],
        docs["r10_execution_guard_verify"],
    )

if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
