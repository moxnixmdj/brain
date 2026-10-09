import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_CERTIFICATE_20261009_V2.json"

EXPECTED_ATOMS = {
    "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1",
    "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1",
    "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
    "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
    "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def _atoms(condition):
    if not isinstance(condition, dict):
        return set()
    if condition.get("op") == "ATOM":
        atom = condition.get("id")
        return {atom} if isinstance(atom, str) and atom else set()
    out = set()
    for row in condition.get("args", []):
        out |= _atoms(row)
    return out

def test_v2_atomizes_every_v1_membership_premise_without_widening_scope():
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    assert cert["policy_id"] == "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
    assert cert["behavior_id"] == "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"
    assert _atoms(cert["policy_condition"]) == EXPECTED_ATOMS
    assert set(cert["condition_atom_semantics"]) == EXPECTED_ATOMS
    assert cert["adequacy_proved"] is True
    assert cert["membership_self_certified"] is False
    assert cert["adequacy_self_certified"] is False
    assert cert["adequacy_theorem"]["whole_behavior_adequacy"] is False
    assert cert["adequacy_theorem"]["whole_cursorbench_adequacy"] is False

def test_v2_binds_exact_verified_v1_region_and_policy_bytes():
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    for key in ("v1_region_certificate", "v1_region_verification", "behavior_registry", "cursorbench_residual_basis"):
        ref = cert["exact_sources"][key]
        p = ROOT / ref["path"]
        assert git_blob_sha(p) == ref["git_blob_sha"], key
    p = ROOT / cert["exact_policy"]["path"]
    assert git_blob_sha(p) == cert["exact_policy"]["git_blob_sha"]

def test_condition_is_not_vacuous_and_requires_all_five_atoms():
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    cond = cert["policy_condition"]
    assert cond["op"] == "AND"
    assert len(cond["args"]) == 5
    assert all(row.get("op") == "ATOM" and row.get("id") in EXPECTED_ATOMS for row in cond["args"])

def test_no_registry_or_membership_authority_is_claimed():
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    assert "NO_CONDITION_ATOM_TRUTH_IS_CREATED_BY_THIS_CERTIFICATE" in cert["hard_nonclaims"]
    assert cert["promotion_authority"] is False
    assert cert["terminal_authority"] is False
    assert cert["accounting"]["acceptance_credit_delta"] == 0
    assert cert["accounting"]["terminal_credit_delta"] == 0
