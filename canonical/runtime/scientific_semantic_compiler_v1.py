"""Bounded source-grounded scientific semantic compiler V1.

Extends the existing explicit numeric compiler with two bounded deterministic
semantic routes:
1. finite zero-learned role paraphrase induction for numeric input/target roles;
2. structural scientific-family recognition for explicit rule/abduction JSON,
   gated by a generic scientific action cue.

It does not claim open-world natural-language understanding. Conflicts and
unsupported language fail closed.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime import general_scientific_capability_controller_v1 as controller
from canonical.runtime import h100_zero_learned_semantic_paraphrase_v1 as roles
from canonical.runtime import scientific_numeric_task_compiler_v1 as numeric

SCHEMA="PROJECT_BRAIN_SCIENTIFIC_SEMANTIC_COMPILER_V1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0
NETWORK_DEPENDENCY_COUNT=0

ACTION_CUE=re.compile(
    r"\b(infer|derive|determine|find|identify|synthesize|compute|solve|"
    r"classify|explain|diagnose|evaluate|estimate|model|predict|fit)\b",re.I
)


def _fail(reason:str,details:Mapping[str,Any]|None=None)->dict[str,Any]:
    out={
        "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":reason,
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "network_dependency_count":0,"terminal_authority":False,
    }
    if details is not None: out["details"]=dict(details)
    return out


def _symbolic_from_roles(instruction:str,raw_rows:Any)->dict[str,Any]:
    try:
        rows,cols=numeric._rows(raw_rows)
    except ValueError as exc:
        return _fail(str(exc))
    try:
        sem=roles.induce_semantic_roles(instruction)
    except Exception as exc:
        return _fail("ROLE_SEMANTICS_REJECTED",{"error_type":type(exc).__name__,"error":str(exc)})
    if sem.get("status")!="ROLES_IDENTIFIED":
        return _fail("ROLE_SEMANTICS_ABSTAINED")
    target=sem.get("target"); inputs=list(sem.get("inputs") or [])
    names=set(cols)
    if not isinstance(target,str) or target not in names:
        return _fail("SEMANTIC_TARGET_NOT_NUMERIC_COLUMN")
    if not inputs or any(x not in names for x in inputs):
        return _fail("SEMANTIC_INPUT_NOT_NUMERIC_COLUMN")
    if target in inputs:
        return _fail("SEMANTIC_INPUT_TARGET_OVERLAP")
    typed=[]; dropped=0
    for row in rows:
        vals={n:numeric._num(row.get(n)) for n in inputs+[target]}
        if all(v is not None for v in vals.values()): typed.append(vals)
        else: dropped+=1
    if len(typed)<8:
        return _fail("SYMBOLIC_COMPLETE_ROWS_INSUFFICIENT")
    problem={"rows":typed,"target":target,"inputs":sorted(inputs),"max_depth":1}
    sig=controller.infer_signature(problem)
    if sig.get("family")!=controller.SYMBOLIC:
        return _fail("SEMANTIC_SYMBOLIC_SIGNATURE_NOT_IDENTIFIED")
    return {
        "schema":SCHEMA,"status":"COMPILED","pass":True,
        "family":controller.SYMBOLIC,"task_problem":problem,
        "semantic_route":"ZERO_LEARNED_ROLE_PARAPHRASE",
        "semantic_evidence":sem,
        "provenance":{"target":target,"inputs":sorted(inputs),"rows_used":len(typed),"rows_dropped":dropped},
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "network_dependency_count":0,"terminal_authority":False,
    }


def compile_numeric(instruction:str,raw_rows:Any)->dict[str,Any]:
    base=numeric.compile_numeric_task(instruction,raw_rows)
    if base.get("status")=="COMPILED":
        return {
            "schema":SCHEMA,"status":"COMPILED","pass":True,
            "family":base["family"],"task_problem":base["task_problem"],
            "semantic_route":"EXPLICIT_NUMERIC_COMPILER",
            "semantic_evidence":{"base_compiler":base},
            "model_dependency_count":0,"external_model_runtime_calls":0,
            "network_dependency_count":0,"terminal_authority":False,
        }
    if base.get("reason")!="NO_SUPPORTED_NUMERIC_SCIENCE_INTENT":
        return _fail("EXPLICIT_NUMERIC_COMPILER_REJECTED",{"base_compiler":base})
    fallback=_symbolic_from_roles(instruction,raw_rows)
    if fallback.get("status")=="COMPILED":
        fallback["semantic_evidence"]["base_compiler_abstention"]=base
        return fallback
    return _fail("NO_BOUNDED_NUMERIC_SEMANTIC_ROUTE",{
        "base_compiler":base,
        "role_route":fallback,
    })


def _rule_problem(value:Any)->dict[str,Any]|None:
    if not isinstance(value,Mapping): return None
    raw=value.get("rule_problem") if isinstance(value.get("rule_problem"),Mapping) else value
    if not isinstance(raw,Mapping) or not all(k in raw for k in ("predicates","examples","emit")):
        return None
    if not isinstance(raw.get("predicates"),list) or not isinstance(raw.get("examples"),list) or not isinstance(raw.get("emit"),Mapping):
        return None
    problem={"predicates":raw["predicates"],"examples":raw["examples"],"emit":dict(raw["emit"])}
    return problem if controller.infer_signature(problem).get("family")==controller.RULE else None


def _abduction_problem(value:Any)->dict[str,Any]|None:
    if not isinstance(value,Mapping): return None
    raw=value.get("abduction") if isinstance(value.get("abduction"),Mapping) else value
    if not isinstance(raw,Mapping) or not all(k in raw for k in ("targets","baseline_facts","implications")):
        return None
    problem={"abduction":dict(raw)}
    return problem if controller.infer_signature(problem).get("family")==controller.ABDUCTION else None


def compile_structured(instruction:str,value:Any)->dict[str,Any]:
    if not isinstance(instruction,str) or not instruction.strip():
        return _fail("INSTRUCTION_INVALID")
    if ACTION_CUE.search(instruction) is None:
        return _fail("GENERIC_SCIENTIFIC_ACTION_CUE_ABSENT")
    candidates=[]
    rp=_rule_problem(value)
    if rp is not None: candidates.append((controller.RULE,rp))
    ap=_abduction_problem(value)
    if ap is not None: candidates.append((controller.ABDUCTION,ap))
    if not candidates:
        return _fail("NO_SUPPORTED_STRUCTURED_SCIENCE_SIGNATURE")
    if len(candidates)!=1:
        return _fail("AMBIGUOUS_STRUCTURED_SCIENCE_SIGNATURE")
    family,problem=candidates[0]
    return {
        "schema":SCHEMA,"status":"COMPILED","pass":True,
        "family":family,"task_problem":problem,
        "semantic_route":"STRUCTURE_PLUS_GENERIC_ACTION_CUE",
        "semantic_evidence":{
            "action_cue":ACTION_CUE.search(instruction).group(0).lower(),
            "resource_signature":family,
        },
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "network_dependency_count":0,"terminal_authority":False,
    }
