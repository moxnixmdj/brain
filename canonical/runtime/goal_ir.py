#!/usr/bin/env python3
"""Deterministic compiler from untrusted semantic Goal IR into capability_problem.

The proposer may describe intent, spans, literal inputs, and optional capability
allowlists. It may not provide executable actions. Executable actions come only
from VERIFIED_BOUND_CAPABILITY registry entries.
"""
from __future__ import annotations

import hashlib
import json
import re


class GoalIRFailure(RuntimeError):
    def __init__(self, code, detail=None):
        self.code=code
        self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


def _strings(value, field, allow_empty=False):
    if not isinstance(value,list) or any(not isinstance(x,str) or not x.strip() for x in value):
        raise GoalIRFailure("INVALID_STRING_LIST",field)
    out=[x.strip() for x in value]
    if not allow_empty and not out:
        raise GoalIRFailure("EMPTY_STRING_LIST",field)
    return out


def _goal_sha256(goal):
    return hashlib.sha256(str(goal).encode("utf-8")).hexdigest()


def _validate_clause_coverage(goal, clauses, targets):
    if not isinstance(clauses,list) or not clauses:
        raise GoalIRFailure("GOAL_IR_CLAUSES_REQUIRED")
    covered=[False]*len(goal)
    seen_indexes=set()
    for i,clause in enumerate(clauses):
        if not isinstance(clause,dict):
            raise GoalIRFailure("GOAL_IR_CLAUSE_INVALID",str(i))
        try:
            start=int(clause["start"])
            end=int(clause["end"])
        except Exception as exc:
            raise GoalIRFailure("GOAL_IR_CLAUSE_SPAN_INVALID",str(i)) from exc
        if start<0 or end<=start or end>len(goal):
            raise GoalIRFailure("GOAL_IR_CLAUSE_SPAN_INVALID",str(i))
        text=str(clause.get("text") or "")
        if goal[start:end]!=text:
            raise GoalIRFailure("GOAL_IR_CLAUSE_TEXT_MISMATCH",str(i))
        clause_targets=_strings(clause.get("target_effects",[]),f"clauses[{i}].target_effects")
        unknown=sorted(set(clause_targets)-set(targets))
        if unknown:
            raise GoalIRFailure("GOAL_IR_CLAUSE_TARGET_UNKNOWN",",".join(unknown))
        for pos in range(start,end):
            covered[pos]=True
        idx=clause.get("index",i)
        if idx in seen_indexes:
            raise GoalIRFailure("GOAL_IR_CLAUSE_INDEX_DUPLICATE",str(idx))
        seen_indexes.add(idx)
    uncovered=[
        i for i,ch in enumerate(goal)
        if not ch.isspace() and not covered[i]
    ]
    if uncovered:
        first=uncovered[0]
        raise GoalIRFailure("GOAL_IR_TEXT_UNCOVERED",f"{first}:{goal[first:first+40]}")
    represented=set()
    for clause in clauses:
        represented.update(clause.get("target_effects") or [])
    missing=sorted(set(targets)-represented)
    if missing:
        raise GoalIRFailure("GOAL_IR_TARGET_UNCOVERED",",".join(missing))


def _placeholders(value):
    out=set()
    if isinstance(value,dict):
        for v in value.values():
            out.update(_placeholders(v))
    elif isinstance(value,list):
        for v in value:
            out.update(_placeholders(v))
    elif isinstance(value,str):
        out.update(re.findall(r"\$\{input\.([A-Za-z_][A-Za-z0-9_]*)\}",value))
    return out


def _resolve_binding(name, spec, inputs, requires):
    if spec is None:
        if name not in inputs:
            raise GoalIRFailure("GOAL_IR_LITERAL_INPUT_MISSING",name)
        return inputs[name]
    if not isinstance(spec,dict):
        raise GoalIRFailure("GOAL_IR_INPUT_CONTRACT_INVALID",name)
    kind=str(spec.get("kind") or "").strip()
    if kind=="goal_input":
        key=str(spec.get("key") or name).strip()
        if key not in inputs:
            raise GoalIRFailure("GOAL_IR_LITERAL_INPUT_MISSING",key)
        return inputs[key]
    if kind=="literal":
        if "value" not in spec:
            raise GoalIRFailure("GOAL_IR_LITERAL_VALUE_MISSING",name)
        return spec["value"]
    if kind=="effect_result":
        effect=str(spec.get("effect") or "").strip()
        field=str(spec.get("field") or "").strip()
        if not effect or not field:
            raise GoalIRFailure("GOAL_IR_EFFECT_BINDING_INVALID",name)
        if effect not in requires:
            raise GoalIRFailure("GOAL_IR_EFFECT_NOT_REQUIRED",f"{name}:{effect}")
        return {"$effect_result":{"effect":effect,"field":field}}
    raise GoalIRFailure("GOAL_IR_INPUT_KIND_UNKNOWN",f"{name}:{kind}")


