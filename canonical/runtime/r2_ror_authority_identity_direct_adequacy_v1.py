"""R2 direct adequacy for exact host -> active ROR organization identity.

Bounded family only:
- one repository-local JSON object containing exactly one candidate object;
- one repository-local JSON output;
- producer is source.authority.identity.ror / source_authority_binding_ror;
- acceptance independently queries the ROR v2 API with curl and requires one
  active exact-domain record with the same ROR id, organization name, and
  matched domain.

This proves host/domain -> organization identity only. It does not prove
primary-source status, objective relevance, factual correctness, evidence
sufficiency, endorsement, or organizational independence between two sources.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import urllib.parse
from typing import Any, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import source_authority_binding_ror
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA="PROJECT_BRAIN_R2_ROR_AUTHORITY_IDENTITY_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::EXACT_ROR_AUTHORITY_IDENTITY_FAMILY_V1"
CAPABILITY_ID="source.authority.identity.ror"
ROOT=Path(__file__).resolve().parents[2]
_PATH=r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR=re.compile(
    r"^Verify ROR authority identity for candidate in (?P<input>"+_PATH+r"\.json) "
    r"and save the verified authority identity to (?P<output>"+_PATH+r"\.json)\.?$",
    re.IGNORECASE,
)


def _base(status:str, passed:bool=False)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "matched":False,
        "semantic_acceptance_complete":False,
        "actual_goal_satisfaction_verified":False,
        "direct_adequacy_authority":False,
        "execution_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _inside(root:Path, rel:str)->Path:
    rr=root.resolve()
    p=(rr/str(rel)).resolve()
    if p==rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _sha(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def _safe_host(raw:Any)->str:
    text=str(raw or "").strip()
    if not text:
        raise ValueError("SAFE_PUBLIC_HOST_REQUIRED")
    try:
        if "://" in text:
            host=urllib.parse.urlsplit(text).hostname or ""
        else:
            host=text
    except Exception as exc:
        raise ValueError("SAFE_PUBLIC_HOST_REQUIRED") from exc
    host=host.lower().strip(".")
    if host.startswith("www."):
        host=host[4:]
    if (
        not host or "." not in host
        or host in {"localhost","127.0.0.1","::1"}
        or host.endswith((".local",".internal"))
        or not re.fullmatch(r"[a-z0-9.-]+",host)
    ):
        raise ValueError("SAFE_PUBLIC_HOST_REQUIRED")
    return host


def _candidate_host(candidate:Mapping[str,Any])->str:
    for key in ("final_host","final_url","candidate_url","url","host"):
        value=candidate.get(key)
        if value:
            try:
                return _safe_host(value)
            except ValueError:
                pass
    raise ValueError("SAFE_PUBLIC_HOST_REQUIRED")


def _load_single_candidate(path:Path)->dict[str,Any]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,Mapping):
        raise ValueError("INPUT_OBJECT_REQUIRED")
    if set(obj.keys())!={"candidate"} or not isinstance(obj.get("candidate"),Mapping):
        raise ValueError("EXACT_SINGLE_CANDIDATE_ENVELOPE_REQUIRED")
    candidate=dict(obj["candidate"])
    host=_candidate_host(candidate)
    return {"candidate":candidate,"host":host}


def _raw_contract(goal:str)->dict[str,Any]:
    contract=compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["source.authority.host_organization_identity"],
    )
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
    if not ids:
        raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
    return contract


def _display_name(record:Mapping[str,Any])->str|None:
    for item in record.get("names") or []:
        if not isinstance(item,Mapping):
            continue
        types={str(x) for x in (item.get("types") or [])}
        if "ror_display" in types:
            value=" ".join(str(item.get("value") or "").split())
            if value:
                return value
    for item in record.get("names") or []:
        if not isinstance(item,Mapping):
            continue
        value=" ".join(str(item.get("value") or "").split())
        if value:
            return value
    return None


def _normalized_domains(record:Mapping[str,Any])->list[str]:
    out=[]
    for raw in record.get("domains") or []:
        try:
            host=_safe_host(raw)
        except ValueError:
            continue
        if host not in out:
            out.append(host)
    return out


def _independent_ror(host:str, *, timeout_s:int=30)->dict[str,Any]:
    query=urllib.parse.urlencode({"query.advanced":f'domains:"{host}"'})
    url="https://api.ror.org/v2/organizations?"+query
    proc=subprocess.run(
        [
            "curl","--fail","--silent","--show-error","--location",
            "--max-time",str(max(2,min(int(timeout_s),40))),
            "--header","Accept: application/json",
            "--header","User-Agent: ProjectBrain-IndependentRORIdentity/1",
            "--write-out","\n__PB_FINAL_URL__:%{url_effective}",
            url,
        ],
        text=False,
        capture_output=True,
        timeout=max(4,min(int(timeout_s)+8,50)),
    )
    if proc.returncode!=0:
        raise RuntimeError(
            "INDEPENDENT_ROR_CURL_FAILED:"
            +proc.stderr.decode("utf-8","replace")[-1200:]
        )
    marker=b"\n__PB_FINAL_URL__:"
    idx=proc.stdout.rfind(marker)
    if idx<0:
        raise RuntimeError("INDEPENDENT_ROR_FINAL_URL_MARKER_MISSING")
    raw=proc.stdout[:idx]
    final_url=proc.stdout[idx+len(marker):].decode("utf-8","strict").strip()
    if (urllib.parse.urlsplit(final_url).hostname or "").lower()!="api.ror.org":
        raise RuntimeError("INDEPENDENT_ROR_REDIRECT_OUTSIDE_API")
    data=json.loads(raw.decode("utf-8"))
    exact=[]
    for record in data.get("items") or []:
        if not isinstance(record,Mapping):
            continue
        if str(record.get("status") or "").lower()!="active":
            continue
        if host in _normalized_domains(record):
            exact.append(record)
    if len(exact)!=1:
        raise RuntimeError("INDEPENDENT_ROR_EXACT_ACTIVE_BINDING_COUNT:"+str(len(exact)))
    record=exact[0]
    ror_id=str(record.get("id") or "")
    name=_display_name(record)
    if not ror_id.startswith("https://ror.org/") or not name:
        raise RuntimeError("INDEPENDENT_ROR_RECORD_INCOMPLETE")
    return {
        "producer_independent":True,
        "verified":True,
        "host":host,
        "ror_id":ror_id,
        "organization_name":name,
        "organization_types":list(record.get("types") or []),
        "ror_domains":_normalized_domains(record),
        "final_url":final_url,
        "response_sha256":sha256(raw).hexdigest(),
    }


def preflight(
    request:Mapping[str,Any],
    *,
    repo_root:str|Path|None=None,
)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request,Mapping):
        return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
    task_id=str(request.get("task_id") or "").strip()
    goal=str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
    match=GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"),"matched":False}
    try:
        input_rel=match.group("input")
        output_rel=match.group("output")
        input_path=_inside(root,input_rel)
        output_path=_inside(root,output_rel)
        if input_path==output_path:
            raise ValueError("INPUT_OUTPUT_COLLISION")
        if not input_path.is_file():
            raise ValueError("AUTHORITY_INPUT_MISSING")
        envelope=_load_single_candidate(input_path)

        registry=live_bound.load_verified_registry()
        entry=registry.get(CAPABILITY_ID)
        if not isinstance(entry,Mapping) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            raise ValueError("ROR_VERIFIED_BOUND_CAPABILITY_REQUIRED")
        if str(entry.get("adapter_module") or "")!="source_authority_binding_ror":
            raise ValueError("ROR_ADAPTER_BINDING_MISMATCH")
        verification=entry.get("verification")
        if (
            not isinstance(verification,Mapping)
            or verification.get("status")!="INDEPENDENT_REMOTE_VERIFICATION_PASS"
            or verification.get("model_dependency_count")!=0
        ):
            raise ValueError("ROR_INDEPENDENT_QUALIFICATION_REQUIRED")

        contract=_raw_contract(goal)
        raw_ids=list(contract["acceptance_contract"]["required_obligation_ids"])
        goal_sha=sha256(goal.encode("utf-8")).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "task_id":task_id,
            "goal":goal,
            "goal_sha256":goal_sha,
            "policy_id":goal_scoped_policy_id(CAPABILITY_ID,goal),
            "capability_id":CAPABILITY_ID,
            "input_path":input_rel,
            "input_sha256":_sha(input_path),
            "candidate_host":envelope["host"],
            "output_path":output_rel,
            "raw_task_contract_sha256":contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids":raw_ids,
            "semantic_scope":"EXACT_PUBLIC_HOST_TO_ONE_ACTIVE_ROR_ORGANIZATION_IDENTITY",
            "preflight_execution_authority":False,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "reason":type(exc).__name__+":"+str(exc),
        }


def _restore(path:Path, existed:bool, original:bytes|None)->None:
    if existed:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(original or b"")
    elif path.exists():
        path.unlink()


def run(
    request:Mapping[str,Any],
    *,
    repo_root:str|Path|None=None,
    independent_provider=None,
)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf

    input_path=_inside(root,str(pf["input_path"]))
    output_path=_inside(root,str(pf["output_path"]))
    existed=output_path.is_file()
    original=output_path.read_bytes() if existed else None

    try:
        if _sha(input_path)!=pf["input_sha256"]:
            raise RuntimeError("AUTHORITY_INPUT_DRIFT_BEFORE_EXECUTION")
        envelope=_load_single_candidate(input_path)

        producer=source_authority_binding_ror.bind_candidate(
            envelope["candidate"],timeout=20
        )
        if (
            not isinstance(producer,Mapping)
            or producer.get("status")!="AUTHORITY_IDENTITY_VERIFIED"
            or producer.get("authority_status")!="VERIFIED"
            or producer.get("output_verified") is not True
            or producer.get("candidate_host")!=pf["candidate_host"]
            or producer.get("matched_domain")!=pf["candidate_host"]
        ):
            raise RuntimeError("ROR_PRODUCER_IDENTITY_NOT_VERIFIED")

        if _sha(input_path)!=pf["input_sha256"]:
            raise RuntimeError("AUTHORITY_INPUT_MUTATED_BY_PRODUCER")

        independent=(
            independent_provider(pf["candidate_host"])
            if independent_provider is not None
            else _independent_ror(pf["candidate_host"])
        )
        if (
            not isinstance(independent,Mapping)
            or independent.get("producer_independent") is not True
            or independent.get("verified") is not True
            or independent.get("host")!=pf["candidate_host"]
            or independent.get("ror_id")!=producer.get("ror_id")
            or independent.get("organization_name")!=producer.get("organization_name")
            or pf["candidate_host"] not in (independent.get("ror_domains") or [])
        ):
            raise RuntimeError("INDEPENDENT_ROR_IDENTITY_MISMATCH")

        payload={
            "schema":SCHEMA,
            "status":"ROR_AUTHORITY_IDENTITY_VERIFIED",
            "candidate_host":pf["candidate_host"],
            "ror_id":producer.get("ror_id"),
            "organization_name":producer.get("organization_name"),
            "organization_types":producer.get("organization_types") or [],
            "matched_domain":producer.get("matched_domain"),
            "authority_claim_scope":"HOST_TO_ROR_ORGANIZATION_DOMAIN_BINDING_ONLY",
            "primary_source_verification":"NOT_PERFORMED",
            "relevance_verification":"NOT_PERFORMED",
            "factual_correctness_verification":"NOT_PERFORMED",
            "evidence_sufficiency_verification":"NOT_PERFORMED",
            "organizational_independence_verification":"NOT_PERFORMED",
            "producer_verification_method":producer.get("verification_method"),
            "independent_verifier":"curl+ROR_v2_exact_active_domain_binding",
            "independent_ror_response_sha256":independent.get("response_sha256"),
            "output_verified":True,
        }
        output_path.parent.mkdir(parents=True,exist_ok=True)
        output_path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        readback=json.loads(output_path.read_text(encoding="utf-8"))
        if (
            readback.get("status")!="ROR_AUTHORITY_IDENTITY_VERIFIED"
            or readback.get("ror_id")!=producer.get("ror_id")
            or readback.get("matched_domain")!=pf["candidate_host"]
            or readback.get("output_verified") is not True
        ):
            raise RuntimeError("ROR_OUTPUT_READBACK_MISMATCH")

        contract=_raw_contract(str(request["goal"]))
        accepted_ids=list(contract["acceptance_contract"]["required_obligation_ids"])
        if accepted_ids!=pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "selected_policy_id":pf["policy_id"],
            "goal_sha256":pf["goal_sha256"],
            "input_path":pf["input_path"],
            "input_sha256":pf["input_sha256"],
            "candidate_host":pf["candidate_host"],
            "ror_id":producer.get("ror_id"),
            "organization_name":producer.get("organization_name"),
            "output_path":pf["output_path"],
            "output_sha256":_sha(output_path),
            "semantic_scope":pf["semantic_scope"],
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":accepted_ids,
            "raw_acceptance_obligation_count":len(accepted_ids),
            "acceptance_receipt":{
                "verified":True,
                "producer_independent":True,
                "verifier":"curl+ROR_v2_exact_active_domain_binding",
                "candidate_host":pf["candidate_host"],
                "ror_id":producer.get("ror_id"),
                "organization_name":producer.get("organization_name"),
                "input_immutability_verified":True,
            },
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "transaction_committed":True,
            "transaction_rolled_back":False,
            "authority_boundary":(
                "EXACT_PUBLIC_HOST_TO_ONE_ACTIVE_ROR_ORGANIZATION_IDENTITY_ONLY;"
                "NO_PARENT_DOMAIN_INFERENCE_OR_FUZZY_IDENTITY_MATCHING;"
                "NO_PRIMARY_SOURCE_RELEVANCE_FACTUAL_CORRECTNESS_EVIDENCE_SUFFICIENCY_ENDORSEMENT_OR_ORGANIZATIONAL_INDEPENDENCE_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(output_path,existed,original)
        return {
            **_base("FAIL_CLOSED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "policy_id":pf.get("policy_id"),
            "goal_sha256":pf.get("goal_sha256"),
            "reason":type(exc).__name__+":"+str(exc),
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "transaction_rolled_back":True,
        }
