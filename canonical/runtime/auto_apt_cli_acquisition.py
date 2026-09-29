#!/usr/bin/env python3
"""Dispatch a conservative autonomous APT-CLI capability acquisition.

Supported class: a zero-cost, zero-secret, low-friction Ubuntu CLI whose
help can be compiled into the generic text -> output-file contract recognized
by cli_contract_inference.py. Unsupported classes fail closed.
"""
from __future__ import annotations
import hashlib,json,pathlib,re

import apt_cli_probe
import capability_discovery
import cli_contract_inference
import goal_compiler


class AutoAcquisitionFailure(RuntimeError):
    def __init__(self,code,detail=None):
        self.code=code; self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


GENERIC_KEYWORDS={"generate","image","text","save","output","input","code","file","create","make"}

def _origin_mission_sha256(root,mission_path):
    root=pathlib.Path(root).resolve()
    missions_root=(root/"canonical"/"astra_runtime"/"missions").resolve()
    mission=(root/str(mission_path)).resolve()
    if mission.parent!=missions_root:
        raise AutoAcquisitionFailure("APT_ORIGIN_MISSION_PATH_INVALID",str(mission_path))
    if not mission.is_file():
        raise AutoAcquisitionFailure("APT_ORIGIN_MISSION_MISSING",str(mission_path))
    return hashlib.sha256(mission.read_bytes()).hexdigest()



def _slug(value):
    out=re.sub(r"[^a-z0-9]+","-",str(value).lower()).strip("-")
    if not out:
        raise AutoAcquisitionFailure("ACQUISITION_SLUG_EMPTY")
    return out[:80]


def _render(value,inputs):
    if isinstance(value,dict):
        return {k:_render(v,inputs) for k,v in value.items()}
    if isinstance(value,list):
        return [_render(v,inputs) for v in value]
    if isinstance(value,str):
        out=value
        for key,val in inputs.items():
            out=out.replace("$"+"{input."+str(key)+"}",str(val))
        if "$"+"{input." in out:
            raise AutoAcquisitionFailure("ACQUISITION_INPUT_UNBOUND",out)
        return out
    return value


def _bind_contract_inputs(goal,root,contract):
    required=list(contract.get("required_inputs") or [])
    if set(required)!={"text","output_path"}:
        raise AutoAcquisitionFailure("ACQUISITION_CONTRACT_CLASS_UNSUPPORTED",",".join(required))
    text=goal_compiler._extract_text_argument(goal)
    paths=goal_compiler._repo_paths(goal,root)
    if len(paths)!=1:
        raise AutoAcquisitionFailure("ACQUISITION_OUTPUT_PATH_AMBIGUOUS",str(len(paths)))
    return {"text":text,"output_path":paths[0][0]}


def _format_terms(goal):
    out=[]
    for ext in re.findall(r"\.([A-Za-z0-9]{2,10})(?=[\s.,;:!?)]|$)",str(goal or "")):
        ext=ext.lower()
        if ext not in out:
            out.append(ext)
    return out


def _acquisition_terms(goal):
    out=[
        t for t in capability_discovery.effect_queries(goal)
        if t not in GENERIC_KEYWORDS and not t.isdigit()
    ]
    for ext in _format_terms(goal):
        if ext not in out:
            out.append(ext)
    return out


def _viable_candidates(discovery, goal=""):
    viable=[]
    goal_lower=str(goal or "").lower()
    producer_intent=any(w in goal_lower for w in ("generate","create","make","render","encode","save"))
    producer_words=("generate","generator","encode","encoder","create","render","write","output")
    consumer_words=("decode","decoder","scan","scanner","reader","inspect","viewer")
    goal_terms=_acquisition_terms(goal)
    for provider_rank,c in enumerate(discovery.get("candidates",[]),1):
        if c.get("binding_kind")!="apt":
            continue
        if not c.get("zero_cost_eligible",False):
            continue
        if int(c.get("required_secret_count",0))!=0:
            continue
        if int(c.get("integration_friction",99))!=0:
            continue
        if not c.get("version") or not re.fullmatch(r"[0-9a-f]{64}",str(c.get("archive_sha256") or "")):
            continue
        x=dict(c)
        role_blob=(" "+str(c.get("name") or "")+" "+str(c.get("description") or "")+" ").lower()
        role_score=0.0
        object_matches=sum(1 for t in goal_terms if t in role_blob or t in (c.get("matched_terms") or []))
        if producer_intent:
            if any(w in role_blob for w in producer_words):
                role_score+=24
            if object_matches:
                role_score+=32*object_matches
            else:
                role_score-=36
            if any(w in role_blob for w in consumer_words) and not any(w in role_blob for w in producer_words):
                role_score-=28
        x["_acquisition_role_score"]=role_score
        x["_acquisition_object_matches"]=object_matches
        x["_acquisition_provider_rank"]=provider_rank
        viable.append(x)
    if not viable:
        raise AutoAcquisitionFailure("NO_LOW_FRICTION_APT_CLI_CANDIDATE")
    viable.sort(key=lambda c:(
        -float(c.get("_acquisition_role_score",0)),
        -int(c.get("_acquisition_object_matches",0)),
        int(c.get("_acquisition_provider_rank",10**9)),
        str(c.get("name","")),
    ))
    return viable[:12]

