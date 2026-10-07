from __future__ import annotations

from canonical.runtime.finance_structured_source_coverage_certificate_v1 import (
    LEAF_DOCUMENT,
    LEAF_SUPERVISORY,
    certify,
    package_sha256,
)


def _seal(package):
    package = dict(package)
    package["package_sha256"] = package_sha256(package)
    return package


def test_supervisory_complete_manifest_passes():
    package = _seal({
        "leaf_id": LEAF_SUPERVISORY,
        "source_id": "ruleset-1",
        "items": [
            {"id": "r1", "category": "APPLICABLE_RULE", "source_ref": "rule:1"},
            {"id": "e1", "category": "MATERIAL_EXCEPTION", "source_ref": "rule:2"},
            {"id": "x1", "category": "ESCALATION", "source_ref": "rule:3"},
            {"id": "d1", "category": "DISCLOSURE", "source_ref": "rule:4"},
        ],
    })
    proposal = {
        "rule_evidence_ids": ["r1"],
        "exception_evidence_ids": ["e1"],
        "escalation_evidence_ids": ["x1"],
        "disclosure_evidence_ids": ["d1"],
    }
    out = certify(package, proposal)
    assert out["pass"] is True
    assert out["covered_item_count"] == 4


def test_supervisory_missing_exception_fails_closed():
    package = _seal({
        "leaf_id": LEAF_SUPERVISORY,
        "source_id": "ruleset-1",
        "items": [
            {"id": "r1", "category": "APPLICABLE_RULE", "source_ref": "rule:1"},
            {"id": "e1", "category": "MATERIAL_EXCEPTION", "source_ref": "rule:2"},
        ],
    })
    out = certify(package, {
        "rule_evidence_ids": ["r1"],
        "exception_evidence_ids": [],
        "escalation_evidence_ids": [],
        "disclosure_evidence_ids": [],
    })
    assert out["pass"] is False
    assert "MISSING_REQUIRED_ITEM:exception_evidence_ids:e1" in out["errors"]


def test_document_complete_manifest_passes():
    package = _seal({
        "leaf_id": LEAF_DOCUMENT,
        "source_id": "document-1",
        "items": [
            {"id": "f1", "category": "DECISION_RELEVANT_FACT", "source_ref": "page:1"},
            {"id": "c1", "category": "CROSS_REFERENCE", "source_ref": "page:2"},
            {"id": "e1", "category": "CONTRADICTION_OR_EXCEPTION", "source_ref": "page:3"},
            {"id": "q1", "category": "RECONCILIATION", "source_ref": "page:4"},
        ],
    })
    proposal = {
        "fact_evidence_ids": ["f1"],
        "cross_reference_evidence_ids": ["c1"],
        "exception_evidence_ids": ["e1"],
        "reconciliation_evidence_ids": ["q1"],
    }
    assert certify(package, proposal)["pass"] is True


def test_package_tamper_fails_hash_binding():
    package = _seal({
        "leaf_id": LEAF_DOCUMENT,
        "source_id": "document-1",
        "items": [
            {"id": "f1", "category": "DECISION_RELEVANT_FACT", "source_ref": "page:1"},
        ],
    })
    tampered = dict(package)
    tampered["source_id"] = "document-2"
    out = certify(tampered, {
        "fact_evidence_ids": ["f1"],
        "cross_reference_evidence_ids": [],
        "exception_evidence_ids": [],
        "reconciliation_evidence_ids": [],
    })
    assert out["pass"] is False
    assert "PACKAGE_HASH_MISMATCH" in out["errors"]


def test_wrong_evidence_channel_fails_closed():
    package = _seal({
        "leaf_id": LEAF_DOCUMENT,
        "source_id": "document-1",
        "items": [
            {"id": "f1", "category": "DECISION_RELEVANT_FACT", "source_ref": "page:1"},
            {"id": "q1", "category": "RECONCILIATION", "source_ref": "page:2"},
        ],
    })
    out = certify(package, {
        "fact_evidence_ids": ["f1", "q1"],
        "cross_reference_evidence_ids": [],
        "exception_evidence_ids": [],
        "reconciliation_evidence_ids": [],
    })
    assert out["pass"] is False
    assert any(x.startswith("ITEM_WRONG_EVIDENCE_CHANNEL:q1") for x in out["errors"])
