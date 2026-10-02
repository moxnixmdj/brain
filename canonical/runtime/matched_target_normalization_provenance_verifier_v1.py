"""Fail-closed verifier for matched-target normalization provenance.

This verifier does not decide semantic equivalence. It proves the narrower claim
that every normalized target atom and metric requirement is explicitly bound to
an exact scalar literal in the frozen family protocol or atomic predicate row,
and that the candidate/provenance cover one another exactly.

Any stronger semantic implication still requires the separate protocol
implication algebra and verified implication edges.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_MATCHED_TARGET_NORMALIZATION_PROVENANCE_VERIFIER_V1"
ALLOWED_SOURCE_DOCS = {"protocol", "predicate"}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "verified_target_count": 0,
        "verified_atom_count": 0,
        "verified_metric_requirement_count": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _strings(value: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(value, str):
        out.add(value)
    elif isinstance(value, Mapping):
        for v in value.values():
            out.update(_strings(v))
    elif isinstance(value, list):
        for v in value:
            out.update(_strings(v))
    return out


def evaluate(
    protocols: Mapping[str, Any],
    registry: Mapping[str, Any],
    candidate: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    protocol_rows = protocols.get("protocols")
    predicate_rows = registry.get("predicates")
    targets = candidate.get("targets")
    prov_targets = provenance.get("targets")
    if not isinstance(protocol_rows, list):
        return _fail("PROTOCOLS_NOT_LIST")
    if not isinstance(predicate_rows, list):
        return _fail("PREDICATES_NOT_LIST")
    if not isinstance(targets, list) or not isinstance(prov_targets, list):
        return _fail("TARGETS_NOT_LIST")

    protocols_by_family = {
        r.get("family"): r
        for r in protocol_rows
        if isinstance(r, Mapping) and isinstance(r.get("family"), str)
    }
    predicates_by_id = {
        r.get("id"): r
        for r in predicate_rows
        if isinstance(r, Mapping) and isinstance(r.get("id"), str)
    }

    candidate_by_id: dict[str, Mapping[str, Any]] = {}
    for row in targets:
        if not isinstance(row, Mapping) or not isinstance(row.get("predicate_id"), str):
            return _fail("CANDIDATE_TARGET_INVALID")
        pid = row["predicate_id"]
        if pid in candidate_by_id:
            return _fail(f"DUPLICATE_CANDIDATE_TARGET:{pid}")
        candidate_by_id[pid] = row

    provenance_by_id: dict[str, Mapping[str, Any]] = {}
    for row in prov_targets:
        if not isinstance(row, Mapping) or not isinstance(row.get("predicate_id"), str):
            return _fail("PROVENANCE_TARGET_INVALID")
        pid = row["predicate_id"]
        if pid in provenance_by_id:
            return _fail(f"DUPLICATE_PROVENANCE_TARGET:{pid}")
        provenance_by_id[pid] = row

    if set(candidate_by_id) != set(provenance_by_id):
        return _fail("CANDIDATE_PROVENANCE_TARGET_SET_MISMATCH")

    errors: list[str] = []
    atom_count = 0
    metric_count = 0
    target_results = []

    for pid in sorted(candidate_by_id):
        cand = candidate_by_id[pid]
        prov = provenance_by_id[pid]
        family = cand.get("family")
        if prov.get("family") != family:
            errors.append(f"FAMILY_MISMATCH:{pid}")
            continue
        protocol = protocols_by_family.get(family)
        predicate = predicates_by_id.get(pid)
        if protocol is None or predicate is None:
            errors.append(f"SOURCE_ROW_MISSING:{pid}")
            continue

        atoms = cand.get("required_atoms")
        atom_sources = prov.get("atom_sources")
        if not isinstance(atoms, list) or not isinstance(atom_sources, list):
            errors.append(f"ATOM_SHAPE_INVALID:{pid}")
            continue
        if any(not isinstance(x, str) or not x for x in atoms):
            errors.append(f"ATOM_ID_INVALID:{pid}")
            continue
        source_by_atom = {}
        for source in atom_sources:
            if not isinstance(source, Mapping) or not isinstance(source.get("atom"), str):
                errors.append(f"ATOM_SOURCE_INVALID:{pid}")
                continue
            atom = source["atom"]
            if atom in source_by_atom:
                errors.append(f"DUPLICATE_ATOM_SOURCE:{pid}:{atom}")
                continue
            source_by_atom[atom] = source
        if set(atoms) != set(source_by_atom):
            errors.append(f"ATOM_SOURCE_COVERAGE_MISMATCH:{pid}")
            continue

        atom_errors = []
        for atom in atoms:
            src = source_by_atom[atom]
            refs = src.get("sources")
            if not isinstance(refs, list) or not refs:
                atom_errors.append(f"NO_SOURCES:{atom}")
                continue
            for ref in refs:
                if not isinstance(ref, Mapping):
                    atom_errors.append(f"SOURCE_INVALID:{atom}")
                    continue
                doc = ref.get("document")
                literal = ref.get("literal")
                if doc not in ALLOWED_SOURCE_DOCS or not isinstance(literal, str) or not literal:
                    atom_errors.append(f"SOURCE_REF_INVALID:{atom}")
                    continue
                source_strings = _strings(protocol if doc == "protocol" else predicate)
                if literal not in source_strings:
                    atom_errors.append(f"LITERAL_NOT_FOUND:{atom}:{doc}:{literal}")
            if not atom_errors:
                atom_count += 1

        metrics = cand.get("metric_requirements", [])
        metric_sources = prov.get("metric_requirement_sources", [])
        if not isinstance(metrics, list) or not isinstance(metric_sources, list):
            errors.append(f"METRIC_SHAPE_INVALID:{pid}")
            continue
        ms_by_name = {}
        for source in metric_sources:
            if not isinstance(source, Mapping) or not isinstance(source.get("metric"), str):
                errors.append(f"METRIC_SOURCE_INVALID:{pid}")
                continue
            name = source["metric"]
            if name in ms_by_name:
                errors.append(f"DUPLICATE_METRIC_SOURCE:{pid}:{name}")
                continue
            ms_by_name[name] = source
        metric_names = {
            m.get("metric")
            for m in metrics
            if isinstance(m, Mapping) and isinstance(m.get("metric"), str)
        }
        if len(metric_names) != len(metrics) or metric_names != set(ms_by_name):
            errors.append(f"METRIC_SOURCE_COVERAGE_MISMATCH:{pid}")
            continue
        metric_errors = []
        for metric in metrics:
            name = metric["metric"]
            src = ms_by_name[name]
            if src.get("direction") != metric.get("direction") or src.get("threshold") != metric.get("threshold"):
                metric_errors.append(f"METRIC_REQUIREMENT_MISMATCH:{name}")
                continue
            refs = src.get("sources")
            if not isinstance(refs, list) or not refs:
                metric_errors.append(f"METRIC_NO_SOURCES:{name}")
                continue
            for ref in refs:
                if not isinstance(ref, Mapping):
                    metric_errors.append(f"METRIC_SOURCE_INVALID:{name}")
                    continue
                doc = ref.get("document")
                literal = ref.get("literal")
                if doc not in ALLOWED_SOURCE_DOCS or not isinstance(literal, str) or not literal:
                    metric_errors.append(f"METRIC_SOURCE_REF_INVALID:{name}")
                    continue
                source_strings = _strings(protocol if doc == "protocol" else predicate)
                if literal not in source_strings:
                    metric_errors.append(f"METRIC_LITERAL_NOT_FOUND:{name}:{doc}:{literal}")
            if not metric_errors:
                metric_count += 1

        if atom_errors:
            errors.extend(f"{pid}:{e}" for e in atom_errors)
        if metric_errors:
            errors.extend(f"{pid}:{e}" for e in metric_errors)

        target_results.append({
            "predicate_id": pid,
            "family": family,
            "atom_count": len(atoms),
            "metric_requirement_count": len(metrics),
            "source_literal_binding_pass": not atom_errors and not metric_errors,
        })

    if errors:
        return {
            **_fail(*errors),
            "target_results": target_results,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_TARGET_ATOMS_AND_METRICS_BOUND_TO_EXACT_FROZEN_SOURCE_LITERALS",
        "errors": [],
        "verified_target_count": len(candidate_by_id),
        "verified_atom_count": atom_count,
        "verified_metric_requirement_count": metric_count,
        "target_results": target_results,
        "semantic_implication_verified": False,
        "rule": (
            "THIS_VERIFIER_PROVES_EXACT_SOURCE_LITERAL_PROVENANCE_AND_COVERAGE_ONLY__"
            "SEMANTIC_EQUIVALENCE_OR_STRONGER_SCOPE_REMAINS_A_SEPARATE_FAIL_CLOSED_PROOF"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
