"""Harbor adapter with Brain-owned load-bearing terminal control."""
from __future__ import annotations
import json
from typing import Any
from canonical.runtime import astra_runtime
from canonical.runtime.coding_control_kernel_v1 import configuration_fingerprint,finish_schema_prompt,render_policy_block,validate_finish
from canonical.runtime.harbor_environment_transport import HarborEnvironmentTransport
from canonical.runtime.harbor_command_policy import validate_environment_command
try:
    from harbor.agents.base import BaseAgent
    from harbor.agents.capabilities import AgentCapabilities
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
except ImportError:
    BaseAgent=object; BaseEnvironment=Any; AgentContext=Any
    class AgentCapabilities:
        def __init__(self,**kwargs:Any)->None: self.kwargs=kwargs
SCHEMA="PROJECT_BRAIN_HARBOR_AGENT_TRACE_V2"; MAX_CYCLES=12; MAX_OUTPUT_CHARS=16000

def _planner_action(raw:dict[str,Any])->dict[str,Any]:
    action=raw.get("action")
    if not isinstance(action,dict):
        actions=raw.get("actions")
        if isinstance(actions,list) and actions and isinstance(actions[0],dict): action=actions[0]
    if not isinstance(action,dict) and isinstance(raw.get("next_action"),dict): action=raw["next_action"]
    if not isinstance(action,dict): raise RuntimeError("HARBOR_PLANNER_ACTION_MISSING")
    typ=action.get("type")
    if isinstance(typ,str) and "." in typ:
        typ=typ.rsplit(".",1)[-1]; action=dict(action); action["type"]=typ
    if typ not in {"environment_exec","finish"}: raise RuntimeError("HARBOR_PLANNER_ACTION_REJECTED:"+str(typ))
    if not isinstance(action.get("args"),dict): raise RuntimeError("HARBOR_PLANNER_ARGS_INVALID")
    return action

async def run_bounded_harbor_goal(goal:str,environment:BaseEnvironment,*,max_cycles:int=8)->dict[str,Any]:
    goal=str(goal or "").strip()
    if not goal: raise ValueError("HARBOR_GOAL_REQUIRED")
    max_cycles=max(1,min(int(max_cycles),MAX_CYCLES))
    observations=[]; trace=[]; block=render_policy_block(); config_sha=configuration_fingerprint()
    for cycle in range(max_cycles):
        obs=astra_runtime._pack_observations_for_model(observations,max_chars=12000)
        prompt=("You are an OPTIONAL proposal source inside Project Brain, not the authority. Return JSON text only. The task environment is isolated and terminal evidence must not be used to discover new external solutions.\n"+block+"\nGoal: "+goal+"\nAllowed actions: environment_exec(command, timeout_s), finish(...). environment_exec may inspect or modify ONLY the supplied task environment. No network acquisition, no package installation, no git fetch/clone/pull, no secrets. Prefer the smallest falsifiable action. "+finish_schema_prompt()+' Schema: {"actions":[{"type":"...","args":{},"why":"..."}]}. Observations envelope: '+obs)
        planned=astra_runtime._planner_post(prompt,timeout_s=20)
        raw=astra_runtime._extract_json_object(planned.get("text","")); action=_planner_action(raw); typ=action["type"]
        if typ=="finish":
            gate=validate_finish(action["args"],trace)
            if not gate["pass"]:
                rejected={"returncode":1,"stdout":"","stderr":"BRAIN_TERMINAL_GATE_REJECTED:"+",".join(gate["errors"])}
                trace.append({"cycle":cycle,"action":{"type":"finish","args":action["args"]},"result":rejected,"brain_control_gate":gate})
                observations.append({"action":action,"result":rejected,"brain_control_gate":gate})
                continue
            return {"schema":SCHEMA,"status":"FINISHED","controller_mode":"BRAIN_OWNED_CONTROL__OPTIONAL_MODEL_PROPOSAL","model_dependency_count":1,"model_role":"GENERAL_COGNITION_SUBSTRATE_CANDIDATE","model_has_terminal_authority":False,"brain_configuration_sha256":config_sha,"planner_model_last":planned.get("model"),"cycles":cycle+1,"trace":trace,"terminal_gate":gate,"summary":str(action["args"]["summary"]).strip()}
        command=validate_environment_command(action["args"].get("command"))
        try: timeout_s=max(1,min(int(action["args"].get("timeout_s",60)),180))
        except (TypeError,ValueError): raise RuntimeError("HARBOR_TIMEOUT_INVALID")
        receipt=await HarborEnvironmentTransport(environment).exec(command,timeout_sec=timeout_s)
        observed={"returncode":receipt.returncode,"stdout":receipt.stdout[-MAX_OUTPUT_CHARS:],"stderr":receipt.stderr[-MAX_OUTPUT_CHARS:]}
        trace.append({"cycle":cycle,"action":{"type":typ,"args":{"command":command,"timeout_s":timeout_s}},"result":observed})
        observations.append({"action":action,"result":observed})
    return {"schema":SCHEMA,"status":"BLOCKED_MAX_CYCLES_NO_BRAIN_AUTHORIZED_FINISH","controller_mode":"BRAIN_OWNED_CONTROL__OPTIONAL_MODEL_PROPOSAL","model_dependency_count":1,"model_role":"GENERAL_COGNITION_SUBSTRATE_CANDIDATE","model_has_terminal_authority":False,"brain_configuration_sha256":config_sha,"cycles":max_cycles,"trace":trace,"summary":""}

class HarborBrainAgent(BaseAgent):
    capabilities=AgentCapabilities()
    @staticmethod
    def name()->str: return "project-brain"
    def version(self)->str: return "1.1.0"
    async def setup(self,environment:BaseEnvironment)->None: return None
    async def run(self,instruction:str,environment:BaseEnvironment,context:AgentContext)->None:
        result=await run_bounded_harbor_goal(instruction,environment)
        self.logs_dir.mkdir(parents=True,exist_ok=True)
        (self.logs_dir/"project_brain_harbor_trace.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        if hasattr(context,"cost_usd"): context.cost_usd=0.0
