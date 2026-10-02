"""P1 typed causal-localization candidate V7.

V7 preserves V6's candidate-visible causal graph and output contract while making
failure_semantics load-bearing:
- DERIVED_UPSTREAM failures are symptoms, never direct repair roots.
- DIRECT_CONTRACT failures on the terminal causal slice remain repair-relevant even
  when causally serial.
- If only derived failures are visible, abstain/escalate rather than invent a root.
"""
from __future__ import annotations
from typing import Any, Mapping

ALLOWED_KINDS={
    "AUTHORITY","SCHEMA","PROVENANCE","INVARIANT",
    "STATE_TRANSITION","TOOL_CONTRACT","DEPENDENCY","SCOPE",
}
ALLOWED_FAILURE_SEMANTICS={"DIRECT_CONTRACT","DERIVED_UPSTREAM"}


def _list_str(value: Any)->list[str]|None:
    if not isinstance(value,list) or any(not isinstance(x,str) or not x for x in value):
        return None
    return list(value)


def _failed_checks(row: Mapping[str,Any])->list[dict[str,Any]]|None:
    checks=row.get("checks")
    if not isinstance(checks,list):
        return None
    out=[]
    for item in checks:
        if not isinstance(item,Mapping):
            return None
        kind=item.get("kind")
        cid=item.get("id")
        passed=item.get("pass")
        evidence=_list_str(item.get("evidence"))
        semantics=item.get("failure_semantics","DIRECT_CONTRACT")
        if kind not in ALLOWED_KINDS or not isinstance(cid,str) or not cid:
            return None
        if type(passed) is not bool or evidence is None:
            return None
        if semantics not in ALLOWED_FAILURE_SEMANTICS:
            return None
        if not passed and not evidence:
            return None
        if not passed:
            out.append({
                "kind":kind,
                "id":cid,
                "evidence":evidence,
                "failure_semantics":semantics,
            })
    return out


