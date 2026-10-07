import json
from pathlib import Path

P=Path(__file__).resolve().parents[2]/"canonical/governance/SYNTHESIS_V2_CACHE_UNCERTAINTY_RECONCILIATION_20261007_V1.json"

def load():
    return json.loads(P.read_text())

def test_broad_v2_full_quality_revoked():
    d=load()["truth_repair"]
    assert d["revoke_broad_v2_as"]=="UNCONDITIONAL_FULL_FROZEN_MATCHED_QUALITY_D_B_REGION"

def test_replacement_requires_uncertainty_closure():
    x=load()["truth_repair"]["replacement_full_quality_region"]
    assert "ZERO_REQUIRED_UNCERTAINTY" in x
    assert "UNCERTAINTY_PRESERVATION_CERTIFICATE" in x

def test_u_cannot_shrink_from_broad_v2_alone():
    assert "BROAD_V2_ALONE" in load()["U_rule"]

def test_zero_credit():
    assert load()["accounting"]["terminal_credit_delta"]==0
