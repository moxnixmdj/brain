import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
REVOCATION = ROOT / "canonical/verification/UNKNOWN_DOMAIN_V6_SUBCLASS_TOTALITY_REVOCATION_20261005_V1.json"
CLASS_SPOOF = ROOT / "canonical/verification/UNKNOWN_DOMAIN_V6_REPAIRED_CLASS_SPOOF_FALSIFIER_20261005_V1.json"
V3_FALSIFIER = ROOT / "canonical/verification/UNKNOWN_DOMAIN_V6_RUNTIME_TYPE_GATE_V3_SELF_FALSIFICATION_20261005_V1.json"
GATE = ROOT / "canonical/governance/UNKNOWN_DOMAIN_V7_GENUINE_TYPE_ROOT3_REPROMOTION_GATE_20261005_V2.json"


def test_terminal_manifest_fail_closes_on_current_unknown_domain_authority():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    r = json.loads(REVOCATION.read_text(encoding="utf-8"))
    c = json.loads(CLASS_SPOOF.read_text(encoding="utf-8"))
    f3 = json.loads(V3_FALSIFIER.read_text(encoding="utf-8"))
    g = json.loads(GATE.read_text(encoding="utf-8"))

    summary = m["opus55_acceptance_summary"]
    delta = summary["unknown_domain_v6_delta"]

    assert r["status"].startswith("REVOKED__")
    assert c["status"].startswith("FALSIFIED__")
    assert f3["status"].startswith("FALSIFIED__")
    assert g["current_authority"]["predicate_state"] == "EXTERNAL_BLOCKED"
    assert g["current_authority"]["proved_atomic"] == 12
    assert g["current_authority"]["unresolved_atomic"] == 26

    assert summary["atomic_predicates"] == {"proved": 12, "unresolved": 26, "total": 38}
    assert delta["state"].startswith("EXTERNAL_BLOCKED__V1_V2_V3_REPROMOTION_ROUTES_INVALID")
    assert delta["v3_self_falsifier_git_blob_sha"] == "0b64f207db2ad07a8b69a53d514f0c717a1d0afc"
    assert delta["repromotion_gate_git_blob_sha"] == "673cb3beae6b74cfcbb10beaec3fb65a58ecab0a"
    assert delta["successor_frozen_branch_head"] == "da7b73c7d007127565b9fe2125c5dca9e4e544f6"
    assert delta["required_python_versions"] == ["3.12.10", "3.13"]
    assert delta["immutable_main_verifier_execution_required"] is True
    assert m["current_machine_verdict"]["achieved"] is False
    assert "12_OF_38_ATOMIC_ACCEPTANCE_PREDICATES_PROVED__26_UNRESOLVED" in m["current_machine_verdict"]["reason"]
    assert "V7_GENUINE_TYPE_GATE_PENDING_DUAL_VERSION_IMMUTABLE_MAIN_VERIFICATION" in m["current_machine_verdict"]["reason"]