def solve(public_case: Mapping[str,Any])->dict[str,Any]:
    task=public_case.get("task")
    if not isinstance(task,Mapping):
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID"}
    rows=task.get("trajectory")
    terminal_failed=_list_str(task.get("terminal_failed_resources"))
    if not isinstance(rows,list) or not rows or terminal_failed is None or not terminal_failed:
        return {"status":"FAIL_CLOSED","reason":"TRAJECTORY_OR_TERMINAL_FAILURE_INVALID"}

    by_id={}
    order={}
    failed={}
    reads={}
    writes={}
    explicit_deps={}
    composition={}

    for idx,row in enumerate(rows):
        if not isinstance(row,Mapping):
            return {"status":"FAIL_CLOSED","reason":"TRAJECTORY_ROW_INVALID"}
        aid=row.get("action_id")
        rds=_list_str(row.get("reads"))
        wrs=_list_str(row.get("writes"))
        deps=_list_str(row.get("depends_on"))
        comp=row.get("dependency_composition","SEQUENTIAL")
        fc=_failed_checks(row)
        if (
            not isinstance(aid,str) or not aid or aid in by_id
            or rds is None or wrs is None or deps is None or fc is None
            or comp not in {"SEQUENTIAL","CONJUNCTIVE","ALTERNATIVE"}
        ):
            return {"status":"FAIL_CLOSED","reason":"STEP_SCHEMA_INVALID"}
        if any(d not in by_id for d in deps):
            return {"status":"FAIL_CLOSED","reason":"NON_TOPOLOGICAL_DEPENDENCY"}
        by_id[aid]=row
        order[aid]=idx
        failed[aid]=fc
        reads[aid]=set(rds)
        writes[aid]=set(wrs)
        explicit_deps[aid]=set(deps)
        composition[aid]=comp

    deps={k:set(v) for k,v in explicit_deps.items()}
    last_writer={}
    for row in rows:
        aid=row["action_id"]
        for resource in reads[aid]:
            p=last_writer.get(resource)
            if p is not None:
                deps[aid].add(p)
        for resource in writes[aid]:
            last_writer[resource]=aid

    terminal_actions={last_writer[r] for r in terminal_failed if r in last_writer}
    if not terminal_actions:
        return {"status":"ESCALATE","reason":"NO_PRODUCER_FOR_TERMINAL_FAILED_RESOURCE"}

    relevant=set()
    stack=list(terminal_actions)
    while stack:
        aid=stack.pop()
        if aid in relevant:
            continue
        relevant.add(aid)
        stack.extend(deps[aid])

    ancestor_cache={}
    def ancestors(aid:str)->set[str]:
        if aid in ancestor_cache:
            return ancestor_cache[aid]
        out=set()
        todo=list(deps[aid])
        while todo:
            x=todo.pop()
            if x in out:
                continue
            out.add(x)
            todo.extend(deps[x])
        ancestor_cache[aid]=out
        return out

    direct_failed={
        aid for aid in relevant
        if any(x["failure_semantics"]=="DIRECT_CONTRACT" for x in failed[aid])
    }
    derived_failed={
        aid for aid in relevant
        if any(x["failure_semantics"]=="DERIVED_UPSTREAM" for x in failed[aid])
    }

    if not direct_failed:
        if derived_failed:
            return {
                "status":"ESCALATE",
                "reason":"ONLY_DERIVED_UPSTREAM_FAILURES_VISIBLE__DIRECT_CAUSAL_ROOT_NOT_ESTABLISHED",
            }
        return {"status":"ESCALATE","reason":"NO_DIRECT_CONTRACT_VIOLATION_ON_TERMINAL_CAUSAL_SLICE"}

    direct_ordered=sorted(direct_failed,key=lambda x:order[x])

    def detail(aid:str)->dict[str,Any]:
        checks=sorted(
            [x for x in failed[aid] if x["failure_semantics"]=="DIRECT_CONTRACT"],
            key=lambda x:(x["kind"],x["id"]),
        )
        kinds=sorted({x["kind"] for x in checks})
        evidence=sorted({e for x in checks for e in x["evidence"]})
        repairs=sorted({f"restore:{aid}:{x['kind']}" for x in checks})
        return {
            "action_id":aid,
            "mechanism_classes":kinds,
            "supporting_receipts":evidence,
            "repair_targets":repairs,
        }

    if len(direct_ordered)==1:
        root=direct_ordered[0]
        d=detail(root)
        return {
            "status":"IDENTIFIED",
            "cause_action_id":root,
            "cause_action_ids":[root],
            "critical_action_id":root,
            "mechanism_classes":d["mechanism_classes"],
            "supporting_receipts":d["supporting_receipts"],
            "repair_targets":d["repair_targets"],
            "reason":"UNIQUE_DIRECT_CONTRACT_VIOLATION_ON_TERMINAL_CAUSAL_SLICE",
        }

    direct_set=set(direct_ordered)

    # Preserve V6 non-identifiability when multiple direct defects feed an explicit
    # ALTERNATIVE merge and no conjunction establishes a joint repair obligation.
    alternative_witnesses=[]
    for aid in relevant:
        if composition[aid]!="ALTERNATIVE":
            continue
        if direct_set.issubset(ancestors(aid) | ({aid} if aid in direct_set else set())):
            alternative_witnesses.append(aid)
    if alternative_witnesses:
        return {
            "status":"AMBIGUOUS",
            "cause_action_id":None,
            "cause_action_ids":direct_ordered,
            "critical_action_id":None,
            "candidates":[detail(x) for x in direct_ordered],
            "reason":"MULTIPLE_DIRECT_CONTRACT_FAILURES_REMAIN_NONIDENTIFIABLE_UNDER_VISIBLE_ALTERNATIVE_DEPENDENCY",
            "information_request":"ACQUIRE_INTERVENTION_OR_ADDITIONAL_CAUSAL_DISCRIMINATOR",
        }

    conjunctive_witnesses=[]
    for aid in relevant:
        if composition[aid]!="CONJUNCTIVE":
            continue
        if direct_set.issubset(ancestors(aid) | ({aid} if aid in direct_set else set())):
            conjunctive_witnesses.append(aid)

    # Serial direct co-faults are jointly repair-relevant even without an explicit
    # conjunctive merge: a later DIRECT_CONTRACT failure remains active after an
    # upstream direct repair. Use the later direct-fault steps as explicit witnesses.
    serial_witnesses=[
        aid for aid in direct_ordered
        if any(other in ancestors(aid) for other in direct_set if other!=aid)
    ]
    witnesses=sorted(set(conjunctive_witnesses+serial_witnesses),key=lambda x:order[x])
    details=[detail(x) for x in direct_ordered]
    return {
        "status":"INTERACTION",
        "cause_action_id":direct_ordered[0],
        "cause_action_ids":direct_ordered,
        "critical_action_id":direct_ordered[0],
        "interaction_witness_action_ids":witnesses,
        "mechanism_by_action":{d["action_id"]:d["mechanism_classes"] for d in details},
        "supporting_receipts":sorted({e for d in details for e in d["supporting_receipts"]}),
        "repair_targets":sorted({r for d in details for r in d["repair_targets"]}),
        "reason":(
            "MULTIPLE_DIRECT_CONTRACT_FAILURES_REQUIRE_JOINT_REPAIR_ON_TERMINAL_CAUSAL_SLICE"
        ),
    }
