"""Candidate bindings for the six remaining terminal behavioral contracts.

Every branch invokes an existing Brain-owned mechanism. No evaluator module,
hidden oracle, or benchmark-specific answer key is imported.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import requirement_acceptance_compiler
from canonical.runtime import exact_artifact_materializer
from canonical.runtime import m4_research_control
from canonical.runtime import shared_decision_primitives as sdp
from canonical.runtime import consensus_dom_grounding
from canonical.runtime import m3_contract_task_decomposition


class BindingError(ValueError):
    pass


def solve(public:Mapping[str,Any],*,workdir:str|Path|None=None)->dict[str,Any]:
    c=public.get("contract"); task=public.get("task")
    if not isinstance(c,str) or not isinstance(task,Mapping):
        raise BindingError("TASK_CONTRACT_INVALID")

    if c=="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001":
        return requirement_acceptance_compiler.compile_requirements(task.get("requirements",[]))

    if c=="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":
        if workdir is None: raise BindingError("WORKDIR_REQUIRED")
        raw=base64.b64decode(str(task.get("target_b64") or ""),validate=True)
        out=Path(workdir)/str(task.get("output_name") or "artifact.bin")
        return exact_artifact_materializer.materialize_exact_artifact(
            out,target_bytes=raw,expected_target_sha256=str(task.get("target_sha256") or "")
        )

    if c=="ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001":
        return m4_research_control.control(
            objective=str(task.get("objective") or ""),
            material_requirements=task.get("material_requirements"),
            resolved_requirement_ids=task.get("resolved_requirement_ids"),
            candidate_actions=task.get("candidate_actions"),
        )

    if c=="TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":
        routes=[]
        for r in task.get("routes",[]):
            routes.append(sdp.ToolRoute(
                route_id=str(r["route_id"]),
                capabilities=frozenset(str(x) for x in r["capabilities"]),
                cost=float(r.get("cost",0.0)),
                available=r.get("available") is True,
                authorized=r.get("authorized") is True,
                verified=r.get("verified") is True,
            ))
        d=sdp.select_verified_tool(task.get("required",[]),routes)
        return {"status":d.status,"route_id":d.route_id,"reason":d.reason}

    if c=="BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001":
        r=task["request"]
        req=consensus_dom_grounding.ConsensusRequest(
            action=str(r["action"]),role=r.get("role"),name=r.get("name"),text=r.get("text"),
            ocr_text=r.get("ocr_text"),attrs=r.get("attrs"),min_independent_cues=int(r.get("min_independent_cues",2))
        )
        els=[
            consensus_dom_grounding.ObservedElement(
                element_id=str(e["element_id"]),role=e.get("role"),name=e.get("name"),text=e.get("text"),
                ocr_text=e.get("ocr_text"),attrs=e.get("attrs") or {},actions=frozenset(e.get("actions") or []),
                visible=e.get("visible") is True,enabled=e.get("enabled") is True,
            ) for e in task.get("elements",[])
        ]
        return consensus_dom_grounding.ground_consensus_action(req,els)

    if c=="TASK_TO_DELEGATION_GRAPH_001":
        steps=[
            m3_contract_task_decomposition.ContractStep(
                task_id=str(x["id"]),requires=frozenset(x["requires"]),produces=frozenset(x["produces"]),
                cost=float(x["cost"]),available=True,verified=True
            ) for x in task.get("steps",[])
        ]
        plan=m3_contract_task_decomposition.compile_task_plan(
            initial_facts=task.get("initial_facts",[]),required_outputs=task.get("required_outputs",[]),steps=steps
        )
        if plan.get("status")!="PASS":
            return plan
        selected=set(plan["task_ids"]); deps={k:list(v) for k,v in plan["dependencies"].items()}
        cap_by_id={str(x["id"]):str(x["capability"]) for x in task.get("steps",[])}
        tasks=[sdp.Task(tid,frozenset(deps[tid]),frozenset([cap_by_id[tid]])) for tid in plan["task_ids"]]
        workers=[sdp.Worker(str(w["id"]),frozenset(w["capabilities"])) for w in task.get("workers",[])]
        completed=set(); assignment={}; waves=[]
        while completed!=selected:
            a=sdp.assign_ready_tasks(tasks,workers,completed)
            wave=sorted(a)
            if not wave:
                raise BindingError("DELEGATION_SCHEDULE_UNRESOLVED")
            waves.append(wave); assignment.update(a); completed.update(wave)
        return {
            "task_ids":plan["task_ids"],"dependencies":deps,"assignment":assignment,"waves":waves,
        }

    raise BindingError("UNSUPPORTED_CONTRACT:"+c)
