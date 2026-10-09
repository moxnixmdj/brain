import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
SRC=ROOT/"canonical/governance/CURSORBENCH_SOURCE_COVERAGE_ATOMS_ACTIVATION_20261009_V1.json"
SRCV=ROOT/"canonical/verification/CURSORBENCH_SOURCE_COVERAGE_ATOMS_INDEPENDENT_VERIFICATION_20261009_V1.json"
INFO=ROOT/"canonical/governance/CURSORBENCH_PREVERIFIER_INFORMATION_BOUNDARY_ATOM_ACTIVATION_20261009_V1.json"
INFOV=ROOT/"canonical/verification/CURSORBENCH_PREVERIFIER_INFORMATION_BOUNDARY_ATOM_INDEPENDENT_VERIFICATION_20261009_V1.json"
DEP=ROOT/"canonical/governance/CURSORBENCH_DEPENDENCY_PROVENANCE_ATOM_ACTIVATION_20261009_V1.json"
DEPV=ROOT/"canonical/verification/CURSORBENCH_DEPENDENCY_PROVENANCE_ATOM_INDEPENDENT_VERIFICATION_20261009_V1.json"
def blob(p):
    d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_current_terminal_binds_all_atom_mechanisms_without_truth_credit():
    a=json.loads(AUTH.read_text())
    s=a["authoritative_sources"]
    assert blob(SRC)==s["cursorbench_source_coverage_atoms_mechanism_20261009_v1"]["git_blob_sha"]
    assert blob(SRCV)==s["cursorbench_source_coverage_atoms_mechanism_20261009_v1"]["independent_verification"]["git_blob_sha"]
    assert blob(INFO)==s["cursorbench_preverifier_information_boundary_mechanism_20261009_v1"]["git_blob_sha"]
    assert blob(INFOV)==s["cursorbench_preverifier_information_boundary_mechanism_20261009_v1"]["independent_verification"]["git_blob_sha"]
    assert blob(DEP)==s["cursorbench_dependency_provenance_mechanism_20261009_v1"]["git_blob_sha"]
    assert blob(DEPV)==s["cursorbench_dependency_provenance_mechanism_20261009_v1"]["independent_verification"]["git_blob_sha"]
    live=a["live_truth"]
    assert live["cursorbench_all_remaining_typed_acceptance_atom_mechanisms_available"] is True
    assert live["cursorbench_remaining_typed_acceptance_mechanism_gap_count"]==0
    assert live["cursorbench_remaining_typed_acceptance_real_evidence_bundle_count"]==3
    assert live["cursorbench_source_coverage_real_receipt_bound"] is False
    assert live["cursorbench_preverifier_information_boundary_real_receipt_bound"] is False
    assert live["cursorbench_dependency_provenance_real_receipt_bound"] is False
    assert live["cursorbench_typed_semantics_atom_truth_proved"] is False
    assert live["cursorbench_failure_mode_completeness_atom_truth_proved"] is False
    assert live["cursorbench_no_hidden_verifier_access_atom_truth_proved"] is False
    assert live["cursorbench_dependency_provenance_atom_truth_proved"] is False
    assert live["cursorbench_typed_acceptance_membership_atom_count_external_when_exact_model_passes"]==4
    rec=a["cursorbench_all_atom_mechanisms_reconciliation_20261009_v1"]
    assert rec["mechanism_gap_count"]==0
    assert rec["real_evidence_bundle_count"]==3
    assert rec["real_atom_truth_delta"]==0
    assert rec["acceptance_credit_delta"]==0
    assert rec["terminal_credit_delta"]==0
