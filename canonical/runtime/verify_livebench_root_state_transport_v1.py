#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
PROJ=ROOT/"canonical/governance/LIVEBENCH_ROOT_PARTITION_PROJECTION_V1.json"
RECL=ROOT/"canonical/governance/LIVEBENCH_LOCAL_ROOT_RECLASSIFICATION_V1.json"

def git_blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert git_blob_sha(STATE)=="c624ca84adcc3585c9afeafe4d1c6f3ebbedee3a"
assert git_blob_sha(PROJ)=="21dc5e07e18ba3e99a97ffef20a098833c684e99"
assert git_blob_sha(RECL)=="eef18a73b23db53082b934976bcbd05cab9c5684"

s=json.loads(STATE.read_text())
p=s["current_residual_root_partition"]
assert s["current_acceptance"]=={
    "accepted_families":5,"open_families":14,"proved_atomic":12,
    "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
assert s["roots"]["root_1_capability_missing"]["status"].startswith("ACTIVE__ONE_POSITIVELY_ESTABLISHED_OPERATIVE_GAP")
assert p["unresolved_total"]==26
assert p["root1_positive_gap_count"]==1
assert p["root1_only_count"]==1 and p["root1_only"]==["LIVEBENCH_IF_GE_65_7"]
assert p["root2_only_count"]==15 and len(p["root2_only"])==15
assert "LIVEBENCH_IF_GE_65_7" not in p["root2_only"]
assert p["root3_only_count"]==7 and len(p["root3_only"])==7
assert p["root2_and_root3_count"]==3 and len(p["root2_and_root3"])==3
parts=[set(p["root1_only"]),set(p["root2_only"]),set(p["root3_only"]),set(p["root2_and_root3"])]
for i in range(len(parts)):
    for j in range(i+1,len(parts)):
        assert parts[i].isdisjoint(parts[j])
assert sum(map(len,parts))==26
assert s["scheduler_policy"]["root1_currently_active"] is True
assert s["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["effective_scheduling_authority"] is False
assert s["scheduler_policy"]["root2_output_only_threshold_dag"]["scheduling_authority"] is False
t=s["root_partition_transport"]
assert t["source_root_git_blob_sha"]=="36ac53134b123cfed7e63c31a871a30f9b4579e4"
assert t["reclassification_git_blob_sha"]=="eef18a73b23db53082b934976bcbd05cab9c5684"
assert t["projection_git_blob_sha"]=="21dc5e07e18ba3e99a97ffef20a098833c684e99"
assert t["acceptance_counts_unchanged"] is True and t["new_acceptance_credit"]==0
print("PASS:LIVEBENCH_ROOT_STATE_TRANSPORT_V1")
