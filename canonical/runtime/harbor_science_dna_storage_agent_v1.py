"""Donor-free Harbor adapter for Brain's DNA storage capability."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import shlex
from typing import Any

from canonical.runtime import dna_storage_codec_v1 as codec
from canonical.runtime import dna_storage_task_adapter_v1 as adapter
from canonical.runtime.harbor_command_policy import validate_environment_command
from canonical.runtime.harbor_environment_transport_v2 import HarborEnvironmentTransport
from execution_guard import terminal_agent_start_barrier_v1 as start_barrier
from execution_guard.logical_attempt_identity_v2 import logical_attempt_id as canonical_logical_attempt_id

try:
    from harbor.agents.base import BaseAgent
    from harbor.agents.capabilities import AgentCapabilities
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
except ImportError:
    BaseAgent=object
    BaseEnvironment=Any
    AgentContext=Any
    class AgentCapabilities:
        def __init__(self,**kwargs:Any)->None: self.kwargs=kwargs

SCHEMA="PROJECT_BRAIN_HARBOR_SCIENCE_DNA_STORAGE_AGENT_V1"
MODEL_DEPENDENCY_COUNT=0
NETWORK_DEPENDENCY_COUNT=0
REMOTE_ROOT="/tmp/project_brain_dna_storage_v1"
REMOTE_REQUEST=REMOTE_ROOT+"/request.json"
MAX_TRANSFER_CHUNK=6000


def logical_attempt_id_for_goal(goal:str)->str:
    if not isinstance(goal,str) or not goal.strip():
        raise ValueError("SCIENCE_GOAL_REQUIRED")
    slot=str(os.environ.get("BRAIN_SLOT_ID") or "").strip()
    digest=str(os.environ.get("BRAIN_TASK_DIGEST") or "").strip()
    carried=str(os.environ.get("BRAIN_LOGICAL_ATTEMPT_ID") or "").strip()
    claim=str(os.environ.get("BRAIN_EXECUTION_CLAIM_BINDING_DIGEST") or "").strip()
    if not slot: raise RuntimeError("BRAIN_SLOT_ID_REQUIRED")
    if not digest: raise RuntimeError("BRAIN_TASK_DIGEST_REQUIRED")
    if not carried: raise RuntimeError("BRAIN_LOGICAL_ATTEMPT_ID_REQUIRED")
    if not claim: raise RuntimeError("BRAIN_EXECUTION_CLAIM_BINDING_DIGEST_REQUIRED")
    expected=canonical_logical_attempt_id(
        slot_id=slot,task_digest=digest,execution_claim_binding_digest=claim
    )
    if carried!=expected:
        raise RuntimeError("BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH")
    return carried


def _artifacts()->list[str]:
    raw=os.environ.get("BRAIN_TASK_ARTIFACTS_JSON") or "[]"
    try:
        value=json.loads(raw)
    except Exception as exc:
        raise RuntimeError("BRAIN_TASK_ARTIFACTS_JSON_INVALID") from exc
    if not isinstance(value,list):
        raise RuntimeError("BRAIN_TASK_ARTIFACTS_JSON_INVALID")
    out=[]
    for item in value:
        if not isinstance(item,str) or not item.startswith("/") or "\x00" in item:
            raise RuntimeError("BRAIN_TASK_ARTIFACT_PATH_INVALID")
        if item not in out: out.append(item)
    return out


def build_request(instruction:str)->dict[str,Any]:
    artifacts=_artifacts()
    plan=adapter.resolve_plan(instruction,artifacts)
    return {
        "schema":"PROJECT_BRAIN_DNA_STORAGE_TASK_REQUEST_V1",
        "instruction":instruction,
        "artifacts":artifacts,
        "prevalidated_plan":{
            "mode":plan.mode,
            "input_path":plan.input_path,
            "output_path":plan.output_path,
        },
        "model_dependency_count":0,
        "network_dependency_count":0,
    }


def _bundle_sources()->dict[str,bytes]:
    return {
        REMOTE_ROOT+"/canonical/__init__.py":b"",
        REMOTE_ROOT+"/canonical/runtime/__init__.py":b"",
        REMOTE_ROOT+"/canonical/runtime/dna_storage_codec_v1.py":pathlib.Path(codec.__file__).read_bytes(),
        REMOTE_ROOT+"/canonical/runtime/dna_storage_task_adapter_v1.py":pathlib.Path(adapter.__file__).read_bytes(),
    }


def _append_commands(remote_path:str,data:bytes)->list[str]:
    encoded=base64.b64encode(data).decode("ascii")
    commands=[validate_environment_command(
        "python3 -c "+shlex.quote("from pathlib import Path;p=Path("+repr(remote_path)+");p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'')")
    )]
    for i in range(0,len(encoded),MAX_TRANSFER_CHUNK):
        chunk=encoded[i:i+MAX_TRANSFER_CHUNK]
        code=(
            "import base64;from pathlib import Path;"
            "p=Path("+repr(remote_path)+");"
            "p.open('ab').write(base64.b64decode("+repr(chunk)+"))"
        )
        commands.append(validate_environment_command("python3 -c "+shlex.quote(code)))
    return commands


async def _transfer(transport:HarborEnvironmentTransport,remote_path:str,data:bytes)->dict[str,Any]:
    count=0
    for command in _append_commands(remote_path,data):
        receipt=await transport.exec(command,timeout_sec=60)
        count+=1
        if receipt.returncode!=0:
            raise RuntimeError("DNA_STORAGE_BUNDLE_TRANSFER_FAILED")
    expected=hashlib.sha256(data).hexdigest()
    code=(
        "import hashlib;from pathlib import Path;"
        "print(hashlib.sha256(Path("+repr(remote_path)+").read_bytes()).hexdigest())"
    )
    check=validate_environment_command("python3 -c "+shlex.quote(code))
    receipt=await transport.exec(check,timeout_sec=60)
    observed=str(receipt.stdout or "").strip().splitlines()[-1] if str(receipt.stdout or "").strip() else ""
    if receipt.returncode!=0 or observed!=expected:
        raise RuntimeError("DNA_STORAGE_BUNDLE_HASH_MISMATCH")
    return {"path":remote_path,"sha256":expected,"commands":count+1}


async def run_dna_storage_goal(instruction:str,environment:BaseEnvironment)->dict[str,Any]:
    request=build_request(instruction)
    transport=HarborEnvironmentTransport(environment)
    transfers=[]
    for path,data in _bundle_sources().items():
        transfers.append(await _transfer(transport,path,data))
    request_bytes=(json.dumps(request,sort_keys=True,separators=(",",":"))+"\n").encode()
    transfers.append(await _transfer(transport,REMOTE_REQUEST,request_bytes))
    command=validate_environment_command(
        "PYTHONPATH="+shlex.quote(REMOTE_ROOT)+" python3 -m canonical.runtime.dna_storage_task_adapter_v1 "+shlex.quote(REMOTE_REQUEST)
    )
    receipt=await transport.exec(command,timeout_sec=3600)
    if receipt.returncode!=0:
        raise RuntimeError("DNA_STORAGE_ADAPTER_NONZERO:"+hashlib.sha256(str(receipt.stderr or "").encode()).hexdigest())
    lines=[x for x in str(receipt.stdout or "").splitlines() if x.strip()]
    if not lines:
        raise RuntimeError("DNA_STORAGE_ADAPTER_RECEIPT_MISSING")
    try:
        result=json.loads(lines[-1])
    except Exception as exc:
        raise RuntimeError("DNA_STORAGE_ADAPTER_RECEIPT_INVALID") from exc
    if not str(result.get("status") or "").startswith("PASS__"):
        raise RuntimeError("DNA_STORAGE_ADAPTER_NOT_PASS")
    if result.get("model_dependency_count")!=0 or result.get("network_dependency_count")!=0:
        raise RuntimeError("DNA_STORAGE_ADAPTER_DEPENDENCY_NONZERO")
    output=str(((result.get("plan") or {}).get("output_path")) or "")
    if not output.startswith("/"):
        raise RuntimeError("DNA_STORAGE_OUTPUT_PATH_INVALID")
    verify_code=(
        "from pathlib import Path;"
        "p=Path("+repr(output)+");"
        "raise SystemExit(0 if p.is_file() and p.stat().st_size>0 else 1)"
    )
    verify=validate_environment_command("python3 -c "+shlex.quote(verify_code))
    vr=await transport.exec(verify,timeout_sec=60)
    if vr.returncode!=0:
        raise RuntimeError("DNA_STORAGE_OUTPUT_POSTCONDITION_FAILED")
    return {
        "schema":SCHEMA,
        "status":"PASS__DNA_STORAGE_AGENT_EXECUTED",
        "plan":result.get("plan"),
        "adapter_receipt_sha256":hashlib.sha256(
            json.dumps(result,sort_keys=True,separators=(",",":")).encode()
        ).hexdigest(),
        "transfer_receipts":transfers,
        "execution_command_sha256":hashlib.sha256(command.encode()).hexdigest(),
        "output_verified":True,
        "model_dependency_count":0,
        "external_model_runtime_calls":0,
        "network_dependency_count":0,
        "task_completion_claimed":False,
        "terminal_authority":False,
    }


class HarborScienceDNAStorageAgent(BaseAgent):
    capabilities=AgentCapabilities()

    @staticmethod
    def name()->str: return "project-brain-science-dna-storage"

    def version(self)->str: return "1.0.0"

    async def setup(self,environment:BaseEnvironment)->None: return None

    async def run(self,instruction:str,environment:BaseEnvironment,context:AgentContext)->None:
        logical_attempt_id=logical_attempt_id_for_goal(instruction)
        await start_barrier.await_start_commit(logical_attempt_id)
        try:
            result=await run_dna_storage_goal(instruction,environment)
        except Exception as exc:
            result={
                "schema":SCHEMA,
                "status":"BLOCKED_DNA_STORAGE_INTERNAL_EXCEPTION",
                "exception_type":type(exc).__name__,
                "exception_sha256":hashlib.sha256(str(exc).encode("utf-8","replace")).hexdigest(),
                "task_completion_claimed":False,
                "model_dependency_count":0,
                "external_model_runtime_calls":0,
                "network_dependency_count":0,
                "terminal_authority":False,
            }
        try:
            self.logs_dir.mkdir(parents=True,exist_ok=True)
            (self.logs_dir/"project_brain_dna_storage_trace.json").write_text(
                json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
            )
        except Exception:
            pass
        if hasattr(context,"cost_usd"):
            try: context.cost_usd=0.0
            except Exception: pass
