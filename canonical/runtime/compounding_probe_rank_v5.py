"""Minimax-first compounding probe ranking for Universal Learning V5."""
from __future__ import annotations
from fractions import Fraction
from typing import Any, Mapping, Sequence

from canonical.runtime import open_world_hypothesis_guard_v4 as guard4

SCHEMA="PROJECT_BRAIN_COMPOUNDING_PROBE_RANK_V5"

class CompoundingProbeRankError(ValueError):
    pass

def _f(value:Any,name:str)->Fraction:
    if isinstance(value,bool):
        raise CompoundingProbeRankError(name.upper()+"_INVALID")
    try:
        out=value if isinstance(value,Fraction) else Fraction(str(value))
    except Exception as exc:
        raise CompoundingProbeRankError(name.upper()+"_INVALID") from exc
    if out<0:
        raise CompoundingProbeRankError(name.upper()+"_NEGATIVE")
    return out

def rank(*,environment_id:str,goal_id:str,hypotheses:Sequence[Mapping[str,Any]],actions:Sequence[Mapping[str,Any]])->dict[str,Any]:
    base=guard4.robust_rank(environment_id=environment_id,goal_id=goal_id,hypotheses=hypotheses,actions=actions)
    raw_by_id={str(x.get("id") or "").strip():x for x in actions}
    enriched=[];rejected=list(base.get("rejected",[]))
    for row in base.get("ranked",[]):
        aid=row["id"];raw=raw_by_id[aid]
        try:
            spend=_f(raw.get("incremental_spend_usd_ub",0),"incremental_spend_usd_ub")
            if spend>0:
                rejected.append({"id":aid,"reason":"POSITIVE_INCREMENTAL_SPEND_FORBIDDEN"})
                continue
            transfer=_f(raw.get("future_transfer_lcb",0),"future_transfer_lcb")
            proof=_f(raw.get("proof_value_lcb",0),"proof_value_lcb")
            burden=_f(raw.get("future_burden_ub",0),"future_burden_ub")
            density=(transfer+proof)/(Fraction(1,1)+burden)
        except CompoundingProbeRankError as exc:
            rejected.append({"id":aid,"reason":str(exc)})
            continue
        item=dict(row)
        item["future_transfer_lcb"]=str(transfer)
        item["proof_value_lcb"]=str(proof)
        item["future_burden_ub"]=str(burden)
        item["secondary_compounding_density"]=str(density)
        item["_secondary"]=density
        enriched.append(item)

    enriched.sort(key=lambda x:(
        -int(x["minimax_action_class_reduction"]),
        -x["_secondary"],
        int(x["worst_case_remaining_action_classes"]),
        x["id"],
    ))
    for row in enriched:
        row.pop("_secondary",None)
    return {
        "schema":SCHEMA,
        "ranked":enriched,
        "rejected":rejected,
        "ranking_order":[
            "MINIMAX_ACTION_CLASS_REDUCTION_DESC",
            "SECONDARY_COMPOUNDING_DENSITY_DESC",
            "WORST_CASE_REMAINING_ACTION_CLASSES_ASC",
            "ACTION_ID_ASC",
        ],
        "v4_open_world_safety_preserved":True,
        "hard_zero_incremental_spend":True,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
    }