def _merge_role_conditioned_apt(discovery,goal):
    merged=json.loads(json.dumps(discovery))
    candidates=list(merged.get("candidates") or [])
    goal_lower=str(goal or "").lower()
    producer_intent=any(w in goal_lower for w in ("generate","create","make","render","encode","save"))
    goal_terms=_acquisition_terms(goal)
    role_queries=[]
    if producer_intent:
        # Output suffixes are direct evidence of the requested capability class
        # and survive even when prose contains low-information scaffolding.
        role_queries.extend(_format_terms(goal)[:2])
        if goal_terms:
            role_queries.append(" ".join(goal_terms[:2]))
    role_queries=list(dict.fromkeys(q for q in role_queries if q.strip()))

    role_results=[]
    by_key={}
    for item in candidates:
        key=(str(item.get("discovery_source") or ""),str(item.get("name") or ""),str(item.get("version") or ""))
        by_key[key]=item
    for role_query in role_queries:
        result=capability_discovery.search_apt_packages(role_query,limit=24)
        role_results.append(result)
        for item in result.get("candidates") or []:
            key=(str(item.get("discovery_source") or ""),str(item.get("name") or ""),str(item.get("version") or ""))
            prior=by_key.get(key)
            if prior is None or float(item.get("score",0))>float(prior.get("score",0)):
                by_key[key]=item
    merged["candidates"]=list(by_key.values())
    merged["_role_conditioned_apt_discovery"]=role_results
    merged["_role_conditioned_queries"]=role_queries
    return merged


