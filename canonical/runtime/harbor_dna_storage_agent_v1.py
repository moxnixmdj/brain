"""Project Brain donor-free Harbor DNA storage agent V1."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import re
import shlex
from typing import Any

from canonical.runtime import dna_storage_codec_v1 as codec
from canonical.runtime import dna_storage_task_kernel_v1 as task_kernel
from canonical.runtime.harbor_environment_transport_v2 import HarborEnvironmentTransport
from canonical.runtime.harbor_command_policy import validate_environment_command
from execution_guard import terminal_agent_start_barrier_v1 as start_barrier
from execution_guard.logical_attempt_identity_v2 import logical_attempt_id as canonical_logical_attempt_id

try:
    from harbor.agents.base import BaseAgent
    from harbor.agents.capabilities import AgentCapabilities
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
except ImportError:
    BaseAgent = object
    BaseEnvironment = Any
    AgentContext = Any
    class AgentCapabilities:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

SCHEMA="PROJECT_BRAIN_HARBOR_DNA_STORAGE_AGENT_V1"
REMOTE_ROOT="/tmp/project_brain_dna_storage_v1"
REMOTE_CODEC=REMOTE_ROOT+"/canonical/runtime/dna_storage_codec_v1.py"
REMOTE_TASK_KERNEL=REMOTE_ROOT+"/canonical/runtime/dna_storage_task_kernel_v1.py"
REMOTE_REQUEST=REMOTE_ROOT+"/request.json"
MAX_TRANSFER_CHUNK=6000


def logical_attempt_id_for_goal(goal:str)->str:
    if not str(goal or "").strip(): raise ValueError("DNA_STORAGE_GOAL_REQUIRED")
    slot=str(os.environ.get("BRAIN_SLOT_ID") or "").strip()
    digest=str(os.environ.get("BRAIN_TASK_DIGEST") or "").strip()
    carried=str(os.environ.get("BRAIN_LOGICAL_ATTEMPT_ID") or "").strip()
    claim=str(os.environ.get("BRAIN_EXECUTION_CLAIM_BINDING_DIGEST") or "").strip()
    if not slot: raise RuntimeError("BRAIN_SLOT_ID_REQUIRED")
    if not digest: raise RuntimeError("BRAIN_TASK_DIGEST_REQUIRED")
    if not carried: raise RuntimeError("BRAIN_LOGICAL_ATTEMPT_ID_REQUIRED")
    if not claim: raise RuntimeError("BRAIN_EXECUTION_CLAIM_BINDING_DIGEST_REQUIRED")
    expected=canonical_logical_attempt_id(slot_id=slot,task_digest=digest,execution_claim_binding_digest=claim)
    if carried!=expected: raise RuntimeError("BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH")
    return carried


def _artifacts()->list[str]:
    try: value=json.loads(os.environ.get("BRAIN_TASK_ARTIFACTS_JSON") or "[]")
    except Exception as exc: raise RuntimeError("BRAIN_TASK_ARTIFACTS_JSON_INVALID") from exc
    if not isinstance(value,list): raise RuntimeError("BRAIN_TASK_ARTIFACTS_JSON_INVALID")
    out=[]
    for item in value:
        if not isinstance(item,str) or not item.startswith("/"): raise RuntimeError("BRAIN_TASK_ARTIFACT_PATH_INVALID")
        if item not in out: out.append(item)
    if not out: raise RuntimeError("BRAIN_TASK_ARTIFACTS_REQUIRED")
    return out


def _input_roots(instruction:str,artifacts:list[str])->list[str]:
    roots=["/root/data","/app","/data","/workspace"]
    for raw in re.findall(r"/[A-Za-z0-9_.+@%=/:-]+",str(instruction or "")):
        p=raw.rstrip(".,;:)]}")
        if not p or any(task_kernel._under(p,a) for a in artifacts): continue
        if p not in roots: roots.append(p)
        parent=str(pathlib.PurePosixPath(p).parent)
        if parent not in roots: roots.append(parent)
    return roots[:24]


def build_payload(instruction:str)->dict[str,Any]:
    artifacts=_artifacts()
    contract=task_kernel.classify_contract(instruction,artifacts)
    if contract.get("supported") is not True: raise RuntimeError("DNA_STORAGE_CONTRACT_UNSUPPORTED")
    return {
        "schema":"PROJECT_BRAIN_DNA_STORAGE_TASK_REQUEST_V1",
        "instruction":str(instruction),
        "artifacts":artifacts,
        "roots":_input_roots(instruction,artifacts),
        "contract_precheck":contract,
        "model_dependency_count":0,
        "network_dependency_count":0,
    }


def _append_commands(remote_path:str,data:bytes)->list[str]:
    encoded=base64.b64encode(data).decode("ascii")
    init=(
        "from pathlib import Path;"
        "p=Path("+repr(remote_path)+");p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'')"
    )
    commands=[validate_environment_command("python3 -c "+shlex.quote(init))]
    for i in range(0,len(encoded),MAX_TRANSFER_CHUNK):
        chunk=encoded[i:i+MAX_TRANSFER_CHUNK]
        code="import base64;open("+repr(remote_path)+",'ab').write(base64.b64decode("+repr(chunk)+"))"
        commands.append(validate_environment_command("python3 -c "+shlex.quote(code)))
    return commands


async def _transfer(transport:HarborEnvironmentTransport,remote_path:str,data:bytes)->list[dict[str,Any]]:
    receipts=[]
    for command in _append_commands(remote_path,data):
        r=await transport.exec(command,timeout_sec=60)
        receipts.append({"command_sha256":hashlib.sha256(command.encode()).hexdigest(),"returncode":int(r.returncode)})
        if int(r.returncode)!=0: raise RuntimeError("DNA_STORAGE_TRANSFER_FAILED")
    expected=hashlib.sha256(data).hexdigest()
    code="import hashlib;p="+repr(remote_path)+";print(hashlib.sha256(open(p,'rb').read()).hexdigest())"
    command=validate_environment_command("python3 -c "+shlex.quote(code))
    r=await transport.exec(command,timeout_sec=60)
    observed=str(r.stdout or "").strip().splitlines()[-1] if str(r.stdout or "").strip() else ""
    if int(r.returncode)!=0 or observed!=expected: raise RuntimeError("DNA_STORAGE_TRANSFER_HASH_MISMATCH")
    return receipts


async def run_dna_storage_goal(instruction:str,environment:BaseEnvironment)->dict[str,Any]:
    payload=build_payload(instruction)
    transport=HarborEnvironmentTransport(environment)
    files={
        REMOTE_ROOT+"/canonical/__init__.py":b"",
        REMOTE_ROOT+"/canonical/runtime/__init__.py":b"",
        REMOTE_CODEC:pathlib.Path(codec.__file__).read_bytes(),
        REMOTE_TASK_KERNEL:pathlib.Path(task_kernel.__file__).read_bytes(),
    }
    transfer_count=0; source_hashes={}
    for path,data in files.items():
        rows=await _transfer(transport,path,data); transfer_count+=len(rows); source_hashes[path]=hashlib.sha256(data).hexdigest()
    request_bytes=(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n").encode()
    transfer_count+=len(await _transfer(transport,REMOTE_REQUEST,request_bytes))
    command=validate_environment_command(
        "PYTHONPATH="+shlex.quote(REMOTE_ROOT)+" python3 "+shlex.quote(REMOTE_TASK_KERNEL)+" "+shlex.quote(REMOTE_REQUEST)
    )
    receipt=await transport.exec(command,timeout_sec=3600)
    if int(receipt.returncode)!=0:
        raise RuntimeError("DNA_STORAGE_TASK_KERNEL_NONZERO:"+hashlib.sha256(str(receipt.stderr or "").encode()).hexdigest())
    lines=[x for x in str(receipt.stdout or "").splitlines() if x.strip()]
    if not lines: raise RuntimeError("DNA_STORAGE_TASK_KERNEL_NO_RECEIPT")
    try: kernel_receipt=json.loads(lines[-1])
    except Exception as exc: raise RuntimeError("DNA_STORAGE_TASK_KERNEL_RECEIPT_INVALID") from exc
    if kernel_receipt.get("model_dependency_count")!=0 or kernel_receipt.get("network_dependency_count")!=0:
        raise RuntimeError("DNA_STORAGE_DEPENDENCY_NONZERO")
    if not str(kernel_receipt.get("status") or "").startswith("PASS__"):
        raise RuntimeError("DNA_STORAGE_TASK_KERNEL_NOT_PASS")
    return {
        "schema":SCHEMA,"status":"PASS__DNA_STORAGE_AGENT_EXECUTED",
        "mode":kernel_receipt.get("mode"),"task_completion_claimed":False,
        "model_dependency_count":0,"external_model_runtime_calls":0,"network_dependency_count":0,
        "source_sha256":source_hashes,"request_sha256":hashlib.sha256(request_bytes).hexdigest(),
        "transfer_command_count":transfer_count,"execution_command_sha256":hashlib.sha256(command.encode()).hexdigest(),
        "kernel_receipt":kernel_receipt,"effect_replay_authority":False,"verification_replay_authority":False,
        "terminal_authority":False,
    }


class HarborDNAStorageAgent(BaseAgent):
    capabilities=AgentCapabilities()
    @staticmethod
    def name()->str: return "project-brain-dna-storage-zero-model"
    def version(self)->str: return "1.0.0"
    async def setup(self,environment:BaseEnvironment)->None: return None
    async def run(self,instruction:str,environment:BaseEnvironment,context:AgentContext)->None:
        logical_attempt_id_for_goal(instruction)
        await start_barrier.await_start_commit(os.environ["BRAIN_LOGICAL_ATTEMPT_ID"])
        try:
            result=await run_dna_storage_goal(instruction,environment)
        except Exception as exc:
            result={"schema":SCHEMA,"status":"BLOCKED_DNA_STORAGE_INTERNAL_EXCEPTION","exception_type":type(exc).__name__,
                    "exception_sha256":hashlib.sha256(str(exc).encode("utf-8","replace")).hexdigest(),
                    "task_completion_claimed":False,"model_dependency_count":0,"external_model_runtime_calls":0,
                    "network_dependency_count":0,"effect_replay_authority":False,"verification_replay_authority":False,
                    "terminal_authority":False}
        try:
            self.logs_dir.mkdir(parents=True,exist_ok=True)
            (self.logs_dir/"project_brain_dna_storage_trace.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        except Exception: pass
        if hasattr(context,"cost_usd"):
            try: context.cost_usd=0.0
            except Exception: pass
