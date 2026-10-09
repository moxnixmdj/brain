import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json"
SOURCE_VERIFY = ROOT / "canonical/verification/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_20261009_V1.json"
NORMALIZED = ROOT / "canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_NORMALIZED_20261009_V1.json"
POLICY = ROOT / "canonical/runtime/independent_acceptance_model.py"

def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def canon_sha(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def test_normalization_is_exact_and_does_not_self_certify_membership():
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    srcv = json.loads(SOURCE_VERIFY.read_text(encoding="utf-8"))
    norm = json.loads(NORMALIZED.read_text(encoding="utf-8"))

    assert blob(SOURCE) == "09d4ac9e2134842fa6d07ace238f2adcc47b4133"
    assert blob(SOURCE_VERIFY) == "8645dca87c5c57d3a6d63299732b32839bcf42d9"
    assert blob(POLICY) == "710298c5d7154b5a3c2a4a1700420c40cb2fa55a"

    assert src["policy_id"] == norm["policy_id"] == "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
    assert src["exact_policy"] == norm["exact_policy"]
    assert srcv["verified_deduction"]["policy_adequate_on_exact_conditional_region"] is True
    assert srcv["verified_deduction"]["whole_cursorbench_adequate"] is False
    assert srcv["verified_deduction"]["hidden_cursorbench_task_membership_proved"] is False

    atom = {"op": "ATOM", "id": "CURSORBENCH_TYPED_ACCEPTANCE_PLAN_REGION_V1"}
    assert norm["policy_condition"] == atom
    assert norm["policy_condition_sha256"] == canon_sha(atom)

    sem = norm["condition_atom_semantics"]
    assert sem["source_condition_id"] == src["policy_condition"]["id"]
    assert sem["source_condition_sha256"] == src["policy_condition_sha256"]
    assert sem["requirements"] == src["policy_condition"]["requirements"]
    assert sem["atom_is_exact_alias_for_full_conjunction"] is True
    assert sem["membership_self_certified"] is False

    assert norm["adequacy_proved"] is True
    assert norm["brain_owned"] is True
    assert norm["load_bearing_constraints_preserved"] is True
    assert "NO_HIDDEN_CURSORBENCH_TASK_MEMBERSHIP" in norm["hard_nonclaims"]
    assert "NO_WHOLE_CURSORBENCH_ADEQUACY" in norm["hard_nonclaims"]
