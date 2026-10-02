"""Generic canonical proof-atom basis compiler with verified refinement overlays.

This v2 compiler extends v1 by allowing independently verified hierarchical
refinements to replace coarse scheduling certificates. It never infers semantic
equivalence. Exact requirement partitions are checked structurally; semantic
replacement refinements require an explicit independent verification receipt.

Outputs scheduling/proof atoms only. No acceptance, capability, family,
execution, or promotion credit is granted.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CANONICAL_PROOF_ATOM_BASIS_V2"
ROOT = Path(__file__).resolve().parents[2]
ALLOWED_MODES = {
    "EXACT_REQUIREMENT_PARTITION",
    "INDEPENDENTLY_VERIFIED_SEMANTIC_REPLACEMENT",
}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "leaf_atom_count": 0,
        "atoms": [],
        "refined_parents": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def atom_id(proposition: str) -> str:
    return "PA1:" + hashlib.sha256(proposition.encode("utf-8")).hexdigest()


def _valid_str_list(v: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(v, list)
        and (bool(v) or not nonempty)
        and all(isinstance(x, str) and bool(x) for x in v)
        and len(v) == len(set(v))
    )


def _validate_global(doc: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc, Mapping):
        return ["GLOBAL_NOT_OBJECT"]
    unresolved = doc.get("unresolved_predicates")
    certs = doc.get("certificates")
    if not _valid_str_list(unresolved, nonempty=True):
        errors.append("GLOBAL_UNRESOLVED_INVALID")
        unresolved_set: set[str] = set()
    else:
        unresolved_set = set(unresolved)
    if not isinstance(certs, list):
        errors.append("GLOBAL_CERTIFICATES_INVALID")
        return errors
    seen: set[str] = set()
    for i, cert in enumerate(certs):
        if not isinstance(cert, Mapping):
            errors.append(f"GLOBAL_CERT_{i}_INVALID")
            continue
        cid = cert.get("id")
        targets = cert.get("target_predicates")
        requires = cert.get("requires")
        if not isinstance(cid, str) or not cid or cid in seen:
            errors.append("GLOBAL_CERT_ID_INVALID_OR_DUPLICATE")
            continue
        seen.add(cid)
        if not _valid_str_list(targets, nonempty=True):
            errors.append(f"GLOBAL_TARGETS_INVALID:{cid}")
        elif unresolved_set and any(x not in unresolved_set for x in targets):
            errors.append(f"GLOBAL_TARGET_OUTSIDE_FRONTIER:{cid}")
        if not _valid_str_list(requires, nonempty=True):
            errors.append(f"GLOBAL_REQUIRES_INVALID:{cid}")
    return errors


def compile_basis(global_frontier: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    errors = _validate_global(global_frontier)
    refs = overlay.get("refinements") if isinstance(overlay, Mapping) else None
    if not isinstance(refs, list) or not refs:
        errors.append("REFINEMENTS_REQUIRED")
    if errors:
        return _fail(*errors)

    global_certs = global_frontier["certificates"]
    parents = {c["id"]: c for c in global_certs}
    refined_ids: set[str] = set()
    rows: list[tuple[str, str, str, list[str]]] = []
    refined_meta: list[dict[str, Any]] = []

    for i, ref in enumerate(refs):
        if not isinstance(ref, Mapping):
            return _fail(f"REFINEMENT_{i}_INVALID")
        pid = ref.get("parent_certificate_id")
        mode = ref.get("mode")
        children = ref.get("children")
        receipt = ref.get("verification_receipt")
        if not isinstance(pid, str) or not pid or pid in refined_ids:
            return _fail("REFINED_PARENT_ID_INVALID_OR_DUPLICATE")
        if pid not in parents:
            return _fail(f"REFINED_PARENT_NOT_FOUND:{pid}")
        if mode not in ALLOWED_MODES:
            return _fail(f"REFINEMENT_MODE_INVALID:{pid}")
        if ref.get("independent_verified") is not True:
            return _fail(f"REFINEMENT_INDEPENDENT_VERIFICATION_REQUIRED:{pid}")
        if not isinstance(receipt, str) or not receipt:
            return _fail(f"REFINEMENT_RECEIPT_REQUIRED:{pid}")
        if not isinstance(children, list) or not children:
            return _fail(f"REFINEMENT_CHILDREN_REQUIRED:{pid}")

        parent = parents[pid]
        parent_targets = set(parent["target_predicates"])
        parent_requires = set(parent["requires"])
        seen_child_ids: set[str] = set()
        target_occurrences: list[str] = []
        requirement_occurrences: list[str] = []

        for j, child in enumerate(children):
            if not isinstance(child, Mapping):
                return _fail(f"REFINEMENT_CHILD_INVALID:{pid}:{j}")
            cid = child.get("id")
            targets = child.get("target_predicates")
            requires = child.get("requires")
            if not isinstance(cid, str) or not cid or cid in seen_child_ids:
                return _fail(f"REFINEMENT_CHILD_ID_INVALID_OR_DUPLICATE:{pid}")
            seen_child_ids.add(cid)
            if not _valid_str_list(targets, nonempty=True):
                return _fail(f"REFINEMENT_CHILD_TARGETS_INVALID:{pid}:{cid}")
            if not _valid_str_list(requires, nonempty=True):
                return _fail(f"REFINEMENT_CHILD_REQUIRES_INVALID:{pid}:{cid}")
            if any(t not in parent_targets for t in targets):
                return _fail(f"REFINEMENT_CHILD_TARGET_OUTSIDE_PARENT:{pid}:{cid}")
            target_occurrences.extend(targets)
            requirement_occurrences.extend(requires)
            for proposition in requires:
                rows.append(("REFINEMENT_CHILD_LEAF", cid, proposition, list(targets)))

        if set(target_occurrences) != parent_targets or len(target_occurrences) != len(set(target_occurrences)):
            return _fail(f"REFINEMENT_TARGET_PARTITION_NOT_EXACT:{pid}")

        if mode == "EXACT_REQUIREMENT_PARTITION":
            if (
                set(requirement_occurrences) != parent_requires
                or len(requirement_occurrences) != len(set(requirement_occurrences))
            ):
                return _fail(f"REFINEMENT_REQUIREMENT_PARTITION_NOT_EXACT:{pid}")
        elif mode == "INDEPENDENTLY_VERIFIED_SEMANTIC_REPLACEMENT":
            source_sha = ref.get("source_blob_sha")
            if (
                not isinstance(source_sha, str)
                or len(source_sha) != 40
                or any(ch not in "0123456789abcdef" for ch in source_sha.lower())
            ):
                return _fail(f"REFINEMENT_SOURCE_BLOB_SHA_REQUIRED:{pid}")

        refined_ids.add(pid)
        refined_meta.append({
            "parent_certificate_id": pid,
            "mode": mode,
            "parent_targets": sorted(parent_targets),
            "parent_requirements": sorted(parent_requires),
            "child_count": len(children),
            "verification_receipt": receipt,
        })

    for cert in global_certs:
        if cert["id"] in refined_ids:
            continue
        for proposition in cert["requires"]:
            rows.append(("GLOBAL_LEAF", cert["id"], proposition, list(cert["target_predicates"])))

    grouped: dict[str, dict[str, Any]] = {}
    for layer, cert_id, proposition, targets in rows:
        key = atom_id(proposition)
        entry = grouped.setdefault(
            key,
            {
                "atom_id": key,
                "proposition": proposition,
                "layers": set(),
                "certificate_ids": set(),
                "associated_target_predicates": set(),
                "occurrence_count": 0,
            },
        )
        if entry["proposition"] != proposition:
            return _fail("SHA256_COLLISION_DETECTED")
        entry["layers"].add(layer)
        entry["certificate_ids"].add(cert_id)
        entry["associated_target_predicates"].update(targets)
        entry["occurrence_count"] += 1

    atoms = []
    for key in sorted(grouped):
        x = grouped[key]
        atoms.append({
            "atom_id": x["atom_id"],
            "proposition": x["proposition"],
            "layers": sorted(x["layers"]),
            "certificate_ids": sorted(x["certificate_ids"]),
            "associated_target_predicates": sorted(x["associated_target_predicates"]),
            "associated_target_count": len(x["associated_target_predicates"]),
            "occurrence_count": x["occurrence_count"],
        })

    total_occurrences = len(rows)
    return {
        "schema": SCHEMA,
        "status": "PASS__GENERIC_VERIFIED_REFINEMENT_PROOF_ATOM_BASIS_COMPILED__ZERO_CREDIT",
        "errors": [],
        "global_unresolved_predicate_count": len(global_frontier["unresolved_predicates"]),
        "global_certificate_count": len(global_certs),
        "refined_parent_count": len(refined_ids),
        "refined_parents": sorted(refined_meta, key=lambda x: x["parent_certificate_id"]),
        "leaf_requirement_occurrence_count": total_occurrences,
        "leaf_atom_count": len(atoms),
        "exact_duplicate_savings": total_occurrences - len(atoms),
        "max_structural_target_fanout": max((x["associated_target_count"] for x in atoms), default=0),
        "atoms": atoms,
        "rules": [
            "ATOM_ID_PRESERVES_PA1_SHA256_OF_EXACT_UTF8_PROPOSITION_LITERAL",
            "DEDUPLICATE_ONLY_BYTE_IDENTICAL_PROPOSITION_LITERALS",
            "REFINED_PARENT_TARGETS_MUST_BE_EXACTLY_PARTITIONED",
            "EXACT_REQUIREMENT_PARTITION_MODE_MUST_PARTITION_PARENT_REQUIREMENTS_EXACTLY",
            "SEMANTIC_REPLACEMENT_MODE_REQUIRES_INDEPENDENT_VERIFICATION_RECEIPT",
            "NO_UNVERIFIED_REFINEMENT_CONSUMPTION",
            "NO_ATOM_OUTPUT_ALONE_GRANTS_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT",
        ],
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    frontier = json.loads(
        (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(
            encoding="utf-8"
        )
    )
    overlay = json.loads(
        (ROOT / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text(
            encoding="utf-8"
        )
    )
    out = compile_basis(frontier, overlay)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
