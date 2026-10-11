"""Project Brain zero-external-model Harbor science agent V1.

This agent never calls a language model. It extracts only explicit task contract
facts, selects a pre-authored deterministic scientific capability, injects the
content of that audited Brain-owned solver into the task container, executes it,
and independently checks declared outputs. Benchmark success remains owned by
the Harbor verifier.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import inspect
import json
import os
import shlex
import zlib
from pathlib import Path
from typing import Any

from canonical.runtime import science_zero_model_contract_v1 as contract_parser
from canonical.runtime import science_zero_model_joint_orbit_v1 as joint_orbit
from canonical.runtime.harbor_command_policy import validate_environment_command
from canonical.runtime.harbor_environment_transport_v2 import HarborEnvironmentTransport
from canonical.runtime import science_typed_action_protocol_v2 as typed_action
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

SCHEMA="PROJECT_BRAIN_HARBOR_SCIENCE_ZERO_MODEL_AGENT_V1"
MAX_SOLVER_TIMEOUT_S=7200


def logical_attempt_id_for_goal(goal:str)->str:
    if not isinstance(goal,str) or not goal.strip(): raise ValueError("SCIENCE_GOAL_REQUIRED")
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


def _solver_source()->str:
    source=inspect.getsource(joint_orbit)
    if "external_model_calls" not in source or "random_search" not in source:
        raise RuntimeError("ZERO_MODEL_SOLVER_SOURCE_INVARIANT_MISSING")
    return source


def build_solver_command(instruction:str)->tuple[str,dict[str,Any]]:
    contract=contract_parser.extract_explicit_contract(instruction)
    if contract.get("capability_class")!="JOINT_RV_ASTROMETRY_FIT":
        raise RuntimeError("ZERO_MODEL_CAPABILITY_NOT_AVAILABLE:"+str(contract.get("capability_class")))
    if not contract.get("output_paths"):
        raise RuntimeError("ZERO_MODEL_EXPLICIT_OUTPUT_PATHS_REQUIRED")
    source=_solver_source().encode("utf-8")
    packed=base64.b64encode(zlib.compress(source,9)).decode("ascii")
    c64=base64.b64encode(json.dumps(contract,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).decode("ascii")
    runner=(
        "import base64,zlib,json;"
        "ns={};"
        f"exec(zlib.decompress(base64.b64decode({packed!r})).decode('utf-8'),ns);"
        f"c=json.loads(base64.b64decode({c64!r}).decode('utf-8'));"
        "r=ns['execute_contract'](c,'/data');"
        "print(json.dumps(r,sort_keys=True,separators=(',',':')))"
    )
    command=validate_environment_command("python -c "+shlex.quote(runner))
    return command,contract


def _output_format(path:str)->str:
    low=path.lower()
    if low.endswith(".json"): return "json"
    if low.endswith(".csv"): return "csv"
    if low.endswith(".npy"): return "npy"
    if low.endswith(".npz"): return "npz"
    if low.endswith(".py"): return "python"
    return "file"


async def run_zero_model_science(instruction:str,environment:BaseEnvironment)->dict[str,Any]:
    command,contract=build_solver_command(instruction)
    transport=HarborEnvironmentTransport(environment)
    receipt=await transport.exec(command,timeout_sec=MAX_SOLVER_TIMEOUT_S)
    if receipt.returncode!=0:
        return {"schema":SCHEMA,"status":"ZERO_MODEL_SOLVER_EXECUTION_FAILED","pass":False,"returncode":receipt.returncode,"stderr_sha256":hashlib.sha256(str(receipt.stderr or '').encode()).hexdigest(),"external_model_calls":0,"external_cognition_calls":0,"network_calls":0,"terminal_authority":False}
    lines=[x for x in str(receipt.stdout or "").splitlines() if x.strip()]
    if not lines: raise RuntimeError("ZERO_MODEL_SOLVER_RECEIPT_MISSING")
    solver=json.loads(lines[-1])
    checks=[]
    for path in contract["output_paths"]:
        check=typed_action.authoritative_deliverable_check_command({"path":path,"format":_output_format(path)})
        r=await transport.exec(check,timeout_sec=60)
        checks.append({"path":path,"format":_output_format(path),"returncode":r.returncode,"verified":r.returncode==0})
    ok=all(x["verified"] for x in checks)
    return {"schema":SCHEMA,"status":"ZERO_MODEL_OUTPUTS_VERIFIED" if ok else "ZERO_MODEL_OUTPUT_POSTCONDITION_FAILED","pass":ok,"capability_class":contract["capability_class"],"output_checks":checks,"solver_status":solver.get("status"),"solver_receipt_sha256":hashlib.sha256(json.dumps(solver,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest(),"external_model_calls":0,"external_cognition_calls":0,"network_calls":0,"random_search":False,"task_completion_claimed":False,"terminal_authority":False}


class HarborScienceZeroModelAgent(BaseAgent):
    capabilities=AgentCapabilities()

    @staticmethod
    def name()->str: return "project-brain-science-zero-model"

    def version(self)->str: return "1.0.0"

    async def setup(self,environment:BaseEnvironment)->None: return None

    async def run(self,instruction:str,environment:BaseEnvironment,context:AgentContext)->None:
        logical_attempt_id=logical_attempt_id_for_goal(instruction)
        await start_barrier.await_start_commit(logical_attempt_id)
        try:
            result=await run_zero_model_science(instruction,environment)
        except Exception as exc:
            result={"schema":SCHEMA,"status":"BLOCKED_ZERO_MODEL_CONTROLLER_EXCEPTION","pass":False,"exception_type":type(exc).__name__,"exception_sha256":hashlib.sha256(str(exc).encode("utf-8","replace")).hexdigest(),"external_model_calls":0,"external_cognition_calls":0,"network_calls":0,"task_completion_claimed":False,"terminal_authority":False}
        try:
            self.logs_dir.mkdir(parents=True,exist_ok=True)
            (self.logs_dir/"project_brain_zero_model_science_trace.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        except Exception:
            pass
        if hasattr(context,"cost_usd"):
            try: context.cost_usd=0.0
            except Exception: pass
