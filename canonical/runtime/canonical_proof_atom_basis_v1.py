"""Compile the active terminal proof frontier into exact canonical proof atoms.

This module is deliberately conservative.  It does not infer semantic
equivalence from names, prefixes, prose, families, or similar-looking
requirements.  Two proof obligations deduplicate iff their proposition
literals are byte-for-byte identical UTF-8 strings.

The active matched-scope parent certificate has a separately verified
lossless target-specific refinement.  Therefore its two coarse parent
requirements are retained as lineage metadata but are not emitted as
executable leaf proof atoms when the verified child subfrontier is supplied.

The output is scheduling structure only.  It grants zero acceptance,
capability, family, execution, or promotion credit.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CANONICAL_PROOF_ATOM_BASIS_V1"
ROOT = Path(__file__).resolve().parents[2]
MATCHED_PARENT_ID = "MATCHED_SCOPE_BINDING_CERTIFICATE"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "leaf_atom_count": 0,
        "atoms": [],
        "refined_parent_requirements": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def atom_id(proposition: str) -> str:
    digest = hashlib.sha256(proposition.encode("utf-8")).hexdigest()
    return f"PA1:{digest}"


def _validate_frontier(doc: Mapping[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc, Mapping):
        return [f"{label}_NOT_OBJECT"]
    unresolved = doc.get("unresolved_predicates")
    certs = doc.get("certificates")
    if (
        not isinstance(unresolved, list)
        or any(not isinstance(x, str) or not x for x in unresolved)
        or len(set(unresolved)) != len(unresolved)
    ):
        errors.append(f"{label}_UNRESOLVED_INVALID")
        unresolved_set: set[str] = set()
    else:
        unresolved_set = set(unresolved)
    if not isinstance(certs, list):
        errors.append(f"{label}_CERTIFICATES_INVALID")
        return errors
    seen_ids: set[str] = set()
    for i, cert in enumerate(certs):
        if not isinstance(cert, Mapping):
            errors.append(f"{label}_CERT_{i}_NOT_OBJECT")
            continue
        cid = cert.get("id")
        targets = cert.get("target_predicates")
        requires = cert.get("requires")
        if not isinstance(cid, str) or not cid or cid in seen_ids:
            errors.append(f"{label}_CERT_ID_INVALID_OR_DUPLICATE")
        else:
            seen_ids.add(cid)
        if (
            not isinstance(targets, list)
            or not targets
            or any(not isinstance(x, str) or not x for x in targets)
            or len(set(targets)) != len(targets)
        ):
            errors.append(f"{label}_TARGETS_INVALID:{cid}")
        elif unresolved_set and any(x not in unresolved_set for x in targets):
            errors.append(f"{label}_TARGET_OUTSIDE_FRONTIER:{cid}")
        if (
            not isinstance(requires, list)
            or not requires
            or any(not isinstance(x, str) or not x for x in requires)
            or len(set(requires)) != len(requires)
        ):
            errors.append(f"{label}_REQUIRES_INVALID:{cid}")
    return errors


def compile_basis(
    global_frontier: Mapping[str, Any],
    matched_subfrontier: Mapping[str, Any],
) -> dict[str, Any]:
    errors = _validate_frontier(global_frontier, "GLOBAL")
    errors.extend(_validate_frontier(matched_subfrontier, "MATCHED"))
    if errors:
        return _fail(*errors)

    global_certs = global_frontier["certificates"]
    child_certs = matched_subfrontier["certificates"]

    parent_rows = [c for c in global_certs if c.get("id") == MATCHED_PARENT_ID]
    if len(parent_rows) != 1:
        return _fail("MATCHED_PARENT_CERTIFICATE_NOT_EXACTLY_ONE")
    parent = parent_rows[0]

    parent_targets = set(parent["target_predicates"])
    child_unresolved = set(matched_subfrontier["unresolved_predicates"])
    if child_unresolved != parent_targets:
        return _fail("MATCHED_CHILD_TARGET_SET_NOT_LOSSLESS")

    child_target_occurrences: defaultdict[str, int] = defaultdict(int)
    for cert in child_certs:
        targets = cert["target_predicates"]
        if len(targets) != 1:
            return _fail("MATCHED_CHILD_NOT_SINGLE_TARGET")
        child_target_occurrences[targets[0]] += 1
        if len(cert["requires"]) != 2:
            return _fail("MATCHED_CHILD_NOT_TWO_REQUIREMENTS")
    if set(child_target_occurrences) != parent_targets or any(
        n != 1 for n in child_target_occurrences.values()
    ):
        return _fail("MATCHED_CHILD_PARTITION_NOT_ONE_TO_ONE")

    refined_parent_requirements = sorted(parent["requires"])

    rows: list[tuple[str, str, str, list[str]]] = []
    for cert in global_certs:
        if cert["id"] == MATCHED_PARENT_ID:
            continue
        for proposition in cert["requires"]:
            rows.append(
                ("GLOBAL_LEAF", cert["id"], proposition, list(cert["target_predicates"]))
            )
    for cert in child_certs:
        for proposition in cert["requires"]:
            rows.append(
                ("MATCHED_CHILD_LEAF", cert["id"], proposition, list(cert["target_predicates"]))
            )

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
        atoms.append(
            {
                "atom_id": x["atom_id"],
                "proposition": x["proposition"],
                "layers": sorted(x["layers"]),
                "certificate_ids": sorted(x["certificate_ids"]),
                "associated_target_predicates": sorted(x["associated_target_predicates"]),
                "associated_target_count": len(x["associated_target_predicates"]),
                "occurrence_count": x["occurrence_count"],
            }
        )

    total_occurrences = len(rows)
    exact_duplicate_savings = total_occurrences - len(atoms)
    max_fanout = max((x["associated_target_count"] for x in atoms), default=0)

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_CANONICAL_PROOF_ATOM_BASIS_COMPILED__ZERO_CREDIT",
        "errors": [],
        "global_unresolved_predicate_count": len(global_frontier["unresolved_predicates"]),
        "global_certificate_count": len(global_certs),
        "matched_child_target_count": len(parent_targets),
        "matched_child_certificate_count": len(child_certs),
        "refined_parent_certificate_id": MATCHED_PARENT_ID,
        "refined_parent_requirements": refined_parent_requirements,
        "leaf_requirement_occurrence_count": total_occurrences,
        "leaf_atom_count": len(atoms),
        "exact_duplicate_savings": exact_duplicate_savings,
        "max_structural_target_fanout": max_fanout,
        "atoms": atoms,
        "rules": [
            "ATOM_ID_IS_SHA256_OF_EXACT_UTF8_PROPOSITION_LITERAL",
            "DEDUPLICATE_ONLY_BYTE_IDENTICAL_PROPOSITION_LITERALS",
            "NO_NAME_PROSE_PREFIX_FAMILY_OR_ANALOGY_BASED_EQUIVALENCE",
            "MATCHED_PARENT_COARSE_REQUIREMENTS_ARE_LINEAGE_ONLY_AFTER_VERIFIED_LOSSLESS_CHILD_REFINEMENT",
            "ASSOCIATED_TARGETS_ARE_STRUCTURAL_CERTIFICATE_MEMBERSHIP_NOT_ACCEPTANCE_IMPLICATION",
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
    global_frontier = json.loads(
        (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(
            encoding="utf-8"
        )
    )
    matched_subfrontier = json.loads(
        (ROOT / "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json").read_text(
            encoding="utf-8"
        )
    )
    out = compile_basis(global_frontier, matched_subfrontier)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
