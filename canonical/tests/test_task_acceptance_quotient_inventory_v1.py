from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime.task_acceptance_quotient_inventory_v1 import (
    InventoryError,
    classify,
    compile_inventory,
)

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVID=ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"

EXPECTED_OPUS={
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}
ZERO_TOP_SUPPORT={
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
}

def _current():
    reg=json.loads(REG.read_text(encoding="utf-8"))
    evid=json.loads(EVID.read_text(encoding="utf-8"))
    proved={x["predicate_id"] for x in evid["claims"] if x.get("state")=="PROVED"}
    return reg["predicates"],proved

def test_current_24_open_atoms_partition_exactly():
    predicates,proved=_current()
    out=compile_inventory(predicates,proved)
    assert out["open_predicate_count"]==24
    assert out["quotient_class_counts"]=={
        "H_SEPARATING":5,
        "M_RESTRICTED":2,
        "OTHER":17,
    }
    assert set(out["opus_case_level_result_required"])==EXPECTED_OPUS
    assert out["opus_case_level_result_required_count"]==5
    assert out["opus_case_level_result_not_required_count"]==19

def test_zero_violation_atoms_route_to_target_free_top_support():
    predicates,_=_current()
    rows={p["id"]:classify(p) for p in predicates if p["id"] in ZERO_TOP_SUPPORT}
    assert set(rows)==ZERO_TOP_SUPPORT
    for row in rows.values():
        assert row["quotient_class"]=="M_RESTRICTED"
        assert row["opus_case_level_result_required"] is False
        assert row["route"]=="UNIVERSAL_ZERO_VIOLATION_TOP_SUPPORT_VIA_COMPLETE_MEDIATION"

def test_fixed_bar_requires_brain_result_but_not_opus_case_result():
    row=classify({
        "id":"X","family":"F","kind":"PUBLIC_FIXED_BAR","acceptance":"score >= 1"
    })
    assert row["quotient_class"]=="OTHER"
    assert row["opus_case_level_result_required"] is False
    assert row["brain_result_or_stronger_proof_required"] is True

def test_matched_noninferiority_is_separating_by_default():
    row=classify({
        "id":"X","family":"F","kind":"MATCHED_NONINFERIORITY",
        "acceptance":"Brain >= Opus on matched portfolio"
    })
    assert row["quotient_class"]=="H_SEPARATING"
    assert row["opus_case_level_result_required"] is True

def test_unknown_semantics_fail_closed():
    with pytest.raises(InventoryError,match="UNCLASSIFIED_OPEN_PREDICATE"):
        classify({"id":"X","family":"F","kind":"MYSTERY","acceptance":"?"})
