import copy

from canonical.runtime.finance_source_universe_gate_v1 import (
    DOCUMENT,
    SUPERVISORY,
    canonical_authority_sha256,
    verify_finance_source_universe,
)

def _authority(leaf):
    base = {
        "authority_id": "case-001",
        "frozen_before_candidate": True,
        "candidate_can_modify_authority": False,
    }
    if leaf == SUPERVISORY:
        base.update({
            "all_material_rule_ids": ["rule-A"],
            "all_material_exception_ids": ["exc-A"],
            "required_disclosure_ids": ["disc-A"],
            "required_escalation_ids": ["esc-A"],
        })
    else:
        base.update({
            "document_fact_universe": ["fact-A", "fact-B"],
            "decision_relevant_fact_universe": ["fact-B"],
            "cross_reference_universe": ["xref-A"],
            "material_exception_ids": ["doc-exc-A"],
        })
    base["authority_sha256"] = canonical_authority_sha256(base)
    return base

def _manifest(a):
    ids = (
        ["rule-A", "exc-A", "disc-A", "esc-A"]
        if "all_material_rule_ids" in a
        else ["fact-A", "fact-B", "xref-A", "doc-exc-A"]
    )
    return {
        "authority_id": a["authority_id"],
        "authority_sha256": a["authority_sha256"],
        "covered_source_ids": list(ids),
        "semantic_binding_source_ids": list(ids),
    }, list(ids)

def test_supervisory_complete_universe_passes():
    a = _authority(SUPERVISORY); m, ids = _manifest(a)
    out = verify_finance_source_universe(
        leaf_id=SUPERVISORY, authority=a, coverage_manifest=m,
        contributing_evidence_ids=ids,
    )
    assert out["pass"] is True, out

def test_document_complete_universe_passes():
    a = _authority(DOCUMENT); m, ids = _manifest(a)
    out = verify_finance_source_universe(
        leaf_id=DOCUMENT, authority=a, coverage_manifest=m,
        contributing_evidence_ids=ids,
    )
    assert out["pass"] is True, out

def test_omitted_material_source_fails_closed_even_if_declared_subset_contributes():
    a = _authority(SUPERVISORY); m, ids = _manifest(a)
    m["covered_source_ids"].remove("exc-A")
    m["semantic_binding_source_ids"].remove("exc-A")
    ids.remove("exc-A")
    out = verify_finance_source_universe(
        leaf_id=SUPERVISORY, authority=a, coverage_manifest=m,
        contributing_evidence_ids=ids,
    )
    assert out["pass"] is False
    assert "SOURCE_UNIVERSE_NOT_COVERED:exc-A" in out["errors"]
    assert "SOURCE_NOT_TERMINALLY_CONTRIBUTING:exc-A" in out["errors"]

def test_candidate_cannot_self_assert_mutable_authority():
    a = _authority(DOCUMENT); m, ids = _manifest(a)
    a["candidate_can_modify_authority"] = True
    a["authority_sha256"] = canonical_authority_sha256(a)
    m["authority_sha256"] = a["authority_sha256"]
    out = verify_finance_source_universe(
        leaf_id=DOCUMENT, authority=a, coverage_manifest=m,
        contributing_evidence_ids=ids,
    )
    assert out["pass"] is False
    assert "AUTHORITY_MUTABILITY_NOT_FORBIDDEN" in out["errors"]

def test_hash_drift_fails_closed():
    a = _authority(SUPERVISORY); m, ids = _manifest(a)
    mutated = copy.deepcopy(a)
    mutated["all_material_rule_ids"].append("rule-B")
    out = verify_finance_source_universe(
        leaf_id=SUPERVISORY, authority=mutated, coverage_manifest=m,
        contributing_evidence_ids=ids,
    )
    assert out["pass"] is False
    assert "AUTHORITY_CONTENT_HASH_INVALID" in out["errors"]
