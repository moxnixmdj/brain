from collections import defaultdict
from fractions import Fraction
from typing import Any, Mapping, Sequence

class DecisionDiscriminatorError(ValueError):
    pass

def _f(x:Any,name:str)->Fraction:
    if isinstance(x,bool):
        raise DecisionDiscriminatorError(name.upper()+"_INVALID")
    try:
        return x if isinstance(x,Fraction) else Fraction(str(x))
    except Exception as exc:
        raise DecisionDiscriminatorError(name.upper()+"_INVALID") from exc

def live(hypotheses:Sequence[Mapping[str,Any]]):
    hs=[];ps={};seen=set()
    for raw in hypotheses:
        hid=str(raw.get("id") or "").strip()
        if not hid or hid in seen:
            raise DecisionDiscriminatorError("HYPOTHESIS_ID_INVALID_OR_DUPLICATE")
        seen.add(hid)
        if raw.get("plausible") is not True:
            continue
        act=str(raw.get("best_action") or "").strip()
        if not act:
            raise DecisionDiscriminatorError("LIVE_HYPOTHESIS_ACTION_REQUIRED")
        p=_f(raw.get("probability",0),"probability")
        if p<0:
            raise DecisionDiscriminatorError("NEGATIVE_PROBABILITY")
        if p==0:
            continue
        hs.append({"id":hid,"best_action":act})
        ps[hid]=p
    if not hs:
        return [],{}
    total=sum(ps.values(),Fraction(0))
    return hs,{h:p/total for h,p in ps.items()}

def ambiguity(hs,ps):
    mass=defaultdict(Fraction)
    by={h["id"]:h for h in hs}
    for hid,p in ps.items():
        mass[by[hid]["best_action"]]+=p
    return Fraction(1)-max(mass.values()) if mass else Fraction(1)

def sufficient(hypotheses):
    hs,ps=live(hypotheses)
    if not hs:
        return {"sufficient":False,"action":None,"reason":"NO_LIVE_POSITIVE_MASS_HYPOTHESES"}
    acts={h["best_action"] for h in hs}
    if len(acts)==1:
        return {"sufficient":True,"action":next(iter(acts)),"reason":"ALL_LIVE_POSITIVE_MASS_HYPOTHESES_AGREE","ambiguity":"0"}
    return {"sufficient":False,"action":None,"reason":"LIVE_HYPOTHESES_DISAGREE","ambiguity":str(ambiguity(hs,ps))}

def rank(*,hypotheses,actions,transfer_weight="1/2",proof_weight="1/2"):
    hs,ps=live(hypotheses)
    if not hs:
        return []
    before=ambiguity(hs,ps)
    if before==0:
        return []
    ids={h["id"] for h in hs}
    by={h["id"]:h for h in hs}
    tw=_f(transfer_weight,"transfer_weight")
    pw=_f(proof_weight,"proof_weight")
    if tw<0 or pw<0:
        raise DecisionDiscriminatorError("NEGATIVE_WEIGHT")
    ranked=[];seen=set()
    for raw in actions:
        aid=str(raw.get("id") or "").strip()
        if not aid or aid in seen:
            raise DecisionDiscriminatorError("ACTION_ID_INVALID_OR_DUPLICATE")
        seen.add(aid)
        if raw.get("safe") is not True:
            continue
        outcomes=raw.get("outcome_by_hypothesis")
        if not isinstance(outcomes,Mapping) or ids-set(map(str,outcomes.keys())):
            raise DecisionDiscriminatorError("ACTION_OUTCOME_MAP_INCOMPLETE:"+aid)
        groups=defaultdict(dict)
        for hid,p in ps.items():
            groups[str(outcomes[hid])][hid]=p
        expected=Fraction(0)
        for group in groups.values():
            mass=sum(group.values(),Fraction(0))
            action_mass=defaultdict(Fraction)
            for hid,p in group.items():
                action_mass[by[hid]["best_action"]]+=p/mass
            expected+=mass*(Fraction(1)-max(action_mass.values()))
        gain=before-expected
        tr=_f(raw.get("transfer_gain",0),"transfer_gain")
        pr=_f(raw.get("proof_gain",0),"proof_gain")
        t=_f(raw.get("time",0),"time")
        c=_f(raw.get("cost",0),"cost")
        r=_f(raw.get("risk",0),"risk")
        if min(tr,pr,t,c,r)<0:
            raise DecisionDiscriminatorError("NEGATIVE_ACTION_DIMENSION:"+aid)
        den=t+c+r
        if den<=0:
            raise DecisionDiscriminatorError("ACTION_TOTAL_COST_MUST_BE_POSITIVE:"+aid)
        if gain>0:
            score=(gain+tw*tr+pw*pr)/den
            ranked.append({
                "id":aid,
                "conditional_decision_gain":str(gain),
                "expected_post_probe_ambiguity":str(expected),
                "gain_basis":"EXACT_CONDITIONAL_ON_DECLARED_HYPOTHESES_PROBABILITIES_TERMINAL_ACTIONS_AND_PREDICTED_OUTCOMES",
                "value_density":str(score),
                "_gain":gain,
                "_score":score,
            })
    ranked.sort(key=lambda x:(-x["_score"],-x["_gain"],x["id"]))
    for x in ranked:
        x.pop("_gain")
        x.pop("_score")
    return ranked
