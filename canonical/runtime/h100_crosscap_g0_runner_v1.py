"""Generic executor for the frozen G0 cross-capability substrate.

This file is frozen before fresh task generation. It never reads answer keys.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_crosscap_g0_v1 as g0


class CrosscapRunnerError(ValueError):
    pass


def _coding(task:Mapping[str,Any])->dict[str,Any]:
    r=g0.synthesize_unary_integer_program(task["examples"],max_depth=int(task.get("max_depth",3)))
    out={"status":r["status"],"source":r.get("source")}
    if r["status"]=="PROGRAM_FOUND":
        out["predictions"]=[g0._expr_value(r["expr"],int(x)) for x in task["queries"]]
    else:
        out["predictions"]=None
    return out


def _vision(task:Mapping[str,Any])->dict[str,Any]:
    r=g0.ppm_foreground_components(str(task["ppm"]))
    comps=r["components"]
    return {
        "component_count":len(comps),
        "areas":sorted(int(c["area"]) for c in comps),
        "bboxes":sorted([list(map(int,c["bbox"])) for c in comps]),
    }


def _tool(task:Mapping[str,Any])->dict[str,Any]:
    r=g0.select_tool_by_contract(
        task["tool_packs"],
        required_effect=str(task["required_effect"]),
        required_keys=task["required_keys"],
    )
    ids=[str(x.get("tool_id")) for x in r["matches"]]
    return {"status":r["status"],"tool_ids":ids}


def _novel(task:Mapping[str,Any])->dict[str,Any]:
    from canonical.runtime import h100_verified_capability_registry_v8 as registry
    resolution=g0.resolve_numeric_capability(task["rows"])
    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        return {"status":resolution.get("status"),"capability_id":None,"predictions":None}
    preds=[registry.predict(resolution,{"x":float(x)}) for x in task["queries"]]
    return {
        "status":"LIBRARY_HIT__VERIFY_BEFORE_USE",
        "capability_id":resolution["match"]["capability_id"],
        "predictions":preds,
    }


def execute_task(task:Mapping[str,Any])->dict[str,Any]:
    kind=str(task["kind"])
    if kind=="REASONING":
        r=g0.solve_finite_csp(task["spec"])
        return {"status":r["status"],"solutions":r["solutions"]}
    if kind=="CODING":
        return _coding(task)
    if kind=="LANGUAGE":
        return g0.resolve_lexical_roles(task["clauses"],task["knowledge"])
    if kind=="VISION":
        return _vision(task)
    if kind=="TOOL_USE":
        return _tool(task)
    if kind=="PLANNING":
        return g0.plan_resources(task["initial_resources"],task["goal_resource"],task["operators"],int(task.get("max_length",8)))
    if kind=="MEMORY":
        r=g0.replay_events(task["events"])
        return {"state":r["state"],"last_seq":r["last_seq"],"last_event_hash":r["last_event_hash"]}
    if kind=="NOVEL_DOMAIN":
        return _novel(task)
    raise CrosscapRunnerError("TASK_KIND_UNKNOWN:"+kind)


def run_suite(public_tasks:Sequence[Mapping[str,Any]])->dict[str,Any]:
    rows=[]
    for task in public_tasks:
        rows.append({"id":str(task["id"]),"kind":str(task["kind"]),"output":execute_task(task)})
    return {
        "schema":"PROJECT_BRAIN_H100_CROSSCAP_G0_SUITE_OUTPUT_V1",
        "task_count":len(rows),
        "rows":rows,
        "target_adapted_persistent_bits_added_after_task_freeze":0,
    }


def main()->None:
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--tasks",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    tasks=json.loads(Path(args.tasks).read_text())
    out=run_suite(tasks["tasks"])
    Path(args.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"task_count":out["task_count"],"out":args.out},sort_keys=True))


if __name__=="__main__":
    main()
