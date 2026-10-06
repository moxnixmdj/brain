"""A Tournament Wave1 generic G0 harness.

Frozen after public task inputs and before oracle labels.
Dispatch is by task kind only. It must not contain Wave1 task IDs, seed strings,
or expected answers.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import h100_verified_capability_registry_v8 as registry
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as symbolic
from canonical.runtime import h100_typed_capability_planner_v1 as planner
from canonical.runtime import h100_verified_effect_tool_registry_v1 as effects
from canonical.runtime import h100_zero_learned_event_memory_v1 as memory
from canonical.runtime import h100_jit_lexical_role_v1 as lexical
from canonical.runtime import h100_zero_learned_compositional_language_v1 as language
from canonical.runtime import h100_zero_learned_tool_trace_normalizer_v1 as traces

ROOT=Path(__file__).resolve().parents[2]
TASKS=ROOT/"canonical/governance/H100_A_TOURNAMENT_WAVE1_PUBLIC_TASKS_V1.json"
SCHEMA="PROJECT_BRAIN_H100_A_TOURNAMENT_WAVE1_G0_RESULT_V1"


def _files(root:Path)->dict[str,str]:
    out={}
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        out[str(p.relative_to(root))]=p.read_text(encoding="utf-8")
    return out


def run_task(task:Mapping[str,Any])->dict[str,Any]:
    kind=str(task["kind"])

    if kind=="PARAMETRIC_REGISTRY":
        out=registry.resolve_verified_capability(
            task["rows"],target=str(task["target"]),input_name=str(task["input_name"])
        )
        pred=None
        if out.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE":
            pred=registry.predict(out,task["probe"])
        return {
            "kind":kind,"status":out.get("status"),"prediction":pred,
            "capability_id":(out.get("match") or {}).get("capability_id"),
        }

    if kind=="SYMBOLIC_DISCOVERY":
        out=symbolic.discover(
            task["rows"],target=str(task["target"]),inputs=list(task["inputs"]),
            max_depth=int(task["max_depth"]),beam_width=int(task["beam_width"]),
            pair_feature_pool=int(task["pair_feature_pool"])
        )
        pred=None
        if out.get("status")=="EXACT_CANDIDATE_FOUND" and out.get("best_candidate"):
            pred=symbolic.predict(out["best_candidate"],task["probe"])
        return {
            "kind":kind,"status":out.get("status"),"prediction":pred,
            "best_candidate":out.get("best_candidate"),
            "generated_tree_count":out.get("generated_tree_count"),
        }

    if kind=="TYPED_PLAN":
        out=planner.derive_plan(list(task["initial_resources"]),str(task["goal_resource"]))
        return {"kind":kind,**out}

    if kind=="EFFECT_TOOL":
        with tempfile.TemporaryDirectory() as td:
            out=effects.invoke(str(task["tool_id"]),task["payload"],Path(td))
            return {"kind":kind,"status":out.get("status"),"files":_files(Path(td))}

    if kind=="EVENT_MEMORY":
        events=[]
        prev=memory.GENESIS
        for seq,spec in enumerate(task["events"],start=1):
            ev=memory.make_event(
                seq=seq,op=str(spec["op"]),key=str(spec["key"]),
                value=spec.get("value"),prev_hash=prev
            )
            events.append(ev)
            prev=ev["event_hash"]
        out=memory.replay(events)
        return {
            "kind":kind,"status":"REPLAY_OK",
            "state":out["state"],"last_seq":out["last_seq"],
            "last_event_hash":out["last_event_hash"],
        }

    if kind=="JIT_LEXICAL":
        out=lexical.induce_roles(task["clauses"],task["knowledge"])
        return {"kind":kind,**out}

    if kind=="COMPOSITIONAL_LANGUAGE":
        out=language.compile_compositional_roles(task["text"])
        return {"kind":kind,**out}

    if kind=="TOOL_TRACE":
        out=traces.normalize_tool_trace(
            task["payload"],inputs=task["inputs"],target=str(task["target"]),
            format_hint=str(task["format_hint"])
        )
        return {"kind":kind,**out}

    if kind=="VISION_PBM_TALLEST_BAR":
        return {
            "kind":kind,
            "status":"G0_UNSUPPORTED_REPRESENTATION",
            "answer":None,
            "reason":"NO_FROZEN_G0_VISION_COMPONENT",
        }

    return {"kind":kind,"status":"G0_UNKNOWN_TASK_KIND"}


def run()->dict[str,Any]:
    doc=json.loads(TASKS.read_text(encoding="utf-8"))
    results=[]
    for task in doc["tasks"]:
        result=run_task(task)
        results.append({"id":task["id"],**result})
    return {
        "schema":SCHEMA,
        "g0_commit":doc["g0_commit"],
        "task_commit":"6f7b9d59e57dc1b375991234122c120304a40099",
        "result_count":len(results),
        "results":results,
        "target_adapted_persistent_bits":0,
        "external_frontier_model_calls":0,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
