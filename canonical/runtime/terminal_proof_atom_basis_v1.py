"""Exact primitive proof-atom basis compiler for the active terminal frontier.

This compiler refines scheduling obligations below certificate granularity without
inventing semantic equivalence. It replaces the coarse matched-scope parent
certificate with its independently verified 11-child refinement, then
canonicalizes exact requirement strings into reusable proof atoms.

V1 deduplicates only byte-identical requirement strings. Any future semantic
merge requires an independently verified equivalence receipt and a new version.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_PROOF_ATOM_BASIS_V1"
ROOT = Path(__file__).resolve().parents[2]

FRONTIER = ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"
SUBFRONTIER = ROOT / "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json"
ACTIVATION = ROOT / "canonical/governance/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_ACTIVATION_V1.json"

PARENT_ID = "MATCHED_SCOPE_BINDING_CERTIFICATE"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "proof_atom_count": 0,
        "effective_certificate_count": 0,
        "covered_predicate_count": 0,
        "uncovered_predicates": [],
        "proof_atoms": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _atom_id(requirement: str) -> str:
    payload = ("PROJECT_BRAIN_PROOF_ATOM_V1\0" + requirement).encode("utf-8")
    return "PA1_" + hashlib.sha256(payload).hexdigest()[:24]


def compile_basis(
    frontier: Mapping[str, Any],
    subfrontier: Mapping[str, Any],
    activation: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    unresolved = frontier.get("unresolved_predicates")
    certs = frontier.get("certificates")
    child_unresolved = subfrontier.get("unresolved_predicates")
    child_certs = subfrontier.get("certificates")

    if not isinstance(unresolved, list) or not unresolved or len(unresolved) != len(set(unresolved)):
        errors.append("FRONTIER_UNRESOLVED_INVALID")
    if not isinstance(certs, list) or not certs:
        errors.append("FRONTIER_CERTIFICATES_INVALID")
    if not isinstance(child_unresolved, list) or not child_unresolved:
        errors.append("SUBFRONTIER_UNRESOLVED_INVALID")
    if not isinstance(child_certs, list) or not child_certs:
        errors.append("SUBFRONTIER_CERTIFICATES_INVALID")
    if not str(activation.get("status", "")).startswith("ACTIVE_INDEPENDENT_PASS"):
        errors.append("HIERARCHICAL_REFINEMENT_NOT_ACTIVE_INDEPENDENT_PASS")
    if errors:
        return _fail(*errors)

    parent_rows = [c for c in certs if isinstance(c, Mapping) and c.get("id") == PARENT_ID]
    if len(parent_rows) != 1:
        return _fail("MATCHED_SCOPE_PARENT_NOT_EXACTLY_ONE")
    parent = parent_rows[0]
    parent_targets = parent.get("target_predicates")
    if not isinstance(parent_targets, list) or set(parent_targets) != set(child_unresolved):
        return _fail("CHILD_TARGET_SET_NOT_EXACT_PARENT_PARTITION")

    seen_child_targets: set[str] = set()
    for i, cert in enumerate(child_certs):
        if not isinstance(cert, Mapping):
            errors.append(f"CHILD_CERT_{i}_INVALID")
            continue
        targets = cert.get("target_predicates")
        requires = cert.get("requires")
        if not isinstance(targets, list) or len(targets) != 1:
            errors.append(f"CHILD_CERT_{i}_TARGET_ARITY_NOT_ONE")
            continue
        target = targets[0]
        if target not in set(parent_targets):
            errors.append(f"CHILD_CERT_TARGET_OUTSIDE_PARENT:{target}")
        if target in seen_child_targets:
            errors.append(f"CHILD_CERT_TARGET_DUPLICATE:{target}")
        seen_child_targets.add(target)
        if not isinstance(requires, list) or len(requires) != 2:
            errors.append(f"CHILD_CERT_REQUIRES_NOT_TWO:{target}")
        elif any(not isinstance(r, str) or not r.startswith(target + "::") for r in requires):
            errors.append(f"CHILD_CERT_REQUIREMENT_NOT_TARGET_SCOPED:{target}")

    if seen_child_targets != set(parent_targets):
        errors.append("CHILD_CERTIFICATES_NOT_LOSSLESS_PARENT_PARTITION")
    if errors:
        return _fail(*errors)

    effective = [c for c in certs if isinstance(c, Mapping) and c.get("id") != PARENT_ID] + list(child_certs)

    atoms: dict[str, dict[str, Any]] = {}
    covered: set[str] = set()
    raw_requirement_count = 0

    for i, cert in enumerate(effective):
        cid = cert.get("id")
        targets = cert.get("target_predicates")
        requires = cert.get("requires")
        if not isinstance(cid, str) or not cid:
            errors.append(f"EFFECTIVE_CERT_{i}_ID_INVALID")
            continue
        if not isinstance(targets, list) or not targets or any(t not in set(unresolved) for t in targets):
            errors.append(f"EFFECTIVE_CERT_TARGETS_INVALID:{cid}")
            continue
        if not isinstance(requires, list) or not requires or any(not isinstance(r, str) or not r for r in requires):
            errors.append(f"EFFECTIVE_CERT_REQUIRES_INVALID:{cid}")
            continue
        covered.update(targets)
        for requirement in requires:
            raw_requirement_count += 1
            aid = _atom_id(requirement)
            row = atoms.setdefault(
                aid,
                {
                    "proof_atom_id": aid,
                    "requirement": requirement,
                    "consumer_certificate_ids": set(),
                    "target_predicates": set(),
                },
            )
            if row["requirement"] != requirement:
                errors.append(f"HASH_COLLISION:{aid}")
                continue
            row["consumer_certificate_ids"].add(cid)
            row["target_predicates"].update(targets)

    if errors:
        return _fail(*errors)

    atom_rows = []
    for aid in sorted(atoms):
        row = atoms[aid]
        atom_rows.append(
            {
                "proof_atom_id": aid,
                "requirement": row["requirement"],
                "consumer_certificate_ids": sorted(row["consumer_certificate_ids"]),
                "target_predicates": sorted(row["target_predicates"]),
                "target_fanout_count": len(row["target_predicates"]),
                "certificate_fanout_count": len(row["consumer_certificate_ids"]),
            }
        )

    unresolved_set = set(unresolved)
    uncovered = sorted(unresolved_set - covered)
    status = "PASS__EXACT_PRIMITIVE_PROOF_ATOM_BASIS_COMPILED__ZERO_CREDIT"
    if uncovered:
        status = "FAIL_CLOSED__PREDICATE_COVERAGE_INCOMPLETE"

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": [],
        "source_frontier": "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
        "source_subfrontier": "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json",
        "source_activation": "canonical/governance/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_ACTIVATION_V1.json",
        "unresolved_predicate_count": len(unresolved_set),
        "effective_certificate_count": len(effective),
        "raw_requirement_occurrence_count": raw_requirement_count,
        "proof_atom_count": len(atom_rows),
        "exact_string_dedup_savings": raw_requirement_count - len(atom_rows),
        "covered_predicate_count": len(covered & unresolved_set),
        "uncovered_predicates": uncovered,
        "proof_atoms": atom_rows,
        "rule": (
            "V1_DEDUPLICATES_ONLY_BYTE_IDENTICAL_REQUIREMENT_STRINGS__"
            "NO_SEMANTIC_OR_ANALOGICAL_MERGE__"
            "MATCHED_SCOPE_PARENT_IS_REPLACED_ONLY_BY_ACTIVE_INDEPENDENTLY_VERIFIED_CHILD_REFINEMENT__"
            "PROOF_ATOM_COMPILATION_IS_SCHEDULING_STRUCTURE_NOT_ACCEPTANCE_PROOF"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    frontier = json.loads(FRONTIER.read_text(encoding="utf-8"))
    subfrontier = json.loads(SUBFRONTIER.read_text(encoding="utf-8"))
    activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
    out = compile_basis(frontier, subfrontier, activation)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
