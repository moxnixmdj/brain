"""Independent private-repo verifier for zero-reality ownership promotion.

This implementation intentionally does not import the promotion compiler.
"""
from __future__ import annotations
import ast, hashlib, json, sys
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
OWNED="VERIFIED_OWNED_EQUAL_OR_BETTER"
STDLIB=set(getattr(sys,"stdlib_module_names",()))|{"__future__","typing"}
FORBIDDEN={"__import__","eval","exec","compile","importlib.import_module",
           "subprocess.run","subprocess.call","subprocess.Popen","os.system"}
TARGETS={
 "SUBAGENT_DELEGATION_AND_COORDINATION":{
   "artifact":"canonical/runtime/delegation_whole_scope_candidate_v2.py",
   "sha":"f1a93ee66d90093de61dc17c6ebf2e24073df522",
   "receipt":"canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
   "pointer":"/exact_brain_blobs/canonical~1runtime~1delegation_whole_scope_candidate_v2.py",
   "acceptance":"canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
 },
 "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY":{
   "artifact":"canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
   "sha":"28940387bd6c11671035ad9201e37bba13fd9bc9",
   "receipt":"canonical/verification/P1_UNIVERSAL_GENERATOR_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
   "pointer":"exact_brain_bytes.candidate_v7_blob",
   "acceptance":"canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"
 },
 "TOOL_DISCOVERY_SELECTION_AND_LEARNING":{
   "artifact":"canonical/runtime/tool_discovery_information_safe_candidate.py",
   "sha":"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
   "receipt":"canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
   "pointer":"/exact_brain_blobs/canonical~1runtime~1tool_discovery_information_safe_candidate.py",
   "acceptance":"canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
 }
}

def j(rel:str)->dict[str,Any]:
    x=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    assert isinstance(x,dict)
    return x

def sha(rel:str)->str:
    b=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def ptr(d:Mapping[str,Any],p:str)->Any:
    parts=([x.replace("~1","/").replace("~0","~") for x in p.split("/")[1:]]
           if p.startswith("/") else p.split("."))
    x:Any=d
    for k in parts: x=x[k]
    return x

def ip(d:Mapping[str,Any])->bool:
    s=d.get("status")
    return isinstance(s,str) and s.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")

def cname(n:ast.Call)->str:
    f=n.func; a=[]
    while isinstance(f,ast.Attribute): a.append(f.attr); f=f.value
    if isinstance(f,ast.Name): a.append(f.id)
    return ".".join(reversed(a))

def provider_clean(rel:str)->tuple[bool,list[str]]:
    e=[]; tree=ast.parse((ROOT/rel).read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            for a in n.names:
                if a.name.split(".",1)[0] not in STDLIB: e.append("NON_STDLIB:"+a.name)
        elif isinstance(n,ast.ImportFrom) and n.level==0:
            top=(n.module or "").split(".",1)[0]
            if top and top not in STDLIB: e.append("NON_STDLIB:"+(n.module or ""))
        elif isinstance(n,ast.Call) and cname(n) in FORBIDDEN:
            e.append("FORBIDDEN_CALL:"+cname(n))
    return not e,sorted(set(e))

def verify()->dict[str,Any]:
    closure=j("canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json")
    matrix=j("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
    cr={x["id"]:x for x in closure["families"]}; mr={x["family"]:x for x in matrix["rows"]}
    rows=[]
    for fam,s in TARGETS.items():
        e=[]; c=cr[fam]; m=mr[fam]
        if not(c.get("opus55_acceptance_state")=="PASS" and c.get("opus55_acceptance_calibrated") is True and c.get("unresolved")==[]):
            e.append("ACCEPTANCE_NOT_CLOSED")
        if m.get("status")==OWNED: e.append("ALREADY_OWNED_UNEXPECTED_FOR_CANDIDATE")
        a=j(s["acceptance"]); r=j(s["receipt"])
        if not ip(a): e.append("ACCEPTANCE_RECEIPT_NOT_INDEPENDENT")
        if not ip(r): e.append("BINDING_RECEIPT_NOT_INDEPENDENT")
        if sha(s["artifact"])!=s["sha"]: e.append("ARTIFACT_HASH_MISMATCH")
        if ptr(r,s["pointer"])!=s["sha"]: e.append("RECEIPT_BINDING_MISMATCH")
        ok,pe=provider_clean(s["artifact"])
        if not ok: e.extend(pe)
        rows.append({"family":fam,"pass":not e,"errors":sorted(set(e)),
                     "artifact":s["artifact"],"artifact_sha":s["sha"],
                     "provider_clean":ok})
    passed=all(x["pass"] for x in rows) and len(rows)==3
    return {
      "schema":"PROJECT_BRAIN_OWNERSHIP_PROMOTION_INDEPENDENT_PRIVATE_VERIFICATION_V1",
      "status":"PASS" if passed else "FAIL_CLOSED",
      "verified_family_count":sum(1 for x in rows if x["pass"]),
      "families":rows,
      "candidate_owned_count_before":2,
      "candidate_owned_count_after":5 if passed else 2,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "promotion_authority":False,
      "rule":"INDEPENDENT_IMPLEMENTATION__NO_COMPILER_IMPORT__EXACT_HASH_BINDING__CURRENT_PROVIDER_AUDIT"
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["status"]=="PASS" else 1)
