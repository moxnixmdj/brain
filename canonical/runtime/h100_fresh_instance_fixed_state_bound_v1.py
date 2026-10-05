"""Fresh-instance fixed-state information bound.

Persistent learned parameters are normally fixed before a fresh benchmark/task
instance is sampled. If two possible fresh worlds produce the same runtime
evidence, a fixed persistent state cannot contain which of those fresh worlds
was sampled.

For each runtime-evidence class, any deterministic decision f(S, O) is constant
because both S and O are constant across worlds in that class. Therefore exact
task accuracy is at most the majority required-label fraction in that class,
regardless of how many bits S contains.

Randomization independent of the fresh world also cannot improve expected
accuracy beyond the majority fraction: expected correctness is a convex
combination of label frequencies.

This is an information theorem, not a compute-time theorem. Fixed learned state
can still encode algorithms, priors, reusable structure, or stable world
knowledge shared across instances.
"""
from __future__ import annotations

from collections import Counter
from typing import Hashable, Iterable, Sequence

SCHEMA="PROJECT_BRAIN_H100_FRESH_INSTANCE_FIXED_STATE_BOUND_V1"

class FreshInstanceBoundError(ValueError):
    pass


def _classes(classes: Iterable[Sequence[Hashable]]) -> tuple[tuple[Hashable,...],...]:
    out=[]
    for cls in classes:
        if isinstance(cls,(str,bytes)) or not isinstance(cls,Sequence) or len(cls)<1:
            raise FreshInstanceBoundError("CLASS_INVALID")
        vals=tuple(cls)
        for value in vals:
            try:
                hash(value)
            except Exception as exc:
                raise FreshInstanceBoundError("LABEL_UNHASHABLE") from exc
        out.append(vals)
    if not out:
        raise FreshInstanceBoundError("CLASSES_EMPTY")
    return tuple(out)


def deterministic_fixed_state_success_upper_bound(
    classes: Iterable[Sequence[Hashable]],
    fixed_state_bits: int | None = None,
) -> float:
    """Majority-label bound; fixed_state_bits is validated but irrelevant."""
    cs=_classes(classes)
    if fixed_state_bits is not None:
        if not isinstance(fixed_state_bits,int) or isinstance(fixed_state_bits,bool) or fixed_state_bits<0:
            raise FreshInstanceBoundError("BITS_INVALID")
    correct=0
    total=0
    for cls in cs:
        counts=Counter(cls)
        correct+=max(counts.values())
        total+=len(cls)
    return correct/total


def randomized_fixed_state_success_upper_bound(
    classes: Iterable[Sequence[Hashable]],
    fixed_state_bits: int | None = None,
) -> float:
    """Independent randomization cannot beat majority expected accuracy."""
    return deterministic_fixed_state_success_upper_bound(classes,fixed_state_bits)


def state_size_sweep(
    classes: Iterable[Sequence[Hashable]],
    bit_counts: Sequence[int],
) -> dict:
    cs=_classes(classes)
    if isinstance(bit_counts,(str,bytes)) or not isinstance(bit_counts,Sequence) or not bit_counts:
        raise FreshInstanceBoundError("BIT_COUNTS_INVALID")
    rows=[]
    for bits in bit_counts:
        rows.append({
            "fixed_state_bits":bits,
            "deterministic_upper_bound":deterministic_fixed_state_success_upper_bound(cs,bits),
            "randomized_upper_bound":randomized_fixed_state_success_upper_bound(cs,bits),
        })
    values={row["deterministic_upper_bound"] for row in rows}
    return {
        "schema":SCHEMA,
        "rows":rows,
        "state_size_changes_information_bound":len(values)>1,
    }


def fresh_instance_certificate(classes: Iterable[Sequence[Hashable]]) -> dict:
    cs=_classes(classes)
    bound=deterministic_fixed_state_success_upper_bound(cs,0)
    return {
        "schema":SCHEMA,
        "status":"FORMAL_FRESH_INSTANCE_FIXED_STATE_BOUND",
        "evidence_classes":[list(x) for x in cs],
        "fixed_state_information_upper_bound":bound,
        "fixed_state_size_affects_bound":False,
        "deduction":[
            "FIXED_PREINSTANCE_STATE_CANNOT_ENCODE_WHICH_FRESH_WORLD_WAS_SAMPLED",
            "INSTANCE_SPECIFIC_MISSING_INFORMATION_MUST_ENTER_THROUGH_RUNTIME_EVIDENCE_INTERACTION_OR_WORLD_DEPENDENT_ONLINE_STATE",
            "MORE_FIXED_LEARNED_BITS_CAN_CHANGE_COMPUTATION_OR_PRIORS_BUT_NOT_THIS_INFORMATION_BOUND",
        ],
        "hard_nonclaims":[
            "DOES_NOT_BOUND_COMPUTATIONAL_SPEEDUP_FROM_FIXED_LEARNED_STATE",
            "DOES_NOT_ADDRESS_STABLE_WORLD_KNOWLEDGE_SHARED_ACROSS_INSTANCES",
            "DOES_NOT_ADDRESS_ONLINE_ADAPTATION_THAT_WRITES_WORLD_DEPENDENT_STATE",
            "DOES_NOT_PROVE_ZERO_LEARNED_STATE_IS UNIVERSALLY SUFFICIENT",
        ],
        "h100_terminal_credit_delta":0,
    }
