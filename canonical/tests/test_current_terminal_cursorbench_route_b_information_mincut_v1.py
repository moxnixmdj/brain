import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_route_b_information_mincut():
    a=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json").read_text())
    q=json.loads((ROOT/"canonical/governance/CURSORBENCH_ROUTE_B_INFORMATION_MINCUT_20261009_V1.json").read_text())
    assert q["accounting"]["verifier_bundle_count"]==3
    assert q["accounting"]["irreducible_external_or_semantic_truth_object_count"]==3
    assert q["accounting"]["cursor_specific_external_owner_fact_count"]==1
    assert q["accounting"]["semantic_proof_object_count"]==2
    assert len(q["irreducible_truth_objects"])==3
    l=a["live_truth"]
    assert l["cursorbench_route_b_irreducible_truth_object_count"]==3
    assert l["cursorbench_route_b_cursor_specific_external_owner_fact_count"]==1
    assert l["cursorbench_route_b_semantic_proof_object_count"]==2
    assert l["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"]==3
    assert a["cursorbench_route_b_information_mincut_reconciliation_20261009_v1"]["atom_truth_delta"]==0
