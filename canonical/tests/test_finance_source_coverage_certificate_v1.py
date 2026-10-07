from canonical.runtime.finance_source_coverage_certificate_v1 import (
    FINANCE_DOCUMENT,
    FINANCE_SUPERVISORY,
    build_manifest,
    derive_source_units,
    verify_finance_source_coverage,
)


def _bundle(text, per_unit):
    return {
        "source_text": text,
        "source_coverage_manifest": build_manifest(text, per_unit, source_id="t"),
    }


def test_complete_manifest_passes():
    text = "Every rule applies. Preserve every material exception."
    units = derive_source_units(text)
    assert len(units) == 2
    out = verify_finance_source_coverage(
        _bundle(text, [["rule"], ["exception"]]),
        contributing_evidence={"rule", "exception"},
        leaf_id=FINANCE_SUPERVISORY,
    )
    assert out["pass"] is True, out
    assert out["derived_source_unit_count"] == 2
    assert out["semantic_completeness_self_certified"] is False


def test_omitted_source_unit_fails_closed():
    text = "Every rule applies. Preserve every material exception."
    manifest = build_manifest(text, [["rule"], ["exception"]], source_id="t")
    manifest["units"] = manifest["units"][:1]
    out = verify_finance_source_coverage(
        {"source_text": text, "source_coverage_manifest": manifest},
        contributing_evidence={"rule", "exception"},
        leaf_id=FINANCE_SUPERVISORY,
    )
    assert out["pass"] is False
    assert "SOURCE_COVERAGE_UNIT_COUNT_MISMATCH" in out["errors"]


def test_noncontributing_bound_evidence_fails_closed():
    text = "Trace all document facts."
    out = verify_finance_source_coverage(
        _bundle(text, [["fact"]]),
        contributing_evidence={"other"},
        leaf_id=FINANCE_DOCUMENT,
    )
    assert out["pass"] is False
    assert any(x.startswith("SOURCE_UNIT_EVIDENCE_NOT_CONTRIBUTING") for x in out["errors"])


def test_source_drift_fails_closed():
    text = "Trace all document facts."
    manifest = build_manifest(text, [["fact"]], source_id="t")
    out = verify_finance_source_coverage(
        {"source_text": text + " Changed.", "source_coverage_manifest": manifest},
        contributing_evidence={"fact"},
        leaf_id=FINANCE_DOCUMENT,
    )
    assert out["pass"] is False
    assert "SOURCE_COVERAGE_SOURCE_HASH_MISMATCH" in out["errors"]
