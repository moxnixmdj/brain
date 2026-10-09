import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
CERT = ROOT / "canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json"
VERIFY = ROOT / "canonical/verification/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_20261009_V1.json"

def blob(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def test_terminal_authority_binds_first_positive_region_without_overclaim():
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    verify = json.loads(VERIFY.read_text(encoding="utf-8"))
    src = auth["authoritative_sources"]["cursorbench_first_authenticated_positive_adequacy_region_20261009_v1"]
    assert blob(CERT) == src["git_blob_sha"]
    assert blob(VERIFY) == src["independent_verification"]["git_blob_sha"]
    assert verify["verified_deduction"]["policy_adequate_on_exact_conditional_region"] is True
    assert verify["verified_deduction"]["whole_specification_behavior_adequate"] is False
    assert verify["verified_deduction"]["whole_cursorbench_adequate"] is False
    live = auth["live_truth"]
    assert live["cursorbench_authenticated_positive_adequacy_region_count"] == 1
    assert live["cursorbench_first_authenticated_positive_adequacy_region_proved"] is True
    assert live["cursorbench_first_authenticated_positive_adequacy_region_id"] == cert["policy_condition"]["id"]
    assert live["cursorbench_first_positive_region_membership_self_certified"] is False
    assert live["cursorbench_first_positive_region_hidden_task_membership_proved"] is False
    assert live["cursorbench_positive_adequacy_cover_closed"] is False
    assert live["cursorbench_dominance_closed"] is False
    assert live["cursorbench_acceptance_predicate_closed"] is False
    assert live["cursorbench_selector_work_authorized_now"] is False
    rec = auth["cursorbench_first_positive_adequacy_region_reconciliation_20261009_v1"]
    assert rec["region_count"] == 1
    assert rec["acceptance_credit_delta"] == 0
    assert rec["terminal_credit_delta"] == 0
