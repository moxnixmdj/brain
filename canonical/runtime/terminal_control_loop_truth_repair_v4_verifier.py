from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OVERLAY=ROOT/"canonical/governance/TERMINAL_CONTROL_LOOP_TRUTH_REPAIR_V4_CURRENT_20261006.json"
THEORY=ROOT/"canonical/governance/TERMINAL_FIRST_PRINCIPLES_THEORY_TOURNAMENT_20261006_V1.json"
THEORY_V=ROOT/"canonical/verification/TERMINAL_THEOREM_MINIMALITY_FALSIFIER_INDEPENDENT_VERIFICATION_20261006_V1.json"
STOCH=ROOT/"canonical/governance/OUTCOME_FRONTIER_STOCHASTIC_RELIABILITY_COUNTERMODEL_V1.json"
STOCH_V=ROOT/"canonical/verification/OUTCOME_FRONTIER_STOCHASTIC_COUNTERMODEL_INDEPENDENT_VERIFICATION_20261006_V1.json"
POINTER=ROOT/"canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"

OLD="C_UNIVERSAL_OBSERVABLE_BEHAVIOR_DOMINANCE_BINDING_V1"
NEW="C_TARGET_RELATIVE_DISTRIBUTIONAL_UTILITY_QUOTIENT_DOMINANCE_AND_OWNERSHIP_V4"

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

def verify():
    o,t,tv,s,sv,p=map(load,[OVERLAY,THEORY,THEORY_V,STOCH,STOCH_V,POINTER])
    assert tv["status"].startswith("INDEPENDENT_EXACT_BYTE_VERIFICATION_PASS")
    assert OLD in tv["consequence"][0]
    assert sv["status"].startswith("INDEPENDENT_EXACT_BYTE_VERIFICATION_PASS")
    assert "POINT_SUPPORT_FRONTIER_READING_FALSIFIED" in sv["status"]
    assert OLD in o["stale_claims"]
    assert o["live_successor"]["id"]==NEW
    assert o["accounting"]["terminal_credit_delta"]==0
    assert o["accounting"]["acceptance_credit_delta"]==0
    assert o["accounting"]["family_credit_delta"]==0
    assert o["accounting"]["capability_credit_delta"]==0
    assert o["accounting"]["ownership_credit_delta"]==0
    assert o["execution_authority"] is False
    assert o["promotion_authority"] is False
    assert o["fresh_reality_authority"] is False
    assert "DISTRIBUT" in o["live_successor"]["statement"]
    assert "RELIABILITY_PRESERVED" in o["live_successor"]["minimum_required_lemmas"]
    assert OLD in p["terminal_falsification_control_loop"]["current_schedule"]
    return {
        "status":"PASS__STALE_ROUTE_PROVED_AND_DISTRIBUTIONAL_SUCCESSOR_FROZEN",
        "stale_pointer_detected":True,
        "killed_route":OLD,
        "successor":NEW,
        "truth_counts_changed":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
