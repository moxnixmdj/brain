import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_static_theorem_does_not_content_address_mutable_current_pointer():
    theorem = load("canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json")
    authority = theorem["r4_canonical_certificate_authority"]
    assert authority["current_authority_manifest"] == "canonical/governance/CURRENT_COVERAGE_COMPLETENESS_ROOT_CERTIFICATES.json"
    assert "current_authority_manifest_git_blob_sha" not in authority
    assert authority["current_authority_manifest_binding_mode"].startswith("PATH_ONLY_IN_STATIC_THEOREM")


def test_currentness_dependency_graph_is_acyclic_and_live_bound():
    claim = load("canonical/governance/COVERAGE_COMPLETENESS_CLAIM_SCOPE_V1.json")
    current = load("canonical/governance/CURRENT_COVERAGE_COMPLETENESS_ROOT_CERTIFICATES.json")
    live = load("canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_LIVE_BINDING_V1.json")
    terminal = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")

    assert claim["root_theorem"]["path"] == "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json"
    assert current["claim_scope"]["claim_scope_path"] == "canonical/governance/COVERAGE_COMPLETENESS_CLAIM_SCOPE_V1.json"
    assert live["root_certificate_registry_precondition"]["current_pointer_path"] == "canonical/governance/CURRENT_COVERAGE_COMPLETENESS_ROOT_CERTIFICATES.json"
    assert terminal["authoritative_sources"]["coverage_completeness_root_theorem_r1_r4"]["path"] == "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_LIVE_BINDING_V1.json"

    assert terminal["terminal_architecture_override"]["terminal"] is False
    assert terminal["r4_live_binding_currentness"]["global_mission_completion"] is False
    assert terminal["r4_live_binding_currentness"]["terminal_credit_delta"] == 0
