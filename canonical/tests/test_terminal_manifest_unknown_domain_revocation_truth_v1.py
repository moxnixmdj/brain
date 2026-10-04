import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
REVOCATION = ROOT / "canonical/verification/UNKNOWN_DOMAIN_V6_SUBCLASS_TOTALITY_REVOCATION_20261005_V1.json"
GATE = ROOT / "canonical/governance/UNKNOWN_DOMAIN_V6_SUBCLASS_REPAIR_ROOT3_REPROMOTION_GATE_20261005_V2.json"


def test_terminal_manifest_fail_closes_on_current_unknown_domain_revocation():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    r = json.loads(REVOCATION.read_text(encoding="utf-8"))
    g = json.loads(GATE.read_text(encoding="utf-8"))

    summary = m["opus55_acceptance_summary"]
    delta = summary["unknown_domain_v6_delta"]

    assert r["status"].startswith("REVOKED__")
    assert g["current_authority"]["predicate_state"] == "EXTERNAL_BLOCKED"
    assert g["current_authority"]["proved_atomic"] == 12
    assert g["current_authority"]["unresolved_atomic"] == 26

    assert summary["atomic_predicates"] == {"proved": 12, "unresolved": 26, "total": 38}
    assert delta["state"].startswith("EXTERNAL_BLOCKED__REVOKED")
    assert delta["revocation_git_blob_sha"] == "a30a19aa0ab9ac18eaf0d005cf1f71b636660fb4"
    assert delta["repromotion_gate_git_blob_sha"] == "0f831e1a56b85d48740ccb8639015ddde4d31b07"
    assert delta["previous_acceptance_reduction_state"] == "REVOKED"
    assert m["current_machine_verdict"]["achieved"] is False
    assert "12_OF_38_ATOMIC_ACCEPTANCE_PREDICATES_PROVED__26_UNRESOLVED" in m["current_machine_verdict"]["reason"]