def dispatch(goal,mission_id,mission_path,root,discovery=None):
    root=pathlib.Path(root).resolve()
    origin_mission_sha256=_origin_mission_sha256(root,mission_path)
    # On the fast path, start from an empty pool and let the role-conditioned
    # APT search supply causally relevant candidates. Callers may pass a broad
    # discovery result only as a fallback after the targeted route fails.
    discovery=discovery if discovery is not None else {"candidates":[]}
    discovery=_merge_role_conditioned_apt(discovery,goal)
    candidates=_viable_candidates(discovery,goal)
    diag_rel=f"canonical/astra_runtime/evidence/{mission_id}__AUTO_APT_CLI_ACQUISITION.json"
    diag_path=root/diag_rel
    diag_path.parent.mkdir(parents=True,exist_ok=True)
    diagnostic={
      "schema":"PROJECT_BRAIN_AUTO_APT_CLI_ACQUISITION_EVIDENCE_V1",
      "mission_id":mission_id,
      "goal":goal,
      "status":"SUPPLIER_CONTRACT_RACE",
      "role_conditioned_discovery":discovery.get("_role_conditioned_apt_discovery"),
      "attempts":[]
    }
    candidate=probe=contract=None
    for cand in candidates:
        attempt={"supplier":cand}
        try:
            pkg=str(cand["name"])
            ver=str(cand["version"])
            digest=str(cand["archive_sha256"]).lower()
            pr=apt_cli_probe.probe(pkg,ver,digest,root)
            attempt["probe"]=pr
        except Exception as exc:
            attempt["status"]="PROBE_FAILED"
            attempt["error"]=type(exc).__name__+":"+str(exc)
            diagnostic["attempts"].append(attempt)
            diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
            continue
        try:
            ct=cli_contract_inference.infer_contract(pr,goal)
        except Exception as exc:
            attempt["status"]="CONTRACT_REJECTED"
            attempt["error"]=type(exc).__name__+":"+str(exc)
            diagnostic["attempts"].append(attempt)
            diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
            continue
        attempt["status"]="CONTRACT_ACCEPTED"
        attempt["contract"]=ct
        diagnostic["attempts"].append(attempt)
        candidate,probe,contract=cand,pr,ct
        break
    if candidate is None:
        diagnostic["status"]="NO_COMPATIBLE_CONTRACT"
        diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        summary=[{"name":a.get("supplier",{}).get("name"),"status":a.get("status"),"error":a.get("error")} for a in diagnostic["attempts"]]
        raise AutoAcquisitionFailure("NO_COMPATIBLE_APT_CLI_CONTRACT",json.dumps(summary,sort_keys=True)[:3000])
    diagnostic["status"]="CONTRACT_INFERRED"
    diagnostic["selected_supplier"]=candidate
    diagnostic["probe"]=probe
    diagnostic["contract"]=contract
    diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    package=str(candidate["name"])
    version=str(candidate["version"])
    sha=str(candidate["archive_sha256"]).lower()
    inputs=_bind_contract_inputs(goal,root,contract)
    argv=_render(contract["argv_template"],inputs)
    verification_args={
      "argv":argv,
      "output_path":_render(contract["output_path_template"],inputs),
      "output_prefix_hex":contract["output_prefix_hex"],
      "output_text_utf8":bool(contract.get("output_text_utf8",False)),
      "timeout_s":int(contract.get("timeout_s",60))
    }
    slug=_slug(package)
    cap_id="auto.apt."+slug
    effect="auto.effect."+slug
    q=capability_discovery.effect_queries(goal)
    keywords=[x for x in q if x not in GENERIC_KEYWORDS]
    if not keywords:
        keywords=q
    entry={
      "provides":[effect],
      "requires":[],
      "keywords":keywords,
      "cost":1,
      "platforms":["linux"],
      "limitations":[
        "Automatically acquired from Ubuntu package metadata and CLI help.",
        "Only the verified text-to-output-file invocation contract is promoted."
      ],
      "adapter_module":"cli_command",
      "entrypoint":"run",
      "action_template":{
        "type":"invoke_capability",
        "args":{
          "capability_id":cap_id,
          "argv":contract["argv_template"],
          "output_path":contract["output_path_template"],
          "output_prefix_hex":contract["output_prefix_hex"],
          "output_text_utf8":bool(contract.get("output_text_utf8",False)),
          "timeout_s":int(contract.get("timeout_s",60))
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True}
      },
      "source":{
        "type":"apt","origin":"Ubuntu",
        "packages":[{"name":package,"version":version,"sha256":sha}]
      },
      "incremental_spend_usd":0,
      "status":"BOUND_PENDING_INDEPENDENT_VERIFICATION",
      "autogenerated":{
        "schema":"PROJECT_BRAIN_AUTO_APT_CLI_BINDING_V1",
        "origin_mission_id":mission_id,
        "origin_goal":goal,
        "supplier_score":candidate.get("score"),
        "integration_friction":candidate.get("integration_friction"),
        "contract_evidence":contract.get("evidence")
      }
    }
    fingerprint=hashlib.sha256((mission_id+"\n"+cap_id+"\n"+json.dumps(verification_args,sort_keys=True)).encode()).hexdigest()[:12]
    pending_rel=f"canonical/astra_runtime/pending_bindings/{mission_id}__{slug}__{fingerprint}.json"
    verify_rel=f"canonical/astra_runtime/evidence/{mission_id}__{slug}__{fingerprint}__AUTO_VERIFY.json"
    verify_mid="ASTRA-AUTO-VERIFY-"+slug.upper()+"-"+fingerprint.upper()
    pending={
      "schema":"PROJECT_BRAIN_PENDING_AUTO_BINDING_V1",
      "capability_id":cap_id,
      "effect":effect,
      "goal":goal,
      "origin_mission_id":mission_id,
      "origin_mission_path":mission_path,
      "origin_mission_sha256_at_acquisition":origin_mission_sha256,
      "selected_supplier":candidate,
      "probe":probe,
      "contract":contract,
      "inputs":inputs,
      "verification_args":verification_args,
      "semantic_verification":{
        "required":True,
        "reason":"Auto-synthesized text-to-binary-file capability must prove semantic content independently of the producer.",
        "expected_text":inputs.get("text"),
        "goal":goal,
        "status":"PENDING_VERIFIER_ACQUISITION"
      },
      "registry_entry":entry,
      "verification_mission_id":verify_mid,
      "verification_result_path":verify_rel,
      "status":"PENDING_INDEPENDENT_VERIFICATION"
    }
    pp=root/pending_rel
    pp.parent.mkdir(parents=True,exist_ok=True)
    pp.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    verifier={
      "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_MISSION_V1",
      "mission_id":verify_mid,
      "purpose":"Fresh independently-invoked effect verification and promotion of an automatically synthesized APT CLI capability binding.",
      "goal":"Verify the pending capability effect, promote only on verified output, then trigger replay of the originating mission.",
      "steps":[
        {
          "id":"verify-pending-cli-binding",
          "adapter":"shell",
          "command":f"set -euo pipefail\npython canonical/runtime/verify_pending_cli_binding.py {pending_rel} {verify_rel}",
          "verify":{"type":"stdout_contains","text":"PENDING_CLI_BINDING_EFFECT_VERIFIED"}
        },
        {
          "id":"promote-and-replay",
          "adapter":"shell",
          "command":f"set -euo pipefail\npython canonical/runtime/promote_pending_binding.py {pending_rel} {verify_rel}",
          "verify":{"type":"stdout_contains","text":"PENDING_CAPABILITY_PROMOTED"}
        }
      ],
      "constraints":{
        "incremental_spend_usd":0,
        "model_controller_required":False,
        "fresh_verification_invocation_required":True,
        "allow_registry_mutation":True,
        "auto_generated_from_mission":mission_id
      }
    }
    vm_rel=f"canonical/astra_runtime/missions/{verify_mid.replace('-','_')}.json"
    vp=root/vm_rel
    if vp.exists():
        raise AutoAcquisitionFailure("VERIFICATION_MISSION_ALREADY_EXISTS",vm_rel)
    vp.write_text(json.dumps(verifier,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {
      "status":"ACQUISITION_DISPATCHED",
      "capability_id":cap_id,
      "effect":effect,
      "supplier":package,
      "pending_binding_path":pending_rel,
      "verification_mission_path":vm_rel,
      "verification_mission_id":verify_mid,
      "keywords":keywords,
      "acquisition_evidence_path":diag_rel
    }
