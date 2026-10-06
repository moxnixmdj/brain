from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Hashable, Any

class DecisionQuotientError(ValueError):
    pass

def common_acceptable(actions_by_world: Mapping[Hashable, Sequence[Hashable]], worlds: Sequence[Hashable]) -> set[Hashable]:
    worlds=list(worlds)
    if not worlds:
        raise DecisionQuotientError("EMPTY_INFORMATION_CELL")
    sets=[]
    for w in worlds:
        if w not in actions_by_world:
            raise DecisionQuotientError("WORLD_MISSING:"+repr(w))
        sets.append(set(actions_by_world[w]))
    out=set(sets[0])
    for s in sets[1:]:
        out.intersection_update(s)
    return out

def cell_sufficient(actions_by_world: Mapping[Hashable, Sequence[Hashable]], worlds: Sequence[Hashable]) -> bool:
    return bool(common_acceptable(actions_by_world,worlds))

def choose_common_action(actions_by_world: Mapping[Hashable, Sequence[Hashable]], worlds: Sequence[Hashable]) -> Hashable:
    common=common_acceptable(actions_by_world,worlds)
    if not common:
        raise DecisionQuotientError("NO_COMMON_TARGET_ACCEPTABLE_ACTION")
    return sorted(common,key=repr)[0]

def partition_sufficient(actions_by_world: Mapping[Hashable, Sequence[Hashable]], cells: Sequence[Sequence[Hashable]]) -> bool:
    covered=[]
    for cell in cells:
        covered.extend(cell)
        if not cell_sufficient(actions_by_world,cell):
            return False
    return set(covered)==set(actions_by_world) and len(covered)==len(set(covered))

def canonical_safe_quotient(actions_by_world: Mapping[Hashable, Sequence[Hashable]]) -> list[list[Hashable]]:
    groups={}
    for w,acts in actions_by_world.items():
        key=tuple(sorted(set(acts),key=repr))
        groups.setdefault(key,[]).append(w)
    return [sorted(v,key=repr) for _,v in sorted(groups.items(),key=lambda kv:repr(kv[0]))]

def refinement_needed(actions_by_world: Mapping[Hashable, Sequence[Hashable]], worlds: Sequence[Hashable]) -> bool:
    return not cell_sufficient(actions_by_world,worlds)

def verify_finite_theorem() -> dict[str,Any]:
    # Same acceptable set => faithful world distinction unnecessary.
    same={"w0":{"a","b"},"w1":{"a","b"}}
    q=canonical_safe_quotient(same)
    assert q==[["w0","w1"]]
    assert choose_common_action(same,q[0]) in {"a","b"}

    # Different worlds can still be merged when they share at least one target-acceptable action.
    overlap={"w0":{"a","b"},"w1":{"b","c"}}
    assert cell_sufficient(overlap,["w0","w1"])
    assert choose_common_action(overlap,["w0","w1"])=="b"

    # Disjoint acceptable sets force a separator for deterministic universal target success.
    disjoint={"w0":{"a"},"w1":{"b"}}
    assert refinement_needed(disjoint,["w0","w1"])
    assert partition_sufficient(disjoint,[["w0"],["w1"]])

    # Abstention is not magic: it works only if acceptable in every remaining world.
    abstain_ok={"w0":{"wait","a"},"w1":{"wait","b"}}
    assert choose_common_action(abstain_ok,["w0","w1"])=="wait"
    abstain_bad={"w0":{"wait","a"},"w1":{"b"}}
    assert refinement_needed(abstain_bad,["w0","w1"])

    return {
      "same_signature_worlds_merge_without_loss":True,
      "overlapping_acceptable_sets_can_merge_without_full_model":True,
      "disjoint_acceptable_sets_require_refinement":True,
      "abstention_is_ordinary_action_not_separator":True,
      "faithful_world_model_is_not_generically_necessary":True,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    import json
    print(json.dumps(verify_finite_theorem(),sort_keys=True))
