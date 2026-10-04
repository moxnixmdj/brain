import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GATE=ROOT/"canonical/governance/UNKNOWN_DOMAIN_V7_GENUINE_TYPE_REPROMOTION_GATE_20261005_V1.json"


def test_v7_gate_is_fail_closed_and_binds_falsifier():
    g=json.loads(GATE.read_text(encoding="utf-8"))
    assert g["current_authority"]["proved_atomic"]==12
    assert g["current_authority"]["unresolved_atomic"]==26
    assert g["current_authority"]["predicate_state"]=="EXTERNAL_BLOCKED"
    assert g["supersedes"]["gate"].endswith("UNKNOWN_DOMAIN_V6_SUBCLASS_REPAIR_ROOT3_REPROMOTION_GATE_20261005_V2.json")
    assert "CLASS_SPOOF" in g["supersedes"]["reason"]
    assert g["promotion_predicate"]["on_any_false_missing_or_hash_mismatch"]["predicate_state"]=="EXTERNAL_BLOCKED"


def test_v7_gate_binds_exact_genuine_type_candidate():
    g=json.loads(GATE.read_text(encoding="utf-8"))
    blobs=g["candidate"]["required_blobs"]
    assert len(blobs)==11
    assert blobs["canonical/runtime/unknown_domain_direct_hidden_generator_v5.py"]=="d2f529ed9a006f53e75d06ece6f2acb54211b127"
    assert blobs["canonical/tests/test_unknown_domain_direct_v5.py"]=="5b1dc24c7ec65edc32475917349c5d8725b9a655"
    assert blobs["canonical/runtime/unknown_domain_direct_v7_genuine_type_proof_v1.py"]=="3d7171b34a19f2600f9c5bb512d116806deba481"
    required=set(g["independent_verifier_contract"]["required"])
    assert "FAKE_STR_CLASS_SPOOF_PROXY_IS_REJECTED_BEFORE_DESCRIPTOR_USE" in required
    assert "FAKE_BYTES_CLASS_SPOOF_PROXY_IS_REJECTED_BEFORE_DESCRIPTOR_USE" in required
    assert "REAL_STR_SUBCLASSES_WITH_HOSTILE_HOOKS_PASS" in required
    assert "REAL_BYTES_SUBCLASSES_WITH_HOSTILE_HOOKS_PASS" in required
