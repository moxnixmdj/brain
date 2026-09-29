#!/usr/bin/env python3
"""Deterministic model-independent evidence -> terminal decision synthesis.

Input is already-structured evidence. This module deliberately does not own
natural-language interpretation, evidence discovery, or source calibration.
ProbLog is used only as an exact weighted logical consequence engine.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import pathlib
import re
from typing import Any

SCHEMA="PROJECT_BRAIN_TYPED_EVIDENCE_DECISION_TASK_V1"
RESULT_SCHEMA="PROJECT_BRAIN_EVIDENCE_DECISION_RESULT_V1"
DECISIONS={"ACCEPT","REJECT","INSUFFICIENT_EVIDENCE"}
STANCES={"SUPPORT","OPPOSE","NEUTRAL"}
_ID_RE=re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,79}$")


class SynthesisError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SynthesisError(code)


def _number(value: Any, code: str, *, lo: float=0.0, hi: float=1.0) -> float:
    _require(isinstance(value,(int,float)) and not isinstance(value,bool),code)
    out=float(value)
    _require(math.isfinite(out) and lo <= out <= hi,code)
    return out


def _atom(prefix: str, raw: str) -> str:
    _require(isinstance(raw,str) and bool(_ID_RE.fullmatch(raw)),f"INVALID_ID:{raw}")
    return prefix + re.sub(r"[^a-zA-Z0-9_]","_",raw).lower()


def _topological_rules(rules: list[dict[str,Any]], evidence_ids: set[str]) -> list[dict[str,Any]]:
    by_id={str(r["id"]):r for r in rules}
    deps: dict[str,set[str]]={}
    for rid,rule in by_id.items():
        refs=set(str(x) for x in rule.get("antecedents") or [])
        unknown=refs-(evidence_ids|set(by_id))
        _require(not unknown,"RULE_UNKNOWN_ANTECEDENT:"+rid+":"+",".join(sorted(unknown)))
        deps[rid]={x for x in refs if x in by_id}

    ordered=[]
    remaining=set(by_id)
    while remaining:
        ready=sorted(r for r in remaining if not (deps[r]&remaining))
        _require(bool(ready),"RULE_DEPENDENCY_CYCLE:"+",".join(sorted(remaining)))
        for rid in ready:
            ordered.append(by_id[rid])
            remaining.remove(rid)
    return ordered


def validate_task(task: dict[str,Any]) -> dict[str,Any]:
    _require(isinstance(task,dict),"TASK_NOT_OBJECT")
    _require(task.get("schema")==SCHEMA,"TASK_SCHEMA_INVALID")
    for key in ("task_id","question","decision_id"):
        _require(isinstance(task.get(key),str) and bool(task[key].strip()),"TASK_FIELD_MISSING:"+key)

    evidence=task.get("evidence")
    rules=task.get("rules")
    policy=task.get("policy")
    hard=task.get("hard_constraints",[])
    _require(isinstance(evidence,list) and evidence,"EVIDENCE_MISSING")
    _require(isinstance(rules,list) and rules,"RULES_MISSING")
    _require(isinstance(policy,dict),"POLICY_MISSING")
    _require(isinstance(hard,list),"HARD_CONSTRAINTS_NOT_LIST")

    evidence_ids=set()
    for item in evidence:
        _require(isinstance(item,dict),"EVIDENCE_ITEM_INVALID")
        eid=str(item.get("id") or "")
        _require(bool(_ID_RE.fullmatch(eid)),"EVIDENCE_ID_INVALID:"+eid)
        _require(eid not in evidence_ids,"EVIDENCE_ID_DUPLICATE:"+eid)
        evidence_ids.add(eid)
        _number(item.get("probability"),"EVIDENCE_PROBABILITY_INVALID:"+eid)
        _require(isinstance(item.get("statement"),str) and bool(item["statement"].strip()),"EVIDENCE_STATEMENT_MISSING:"+eid)
        provenance=item.get("provenance")
        _require(isinstance(provenance,dict) and bool(provenance),"EVIDENCE_PROVENANCE_MISSING:"+eid)

    rule_ids=set()
    for rule in rules:
        _require(isinstance(rule,dict),"RULE_INVALID")
        rid=str(rule.get("id") or "")
        _require(bool(_ID_RE.fullmatch(rid)),"RULE_ID_INVALID:"+rid)
        _require(rid not in rule_ids and rid not in evidence_ids,"RULE_ID_DUPLICATE:"+rid)
        rule_ids.add(rid)
        ants=rule.get("antecedents")
        _require(isinstance(ants,list) and ants and all(isinstance(x,str) for x in ants),"RULE_ANTECEDENTS_INVALID:"+rid)
        _number(rule.get("strength",1.0),"RULE_STRENGTH_INVALID:"+rid)
        stance=str(rule.get("stance") or "")
        _require(stance in STANCES,"RULE_STANCE_INVALID:"+rid)

    _topological_rules(rules,evidence_ids)
    all_refs=evidence_ids|rule_ids
    for item in hard:
        _require(isinstance(item,dict),"HARD_CONSTRAINT_INVALID")
        hid=str(item.get("id") or "")
        _require(bool(_ID_RE.fullmatch(hid)),"HARD_CONSTRAINT_ID_INVALID:"+hid)
        ref=str(item.get("ref") or "")
        _require(ref in all_refs,"HARD_CONSTRAINT_REF_INVALID:"+hid)
        _number(item.get("trigger_probability",1.0),"HARD_CONSTRAINT_THRESHOLD_INVALID:"+hid)
        _require(str(item.get("decision") or "") in {"ACCEPT","REJECT"},"HARD_CONSTRAINT_DECISION_INVALID:"+hid)
        _require(isinstance(item.get("reason"),str) and bool(item["reason"].strip()),"HARD_CONSTRAINT_REASON_MISSING:"+hid)

    accept=_number(policy.get("accept_threshold"),"ACCEPT_THRESHOLD_INVALID")
    reject=_number(policy.get("reject_threshold"),"REJECT_THRESHOLD_INVALID")
    margin=_number(policy.get("min_margin"),"MIN_MARGIN_INVALID")
    conflict=_number(policy.get("conflict_threshold"),"CONFLICT_THRESHOLD_INVALID")
    floor=_number(policy.get("evidence_floor"),"EVIDENCE_FLOOR_INVALID")
    _require(accept >= 0.5 and reject >= 0.5,"DECISION_THRESHOLD_TOO_LOW")
    _require(margin > 0.0,"MIN_MARGIN_MUST_BE_POSITIVE")
    _require(conflict > 0.0,"CONFLICT_THRESHOLD_MUST_BE_POSITIVE")
    _require(floor > 0.0,"EVIDENCE_FLOOR_MUST_BE_POSITIVE")
    return task


def compile_problog(task: dict[str,Any]) -> tuple[str,dict[str,str]]:
    validate_task(task)
    evidence=task["evidence"]
    rules=_topological_rules(task["rules"],{x["id"] for x in evidence})
    atoms: dict[str,str]={}
    lines=[
        "% Project Brain model-independent evidence synthesis.",
        "% Input SHA-256: "+sha256_json(task),
        "0.0::support_signal.",
        "0.0::oppose_signal.",
    ]

    for item in sorted(evidence,key=lambda x:x["id"]):
        atom=_atom("ev_",item["id"])
        atoms[item["id"]]=atom
        p=float(item["probability"])
        lines.append(f"{p:.12g}::{atom}.")

    for rule in rules:
        atom=_atom("rule_",rule["id"])
        atoms[rule["id"]]=atom
        ant_atoms=[atoms[x] for x in rule["antecedents"]]
        body=", ".join(ant_atoms)
        strength=float(rule.get("strength",1.0))
        if strength >= 1.0-1e-15:
            lines.append(f"{atom} :- {body}.")
        else:
            lines.append(f"{strength:.12g}::{atom} :- {body}.")
        if rule["stance"]=="SUPPORT":
            lines.append(f"support_signal :- {atom}.")
        elif rule["stance"]=="OPPOSE":
            lines.append(f"oppose_signal :- {atom}.")

    query_atoms=["support_signal","oppose_signal"]+[atoms[k] for k in sorted(atoms)]
    for atom in query_atoms:
        lines.append(f"query({atom}).")
    return "\n".join(lines)+"\n",atoms


def _evaluate(program: str) -> dict[str,float]:
    try:
        from problog import get_evaluatable
        from problog.program import PrologString
    except Exception as exc:
        raise SynthesisError("PROBLOG_IMPORT_FAILED:"+type(exc).__name__) from exc
    try:
        raw=get_evaluatable().create_from(PrologString(program)).evaluate()
    except Exception as exc:
        raise SynthesisError("PROBLOG_EVALUATION_FAILED:"+type(exc).__name__+":"+str(exc)) from exc
    return {str(k):float(v) for k,v in raw.items()}


def synthesize(task: dict[str,Any]) -> dict[str,Any]:
    task=validate_task(task)
    program,atoms=compile_problog(task)
    values=_evaluate(program)

    support=float(values.get("support_signal",0.0))
    oppose=float(values.get("oppose_signal",0.0))
    policy=task["policy"]
    conflict_mass=min(support,oppose)
    ignorance=max(0.0,1.0-max(support,oppose))
    margin=abs(support-oppose)

    triggered=[]
    for hc in task.get("hard_constraints",[]):
        atom=atoms[hc["ref"]]
        probability=float(values.get(atom,0.0))
        if probability+1e-12 >= float(hc.get("trigger_probability",1.0)):
            triggered.append({
                "id":hc["id"],
                "ref":hc["ref"],
                "probability":probability,
                "decision":hc["decision"],
                "reason":hc["reason"],
            })

    forced={x["decision"] for x in triggered}
    policy_path=[]
    if len(forced)>1:
        decision="INSUFFICIENT_EVIDENCE"
        policy_path.append("CONFLICTING_HARD_CONSTRAINTS")
    elif len(forced)==1:
        decision=next(iter(forced))
        policy_path.append("HARD_CONSTRAINT")
    elif max(support,oppose) < float(policy["evidence_floor"]):
        decision="INSUFFICIENT_EVIDENCE"
        policy_path.append("BELOW_EVIDENCE_FLOOR")
    elif support >= float(policy["conflict_threshold"]) and oppose >= float(policy["conflict_threshold"]):
        decision="INSUFFICIENT_EVIDENCE"
        policy_path.append("UNRESOLVED_SUPPORT_OPPOSITION_CONFLICT")
    elif support >= float(policy["accept_threshold"]) and support-oppose >= float(policy["min_margin"]):
        decision="ACCEPT"
        policy_path.append("SUPPORT_THRESHOLD_AND_MARGIN")
    elif oppose >= float(policy["reject_threshold"]) and oppose-support >= float(policy["min_margin"]):
        decision="REJECT"
        policy_path.append("OPPOSITION_THRESHOLD_AND_MARGIN")
    else:
        decision="INSUFFICIENT_EVIDENCE"
        policy_path.append("NO_TERMINAL_THRESHOLD")

    version=importlib.metadata.version("problog")
    trace_items=[]
    for item in sorted(task["evidence"],key=lambda x:x["id"]):
        trace_items.append({
            "kind":"EVIDENCE",
            "id":item["id"],
            "probability":float(values.get(atoms[item["id"]],0.0)),
            "statement":item["statement"],
            "provenance":item["provenance"],
        })
    for rule in sorted(task["rules"],key=lambda x:x["id"]):
        trace_items.append({
            "kind":"RULE",
            "id":rule["id"],
            "antecedents":list(rule["antecedents"]),
            "stance":rule["stance"],
            "strength":float(rule.get("strength",1.0)),
            "activation_probability":float(values.get(atoms[rule["id"]],0.0)),
            "description":rule.get("description",""),
        })

    result={
        "schema":RESULT_SCHEMA,
        "task_id":task["task_id"],
        "decision_id":task["decision_id"],
        "question":task["question"],
        "decision":decision,
        "support_probability":support,
        "opposition_probability":oppose,
        "conflict_mass":conflict_mass,
        "ignorance_mass":ignorance,
        "decision_margin":margin,
        "hard_constraints_triggered":triggered,
        "unresolved_conflict":bool(
            support >= float(policy["conflict_threshold"])
            and oppose >= float(policy["conflict_threshold"])
        ),
        "policy_path":policy_path,
        "input_sha256":sha256_json(task),
        "generated_problog_sha256":hashlib.sha256(program.encode("utf-8")).hexdigest(),
        "generated_problog":program,
        "problog_version":version,
        "model_dependency_count":0,
        "trace":trace_items,
    }
    return result


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--out")
    ns=ap.parse_args()
    path=pathlib.Path(ns.task)
    task=json.loads(path.read_text(encoding="utf-8"))
    result=synthesize(task)
    text=json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
    if ns.out:
        pathlib.Path(ns.out).write_text(text,encoding="utf-8")
    print(text,end="")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
