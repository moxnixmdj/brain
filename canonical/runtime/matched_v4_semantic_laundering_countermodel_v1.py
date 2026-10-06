from __future__ import annotations
import hashlib, json
from canonical.runtime.matched_success_component_bound_v4 import INPUT_SCHEMA,RULES,SCORERS,compile_v4

def h(x:str)->str:
    return hashlib.sha256(x.encode()).hexdigest()
def b(x:str)->str:
    return hashlib.sha1(x.encode()).hexdigest()
def digest(x)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def receipt(label,binding):
    return {"path":"countermodel/"+label+".json","git_blob_sha":b(label),"independent_or_objective":True,"binding_sha256":digest(binding)}

def build_semantically_ungrounded_bundle():
    classes=[]
    for cid,(kinds,atoms) in RULES.items():
        comps=[]
        for i,kind in enumerate(kinds):
            path,sha=SCORERS[kind]
            row={
                "component_id":f"{cid}::{i}::{kind}",
                "kind":kind,
                "case_payload_sha256":h(f"{cid}:{i}:case"),
                "candidate_output_sha256":h(f"{cid}:{i}:output"),
                "scorer_result_sha256":h(f"{cid}:{i}:result"),
                "semantic_projection_sha256":h(f"ARBITRARY_UNINTERPRETED_TOKEN:{cid}:{i}"),
                "scorer_path":path,
                "scorer_git_blob_sha":sha,
                "base_scorer_pass":True,
            }
            row["receipt"]=receipt(f"{cid}_{i}_component",row)
            comps.append(row)
        edges=[]
        for i in range(len(comps)-1):
            left,right=comps[i],comps[i+1]
            eid=left["component_id"]+"->"+right["component_id"]
            shape=h(f"{cid}:{i}:shape")
            def run(role,sem,terminal,bridge,composite):
                row={
                    "edge_id":eid,"run_role":role,
                    "transported_semantic_sha256":sem,
                    "transported_shape_sha256":shape,
                    "downstream_terminal_semantic_sha256":terminal,
                    "downstream_case_payload_sha256":right["case_payload_sha256"],
                    "downstream_scorer_path":right["scorer_path"],
                    "downstream_scorer_git_blob_sha":right["scorer_git_blob_sha"],
                    "base_scorer_pass":True,
                    "bridge_check_pass":bridge,
                    "composite_pass":composite,
                }
                row["receipt"]=receipt(f"{cid}_{i}_{role}",row)
                return row
            edges.append({
                "edge_id":eid,
                "true_run":run("true",left["semantic_projection_sha256"],right["semantic_projection_sha256"],True,True),
                "ablated_run":run("ablated",h(f"DECOY:{cid}:{i}"),h(f"BAD:{cid}:{i}"),False,False),
                "rescue_run":run("rescue",left["semantic_projection_sha256"],right["semantic_projection_sha256"],True,True),
            })
        v3={
            "class_id":cid,
            "true_upstream_semantic_sha256":comps[0]["semantic_projection_sha256"],
            "true_terminal_semantic_sha256":comps[-1]["semantic_projection_sha256"],
            "true_run_semantics_sha256":h(cid+":true"),
            "ablated_run_semantics_sha256":h(cid+":ablated"),
            "rescue_run_semantics_sha256":h(cid+":rescue"),
        }
        v3["receipt"]=receipt(cid+"_v3",v3)
        v3_no_receipt={k:v for k,v in v3.items() if k!="receipt"}
        class_digest=digest({
            "components":[c["semantic_projection_sha256"] for c in comps],
            "edges":[e["edge_id"] for e in edges],
            "v3":v3_no_receipt,
        })
        bridges=[]
        for atom in atoms:
            binding={
                "class_id":cid,
                "atom":atom,
                "implication_rule_id":"COMPONENT_BOUND_INTERVENTIONAL_V4::"+atom.split(":",1)[1],
                "class_evidence_sha256":class_digest,
            }
            bridges.append({
                "atom":atom,
                "implication_rule_id":binding["implication_rule_id"],
                "receipt":receipt(cid+"_"+atom,binding),
            })
        classes.append({"class_id":cid,"components":comps,"edges":edges,"v3_binding":v3,"atom_bridges":bridges})
    return {"schema":INPUT_SCHEMA,"classes":classes}

def evaluate():
    bundle=build_semantically_ungrounded_bundle()
    out=compile_v4(bundle)
    accepted=out.get("status","").startswith("PASS__COMPONENT_BOUND_INTERVENTIONAL_V4")
    return {
        "schema":"PROJECT_BRAIN_MATCHED_V4_SEMANTIC_LAUNDERING_COUNTERMODEL_V1",
        "status":"COUNTERMODEL_CONFIRMED__V4_ACCEPTS_UNINTERPRETED_SEMANTIC_TOKENS" if accepted else "COUNTERMODEL_REJECTED",
        "countermodel_confirmed":accepted,
        "v4_status":out.get("status"),
        "semantic_grounding_present":False,
        "atom_meaning_executable_checker_present":False,
        "implication_soundness_proved":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
