"""Computable capability / resource tradeoff theorem for H100.

The theorem is deliberately narrow:

If a task is input-complete and its correct behavior is a total computable
function f, then by definition some finite deterministic program computes f.
If deterministic program bytes are allowed and accounted separately from
learned state, positive persistent learned state is not logically necessary.

This is not a practical efficiency claim. Capability may migrate into:
- deterministic program description length L,
- runtime T,
- external information E,
- nonlearned task state S.

Therefore B=learned bits must be studied jointly with (L,T,E,S).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

SCHEMA="PROJECT_BRAIN_H100_COMPUTABLE_CAPABILITY_RESOURCE_TRADEOFF_V1"


class ResourceTradeoffError(ValueError):
    pass


@dataclass(frozen=True)
class ResourceVector:
    learned_bits: int
    deterministic_capability_bits: int
    runtime_steps: int
    external_information_bits: int
    task_state_bits: int

    def __post_init__(self):
        for name,value in asdict(self).items():
            if not isinstance(value,int) or isinstance(value,bool) or value<0:
                raise ResourceTradeoffError("RESOURCE_INVALID:"+name)

    def to_dict(self)->dict[str,int]:
        return dict(asdict(self))


def logical_learned_state_lower_bound(
    *,
    input_complete: bool,
    total_computable: bool,
    deterministic_program_allowed: bool,
    deterministic_program_bits_count_as_learned: bool,
)->dict[str,Any]:
    assumptions={
        "input_complete":bool(input_complete),
        "total_computable":bool(total_computable),
        "deterministic_program_allowed":bool(deterministic_program_allowed),
        "deterministic_program_bits_count_as_learned":bool(deterministic_program_bits_count_as_learned),
    }
    theorem_applies=(
        input_complete
        and total_computable
        and deterministic_program_allowed
        and not deterministic_program_bits_count_as_learned
    )
    if theorem_applies:
        return {
            "schema":SCHEMA,
            "status":"ZERO_LOGICAL_LEARNED_STATE_NECESSITY_BOUND",
            "logical_learned_state_lower_bound_bits":0,
            "theorem_applies":True,
            "assumptions":assumptions,
            "deduction":"SOME_FINITE_WORLD_INDEPENDENT_DETERMINISTIC_PROGRAM_COMPUTES_THE_TASK_BY_DEFINITION_OF_TOTAL_COMPUTABILITY",
        }
    return {
        "schema":SCHEMA,
        "status":"THEOREM_NOT_APPLICABLE__NO_ZERO_BOUND_CLAIM",
        "logical_learned_state_lower_bound_bits":None,
        "theorem_applies":False,
        "assumptions":assumptions,
    }


def finite_lookup_resource(
    *,
    case_count:int,
    key_bits_per_case:int,
    answer_bits_per_case:int,
)->ResourceVector:
    for name,value in {
        "case_count":case_count,
        "key_bits_per_case":key_bits_per_case,
        "answer_bits_per_case":answer_bits_per_case,
    }.items():
        if not isinstance(value,int) or isinstance(value,bool) or value<1:
            raise ResourceTradeoffError("LOOKUP_INVALID:"+name)
    return ResourceVector(
        learned_bits=0,
        deterministic_capability_bits=case_count*(key_bits_per_case+answer_bits_per_case),
        runtime_steps=max(1,case_count.bit_length()),
        external_information_bits=0,
        task_state_bits=0,
    )


def finite_lookup_capability_credit(*, hidden_cases_encoded:bool, scope_general_rule_proved:bool)->dict[str,Any]:
    if scope_general_rule_proved:
        status="GENERAL_RULE_EVIDENCE_MAY_BE_ADMISSIBLE"
        admissible=True
    elif hidden_cases_encoded:
        status="REJECT__HELDOUT_OR_CASE_MEMORIZATION"
        admissible=False
    else:
        status="INSUFFICIENT_FOR_GENERAL_CAPABILITY"
        admissible=False
    return {
        "status":status,
        "admissible_general_capability_evidence":admissible,
    }


def pareto_dominates(a:ResourceVector,b:ResourceVector)->bool:
    av=tuple(a.to_dict().values())
    bv=tuple(b.to_dict().values())
    return all(x<=y for x,y in zip(av,bv)) and any(x<y for x,y in zip(av,bv))


def learned_only_comparison_can_reverse(a:ResourceVector,b:ResourceVector)->dict[str,Any]:
    learned_pref="A" if a.learned_bits<b.learned_bits else ("B" if b.learned_bits<a.learned_bits else "TIE")
    a_dom=pareto_dominates(a,b)
    b_dom=pareto_dominates(b,a)
    return {
        "learned_only_preference":learned_pref,
        "a_pareto_dominates_b":a_dom,
        "b_pareto_dominates_a":b_dom,
        "resource_vectors":{"A":a.to_dict(),"B":b.to_dict()},
        "warning":"LEARNED_BITS_ALONE_DO_NOT_ORDER_TOTAL_CAPABILITY_COST_UNLESS_OTHER_RESOURCES_ARE_CONSTRAINED",
    }


def certificate()->dict[str,Any]:
    base=logical_learned_state_lower_bound(
        input_complete=True,
        total_computable=True,
        deterministic_program_allowed=True,
        deterministic_program_bits_count_as_learned=False,
    )
    return {
        "schema":SCHEMA,
        "status":"FORMAL_RESOURCE_TRADEOFF_CERTIFICATE",
        "logical_zero_bound":base,
        "resource_vector":["B_LEARNED_BITS","L_DETERMINISTIC_CAPABILITY_BITS","T_RUNTIME_STEPS","E_EXTERNAL_INFORMATION_BITS","S_TASK_STATE_BITS"],
        "deduction":[
            "FOR_INPUT_COMPLETE_TOTAL_COMPUTABLE_TASKS__ZERO_LEARNED_BITS_IS_LOGICALLY_POSSIBLE_WHEN_WORLD_INDEPENDENT_DETERMINISTIC_PROGRAM_STATE_IS_ALLOWED_AND_ACCOUNTED_SEPARATELY",
            "THIS_DOES_NOT_BOUND_DETERMINISTIC_PROGRAM_SIZE_OR_RUNTIME",
            "FINITE_LOOKUP_IS_A_ZERO_LEARNED_IMPLEMENTATION_BUT_NOT_GENERAL_CAPABILITY_EVIDENCE_IF_IT_ENCODES_HIDDEN_CASES",
            "POSITIVE_PRACTICAL_LEARNED_STATE_NECESSITY_REQUIRES_RESOURCE_BOUNDS_OR_MISSING_INFORMATION",
        ],
        "hard_nonclaims":[
            "NO_PRACTICAL_FRONTIER_EQUIVALENCE_CLAIM",
            "NO_SMALL_PROGRAM_CLAIM",
            "NO_FAST_RUNTIME_CLAIM",
            "NO_PERMISSION_TO_MEMORIZE_HELDOUT_CASES",
        ],
        "h100_terminal_credit_delta":0,
    }
