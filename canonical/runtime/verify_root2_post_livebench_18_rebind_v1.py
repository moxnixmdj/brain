#!/usr/bin/env python3
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=lambda s: ROOT/s
def sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
state=P("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
old=P("canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1.json")
new=P("canonical/governance/ROOT2_POST_LIVEBENCH_18_PREDICATE_REBIND_V1.json")
proj=P("canonical/governance/LIVEBENCH_ROOT_PARTITION_PROJECTION_V1.json")
recl=P("canonical/governance/LIVEBENCH_LOCAL_ROOT_RECLASSIFICATION_V1.json")
assert sha(state)=="c624ca84adcc3585c9afeafe4d1c6f3ebbedee3a"
assert sha(old)=="1fba51d15bcfdf6accd90948155517f7c9b98bbb"
assert sha(new)=="8ccf5c09357e0d644a90af67dbcd18c3b5ce5925"
assert sha(proj)=="21dc5e07e18ba3e99a97ffef20a098833c684e99"
assert sha(recl)=="eef18a73b23db53082b934976bcbd05cab9c5684"
s=json.loads(state.read_text()); o=json.loads(old.read_text()); n=json.loads(new.read_text())
p=s["current_residual_root_partition"]
expected=p["root2_only"]+p["root2_and_root3"]
assert len(expected)==18 and len(set(expected))==18
assert "LIVEBENCH_IF_GE_65_7" not in expected
ids=[x["id"] for x in n["predicates"]]
assert ids==[x["id"] for x in o["predicates"] if x["id"]!="LIVEBENCH_IF_GE_65_7"]
assert set(ids)==set(expected)
assert n["exact_partition"]["root2_touching_count"]==18
assert n["exact_partition"]["root2_touching_predicates"]==ids
assert n["removed_predicate"]["id"]=="LIVEBENCH_IF_GE_65_7"
assert n["removed_predicate"]["measurement_state"]=="RESOLVED_NEGATIVELY"
assert n["removed_predicate"]["full_population_upper_percent"]==64.0
assert n["removed_predicate"]["threshold_percent"]==65.7
assert n["proof_precedence"]==o["proof_precedence"]
assert n["cross_predicate_reuse"]==o["cross_predicate_reuse"]
assert n["authority"]=={"scheduling":False,"execution":False,"promotion":False,"fresh_reality":False,"acceptance_credit":False}
assert all(v==0 for v in n["accounting"].values())
print("PASS:ROOT2_POST_LIVEBENCH_18_PREDICATE_REBIND_V1")
