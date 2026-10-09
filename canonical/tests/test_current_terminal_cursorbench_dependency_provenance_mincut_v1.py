import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_dependency_provenance_mincut():
    a=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json").read_text())
    c=json.loads((ROOT/"canonical/governance/CURSORBENCH_DEPENDENCY_PROVENANCE_MINCUT_20261009_V1.json").read_text())
    assert c["deduction"]["external_cursor_specific_unknown_count"]==0
    assert c["deduction"]["per_model_internal_audit_count"]==1
    assert c["deduction"]["dependency_provenance_atom_truth_proved"] is False
    l=a["live_truth"]
    assert l["cursorbench_dependency_provenance_bundle_brain_controlled"] is True
    assert l["cursorbench_dependency_provenance_atom_truth_proved"] is False
    assert l["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"]==3
