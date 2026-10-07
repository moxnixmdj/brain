"""Finance source-coverage terminal gate.

This wrapper closes a concrete omission hole in the Brain-owned finance judgment
route. A FINANCE conclusion is not terminally accepted unless:

1. the exact source package is bound,
2. every source atom is covered by at least two independent semantic mechanisms,
3. the mechanisms agree exactly on span, class, semantic fingerprint and
   decision relevance,
4. ambiguity or disagreement fails closed,
5. every decision-relevant semantic unit is bound to typed evidence, and
6. every such evidence item actually contributes to the recomputed Brain decision.

This is a coverage/admission mechanism, not an arbitrary natural-language
semantic oracle. Unresolved semantics remain unresolved.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence

from canonical.runtime.judgment_control_envelope_v1 import configured_terminal_decision
from canonical.runtime.source_contract_compiler import (
    DISPOSITIONS,
    atomize_source,
    reconstruct_source,
    semantic_unit_id,
    validate_semantic_consensus,
)

SCHEMA = "PROJECT_BRAIN_FINANCE_SOURCE_COVERAGE_TERMINAL_GATE_V1"
CERT_SCHEMA = "PROJECT_BRAIN_FINANCE_SOURCE_COVERAGE_CERTIFICATE_V1"
FINANCE_SUPERVISORY = "SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE"
FINANCE_DOCUMENT = "DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"
FINANCE_LEAVES = {FINANCE_SUPERVISORY, FINANCE_DOCUMENT}
OPERATIVE_KINDS = {"BEHAVIOR", "ENVIRONMENT", "RESOURCE", "SOURCE_BOUNDARY", "EVALUATION"}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_ws_positions(text: str) -> set[int]:
    return {i for i, ch in enumerate(text) if not ch.isspace()}


def _source_package_from_bundle(bundle: Any) -> dict[str, str]:
    if not isinstance(bundle, Mapping):
        return {}
    out: dict[str, str] = {}
    source_id = str(bundle.get("source_id") or "").strip()
    source_text = bundle.get("source_text")
    if source_id and isinstance(source_text, str) and source_text:
        out[source_id] = source_text

    rows = bundle.get("source_package")
    if rows is None:
        return out
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return {}
    for row in rows:
        if not isinstance(row, Mapping):
            return {}
        sid = str(row.get("source_id") or "").strip()
        text = row.get("source_text")
        if not sid or not isinstance(text, str) or not text:
            return {}
        if sid in out and out[sid] != text:
            return {}
        out[sid] = text
    return out


def _unit_signature(unit: Mapping[str, Any], atom_text: str) -> tuple[Any, ...] | None:
    start = unit.get("start")
    end = unit.get("end")
    kind = unit.get("kind")
    fingerprint = unit.get("semantic_fingerprint")
    relevant = unit.get("decision_relevant")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end > len(atom_text)
        or kind not in DISPOSITIONS
        or not _nonempty(fingerprint)
        or not isinstance(relevant, bool)
    ):
        return None
    expected_hash = sha256(atom_text[start:end].encode("utf-8")).hexdigest()
    if unit.get("text_sha256") != expected_hash:
        return None
    if not _nonempty(unit.get("rationale")):
        return None
    if relevant is False and not _nonempty(unit.get("decision_relevance_rationale")):
        return None
    return (start, end, str(kind), str(fingerprint).strip(), relevant)


def _full_atom_consensus_errors(
    *,
    source_text: str,
    atoms: Sequence[Any],
    extractor_units: Mapping[str, Sequence[Mapping[str, Any]]],
    extractor_groups: Mapping[str, str],
    requirements: Sequence[Mapping[str, Any]],
) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    by_atom = {a.atom_id: a for a in atoms}
    if not isinstance(extractor_units, Mapping) or len(extractor_units) < 2:
        return ["INDEPENDENT_SEMANTIC_EXTRACTORS_LT_2"], set()
    if not isinstance(extractor_groups, Mapping):
        return ["EXTRACTOR_GROUPS_REQUIRED"], set()

    groups: set[str] = set()
    normalized: dict[str, dict[str, list[tuple[Any, ...]]]] = {}
    raw_units: dict[str, dict[tuple[str, int, int], Mapping[str, Any]]] = {}

    for extractor_id, units in extractor_units.items():
        if not _nonempty(extractor_id):
            errors.append("EXTRACTOR_ID_INVALID")
            continue
        group = extractor_groups.get(extractor_id)
        if not _nonempty(group):
            errors.append(f"EXTRACTOR_INDEPENDENCE_GROUP_MISSING:{extractor_id}")
            continue
        groups.add(str(group).strip())
        if not isinstance(units, Sequence) or isinstance(units, (str, bytes)):
            errors.append(f"EXTRACTOR_UNITS_INVALID:{extractor_id}")
            continue

        per_atom: dict[str, list[tuple[Any, ...]]] = {}
        raw_map: dict[tuple[str, int, int], Mapping[str, Any]] = {}
        for i, unit in enumerate(units):
            if not isinstance(unit, Mapping):
                errors.append(f"SEMANTIC_UNIT_INVALID:{extractor_id}:{i}")
                continue
            aid = unit.get("atom_id")
            atom = by_atom.get(aid)
            if atom is None:
                errors.append(f"SEMANTIC_UNIT_UNKNOWN_ATOM:{extractor_id}:{aid}")
                continue
            sig = _unit_signature(unit, atom.text)
            if sig is None:
                errors.append(f"SEMANTIC_UNIT_CONTRACT_INVALID:{extractor_id}:{aid}:{i}")
                continue
            start, end, *_ = sig
            key = (str(aid), int(start), int(end))
            if key in raw_map:
                errors.append(f"SEMANTIC_UNIT_DUPLICATE:{extractor_id}:{aid}:{start}:{end}")
                continue
            raw_map[key] = unit
            per_atom.setdefault(str(aid), []).append(sig)

        for aid, atom in by_atom.items():
            rows = sorted(per_atom.get(aid, []))
            covered: set[int] = set()
            previous_end = -1
            for row in rows:
                start, end = row[0], row[1]
                if start < previous_end:
                    errors.append(f"SEMANTIC_SPAN_OVERLAP:{extractor_id}:{aid}")
                previous_end = max(previous_end, end)
                covered.update(range(start, end))
            if _non_ws_positions(atom.text) - covered:
                errors.append(f"FULL_SOURCE_ATOM_UNCOVERED:{extractor_id}:{aid}")
        normalized[str(extractor_id)] = {
            aid: sorted(rows) for aid, rows in per_atom.items()
        }
        raw_units[str(extractor_id)] = raw_map

    if len(groups) < 2:
        errors.append("INDEPENDENT_SEMANTIC_GROUPS_LT_2")

    valid_ids = sorted(normalized)
    if len(valid_ids) < 2:
        errors.append("VALID_SEMANTIC_EXTRACTORS_LT_2")
        return sorted(set(errors)), set()

    reference_id = valid_ids[0]
    reference = normalized[reference_id]
    for aid in by_atom:
        ref = reference.get(aid, [])
        for extractor_id in valid_ids[1:]:
            if normalized[extractor_id].get(aid, []) != ref:
                errors.append(f"FULL_SEMANTIC_EXTRACTOR_DISAGREEMENT:{aid}")

    requirement_by_unit: dict[str, list[Mapping[str, Any]]] = {}
    for i, req in enumerate(requirements):
        if not isinstance(req, Mapping):
            errors.append(f"REQUIREMENT_INVALID:{i}")
            continue
        rid = req.get("id")
        if not _nonempty(rid):
            errors.append(f"REQUIREMENT_ID_INVALID:{i}")
            continue
        refs = req.get("source_semantic_unit_ids")
        evidence_ids = req.get("evidence_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"REQUIREMENT_WITHOUT_SEMANTIC_UNITS:{rid}")
            continue
        if not isinstance(evidence_ids, list) or any(not _nonempty(x) for x in evidence_ids):
            errors.append(f"REQUIREMENT_EVIDENCE_IDS_INVALID:{rid}")
            continue
        for sid in refs:
            if not _nonempty(sid):
                errors.append(f"REQUIREMENT_SEMANTIC_UNIT_ID_INVALID:{rid}")
                continue
            requirement_by_unit.setdefault(str(sid), []).append(req)

    relevant_evidence: set[str] = set()
    ref_raw = raw_units.get(reference_id, {})
    for aid, atom in by_atom.items():
        for sig in reference.get(aid, []):
            start, end, kind, _fingerprint, relevant = sig
            sid = semantic_unit_id(aid, start, end)
            rows = requirement_by_unit.get(sid, [])
            if kind == "AMBIGUOUS":
                errors.append(f"OPEN_SPECIFICATION_HOLE:{sid}")
            if kind in OPERATIVE_KINDS and not rows:
                errors.append(f"OPERATIVE_SEMANTIC_UNIT_WITHOUT_REQUIREMENT:{sid}")
            if relevant:
                if not rows:
                    errors.append(f"DECISION_RELEVANT_UNIT_WITHOUT_REQUIREMENT:{sid}")
                    continue
                for req in rows:
                    relevant_evidence.update(
                        str(x) for x in req.get("evidence_ids", []) if _nonempty(x)
                    )

            unit = ref_raw.get((aid, start, end))
            if unit is None:
                errors.append(f"REFERENCE_UNIT_MISSING:{sid}")

    risky_unit_ids: set[str] = set()
    for aid, atom in by_atom.items():
        if not (atom.normative or atom.high_risk):
            continue
        for sig in reference.get(aid, []):
            risky_unit_ids.add(semantic_unit_id(aid, sig[0], sig[1]))
    risky_requirements: list[dict[str, Any]] = []
    for req in requirements:
        if not isinstance(req, Mapping):
            continue
        refs = [
            str(x) for x in (req.get("source_semantic_unit_ids") or [])
            if str(x) in risky_unit_ids
        ]
        if refs:
            row = dict(req)
            row["source_semantic_unit_ids"] = refs
            risky_requirements.append(row)

    risky_errors = validate_semantic_consensus(
        source_text=source_text,
        atoms=atoms,
        extractor_units=extractor_units,
        requirements=risky_requirements,
    )
    errors.extend(risky_errors)
    return sorted(set(errors)), relevant_evidence


def verify_coverage_certificate(
    *,
    proposal: Any,
    proof_bundle: Any,
    certificate: Any,
) -> dict[str, Any]:
    errors: list[str] = []
    relevant_evidence: set[str] = set()

    if not isinstance(proposal, Mapping):
        return {"pass": False, "errors": ["PROPOSAL_NOT_OBJECT"], "relevant_evidence_ids": []}
    leaf_id = str(proposal.get("leaf_id") or "")
    if leaf_id not in FINANCE_LEAVES:
        errors.append("FINANCE_LEAF_ID_INVALID")

    if not isinstance(certificate, Mapping):
        return {"pass": False, "errors": ["COVERAGE_CERTIFICATE_NOT_OBJECT"], "relevant_evidence_ids": []}
    if certificate.get("schema") != CERT_SCHEMA:
        errors.append("COVERAGE_CERTIFICATE_SCHEMA_INVALID")
    if certificate.get("leaf_id") != leaf_id:
        errors.append("COVERAGE_CERTIFICATE_LEAF_MISMATCH")

    bound_package = _source_package_from_bundle(proof_bundle)
    if not bound_package:
        errors.append("PROOF_BUNDLE_SOURCE_PACKAGE_INVALID")

    sources = certificate.get("sources")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)) or not sources:
        errors.append("COVERAGE_CERTIFICATE_SOURCES_INVALID")
        sources = []

    cert_package: dict[str, str] = {}
    for i, row in enumerate(sources):
        if not isinstance(row, Mapping):
            errors.append(f"COVERAGE_SOURCE_INVALID:{i}")
            continue
        sid = str(row.get("source_id") or "").strip()
        text = row.get("source_text")
        if not sid or not isinstance(text, str) or not text:
            errors.append(f"COVERAGE_SOURCE_ID_OR_TEXT_INVALID:{i}")
            continue
        if sid in cert_package:
            errors.append(f"COVERAGE_SOURCE_DUPLICATE:{sid}")
            continue
        cert_package[sid] = text
        if row.get("source_sha256") != sha256(text.encode("utf-8")).hexdigest():
            errors.append(f"COVERAGE_SOURCE_SHA256_MISMATCH:{sid}")

        atoms = atomize_source(text, sid)
        if reconstruct_source(atoms) != text:
            errors.append(f"COVERAGE_SOURCE_RECONSTRUCTION_MISMATCH:{sid}")
            continue
        per_errors, per_evidence = _full_atom_consensus_errors(
            source_text=text,
            atoms=atoms,
            extractor_units=row.get("extractor_units", {}),
            extractor_groups=row.get("extractor_groups", {}),
            requirements=row.get("requirements", []),
        )
        errors.extend(f"{sid}:{x}" for x in per_errors)
        relevant_evidence.update(per_evidence)

    if bound_package and cert_package != bound_package:
        errors.append("COVERAGE_CERTIFICATE_DOES_NOT_EQUAL_BOUND_SOURCE_PACKAGE")
    if not relevant_evidence and proposal.get("decision") == "CONCLUDE":
        errors.append("CONCLUSION_WITHOUT_DECISION_RELEVANT_COVERED_EVIDENCE")

    return {
        "pass": not errors,
        "errors": sorted(set(errors)),
        "leaf_id": leaf_id,
        "source_count": len(cert_package),
        "relevant_evidence_ids": sorted(relevant_evidence),
        "source_package_sha256": sha256(
            "\n".join(
                sid + "\0" + sha256(text.encode("utf-8")).hexdigest()
                for sid, text in sorted(cert_package.items())
            ).encode("utf-8")
        ).hexdigest() if cert_package else None,
    }


def finance_terminal_decision(
    proposal: Any,
    proof_bundle: Any,
    *,
    coverage_certificate: Any,
) -> dict[str, Any]:
    coverage = verify_coverage_certificate(
        proposal=proposal,
        proof_bundle=proof_bundle,
        certificate=coverage_certificate,
    )
    base = configured_terminal_decision(proposal, proof_bundle, mode="FINANCE")
    errors = list(coverage.get("errors") or [])
    errors.extend(base.get("errors") or [])

    if isinstance(proposal, Mapping) and proposal.get("decision") == "CONCLUDE":
        decision = (base.get("recomputed_proof") or {}).get("decision") or {}
        selected = decision.get("selected_alternative")
        rankings = decision.get("rankings") if isinstance(decision.get("rankings"), list) else []
        selected_row = next(
            (x for x in rankings if isinstance(x, Mapping) and x.get("alternative") == selected),
            {},
        )
        contributing = set(selected_row.get("contributing_evidence") or [])
        missing = sorted(set(coverage.get("relevant_evidence_ids") or []) - contributing)
        errors.extend(f"COVERED_RELEVANT_EVIDENCE_NOT_CONTRIBUTING:{x}" for x in missing)

    accepted = not errors and coverage.get("pass") is True and base.get("accepted") is True
    return {
        "schema": SCHEMA,
        "accepted": accepted,
        "status": "TERMINAL_ACCEPTED" if accepted else "TERMINAL_BLOCKED",
        "errors": sorted(set(errors)),
        "coverage": coverage,
        "configured_judgment": base,
        "mode": "FINANCE",
        "leaf_id": str(proposal.get("leaf_id") or "") if isinstance(proposal, Mapping) else "",
        "terminal_authority": accepted,
        "rule": (
            "FINANCE_CONCLUSION_REQUIRES_EXACT_SOURCE_PACKAGE_BINDING__"
            "TWO_OR_MORE_INDEPENDENT_FULL_SOURCE_SEMANTIC_COVERAGE_ROUTES__"
            "ZERO_UNRESOLVED_SEMANTIC_DISAGREEMENT__"
            "ALL_DECISION_RELEVANT_UNITS_BOUND_TO_EVIDENCE__"
            "ALL_BOUND_RELEVANT_EVIDENCE_MUST_CONTRIBUTE_TO_RECOMPUTED_BRAIN_DECISION"
        ),
    }
