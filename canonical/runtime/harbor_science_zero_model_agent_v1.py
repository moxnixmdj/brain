"""Project Brain zero-model Harbor science agent V1.

No external or local language model is used at runtime. The agent deterministically
classifies a bounded science family, transfers a content-addressed stdlib kernel
into the Harbor task container, executes it, and records an auditable receipt.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import shlex
from typing import Any

from canonical.runtime import tb_science_zero_model_scientific_kernel_v1 as kernel
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


SCHEMA = "PROJECT_BRAIN_HARBOR_SCIENCE_ZERO_MODEL_AGENT_V1"
REMOTE_KERNEL = "/tmp/project_brain_zero_model_science_kernel_v1.py"
REMOTE_REQUEST = "/tmp/project_brain_zero_model_science_request_v1.json"
MAX_TRANSFER_CHUNK = 6000


def logical_attempt_id_for_goal(goal: str) -> str:
    goal=str(goal or "").strip()
    if not goal:
        raise ValueError("SCIENCE_GOAL_REQUIRED")
    slot_id=str(os.environ.get("BRAIN_SLOT_ID") or "").strip()
    task_digest=str(os.environ.get("BRAIN_TASK_DIGEST") or "").strip()
    carried=str(os.environ.get("BRAIN_LOGICAL_ATTEMPT_ID") or "").strip()
    claim_digest=str(os.environ.get("BRAIN_EXECUTION_CLAIM_BINDING_DIGEST") or "").strip()
    if not slot_id:
        raise RuntimeError("BRAIN_SLOT_ID_REQUIRED")
    if not task_digest:
        raise RuntimeError("BRAIN_TASK_DIGEST_REQUIRED")
    if not carried:
        raise RuntimeError("BRAIN_LOGICAL_ATTEMPT_ID_REQUIRED")
    if not claim_digest:
        raise RuntimeError("BRAIN_EXECUTION_CLAIM_BINDING_DIGEST_REQUIRED")
    expected=canonical_logical_attempt_id(
        slot_id=slot_id,
        task_digest=task_digest,
        execution_claim_binding_digest=claim_digest,
    )
    if carried!=expected:
        raise RuntimeError("BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH")
    return carried


def _artifacts() -> list[str]:
    raw=os.environ.get("BRAIN_TASK_ARTIFACTS_JSON") or "[]"
    try:
        value=json.loads(raw)
    except Exception as exc:
        raise RuntimeError("BRAIN_TASK_ARTIFACTS_JSON_INVALID") from exc
    if not isinstance(value,list):
        raise RuntimeError("BRAIN_TASK_ARTIFACTS_JSON_INVALID")
    out=[]
    for item in value:
        if not isinstance(item,str) or not item.startswith("/"):
            raise RuntimeError("BRAIN_TASK_ARTIFACT_PATH_INVALID")
        if item not in out:
            out.append(item)
    if not out:
        raise RuntimeError("BRAIN_TASK_ARTIFACTS_REQUIRED")
    return out


def _explicit_input_roots(instruction: str) -> list[str]:
    roots=["/app","/data","/workspace"]
    artifacts=set(_artifacts())
    for path in __import__("re").findall(r"/[A-Za-z0-9_./-]+",str(instruction or "")):
        p=path.rstrip(".,;:)")
        if p in artifacts:
            continue
        parent=str(pathlib.PurePosixPath(p).parent)
        if parent.startswith(("/app","/data","/workspace")) and parent not in roots:
            roots.append(parent)
    return roots[:12]


def build_payload(instruction: str) -> dict[str, Any]:
    slot_id=str(os.environ.get("BRAIN_SLOT_ID") or "")
    route=kernel.classify(instruction,slot_id)
    if not route.get("route"):
        raise RuntimeError("ZERO_MODEL_SCIENCE_ROUTE_UNQUALIFIED")
    return {
        "schema":"PROJECT_BRAIN_ZERO_MODEL_SCIENCE_REQUEST_V1",
        "instruction":str(instruction),
        "slot_id":slot_id,
        "route":route["route"],
        "route_evidence":route,
        "artifacts":_artifacts(),
        "roots":_explicit_input_roots(instruction),
        "model_dependency_count":0,
        "network_dependency_count":0,
    }


def _append_commands(remote_path: str, data: bytes) -> list[str]:
    encoded=base64.b64encode(data).decode("ascii")
    commands=[
        validate_environment_command(
            "python3 -c "+shlex.quote("open("+repr(remote_path)+",'wb').close()")
        )
    ]
    for i in range(0,len(encoded),MAX_TRANSFER_CHUNK):
        chunk=encoded[i:i+MAX_TRANSFER_CHUNK]
        code=(
            "import base64;"
            "open("+repr(remote_path)+",'ab').write(base64.b64decode("+repr(chunk)+"))"
        )
        commands.append(validate_environment_command("python3 -c "+shlex.quote(code)))
    return commands


async def _transfer(transport: HarborEnvironmentTransport, remote_path: str, data: bytes) -> list[dict[str,Any]]:
    receipts=[]
    for command in _append_commands(remote_path,data):
        r=await transport.exec(command,timeout_sec=60)
        receipts.append({
            "command_sha256":hashlib.sha256(command.encode()).hexdigest(),
            "returncode":int(r.returncode),
            "stdout":str(r.stdout or "")[-1000:],
            "stderr":str(r.stderr or "")[-1000:],
        })
        if int(r.returncode)!=0:
            raise RuntimeError("ZERO_MODEL_KERNEL_TRANSFER_FAILED")
    expected=hashlib.sha256(data).hexdigest()
    code=(
        "import hashlib;"
        "p="+repr(remote_path)+";"
        "print(hashlib.sha256(open(p,'rb').read()).hexdigest())"
    )
    command=validate_environment_command("python3 -c "+shlex.quote(code))
    r=await transport.exec(command,timeout_sec=60)
    observed=str(r.stdout or "").strip().splitlines()[-1] if str(r.stdout or "").strip() else ""
    if int(r.returncode)!=0 or observed!=expected:
        raise RuntimeError("ZERO_MODEL_KERNEL_TRANSFER_HASH_MISMATCH")
    return receipts


async def run_zero_model_science_goal(instruction: str, environment: BaseEnvironment) -> dict[str,Any]:
    payload=build_payload(instruction)
    transport=HarborEnvironmentTransport(environment)
    source=pathlib.Path(kernel.__file__).read_bytes()
    transfer=await _transfer(transport,REMOTE_KERNEL,source)
    request_bytes=(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n").encode()
    request_transfer=await _transfer(transport,REMOTE_REQUEST,request_bytes)
    command=validate_environment_command(
        "python3 "+shlex.quote(REMOTE_KERNEL)+" "+shlex.quote(REMOTE_REQUEST)
    )
    receipt=await transport.exec(command,timeout_sec=1800)
    if int(receipt.returncode)!=0:
        raise RuntimeError(
            "ZERO_MODEL_SCIENCE_KERNEL_NONZERO:"
            +hashlib.sha256(str(receipt.stderr or "").encode()).hexdigest()
        )
    lines=[x for x in str(receipt.stdout or "").splitlines() if x.strip()]
    if not lines:
        raise RuntimeError("ZERO_MODEL_SCIENCE_KERNEL_NO_RECEIPT")
    try:
        kernel_receipt=json.loads(lines[-1])
    except Exception as exc:
        raise RuntimeError("ZERO_MODEL_SCIENCE_KERNEL_RECEIPT_INVALID") from exc
    if kernel_receipt.get("model_dependency_count")!=0:
        raise RuntimeError("ZERO_MODEL_SCIENCE_MODEL_DEPENDENCY_NONZERO")
    if not str(kernel_receipt.get("status") or "").startswith("PASS__"):
        raise RuntimeError("ZERO_MODEL_SCIENCE_KERNEL_NOT_PASS")
    return {
        "schema":SCHEMA,
        "status":"PASS__ZERO_MODEL_SCIENCE_AGENT_EXECUTED",
        "route":payload["route"],
        "task_completion_claimed":False,
        "model_dependency_count":0,
        "external_model_runtime_calls":0,
        "network_dependency_count":0,
        "kernel_sha256":hashlib.sha256(source).hexdigest(),
        "request_sha256":hashlib.sha256(request_bytes).hexdigest(),
        "transfer_command_count":len(transfer)+len(request_transfer),
        "execution_command_sha256":hashlib.sha256(command.encode()).hexdigest(),
        "kernel_receipt":kernel_receipt,
        "effect_replay_authority":False,
        "verification_replay_authority":False,
        "terminal_authority":False,
    }


class HarborScienceZeroModelAgent(BaseAgent):
    capabilities=AgentCapabilities()

    @staticmethod
    def name() -> str:
        return "project-brain-science-zero-model"

    def version(self) -> str:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        logical_attempt_id_for_goal(instruction)
        await start_barrier.await_start_commit(os.environ["BRAIN_LOGICAL_ATTEMPT_ID"])
        try:
            result=await run_zero_model_science_goal(instruction,environment)
        except Exception as exc:
            result={
                "schema":SCHEMA,
                "status":"BLOCKED_ZERO_MODEL_SCIENCE_INTERNAL_EXCEPTION",
                "exception_type":type(exc).__name__,
                "exception_sha256":hashlib.sha256(str(exc).encode("utf-8","replace")).hexdigest(),
                "task_completion_claimed":False,
                "model_dependency_count":0,
                "external_model_runtime_calls":0,
                "effect_replay_authority":False,
                "verification_replay_authority":False,
                "terminal_authority":False,
            }
        try:
            self.logs_dir.mkdir(parents=True,exist_ok=True)
            (self.logs_dir/"project_brain_science_trace.json").write_text(
                json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
            )
        except Exception:
            pass
        if hasattr(context,"cost_usd"):
            try:
                context.cost_usd=0.0
            except Exception:
                pass
