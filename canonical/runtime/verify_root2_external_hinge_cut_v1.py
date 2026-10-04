from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
cut=json.loads((ROOT/"canonical/governance/ROOT2_EXTERNAL_HINGE_CUT_V1.json").read_text())
root=json.loads((ROOT/"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json").read_text())
inv=json.loads((ROOT/"canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json").read_text())

partition=root["current_residual_root_partition"]
current=set(partition["root2_only"]) | set(partition["root2_and_root3"])
assert len(current)==19

seen=set()
for hinge in cut["hinges"]:
    ps=set(hinge["predicates"])
    assert len(ps)==hinge["predicate_count"]
    assert not (seen & ps)
    seen |= ps
assert seen==current

fixed_inventory=set()
for route in inv["routes"]:
    fixed_inventory.update(route["predicate_ids"])

fixed_from_cut=set()
for hinge in cut["hinges"]:
    for p in hinge["predicates"]:
        if p not in partition["root2_and_root3"] and p!="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR":
            fixed_from_cut.add(p)
assert fixed_from_cut==fixed_inventory

h7=next(h for h in cut["hinges"] if h["hinge_id"]=="H7_MATCHED_COMPARATOR_PERFORMANCE")
assert set(h7["predicates"])==set(partition["root2_and_root3"])|{"SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"}

for ev in cut["shared_prerequisite_events"]:
    assert ev["blocker_relief_fanout"]==len(set(ev["blocker_relief_predicates"]))
    assert ev["guaranteed_closure_count"]==0
    assert set(ev["blocker_relief_predicates"]) <= current

assert sum(h["predicate_count"] for h in cut["hinges"])==19
for key in ("new_reality_units_consumed","terminal_cases_consumed","incremental_spend_usd","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
    assert cut[key]==0
for key in ("execution_authority","promotion_authority","fresh_reality_authority"):
    assert cut[key] is False

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_EXTERNAL_HINGE_CUT_V1_LOCAL_VERIFICATION",
 "status":"PASS__19_ROOT2_PREDICATES_PARTITIONED_TO_7_HINGES__SHARED_FANOUT_BOUND__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
