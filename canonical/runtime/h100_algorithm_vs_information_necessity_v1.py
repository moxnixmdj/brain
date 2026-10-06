"""Separate information necessity from algorithm/compute necessity for H100."""
from __future__ import annotations

import hashlib, json
from typing import Any, Callable, Iterable

SCHEMA="PROJECT_BRAIN_H100_ALGORITHM_VS_INFORMATION_NECESSITY_V1"

class NecessityError(ValueError):
    pass

def deterministic_function_certificate(*, runtime_information_complete: bool, function_computable: bool) -> dict[str,Any]:
    if not isinstance(runtime_information_complete,bool) or not isinstance(function_computable,bool):
        raise NecessityError("BOOLEAN_REQUIRED")
    exists_zero_world_dependent_bit_program = runtime_information_complete and function_computable
    return {
        "schema":SCHEMA,
        "runtime_information_complete":runtime_information_complete,
        "function_computable":function_computable,
        "zero_world_dependent_learned_bits_information_theoretically_sufficient":exists_zero_world_dependent_bit_program,
        "positive_learned_bits_information_theoretically_necessary":False if exists_zero_world_dependent_bit_program else None,
        "remaining_possible_barriers":[
            "PROGRAM_DESCRIPTION_LENGTH",
            "RUNTIME_COMPUTE",
            "WORKING_MEMORY",
            "SEARCH_COST",
            "UNKNOWN_OR_UNAVAILABLE_RUNTIME_INFORMATION",
        ],
    }

def finite_lookup_program(pairs: Iterable[tuple[Any,Any]]) -> Callable[[Any],Any]:
    """Construct an explicit deterministic finite-domain zero-learned solver."""
    table={}
    for x,y in pairs:
        key=json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        if key in table and table[key]!=y:
            raise NecessityError("INPUT_NOT_FUNCTIONAL")
        table[key]=y
    if not table:
        raise NecessityError("EMPTY_DOMAIN")
    def solve(x:Any)->Any:
        key=json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        if key not in table:
            raise NecessityError("OUT_OF_DOMAIN")
        return table[key]
    return solve

def finite_solver_description_bytes(pairs: Iterable[tuple[Any,Any]]) -> int:
    rows=list(pairs)
    if not rows:
        raise NecessityError("EMPTY_DOMAIN")
    blob=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return len(blob)

def learned_state_role(*, carries_instance_specific_missing_information: bool, carries_algorithm_or_prior: bool, carries_world_knowledge: bool) -> str:
    flags=[carries_instance_specific_missing_information,carries_algorithm_or_prior,carries_world_knowledge]
    if any(not isinstance(x,bool) for x in flags):
        raise NecessityError("BOOLEAN_REQUIRED")
    roles=[]
    if carries_instance_specific_missing_information: roles.append("INSTANCE_INFORMATION")
    if carries_algorithm_or_prior: roles.append("ALGORITHM_OR_PRIOR")
    if carries_world_knowledge: roles.append("WORLD_KNOWLEDGE")
    return "+".join(roles) if roles else "NONE"

def certificate()->dict[str,Any]:
    c=deterministic_function_certificate(runtime_information_complete=True,function_computable=True)
    return {
        "schema":SCHEMA,
        "status":"FORMAL_SEPARATION_OF_INFORMATION_AND_ALGORITHMIC_NECESSITY",
        "core":c,
        "deduction":[
            "WHEN_AVAILABLE_RUNTIME_INFORMATION_FULLY_DETERMINES_THE_OUTPUT_AND_THE_MAPPING_IS_COMPUTABLE__POSITIVE_LEARNED_STATE_IS_NOT_REQUIRED_BY_INFORMATION_THEORY",
            "LEARNED_STATE_MAY_STILL_COMPRESS_A_LARGE_PROGRAM_PRIOR_OR_WORLD_KNOWLEDGE_AND_THUS_BE_CRITICAL_UNDER_RESOURCE_BOUNDS",
            "THE_NEXT_LOWER_BOUND_TARGET_IS_RESOURCE_BOUNDED_ALGORITHM_DESCRIPTION_OR_COMPUTE__NOT_RAW_INFORMATION",
        ],
        "h100_terminal_credit_delta":0,
    }
