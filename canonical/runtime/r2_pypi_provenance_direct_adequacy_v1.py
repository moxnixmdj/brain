"""R2 direct adequacy for exact PyPI pinned-artifact provenance audits.

Bounded family only:
- one repository-local canonical selection JSON,
- one repository-local PyPI metadata JSON,
- one repository-local audit report JSON,
- producer is the verified pypi.provenance.audit_live_artifact adapter,
- acceptance independently refetches canonical PyPI metadata with curl,
  independently re-downloads the exact wheel, and requires the recorded,
  live-metadata, producer-downloaded, and independent-downloaded SHA-256
  values to be identical.

Selection and metadata bytes are immutable. The report is transactional.
No package installation, arbitrary host, credential, or mutating network
authority is granted.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping
from urllib.parse import urlsplit

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import pypi_provenance_audit
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA="PROJECT_BRAIN_R2_PYPI_PROVENANCE_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::PYPI_PINNED_ARTIFACT_PROVENANCE_FAMILY_V1"
CAPABILITY_ID="pypi.provenance.audit_live_artifact"
ROOT=Path(__file__).resolve().parents[2]
_PATH=r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR=re.compile(
    r"^Audit PyPI provenance using selection (?P<selection>"+_PATH+r"\.json), "
    r"metadata (?P<metadata>"+_PATH+r"\.json), and save the verified report to "
    r"(?P<report>"+_PATH+r"\.json)\.?$",
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


def _https_host(url:str, expected_host:str)->str:
    p=urlsplit(str(url or ""))
    if (
        p.scheme!="https"
        or not p.hostname
        or p.username
        or p.password
        or p.fragment
        or p.hostname.lower()!=expected_host
    ):
        raise ValueError("HTTPS_CANONICAL_HOST_REQUIRED:"+expected_host)
    return str(url)


def _curl_bytes(url:str, *, timeout_s:int=60, max_bytes:int=20_000_000)->tuple[bytes,str]:
    proc=subprocess.run(
        [
            "curl","--fail","--silent","--show-error","--location",
            "--max-time",str(max(1,min(int(timeout_s),120))),
            "--header","User-Agent: ProjectBrain-IndependentPyPIProvenance/1",
            "--write-out","\n__PB_FINAL_URL__:%{url_effective}",
            url,
        ],
        text=False,
        capture_output=True,
        timeout=max(2,min(int(timeout_s)+10,130)),
    )
    if proc.returncode!=0:
        raise RuntimeError(
            "CURL_FETCH_FAILED:"
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
    return body,final_url


def _selection_semantics(selection:Any)->dict[str,str]:
    if not isinstance(selection,Mapping):
        raise ValueError("SELECTION_NOT_OBJECT")
    cid=str(selection.get("id") or "").strip()
    record=selection.get("record")
    if not isinstance(record,Mapping):
        raise ValueError("SELECTION_RECORD_MISSING")
    source=record.get("source")
    if not isinstance(source,Mapping) or source.get("type")!="pypi":
        raise ValueError("PYPI_SOURCE_REQUIRED")
    project=str(source.get("project") or "").strip()
    version=str(source.get("version") or "").strip()
    filename=str(source.get("wheel_filename") or "").strip()
    recorded_hash=str(source.get("wheel_sha256") or "").strip().lower()
    metadata_url=_https_host(str(source.get("metadata_url") or ""),"pypi.org")
    if not cid or not project or not version or not filename:
        raise ValueError("PYPI_SELECTION_METADATA_INCOMPLETE")
    if not re.fullmatch(r"[0-9a-f]{64}",recorded_hash):
        raise ValueError("PYPI_RECORDED_HASH_INVALID")
    if "/" in filename or "\\" in filename or not filename.endswith(".whl"):
        raise ValueError("PYPI_WHEEL_FILENAME_INVALID")
    return {
        "audited_capability_id":cid,
        "project":project,
        "version":version,
        "wheel_filename":filename,
        "recorded_hash":recorded_hash,
        "metadata_url":metadata_url,
    }


def _metadata_semantics(metadata:Any, expected:Mapping[str,str])->dict[str,str]:
    if not isinstance(metadata,Mapping):
        raise ValueError("PYPI_METADATA_NOT_OBJECT")
    info=metadata.get("info")
    if not isinstance(info,Mapping):
        raise ValueError("PYPI_METADATA_INFO_MISSING")
    if str(info.get("name") or "").lower()!=expected["project"].lower():
        raise ValueError("PYPI_PROJECT_MISMATCH")
    if str(info.get("version") or "")!=expected["version"]:
        raise ValueError("PYPI_VERSION_MISMATCH")
    urls=metadata.get("urls")
    if not isinstance(urls,list):
        raise ValueError("PYPI_URLS_MISSING")
    matches=[
        row for row in urls
        if isinstance(row,Mapping)
        and str(row.get("filename") or "")==expected["wheel_filename"]
    ]
    if len(matches)!=1:
        raise ValueError("PYPI_WHEEL_NOT_UNIQUE:"+str(len(matches)))
    artifact=matches[0]
    digest=str(((artifact.get("digests") or {}).get("sha256") or "")).lower()
    if not re.fullmatch(r"[0-9a-f]{64}",digest):
        raise ValueError("PYPI_LIVE_DIGEST_INVALID")
    artifact_url=_https_host(str(artifact.get("url") or ""),"files.pythonhosted.org")
    return {"live_metadata_hash":digest,"artifact_url":artifact_url}


def _raw_contract(goal:str)->dict[str,Any]:
    contract=compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["pypi.provenance.audit_live_artifact"],
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


def _independent_verify(pf:Mapping[str,Any])->dict[str,Any]:
    metadata_raw,metadata_final=_curl_bytes(
        pf["metadata_url"],timeout_s=60,max_bytes=5_000_000
    )
    metadata=json.loads(metadata_raw.decode("utf-8"))
    live=_metadata_semantics(metadata,pf)
    artifact_raw,artifact_final=_curl_bytes(
        live["artifact_url"],timeout_s=120,max_bytes=50_000_000
    )
    downloaded_hash=sha256(artifact_raw).hexdigest()
    verified=(
        pf["recorded_hash"]
        == live["live_metadata_hash"]
        == downloaded_hash
    )
    return {
        "verified":verified,
        "producer_independent":True,
        "transport":"curl",
        "metadata_final_url":metadata_final,
        "artifact_final_url":artifact_final,
        "fresh_metadata_sha256":sha256(metadata_raw).hexdigest(),
        "recorded_hash":pf["recorded_hash"],
        "live_metadata_hash":live["live_metadata_hash"],
        "downloaded_artifact_hash":downloaded_hash,
        "artifact_bytes":len(artifact_raw),
        "artifact_url":live["artifact_url"],
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
        selection_rel=match.group("selection")
        metadata_rel=match.group("metadata")
        report_rel=match.group("report")
        selection_path=_inside(root,selection_rel)
        metadata_path=_inside(root,metadata_rel)
        report_path=_inside(root,report_rel)
        if len({selection_path,metadata_path,report_path})!=3:
            raise ValueError("PROVENANCE_PATH_COLLISION")
        if not selection_path.is_file() or not metadata_path.is_file():
            raise ValueError("PROVENANCE_INPUT_MISSING")

        selection=json.loads(selection_path.read_text(encoding="utf-8"))
        semantic=_selection_semantics(selection)
        metadata=json.loads(metadata_path.read_text(encoding="utf-8"))
        live=_metadata_semantics(metadata,semantic)
        if semantic["recorded_hash"]!=live["live_metadata_hash"]:
            raise ValueError("LOCAL_METADATA_DIGEST_DISAGREES_WITH_RECORDED_HASH")

        registry=live_bound.load_verified_registry()
        entry=registry.get(CAPABILITY_ID)
        if not isinstance(entry,Mapping) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            raise ValueError("PYPI_AUDIT_VERIFIED_BOUND_CAPABILITY_REQUIRED")
        if str(entry.get("adapter_module") or "")!="pypi_provenance_audit":
            raise ValueError("PYPI_AUDIT_ADAPTER_BINDING_MISMATCH")
        verification=entry.get("verification")
        if (
            not isinstance(verification,Mapping)
            or verification.get("independent_report_assertion") is not True
            or str(verification.get("independent_verifier") or "").lower()!="curl"
        ):
            raise ValueError("PYPI_AUDIT_CURL_INDEPENDENT_VERIFICATION_REQUIRED")

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
            "selection_path":selection_rel,
            "selection_sha256":_sha(selection_path),
            "metadata_path":metadata_rel,
            "metadata_sha256":_sha(metadata_path),
            "report_path":report_rel,
            **semantic,
            "artifact_url_from_local_metadata":live["artifact_url"],
            "raw_task_contract_sha256":contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids":raw_ids,
            "semantic_scope":"EXACT_CANONICAL_PYPI_PINNED_WHEEL_PROVENANCE_AUDIT",
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
    independent_verifier=None,
)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf

    selection_path=_inside(root,str(pf["selection_path"]))
    metadata_path=_inside(root,str(pf["metadata_path"]))
    report_path=_inside(root,str(pf["report_path"]))
    existed=report_path.is_file()
    original=report_path.read_bytes() if existed else None

    try:
        if (
            _sha(selection_path)!=pf["selection_sha256"]
            or _sha(metadata_path)!=pf["metadata_sha256"]
        ):
            raise RuntimeError("PROVENANCE_INPUT_DRIFT_BEFORE_EXECUTION")

        producer=pypi_provenance_audit.run(
            {
                "selection_path":pf["selection_path"],
                "metadata_path":pf["metadata_path"],
                "report_path":pf["report_path"],
                "max_bytes":20_000_000,
                "timeout_s":60,
            },
            root,
        )
        if (
            not isinstance(producer,Mapping)
            or producer.get("verified") is not True
            or producer.get("report_path")!=pf["report_path"]
            or producer.get("capability_id")!=pf["audited_capability_id"]
            or producer.get("recorded_hash")!=pf["recorded_hash"]
            or producer.get("live_metadata_hash")!=pf["recorded_hash"]
            or producer.get("downloaded_artifact_hash")!=pf["recorded_hash"]
        ):
            raise RuntimeError("PYPI_PRODUCER_AUDIT_BINDING_MISMATCH")
        if (
            _sha(selection_path)!=pf["selection_sha256"]
            or _sha(metadata_path)!=pf["metadata_sha256"]
        ):
            raise RuntimeError("PROVENANCE_INPUT_MUTATED_BY_PRODUCER")
        if not report_path.is_file():
            raise RuntimeError("PROVENANCE_REPORT_MISSING")

        report=json.loads(report_path.read_text(encoding="utf-8"))
        independent=(
            independent_verifier(pf)
            if independent_verifier is not None
            else _independent_verify(pf)
        )
        if (
            not isinstance(independent,Mapping)
            or independent.get("producer_independent") is not True
            or independent.get("verified") is not True
            or independent.get("recorded_hash")!=pf["recorded_hash"]
            or independent.get("live_metadata_hash")!=pf["recorded_hash"]
            or independent.get("downloaded_artifact_hash")!=pf["recorded_hash"]
        ):
            raise RuntimeError("INDEPENDENT_PYPI_PROVENANCE_VERIFICATION_FAILED")
        required_report={
            "capability_id":pf["audited_capability_id"],
            "project":pf["project"],
            "pinned_version":pf["version"],
            "wheel_filename":pf["wheel_filename"],
            "recorded_hash":pf["recorded_hash"],
            "live_metadata_hash":pf["recorded_hash"],
            "downloaded_artifact_hash":pf["recorded_hash"],
            "metadata_url":pf["metadata_url"],
            "verified":True,
        }
        for key,value in required_report.items():
            if report.get(key)!=value:
                raise RuntimeError("PROVENANCE_REPORT_FIELD_MISMATCH:"+key)

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
            "selection_path":pf["selection_path"],
            "selection_sha256":pf["selection_sha256"],
            "metadata_path":pf["metadata_path"],
            "metadata_sha256":pf["metadata_sha256"],
            "report_path":pf["report_path"],
            "report_sha256":_sha(report_path),
            "project":pf["project"],
            "pinned_version":pf["version"],
            "wheel_filename":pf["wheel_filename"],
            "verified_wheel_sha256":pf["recorded_hash"],
            "semantic_scope":pf["semantic_scope"],
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":accepted_ids,
            "raw_acceptance_obligation_count":len(accepted_ids),
            "producer_result":deepcopy(dict(producer)),
            "acceptance_receipt":{
                "verified":True,
                "producer_independent":True,
                "verifier":"curl",
                "recorded_hash":pf["recorded_hash"],
                "producer_live_metadata_hash":producer.get("live_metadata_hash"),
                "producer_downloaded_artifact_hash":producer.get("downloaded_artifact_hash"),
                "independent_live_metadata_hash":independent.get("live_metadata_hash"),
                "independent_downloaded_artifact_hash":independent.get("downloaded_artifact_hash"),
                "selection_immutability_verified":True,
                "metadata_immutability_verified":True,
                "independent_artifact_bytes":independent.get("artifact_bytes"),
            },
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "transaction_committed":True,
            "transaction_rolled_back":False,
            "authority_boundary":(
                "EXACT_CANONICAL_PYPI_PINNED_WHEEL_PROVENANCE_AUDIT_ONLY;"
                "METADATA_HOST_PYPI_ORG;ARTIFACT_HOST_FILES_PYTHONHOSTED_ORG;"
                "VERIFIED_PRODUCER_PLUS_INDEPENDENT_CURL_METADATA_AND_WHEEL_REDOWNLOAD;"
                "SELECTION_AND_METADATA_IMMUTABLE;ONE_REPOSITORY_LOCAL_REPORT;"
                "NO_INSTALLATION_CREDENTIAL_ARBITRARY_HOST_OR_MUTATING_NETWORK_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(report_path,existed,original)
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
