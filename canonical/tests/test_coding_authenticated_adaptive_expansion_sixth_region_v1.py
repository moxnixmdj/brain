import hashlib,json
from pathlib import Path
from canonical.runtime.universal_verified_adaptive_solver_v12 import run
from canonical.tests.test_universal_verified_adaptive_solver_v12 import make_problem,make_capability

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical/runtime/universal_verified_adaptive_solver_v12.py"
CERT=ROOT/"canonical/governance/CODING_AUTHENTICATED_ADAPTIVE_EXPANSION_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json"
DISTINCT=ROOT/"canonical/governance/CODING_ADAPTIVE_EXPANSION_REGION_NONSUBSUMPTION_20261009_V1.json"
ATOMS=[
"CODING_ADAPTIVE_TASK_TARGET_CONTRACT_BOUND_V1",
"CODING_ADAPTIVE_FINITE_EXPANSION_WITNESS_V1",
"CODING_ADAPTIVE_EXPANDED_CAPABILITY_SEMANTICS_AUTHENTICATED_V1",
"CODING_ADAPTIVE_STEP_VERIFIERS_TOTAL_SOUND_COMPLETE_V1",
"CODING_ADAPTIVE_PROPOSAL_WITNESS_WITHIN_BUDGET_V1",
"CODING_ADAPTIVE_EFFECT_OUTCOME_VERIFIED_V1",
"CODING_ADAPTIVE_CYCLE_EXPANSION_BUDGET_SUFFICIENT_V1",
"CODING_ADAPTIVE_PRETERMINAL_INFORMATION_ADMISSIBLE_V1"]

def blob(p):
 d=p.read_bytes();h=hashlib.sha1();h.update(b"blob "+str(len(d)).encode()+b"\0"+d);return h.hexdigest()

def test_certificate():
 c=json.loads(CERT.read_text())
 assert c["exact_policy"]["git_blob_sha"]==blob(RUNTIME)
 assert [x["id"] for x in c["policy_condition"]["args"]]==ATOMS
 assert c["adequacy_proved"] is True
 assert c["target_membership_proved"] is False

def test_distinct_witness(tmp_path):
 p=make_problem();assert p["capabilities"]==[]
 cap=make_capability(tmp_path,p)
 def expand(request,index,current): return {"source_id":"sixth-region-test","capabilities":[cap]}
 def propose(request,index,prior): return {"candidate":{"answer":42}}
 out=run(p,repo_root=tmp_path,capability_expander=expand,max_capability_expansions=1,proposal_provider=propose,proposal_provider_max_candidates=1)
 assert out["pass"] is True
 assert out["verified_facts"]==["GOAL"]
 assert out["expanded_capability_ids"]==["new-route"]
 w=json.loads(DISTINCT.read_text())["witness"]
 assert w["region_truth"]=={"A":True,"T":False,"F":False,"R":False,"S":False,"V":False}

if __name__ == "__main__":
    import tempfile
    test_certificate()
    with tempfile.TemporaryDirectory() as td:
        test_distinct_witness(Path(td))
    print("PASS 2/2 adaptive sixth region")
