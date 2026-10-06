from __future__ import annotations
import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
POINTER=ROOT/"canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V2.json"
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V2.json"
COV=ROOT/"canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V4.json"
FACT=ROOT/"canonical/runtime/terminal_frontier_factorizer_v2.py"
COMP=ROOT/"canonical/runtime/terminal_coverage_partition_compiler_v2.py"
K6=ROOT/"canonical/governance/K6_SHARED_SEPARATOR_KERNEL_PROJECTION_20261006_V1.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def mod(path,name):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s); assert s.loader is not None; s.loader.exec_module(m); return m

def verify():
    p,a,c,k=map(load,(POINTER,AUTH,COV,K6))
    f=mod(FACT,"factorizer29")
    cp=mod(COMP,"coverage29")
    fo=f.factorize()
    co=cp.compile_partition()
    assert fo["atomic_count"]==21 and fo["meta_count"]==8 and fo["truth_obligation_count"]==29
    assert fo["truth_obligations_deleted"]==3
    assert co["truth_obligation_count"]==29
    assert co["route_counts"]=={"J":0,"G":0,"T":0,"D":15,"U":14}
    assert co["truth_obligations_deleted"]==3
    assert c["projection"]["truth_obligations"]==29
    assert c["projection"]["route_counts"]==co["route_counts"]
    assert {x["id"] for x in c["deleted_obligations"]}=={
      "COMPOSITION_COMPONENT_SCOPED_PROOFS",
      "ARTIFACT_AA_BRIEFCASE_GE_1822",
      "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    }
    s=p["exact_state"]
    assert s["load_bearing_atomic_open"]==21
    assert s["meta_open"]==8
    assert s["current_open_truth_obligations"]==29
    assert s["historical_atomic_registry_count"]==38
    assert s["verified_truth_basis_deletions"]==3
    assert s["current_load_bearing_atomic_count"]==35
    assert s["root2_touching_count"]==17
    assert s["root3_touching_count"]==7
    assert s["route_counts"]=={"J":0,"G":0,"T":0,"D":15,"U":14}
    assert s["terminal"] is False
    assert a["current_truth"]==s
    gf=a["generator_frontier"]
    assert gf["verified_owned_generators"]==5
    assert gf["unbound_semantic_generators"]==1
    assert gf["unbound_semantic_generator"]=="K6_TASK_SUFFICIENT_MODEL_AND_SEPARATOR_ACQUISITION"
    assert k["candidate_global_compression"]["verified_owned_generator_count"]==5
    assert k["candidate_global_compression"]["unbound_semantic_generator_count"]==1
    assert a["root3_frontier"]["parent_effect_membrane_substrate_verified"] is True
    assert a["root3_frontier"]["production_parent_binding_open"] is True
    assert a["root3_frontier"]["broker_totality_open"] is True
    assert a["root3_frontier"]["persistence_totality_open"] is True
    return {
      "status":"PASS__CURRENT_V2_AUTHORITY_BINDS_VERIFIED_29_TRUTH_BASIS",
      "open_truth_obligations":29,
      "route_counts":co["route_counts"],
      "root2_touching":17,
      "root3_touching":7,
      "verified_owned_generators":5,
      "unbound_semantic_generators":1,
      "terminal":False,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
