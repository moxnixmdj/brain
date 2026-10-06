from __future__ import annotations

class AccountingError(ValueError): pass

def account(*, learned_target_bytes:int, deterministic_target_bytes:int, generic_frozen_code_bytes:int=0, task_state_bytes:int=0, external_knowledge_bytes_accessed:int=0):
    vals=[learned_target_bytes,deterministic_target_bytes,generic_frozen_code_bytes,task_state_bytes,external_knowledge_bytes_accessed]
    if any((not isinstance(x,int)) or isinstance(x,bool) or x<0 for x in vals):
        raise AccountingError("NONNEGATIVE_INTEGER_BYTES_REQUIRED")
    return {
        "target_adapted_capability_bytes":learned_target_bytes+deterministic_target_bytes,
        "learned_target_bytes":learned_target_bytes,
        "deterministic_target_bytes":deterministic_target_bytes,
        "generic_frozen_code_bytes":generic_frozen_code_bytes,
        "task_state_bytes":task_state_bytes,
        "external_knowledge_bytes_accessed":external_knowledge_bytes_accessed,
    }

def relabel_invariant(total_target_bytes:int, learned_before:int, learned_after:int):
    if min(total_target_bytes,learned_before,learned_after)<0 or learned_before>total_target_bytes or learned_after>total_target_bytes:
        raise AccountingError("INVALID_RELABEL")
    before=account(learned_target_bytes=learned_before,deterministic_target_bytes=total_target_bytes-learned_before)
    after=account(learned_target_bytes=learned_after,deterministic_target_bytes=total_target_bytes-learned_after)
    return {
        "before":before,
        "after":after,
        "target_adapted_bytes_invariant":before["target_adapted_capability_bytes"]==after["target_adapted_capability_bytes"],
    }
