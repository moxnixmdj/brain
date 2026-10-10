from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TA = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
DISCOVERY = ROOT / "canonical/runtime/regcap_mrel_property_candidate_discovery_v1.py"
CONTROL = ROOT / "canonical/runtime/regcap_candidate_ambiguity_control_v1.py"
VERIFY = ROOT / "canonical/verification/R2_FOUR_WAY_REGCAP_MREL_MINIMUM_INFORMATION_VERIFY_20261010_V1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def test_r2_v79_binds_exact_four_way_minimum_information_runtime():
    r2 = load(R2)
    cap = r2["regcap_mrel_four_way_minimum_information"]
    assert "__V79__" in r2["status"]
    assert cap["candidate_discovery_git_blob_sha"] == blob(DISCOVERY)
    assert cap["ambiguity_control_git_blob_sha"] == blob(CONTROL)
    assert cap["verification_path"] == str(VERIFY.relative_to(ROOT)).replace("\\", "/")
    assert cap["bound_candidate_ids"] == [
        "REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC", "REGCAP::MREL"
    ]
    assert cap["bare_shared_property_identity_authority"] is False
    assert cap["incomplete_observation_model_routes_minimum_information"] is True
    assert cap["finance_tail_closed"] is False
    assert cap["terminal_credit_delta"] == 0


def test_terminal_authority_projects_v79_without_inflating_closure():
    r2 = load(R2)
    ta = load(TA)
    rec = ta["r2_v79_four_way_minimum_information_reconciliation"]
    assert "CURRENT_R2_V79" in ta["status"]
    assert ta["authoritative_sources"]["current_r2_decision_intelligence"]["status"] == r2["status"]
    assert rec["current_r2_expected_git_blob_sha"] == blob(R2)
    assert rec["bound_candidate_count"] == 4
    assert rec["direct_route_count_delta"] == 0
    assert rec["finance_tail_closed"] is False
    assert rec["terminal_credit_delta"] == 0
    assert ta["terminal_architecture_override"]["terminal"] is False
    assert "ONE_FINANCE_RESIDUAL_REMAINS" in ta["live_truth"]["current_r2_semantic_revision"]
