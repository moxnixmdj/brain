"""R2 direct adequacy for exact state-keyed HTTPS JSON observation.

Bounded family only:
- one repository-local JSON state file,
- one exact URL key named by the raw goal,
- one repository-local JSON output,
- producer is the verified http.json.fetch_from_state capability,
- acceptance independently refetches the resolved HTTPS URL with curl and
  requires parsed JSON semantic equality with the producer output.

The state bytes are hash-bound before execution and must remain unchanged.
The output is transactional. This route authorizes read-only observation only;
it grants no write, browser-interaction, credential, or arbitrary-URL authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import http_json_fetch
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA="PROJECT_BRAIN_R2_HTTP_JSON_OBSERVATION_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::STATE_KEYED_HTTPS_JSON_OBSERVATION_FAMILY_V1"
CAPABILITY_ID="http.json.fetch_from_state"
ROOT=Path(__file__).resolve().parents[2]
_PATH=r"canonical/[A-Za-z0-9_.\-/]+"
_KEY=r"[A-Za-z_][A-Za-z0-9_]{0,127}"
GRAMMAR=re.compile(
    r"^Fetch JSON from URL key (?P<key>"+_KEY+r") in "
    r"(?P<state>"+_PATH+r"\.json) and save the verified result to "
    r"(?P<output>"+_PATH+r"\.json)\.?$",
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


def _find_key(value:Any,key:str,path=()):
    hits=[]
    if isinstance(value,dict):
        for k,v in value.items():
            p=path+(str(k),)
            if str(k)==key and isinstance(v,str):
                hits.append((p,v))
            hits.extend(_find_key(v,key,p))
    elif isinstance(value,list):
        for i,v in enumerate(value):
            hits.extend(_find_key(v,key,path+(str(i),)))
    return hits


def _raw_contract(goal:str)->dict[str,Any]:
    contract=compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["http.json.fetch_from_state"],
    )
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    ids=list(
        (contract.get("acceptance_contract") or {}).get("required_obligation_ids")
        or []
    )
    if not ids:
        raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
    return contract


def _curl_json(url:str, *, timeout_s:int=45, max_bytes:int=5_000_000)->dict[str,Any]:
    proc=subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            str(max(1,min(int(timeout_s),60))),
            "--header",
            "Accept: application/json",
            "--header",
            "User-Agent: ProjectBrain-IndependentJSONObservationVerifier/1",
            "--write-out",
            "\n__PB_FINAL_URL__:%{url_effective}",
            url,
        ],
        text=False,
        capture_output=True,
        timeout=max(2,min(int(timeout_s)+5,70)),
    )
    if proc.returncode!=0:
        raise RuntimeError(
            "CURL_INDEPENDENT_FETCH_FAILED:"
            +proc.stderr.decode("utf-8","replace")[-1200:]
        )
    marker=b"\n__PB_FINAL_URL__:"
    idx=proc.stdout.rfind(marker)
    if idx<0:
        raise RuntimeError("CURL_FINAL_URL_MARKER_MISSING")
    body=proc.stdout[:idx]
    final_url=proc.stdout[idx+len(marker):].decode("utf-8","strict").strip()
    if len(body)>max_bytes:
        raise RuntimeError("CURL_BODY_TOO_LARGE")
    parsed=json.loads(body.decode("utf-8"))
    return {
        "verified_transport":True,
        "producer_independent":True,
        "transport":"curl",
        "requested_url":url,
        "final_url":final_url,
        "body_bytes":len(body),
        "body_sha256":sha256(body).hexdigest(),
        "parsed_json":parsed,
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
        key=match.group("key")
        state_rel=match.group("state")
        output_rel=match.group("output")
        state_path=_inside(root,state_rel)
        output_path=_inside(root,output_rel)
        if state_path==output_path:
            raise ValueError("STATE_OUTPUT_COLLISION")
        if not state_path.is_file():
            raise ValueError("STATE_JSON_MISSING")

        state=json.loads(state_path.read_text(encoding="utf-8"))
        hits=_find_key(state,key)
        if len(hits)!=1:
            raise ValueError("URL_KEY_NOT_UNIQUE:"+str(len(hits)))
        field_path,url=hits[0]
        if not re.fullmatch(r"https://[^\s#]+",url,re.IGNORECASE):
            raise ValueError("HTTPS_URL_REQUIRED")
        lowered=url.lower()
        if "@" in url.split("://",1)[1].split("/",1)[0]:
            raise ValueError("URL_CREDENTIALS_REJECTED")
        host=url.split("://",1)[1].split("/",1)[0].split(":",1)[0].lower()
        if host in {"localhost","localhost.localdomain","127.0.0.1","::1"}:
            raise ValueError("LOCALHOST_URL_REJECTED")

        registry=live_bound.load_verified_registry()
        entry=registry.get(CAPABILITY_ID)
        if not isinstance(entry,Mapping) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            raise ValueError("HTTP_JSON_VERIFIED_BOUND_CAPABILITY_REQUIRED")
        verification=entry.get("verification")
        if (
            not isinstance(verification,Mapping)
            or verification.get("independent_semantics_equal") is not True
            or str(verification.get("independent_verifier") or "").lower()!="curl"
        ):
            raise ValueError("HTTP_JSON_CURL_INDEPENDENT_VERIFICATION_REQUIRED")

        if str(entry.get("adapter_module") or "")!="http_json_fetch":
            raise ValueError("HTTP_JSON_ADAPTER_BINDING_MISMATCH")
        goal_sha=sha256(goal.encode("utf-8")).hexdigest()
        contract=_raw_contract(goal)
        raw_ids=list(contract["acceptance_contract"]["required_obligation_ids"])
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "task_id":task_id,
            "goal":goal,
            "goal_sha256":goal_sha,
            "policy_id":goal_scoped_policy_id(CAPABILITY_ID,goal),
            "capability_id":CAPABILITY_ID,
            "state_path":state_rel,
            "state_sha256":_sha(state_path),
            "url_key":key,
            "url_field_path":list(field_path),
            "requested_url":url,
            "output_path":output_rel,
            "raw_task_contract_sha256":contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids":raw_ids,
            "producer_adapter_module":"http_json_fetch",
            "producer_registry_verification_mission":verification.get("mission_id"),
            "semantic_scope":"EXACT_STATE_KEYED_READ_ONLY_HTTPS_JSON_OBSERVATION",
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
    independent_fetch_provider=None,
)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf

    state_path=_inside(root,str(pf["state_path"]))
    output_path=_inside(root,str(pf["output_path"]))
    existed=output_path.is_file()
    original=output_path.read_bytes() if existed else None

    try:
        if _sha(state_path)!=pf["state_sha256"]:
            raise RuntimeError("STATE_DRIFT_BEFORE_EXECUTION")

        result=http_json_fetch.run(
            {
                "source_json_path":pf["state_path"],
                "url_key":pf["url_key"],
                "output_path":pf["output_path"],
                "max_bytes":5_000_000,
                "timeout_s":30,
            },
            root,
        )
        produced={
            "pass":True,
            "capability_id":CAPABILITY_ID,
            "adapter_module":"http_json_fetch",
            "result":deepcopy(dict(result)),
        }
        if (
            not isinstance(result,Mapping)
            or result.get("output_verified") is not True
            or result.get("output_path")!=pf["output_path"]
            or result.get("requested_url")!=pf["requested_url"]
        ):
            raise RuntimeError("HTTP_JSON_EXECUTION_BINDING_MISMATCH")
        if _sha(state_path)!=pf["state_sha256"]:
            raise RuntimeError("STATE_MUTATED_BY_PRODUCER")
        if not output_path.is_file():
            raise RuntimeError("OBSERVATION_OUTPUT_MISSING")

        actual=json.loads(output_path.read_text(encoding="utf-8"))
        independent=(
            independent_fetch_provider(pf["requested_url"])
            if independent_fetch_provider is not None
            else _curl_json(pf["requested_url"])
        )
        if (
            not isinstance(independent,Mapping)
            or independent.get("producer_independent") is not True
            or independent.get("parsed_json")!=actual
        ):
            raise RuntimeError("INDEPENDENT_HTTP_JSON_SEMANTIC_MISMATCH")

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
            "state_path":pf["state_path"],
            "state_sha256":pf["state_sha256"],
            "url_key":pf["url_key"],
            "requested_url":pf["requested_url"],
            "output_path":pf["output_path"],
            "output_sha256":_sha(output_path),
            "semantic_scope":pf["semantic_scope"],
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":accepted_ids,
            "raw_acceptance_obligation_count":len(accepted_ids),
            "producer_result":deepcopy(dict(produced)),
            "acceptance_receipt":{
                "verified":True,
                "producer_independent":True,
                "verifier":"curl",
                "requested_url":pf["requested_url"],
                "producer_final_url":result.get("final_url"),
                "independent_final_url":independent.get("final_url"),
                "semantic_json_equal":True,
                "state_immutability_verified":True,
                "independent_body_sha256":independent.get("body_sha256"),
            },
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "transaction_committed":True,
            "transaction_rolled_back":False,
            "authority_boundary":(
                "EXACT_STATE_KEYED_READ_ONLY_HTTPS_JSON_OBSERVATION_ONLY;"
                "URL_MUST_ALREADY_EXIST_UNIQUELY_IN_REPOSITORY_LOCAL_STATE;"
                "VERIFIED_PYTHON_STDLIB_PRODUCER_PLUS_INDEPENDENT_CURL_REFETCH;"
                "STATE_IMMUTABLE;ONE_REPOSITORY_LOCAL_JSON_OUTPUT;"
                "NO_WRITE_BROWSER_CREDENTIAL_OR_ARBITRARY_URL_AUTHORITY"
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
