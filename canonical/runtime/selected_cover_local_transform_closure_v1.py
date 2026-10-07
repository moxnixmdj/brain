from typing import Mapping, Sequence, AbstractSet

class LocalClosureError(ValueError):
    pass

def certify_selected_cover(
    *,
    target_contexts: AbstractSet[str],
    context_to_route: Mapping[str,str],
    route_primitive_dominance: Mapping[str,bool],
    route_local_c_closure: Mapping[str,bool],
    route_transforms: Mapping[str,Sequence[str]],
    known_transforms: AbstractSet[str],
):
    U=set(map(str,target_contexts))
    known=set(map(str,known_transforms))
    used_routes=set()
    uncovered=[]
    bad_primitive=[]
    bad_c=[]
    unknown_transform=[]
    used_transforms=set()
    for c in sorted(U):
        rid=context_to_route.get(c)
        if not isinstance(rid,str) or not rid:
            uncovered.append(c); continue
        used_routes.add(rid)
        if route_primitive_dominance.get(rid) is not True:
            bad_primitive.append((c,rid))
        if route_local_c_closure.get(rid) is not True:
            bad_c.append((c,rid))
        for t in route_transforms.get(rid,()):
            ts=str(t); used_transforms.add(ts)
            if ts not in known:
                unknown_transform.append((c,rid,ts))
    errors=[]
    if uncovered: errors.append("UNCOVERED_TARGET_CONTEXT")
    if bad_primitive: errors.append("SELECTED_ROUTE_PRIMITIVE_DOMINANCE_OPEN")
    if bad_c: errors.append("SELECTED_ROUTE_LOCAL_C_OPEN")
    if unknown_transform: errors.append("SELECTED_ROUTE_UNKNOWN_TRANSFORM")
    return {
      "status":"PASS__SELECTED_COVER_LOCAL_ABC_CERTIFIED" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "uncovered_contexts":uncovered,
      "bad_primitive_routes":bad_primitive,
      "bad_local_c_routes":bad_c,
      "unknown_selected_transforms":unknown_transform,
      "used_routes":sorted(used_routes),
      "used_transforms":sorted(used_transforms),
      "unused_transforms":sorted(known-used_transforms),
      "global_all_transform_closure_required":False,
      "terminal_credit_delta":0,
    }
