"""Task-label information lower bound under runtime evidence.

Hidden worlds need not be identified if they require the same task output.
For each runtime-evidence equivalence class, let label multiplicities be the
counts of worlds requiring each distinct output label. With B bits of
world-dependent persistent state, at most M=2^B state values can be selected.
Each state value can support one output label inside an evidence class.

Therefore the maximum average exact-task success under a uniform world prior is

    (1/N) * sum_j sum(top_M label multiplicities in class j).

For B=0 this is majority-label accuracy within each evidence class.
Perfect task success requires enough state values to cover the maximum number
of distinct required labels in any evidence class, yielding the counting lower
bound ceil(log2(max_j distinct_labels_j)).

This is an information bound only. It says nothing about how much computation
is required to decode available runtime evidence.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Hashable, Iterable, Sequence

SCHEMA="PROJECT_BRAIN_H100_TASK_LABEL_INFORMATION_BOUND_V1"

class TaskLabelInformationBoundError(ValueError):
    pass

def _classes(classes: Iterable[Sequence[Hashable]]) -> tuple[tuple[Hashable,...],...]:
    out=[]
    for cls in classes:
        if isinstance(cls,(str,bytes)) or not isinstance(cls,Sequence) or len(cls)<1:
            raise TaskLabelInformationBoundError("CLASS_INVALID")
        vals=tuple(cls)
        for x in vals:
            try:
                hash(x)
            except Exception as exc:
                raise TaskLabelInformationBoundError("LABEL_UNHASHABLE") from exc
        out.append(vals)
    if not out:
        raise TaskLabelInformationBoundError("CLASSES_EMPTY")
    return tuple(out)

def class_success_count_upper_bound(labels: Sequence[Hashable], learned_bits: int) -> int:
    if isinstance(labels,(str,bytes)) or not isinstance(labels,Sequence) or len(labels)<1:
        raise TaskLabelInformationBoundError("LABELS_INVALID")
    if not isinstance(learned_bits,int) or isinstance(learned_bits,bool) or learned_bits<0:
        raise TaskLabelInformationBoundError("BITS_INVALID")
    counts=sorted(Counter(labels).values(),reverse=True)
    m=1<<learned_bits
    return sum(counts[:m])

def average_success_upper_bound(classes: Iterable[Sequence[Hashable]], learned_bits: int) -> float:
    cs=_classes(classes)
    n=sum(len(x) for x in cs)
    return sum(class_success_count_upper_bound(x,learned_bits) for x in cs)/n

def zero_bit_upper_bound(classes: Iterable[Sequence[Hashable]]) -> float:
    return average_success_upper_bound(classes,0)

def minimum_bits_for_perfect_task_success(classes: Iterable[Sequence[Hashable]]) -> int:
    cs=_classes(classes)
    max_labels=max(len(set(x)) for x in cs)
    return 0 if max_labels<=1 else int(math.ceil(math.log2(max_labels)))

def minimum_bits_for_target(classes: Iterable[Sequence[Hashable]], target_success: float) -> int:
    cs=_classes(classes)
    try:
        t=float(target_success)
    except Exception as exc:
        raise TaskLabelInformationBoundError("TARGET_INVALID") from exc
    if not math.isfinite(t) or not (0.0<t<=1.0):
        raise TaskLabelInformationBoundError("TARGET_OUT_OF_RANGE")
    b=0
    while average_success_upper_bound(cs,b)+1e-15<t:
        b+=1
    return b

def ambiguity_stats(classes: Iterable[Sequence[Hashable]]) -> dict:
    cs=_classes(classes)
    n=sum(len(x) for x in cs)
    distinct=[len(set(x)) for x in cs]
    return {
        "world_count":n,
        "evidence_class_count":len(cs),
        "largest_evidence_class":max(len(x) for x in cs),
        "maximum_distinct_required_labels_within_class":max(distinct),
        "zero_bit_success_upper_bound":zero_bit_upper_bound(cs),
        "bits_for_perfect_task_success":minimum_bits_for_perfect_task_success(cs),
    }

def certificate(classes: Iterable[Sequence[Hashable]], learned_bits:int, target_success:float)->dict:
    cs=_classes(classes)
    upper=average_success_upper_bound(cs,learned_bits)
    return {
        "schema":SCHEMA,
        "status":"FORMAL_TASK_LABEL_INFORMATION_BOUND",
        "classes":[list(x) for x in cs],
        "learned_bits":learned_bits,
        "success_upper_bound":upper,
        "target_success":float(target_success),
        "minimum_bits_for_target":minimum_bits_for_target(cs,target_success),
        "target_ruled_out_by_current_bits":upper<float(target_success),
        "ambiguity":ambiguity_stats(cs),
        "deduction":[
            "ONLY_DISTINCT_REQUIRED_OUTPUTS_WITHIN_THE_SAME_RUNTIME_EVIDENCE_CLASS_REQUIRE_WORLD_DEPENDENT_STATE_FOR_INFORMATION_THEORETIC_DISAMBIGUATION",
            "LATENT_WORLD_DIFFERENCES_THAT_SHARE_THE_SAME_REQUIRED_OUTPUT_DO_NOT_CREATE_A_TASK_RELEVANT_STATE_LOWER_BOUND",
            "THIS_BOUND_DOES_NOT_ADDRESS_COMPUTATIONAL_COST_OF_DECODING_RUNTIME_EVIDENCE",
        ],
        "h100_terminal_credit_delta":0,
    }
