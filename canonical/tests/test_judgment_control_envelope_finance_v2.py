from canonical.runtime.finance_source_coverage_certificate_v1 import build_manifest
from canonical.runtime.judgment_control_envelope_finance_v2 import configured_terminal_decision
from canonical.runtime.judgment_control_envelope_v1 import (
    FINANCE_SUPERVISORY,
    _base_bundle,
)


def _proposal():
    return {
        "decision": "CONCLUDE",
        "leaf_id": FINANCE_SUPERVISORY,
        "selected_alternative": "APPLY_RULE",
        "rule_evidence_ids": ["rule"],
        "exception_evidence_ids": ["exception"],
        "reconciliation_checks": [],
    }


def _bundle():
    text = "Every applicable rule applies. Preserve every material exception."
    bundle = _base_bundle(text, "finance-source-gate-test", ["rule", "exception"], "APPLY_RULE")
    bundle["source_coverage_manifest"] = build_manifest(
        text,
        [["rule"], ["exception"]],
        source_id="finance-source-gate-test",
    )
    return bundle


def test_complete_source_coverage_preserves_acceptance():
    out = configured_terminal_decision(_proposal(), _bundle(), mode="FINANCE")
    assert out["accepted"] is True, out
    assert out["finance_source_coverage"]["pass"] is True


def test_omitted_source_unit_blocks_finance_conclusion():
    bundle = _bundle()
    bundle["source_coverage_manifest"]["units"] = bundle["source_coverage_manifest"]["units"][:1]
    out = configured_terminal_decision(_proposal(), bundle, mode="FINANCE")
    assert out["accepted"] is False
    assert out["status"] == "TERMINAL_BLOCKED"
    assert "FINANCE_SOURCE_COVERAGE_FAIL_CLOSED" in out["errors"]
    assert "SOURCE_COVERAGE_UNIT_COUNT_MISMATCH" in out["errors"]
