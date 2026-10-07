"""Finance-only proof-carrying source-semantic coverage gate.

This wrapper does not infer finance meaning. It closes the structural omission path
between raw authoritative source bytes and the existing Brain-owned finance judgment
controller. A FINANCE conclusion is admitted only when:
1) raw source bytes are losslessly atomized and dispositioned,
2) at least two semantic decompositions exactly agree on every risky source span,
3) every operative semantic unit is bidirectionally bound to a requirement,
4) every requirement is bound to evidence already present in the finance source
   coverage manifest, and
5) the existing judgment controller independently proves that manifest evidence
   actually contributes to the selected decision.

Agreement is necessary, not metaphysical semantic truth. Ambiguity stays blocking.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_contract_compiler import (
    atomize_source,
    validate_contract_coverage,
    validate_semantic_consensus,
)

SCHEMA = "PROJECT_BRAIN_FINANCE_PROOF_CARRYING_SOURCE_GATE_V1"


def _strings(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        out.append(item.strip())
    return out


def verify_source_semantic_coverage(bundle: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(bundle, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED",
                "errors": ["PROOF_BUNDLE_NOT_OBJECT"]}

    text = bundle.get("source_text")
    source_id = bundle.get("source_id")
    if not isinstance(text, str) or not text:
        errors.append("SOURCE_TEXT_MISSING")
        text = ""
    if not isinstance(source_id, str) or not source_id.strip():
        errors.append("SOURCE_ID_MISSING")
        source_id = "invalid-source"

    cert = bundle.get("source_semantic_coverage")
    if not isinstance(cert, Mapping):
        errors.append("SOURCE_SEMANTIC_COVERAGE_MISSING")
        cert = {}

    try:
        atoms = atomize_source(text, source_id)
    except Exception as exc:
        atoms = []
        errors.append("SOURCE_ATOMIZATION_FAILED:" + type(exc).__name__)

    dispositions = cert.get("dispositions")
    requirements = cert.get("requirements")
    extractor_units = cert.get("extractor_units")
    if not isinstance(dispositions, Sequence) or isinstance(dispositions, (str, bytes)):
        dispositions = []
        errors.append("DISPOSITIONS_INVALID")
    if not isinstance(requirements, Sequence) or isinstance(requirements, (str, bytes)):
        requirements = []
        errors.append("REQUIREMENTS_INVALID")
    if not isinstance(extractor_units, Mapping):
        extractor_units = {}
        errors.append("EXTRACTOR_UNITS_INVALID")

    if atoms:
        errors.extend(validate_contract_coverage(
            source_text=text,
            atoms=atoms,
            dispositions=dispositions,
            requirements=requirements,
        ))
        errors.extend(validate_semantic_consensus(
            source_text=text,
            atoms=atoms,
            extractor_units=extractor_units,
            requirements=requirements,
        ))

    manifest = bundle.get("source_coverage_manifest")
    manifest_evidence: set[str] = set()
    if not isinstance(manifest, Mapping):
        errors.append("SOURCE_COVERAGE_MANIFEST_MISSING")
    else:
        rows = manifest.get("units")
        if not isinstance(rows, list) or not rows:
            errors.append("SOURCE_COVERAGE_MANIFEST_UNITS_MISSING")
        else:
            for i, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    errors.append(f"SOURCE_COVERAGE_ROW_INVALID:{i}")
                    continue
                ids = _strings(row.get("evidence_ids"))
                if ids is None:
                    errors.append(f"SOURCE_COVERAGE_ROW_EVIDENCE_INVALID:{i}")
                    continue
                manifest_evidence.update(ids)

    requirement_evidence: set[str] = set()
    req_ids: set[str] = set()
    for i, req in enumerate(requirements):
        if not isinstance(req, Mapping):
            errors.append(f"REQUIREMENT_NOT_OBJECT:{i}")
            continue
        rid = req.get("id")
        if not isinstance(rid, str) or not rid.strip():
            continue
        rid = rid.strip()
        req_ids.add(rid)
        ids = _strings(req.get("evidence_ids"))
        if ids is None:
            errors.append(f"REQUIREMENT_EVIDENCE_IDS_MISSING:{rid}")
            continue
        requirement_evidence.update(ids)
        missing = sorted(set(ids) - manifest_evidence)
        errors.extend(f"REQUIREMENT_EVIDENCE_NOT_IN_SOURCE_MANIFEST:{rid}:{x}" for x in missing)

    if manifest_evidence and not requirement_evidence:
        errors.append("NO_REQUIREMENT_EVIDENCE_BINDINGS")
    orphan_manifest = sorted(manifest_evidence - requirement_evidence)
    errors.extend("SOURCE_MANIFEST_EVIDENCE_WITHOUT_SEMANTIC_REQUIREMENT:" + x for x in orphan_manifest)

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "PASS__LOSSLESS_DUAL_EXTRACTOR_SOURCE_SEMANTIC_REQUIREMENT_EVIDENCE_CHAIN"
            if passed else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "source_atom_count": len(atoms),
        "requirement_count": len(req_ids),
        "manifest_evidence_ids": sorted(manifest_evidence),
        "requirement_evidence_ids": sorted(requirement_evidence),
        "semantic_truth_self_certified": False,
        "remaining_obligation": (
            "SOURCE_GROUNDED_SEMANTIC_INTERPRETATION_MUST_BE_SOUND__"
            "DUAL_EXTRACTOR_AGREEMENT_IS_NECESSARY_NOT_METAPHYSICAL_TRUTH"
        ),
    }


def configured_finance_terminal_decision(
    proposal: Any,
    proof_bundle: Any,
) -> dict[str, Any]:
    coverage = verify_source_semantic_coverage(proof_bundle)
    if coverage.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "accepted": False,
            "status": "TERMINAL_BLOCKED",
            "errors": ["FINANCE_SOURCE_SEMANTIC_COVERAGE_FAIL_CLOSED", *(coverage.get("errors") or [])],
            "source_semantic_coverage": coverage,
        }

    # Import only after the stronger source gate passes. This keeps the structural
    # verifier independently executable with only source_contract_compiler present.
    from canonical.runtime.judgment_control_envelope_v1 import configured_terminal_decision

    out = configured_terminal_decision(proposal, proof_bundle, mode="FINANCE")
    result = dict(out)
    result["source_semantic_coverage"] = coverage
    result["finance_wrapper_schema"] = SCHEMA
    return result