def _render(value, bindings):
    if isinstance(value,dict):
        return {k:_render(v,bindings) for k,v in value.items()}
    if isinstance(value,list):
        return [_render(v,bindings) for v in value]
    if isinstance(value,str):
        m=re.fullmatch(r"\$\{input\.([A-Za-z_][A-Za-z0-9_]*)\}",value)
        if m:
            return bindings[m.group(1)]
        out=value
        for key,val in bindings.items():
            token="${input."+key+"}"
            if token in out:
                if isinstance(val,(dict,list)):
                    raise GoalIRFailure("GOAL_IR_COMPLEX_INPUT_EMBEDDED",key)
                out=out.replace(token,str(val))
        if "${input." in out:
            raise GoalIRFailure("GOAL_IR_TEMPLATE_INPUT_UNRESOLVED",out)
        return out
    return value


def build_capability_problem(goal, ir, registry):
    goal=str(goal or "")
    if not goal.strip():
        raise GoalIRFailure("GOAL_REQUIRED")
    if not isinstance(ir,dict) or ir.get("schema")!="PROJECT_BRAIN_GOAL_IR_V1":
        raise GoalIRFailure("GOAL_IR_SCHEMA_INVALID")
    expected_sha=str(ir.get("goal_sha256") or "").lower()
    actual_sha=_goal_sha256(goal)
    if expected_sha!=actual_sha:
        raise GoalIRFailure("GOAL_IR_GOAL_HASH_MISMATCH")

    initial=_strings(ir.get("initial_facts",[]),"initial_facts",allow_empty=True)
    targets=_strings(ir.get("target_effects",[]),"target_effects")
    _validate_clause_coverage(goal,ir.get("clauses"),targets)

    inputs=ir.get("inputs") or {}
    if not isinstance(inputs,dict):
        raise GoalIRFailure("GOAL_IR_INPUTS_INVALID")

    allow=ir.get("capability_allowlist")
    if allow is not None:
        allow=_strings(allow,"capability_allowlist")
        missing=sorted(set(allow)-set((registry or {}).keys()))
        if missing:
            raise GoalIRFailure("GOAL_IR_CAPABILITY_UNKNOWN",",".join(missing))
        allow=set(allow)

    caps=[]
    for cid,entry in sorted((registry or {}).items()):
        if allow is not None and cid not in allow:
            continue
        if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            continue
        template=entry.get("action_template")
        if not isinstance(template,dict):
            continue
        requires=_strings(entry.get("requires",[]),f"{cid}.requires",allow_empty=True)
        provides=_strings(entry.get("provides",[]),f"{cid}.provides")
        placeholders=_placeholders(template)
        contract=entry.get("input_contract") or {}
        if not isinstance(contract,dict):
            raise GoalIRFailure("GOAL_IR_REGISTRY_INPUT_CONTRACT_INVALID",cid)
        bindings={}
        unavailable=False
        for name in sorted(placeholders):
            try:
                bindings[name]=_resolve_binding(name,contract.get(name),inputs,requires)
            except GoalIRFailure as exc:
                if exc.code=="GOAL_IR_LITERAL_INPUT_MISSING":
                    unavailable=True
                    break
                raise
        if unavailable:
            continue
        try:
            cost=float(entry.get("cost",1))
        except Exception as exc:
            raise GoalIRFailure("GOAL_IR_CAPABILITY_COST_INVALID",cid) from exc
        if cost<0:
            raise GoalIRFailure("GOAL_IR_CAPABILITY_COST_INVALID",cid)
        result_fields=_strings(entry.get("result_fields",[]),f"{cid}.result_fields",allow_empty=True)
        caps.append({
          "id":cid,
          "requires":requires,
          "provides":provides,
          "cost":cost,
          "action":_render(template,bindings),
          "result_fields":result_fields,
        })

    if not caps:
        raise GoalIRFailure("GOAL_IR_NO_EXECUTABLE_VERIFIED_CAPABILITIES")
    return {
      "schema":"PROJECT_BRAIN_CAPABILITY_PROBLEM_V1",
      "goal_sha256":actual_sha,
      "initial_facts":initial,
      "target_effects":targets,
      "capabilities":caps,
      "finish_summary":"GOAL_IR_COMPLETE",
      "max_expansions":max(1,min(int(ir.get("max_expansions",5000)),100000)),
    }
