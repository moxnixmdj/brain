from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from canonical.runtime.finance_source_coverage_terminal_gate_v1 import (
    CERT_SCHEMA,
    FINANCE_SUPERVISORY,
    finance_terminal_decision,
)
from canonical.runtime.judgment_control_envelope_v1 import _base_bundle
from canonical.runtime.source_contract_compiler import atomize_source, semantic_unit_id


TEXT = "Every applicable rule must not omit a material exception before execution."
SOURCE_ID = "synthetic-finance"
ALT = "APPLY_RULE"


def _proposal():
    return {
        "decision": "CONCLUDE",
        "leaf_id": FINANCE_SUPERVISORY,
        "selected_alternative": ALT,
        "rule_evidence_ids": ["rule"],
        "exception_evidence_ids": ["exception"],
        "reconciliation_checks": [],
    }


def _bundle():
    return _base_bundle(TEXT, SOURCE_ID, ["rule", "exception"], ALT)


def _certificate(evidence_ids=None):
    atoms = atomize_source(TEXT, SOURCE_ID)
    assert len(atoms) == 1
    atom = atoms[0]
    split = TEXT.index(" before")
    spans = [(0, split), (split, len(TEXT))]
    units = []
    sids = []
    for i, (start, end) in enumerate(spans):
        sids.append(semantic_unit_id(atom.atom_id, start, end))
        units.append({
            "atom_id": atom.atom_id,
            "start": start,
            "end": end,
            "text_sha256": sha256(TEXT[start:end].encode("utf-8")).hexdigest(),
            "kind": "EVALUATION",
            "semantic_fingerprint": f"finance-obligation-{i}",
            "rationale": "Operative finance source obligation.",
            "decision_relevant": True,
        })
    return {
        "schema": CERT_SCHEMA,
        "leaf_id": FINANCE_SUPERVISORY,
        "sources": [{
            "source_id": SOURCE_ID,
            "source_text": TEXT,
            "source_sha256": sha256(TEXT.encode("utf-8")).hexdigest(),
            "extractor_groups": {
                "deterministic-route-a": "mechanism-a",
                "deterministic-route-b": "mechanism-b",
            },
            "extractor_units": {
                "deterministic-route-a": deepcopy(units),
                "deterministic-route-b": deepcopy(units),
            },
            "requirements": [{
                "id": "finance-source-obligation",
                "source_semantic_unit_ids": sids,
                "evidence_ids": list(evidence_ids or ["rule", "exception"]),
            }],
        }],
    }


def test_finance_conclusion_accepts_only_with_full_independent_source_coverage():
    out = finance_terminal_decision(
        _proposal(),
        _bundle(),
        coverage_certificate=_certificate(),
    )
    assert out["accepted"] is True, out
    assert out["coverage"]["pass"] is True
    assert out["coverage"]["relevant_evidence_ids"] == ["exception", "rule"]


def test_finance_conclusion_blocks_independent_semantic_disagreement():
    cert = _certificate()
    cert["sources"][0]["extractor_units"]["deterministic-route-b"][1][
        "semantic_fingerprint"
    ] = "different-meaning"
    out = finance_terminal_decision(
        _proposal(),
        _bundle(),
        coverage_certificate=cert,
    )
    assert out["accepted"] is False
    assert any("FULL_SEMANTIC_EXTRACTOR_DISAGREEMENT" in x for x in out["errors"])


def test_finance_conclusion_blocks_covered_evidence_that_does_not_contribute():
    cert = _certificate(evidence_ids=["ghost"])
    out = finance_terminal_decision(
        _proposal(),
        _bundle(),
        coverage_certificate=cert,
    )
    assert out["accepted"] is False
    assert "COVERED_RELEVANT_EVIDENCE_NOT_CONTRIBUTING:ghost" in out["errors"]


def test_finance_conclusion_blocks_source_package_mismatch():
    cert = _certificate()
    cert["sources"][0]["source_text"] = TEXT + " Hidden extra source item."
    cert["sources"][0]["source_sha256"] = sha256(
        cert["sources"][0]["source_text"].encode("utf-8")
    ).hexdigest()
    out = finance_terminal_decision(
        _proposal(),
        _bundle(),
        coverage_certificate=cert,
    )
    assert out["accepted"] is False
    assert "COVERAGE_CERTIFICATE_DOES_NOT_EQUAL_BOUND_SOURCE_PACKAGE" in out["errors"]
