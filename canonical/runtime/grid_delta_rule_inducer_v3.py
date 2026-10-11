"""Grid delta rule inducer V3 with representation-invention fallback.

V3 first reuses V2's cheaper adaptive equality-atom synthesis. Only when V2
cannot produce a verified rule does it escalate to the generic finite feature-
expression inventor, which can synthesize relations between structural features
such as equality, ordering, differences, sums, and observed thresholds.

Every invented selector is exact-replayed against every training cell. On a new
input, equal-minimum alternatives must agree on the selected cells or V3
abstains.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping, Sequence

from canonical.runtime import grid_delta_rule_inducer_v2 as v2
from canonical.runtime.finite_feature_expression_inventor_v1 import (
    LabeledRow,
    evaluate as evaluate_discriminator,
    invent as invent_discriminator,
)

SCHEMA="PROJECT_BRAIN_GRID_DELTA_RULE_INDUCER_V3"


def _parse_pairs(training_pairs:Sequence[Mapping[str,Sequence[Sequence[int]]]]):
    pairs=[]
    if not isinstance(training_pairs,Sequence) or isinstance(training_pairs,(str,bytes)) or not training_pairs:
        return None,{"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"TRAINING_PAIRS_INVALID"}
    try:
        for i,raw in enumerate(training_pairs):
            inp=v2._grid(raw["input"],f"pair_{i}_input")
            out=v2._grid(raw["output"],f"pair_{i}_output")
            if v2._shape(inp)!=v2._shape(out):
                return None,{"schema":SCHEMA,"status":"UNSUPPORTED","reason":"SHAPE_CHANGE"}
            pairs.append((inp,out))
    except Exception as exc:
        return None,{"schema":SCHEMA,"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc)}
    return pairs,None


def _features_for_grid(grid):
    contexts=v2._contexts(grid)
    return {pos:{k:int(val) for k,val in asdict(ctx).items()} for pos,ctx in contexts.items()}


def _target_rows(pairs,target:int):
    rows=[]
    for pi,(inp,out) in enumerate(pairs):
        features=_features_for_grid(inp)
        for (r,c),vals in features.items():
            positive=inp[r][c]!=out[r][c] and out[r][c]==target
            rows.append(LabeledRow(f"t{target}_p{pi}_r{r}_c{c}",vals,positive))
    return rows


def _selected_positions(grid,discriminator):
    features=_features_for_grid(grid)
    return frozenset(
        pos for pos,vals in features.items()
        if evaluate_discriminator(discriminator,vals)
    )


def _invented_predict(grid,target_options):
    selections={}
    for group in target_options:
        target=int(group["target_color"])
        position_sets={_selected_positions(grid,d) for d in group["discriminators"]}
        if len(position_sets)!=1:
            return "AMBIGUOUS_PREDICTION",None
        selections[target]=next(iter(position_sets))

    occupied={}
    for target,positions in selections.items():
        for pos in positions:
            if pos in occupied and occupied[pos]!=target:
                return "UNDEFINED_CONFLICT",None
            occupied[pos]=target

    out=[list(row) for row in grid]
    for (r,c),target in occupied.items():
        out[r][c]=target
    return "PREDICTED",tuple(tuple(row) for row in out)


def induce(training_pairs:Sequence[Mapping[str,Sequence[Sequence[int]]]])->dict[str,Any]:
    baseline=v2.induce(training_pairs)
    if baseline.get("status")=="VERIFIED_FACTORIZED_RULE_OPTIONS":
        return {
            "schema":SCHEMA,
            "status":"VERIFIED_RULE_OPTIONS",
            "route":"V2_BASE_ATTRIBUTE_SYNTHESIS",
            "baseline":baseline,
            "training_full_replay_verified":baseline.get("training_full_replay_verified") is True,
            "representation_invention_used":False,
            "terminal_authority":False,
            "promotion_authority":False,
        }
    if baseline.get("status")=="UNSUPPORTED":
        return {
            "schema":SCHEMA,
            "status":"UNSUPPORTED",
            "reason":baseline.get("reason"),
            "representation_invention_used":False,
            "terminal_authority":False,
        }

    pairs,error=_parse_pairs(training_pairs)
    if error is not None:
        return error
    assert pairs is not None

    targets=sorted({
        out[r][c]
        for inp,out in pairs
        for r in range(len(inp))
        for c in range(len(inp[0]))
        if inp[r][c]!=out[r][c]
    })
    if not targets:
        return {"schema":SCHEMA,"status":"UNSUPPORTED","reason":"NO_CHANGE","terminal_authority":False}

    target_options=[]
    for target in targets:
        invented=invent_discriminator(_target_rows(pairs,target))
        if invented.get("status")!="INVENTED_DISCRIMINATORS":
            return {
                "schema":SCHEMA,
                "status":"REPRESENTATION_INVENTION_FAILED",
                "failed_target_color":target,
                "inventor_status":invented.get("status"),
                "inventor_reason":invented.get("reason"),
                "baseline_status":baseline.get("status"),
                "representation_invention_used":True,
                "terminal_authority":False,
            }
        target_options.append({
            "target_color":target,
            "minimum_cost":invented["minimum_cost"],
            "discriminators":invented["discriminators"],
            "discriminator_count":invented["discriminator_count"],
            "grammar_scope":invented["grammar_scope"],
        })

    for inp,out in pairs:
        status,predicted=_invented_predict(inp,target_options)
        if status!="PREDICTED" or predicted!=out:
            return {
                "schema":SCHEMA,
                "status":"INTERNAL_TRAINING_REPLAY_FAILURE",
                "reason":status,
                "representation_invention_used":True,
                "terminal_authority":False,
            }

    return {
        "schema":SCHEMA,
        "status":"VERIFIED_RULE_OPTIONS",
        "route":"V3_DERIVED_FEATURE_EXPRESSION_INVENTION",
        "changed_target_colors":targets,
        "target_options":target_options,
        "training_full_replay_verified":True,
        "representation_invention_used":True,
        "inventor":"PROJECT_BRAIN_FINITE_FEATURE_EXPRESSION_INVENTOR_V1",
        "open_world_representation_invention_claimed":False,
        "terminal_authority":False,
        "promotion_authority":False,
    }


def predict(result:Mapping[str,Any],grid:Sequence[Sequence[int]])->dict[str,Any]:
    route=result.get("route")
    if route=="V2_BASE_ATTRIBUTE_SYNTHESIS":
        out=v2.predict(result["baseline"],grid)
        return {
            "schema":SCHEMA,
            "status":out.get("status"),
            "prediction":out.get("prediction"),
            "route":route,
            "terminal_authority":False,
        }
    if route!="V3_DERIVED_FEATURE_EXPRESSION_INVENTION":
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"UNKNOWN_OR_MISSING_ROUTE"}
    try:
        g=v2._grid(grid,"grid")
        status,out=_invented_predict(g,result["target_options"])
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc)}
    if status!="PREDICTED" or out is None:
        return {"schema":SCHEMA,"status":status,"prediction":None,"route":route}
    return {
        "schema":SCHEMA,
        "status":"PREDICTED",
        "prediction":[list(row) for row in out],
        "route":route,
        "terminal_authority":False,
    }
