"""Fail-closed proof transmutation compiler for Project Brain Opus 5.5 acceptance.

Scheduling/proof-routing authority only. Never grants capability or family credit.
A stronger proof may satisfy an unchanged frozen protocol only when the witness is
verified, independent, contamination-clean, binds the frozen protocol, and covers
the entire protocol scope. Behavioral-only evidence can never close ownership.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Mapping

PASS="PASS"
OPEN="DEFINED_RESULT_OPEN"
PROOF_PRIORITY=("UNIVERSAL","EXHAUSTIVE_FINITE","ABSOLUTE_DOMINANCE","PUBLIC_FIXED_BAR","MATCHED_COMPARATOR")

def _base(e: Mapping[str, Any]) -> tuple[bool,list[str]]:
    failures=[]
    for key,msg in (
        ("verified","NOT_VERIFIED"),
        ("independent","NOT_INDEPENDENT"),
        ("contamination_clean","CONTAMINATION_NOT_CLEAN"),
        ("binds_frozen_protocol","DOES_NOT_BIND_FROZEN_PROTOCOL"),
        ("closes_entire_protocol","DOES_NOT_CLOSE_ENTIRE_PROTOCOL"),
    ):
        if e.get(key) is not True: failures.append(msg)
    if e.get("scope_relation") not in {"EXACT","PROVEN_STRONGER"}:
        failures.append("SCOPE_NOT_EXACT_OR_PROVEN_STRONGER")
    return (not failures,failures)

def _num(v: Any) -> float|None:
    if isinstance(v,bool) or not isinstance(v,(int,float)): return None
    return float(v)

def _absolute(r: Mapping[str,Any]) -> tuple[bool,str]:
    direction=r.get("direction")
    if direction=="higher":
        b=_num(r.get("brain_lower_bound"))
        t=_num(r.get("theoretical_upper_bound"))
        u=_num(r.get("target_upper_bound"))
        if b is None: return False,"BRAIN_LOWER_BOUND_MISSING"
        if t is not None and b>=t: return True,"THEORETICAL_CEILING_DOMINANCE"
        if u is not None and b>=u: return True,"TARGET_UPPER_BOUND_SQUEEZE"
        return False,"NO_HIGHER_IS_BETTER_DOMINANCE"
    if direction=="lower":
        b=_num(r.get("brain_upper_bound"))
        t=_num(r.get("theoretical_lower_bound"))
        l=_num(r.get("target_lower_bound"))
        if b is None: return False,"BRAIN_UPPER_BOUND_MISSING"
        if t is not None and b<=t: return True,"THEORETICAL_FLOOR_DOMINANCE"
        if l is not None and b<=l: return True,"TARGET_LOWER_BOUND_SQUEEZE"
        return False,"NO_LOWER_IS_BETTER_DOMINANCE"
    return False,"DIRECTION_INVALID"

def _absolute_scope_complete(e: Mapping[str,Any]) -> tuple[bool,str]:
    """Require a proof that the bound applies to the entire frozen protocol scope.

    A perfect score on a finite sampled population is an empirical result, not a
    protocol-wide mathematical lower/upper bound.  ABSOLUTE_DOMINANCE therefore
    needs an independently verified completeness certificate in addition to the
    numerical ceiling/floor relation.
    """
    s=e.get("scope_completeness")
    if not isinstance(s,Mapping):
        return False,"ABSOLUTE_SCOPE_COMPLETENESS_MISSING"
    if s.get("verified") is not True:
        return False,"ABSOLUTE_SCOPE_COMPLETENESS_NOT_VERIFIED"
    if s.get("independent") is not True:
        return False,"ABSOLUTE_SCOPE_COMPLETENESS_NOT_INDEPENDENT"

    exact=(
        s.get("basis")=="EXACT_COMPLETE_TARGET_CASE_UNIVERSE"
        and s.get("complete_target_case_set") is True
    )
    exhaustive=(
        s.get("basis")=="EXHAUSTIVE_FINITE_SUPERSET"
        and s.get("exhaustive") is True
        and s.get("target_subset_proved") is True
    )
    universal=(
        s.get("basis")=="UNIVERSAL_FORMAL_SCOPE_PROOF"
        and s.get("all_admissible_target_inputs_proved") is True
        and s.get("formal_completeness") is True
    )
    if not (exact or exhaustive or universal):
        return False,"ABSOLUTE_SCOPE_COMPLETENESS_BASIS_INVALID"
    receipt=s.get("receipt")
    if not isinstance(receipt,str) or not receipt:
        return False,"ABSOLUTE_SCOPE_COMPLETENESS_RECEIPT_MISSING"
    return True,str(s.get("basis"))

def _mode_pass(e: Mapping[str,Any]) -> tuple[bool,str]:
    mode=e.get("mode")
    r=e.get("result")
    if not isinstance(r,Mapping): return False,"RESULT_MISSING"
    if mode=="BEHAVIORAL_ONLY":
        return False,"BEHAVIORAL_ONLY_NEVER_CLOSES_OPUS55_ACCEPTANCE"
    if mode=="UNIVERSAL":
        ok=r.get("all_admissible_inputs_proved") is True and r.get("formal_completeness") is True
        return ok,"UNIVERSAL_COMPLETE" if ok else "UNIVERSAL_INCOMPLETE"
    if mode=="EXHAUSTIVE_FINITE":
        ok=r.get("exhaustive") is True and r.get("all_cases_pass") is True
        return ok,"EXHAUSTIVE_FINITE_COMPLETE" if ok else "EXHAUSTIVE_FINITE_INCOMPLETE"
    if mode=="ABSOLUTE_DOMINANCE":
        scope_ok,scope_reason=_absolute_scope_complete(e)
        if not scope_ok:
            return False,scope_reason
        ok,reason=_absolute(r)
        return ok,reason if ok else reason
    if mode=="PUBLIC_FIXED_BAR":
        ok=r.get("threshold_pass") is True
        return ok,"PUBLIC_FIXED_BAR_PASS" if ok else "PUBLIC_FIXED_BAR_NOT_PASS"
    if mode=="MATCHED_COMPARATOR":
        ok=r.get("noninferiority_pass") is True
        return ok,"MATCHED_NONINFERIORITY_PASS" if ok else "MATCHED_NONINFERIORITY_NOT_PASS"
    return False,"UNKNOWN_PROOF_MODE"

def _candidates(p: Mapping[str,Any]) -> list[str]:
    out=["UNIVERSAL","EXHAUSTIVE_FINITE","ABSOLUTE_DOMINANCE"]
    mode=str(p.get("proof_mode") or "")
    if "PUBLIC" in mode or "BAR" in mode: out.append("PUBLIC_FIXED_BAR")
    if "MATCHED" in mode or "NONINFERIORITY" in mode or "OSWORLD" in mode: out.append("MATCHED_COMPARATOR")
    return out

def evaluate(protocols_doc: Mapping[str,Any], evidence_doc: Mapping[str,Any]|None=None) -> dict[str,Any]:
    rows=protocols_doc.get("protocols")
    if not isinstance(rows,list):
        return {"schema":"PROJECT_BRAIN_ACCEPTANCE_PROOF_TRANSMUTATION_VERDICT_V1","status":"FAIL_CLOSED","errors":["PROTOCOLS_NOT_LIST"],"families":[],"closed_family_count":0,"open_family_count":0,"capability_credit_delta":0,"family_credit_delta":0}
    evidence=[]
    if evidence_doc is not None:
        raw=evidence_doc.get("evidence")
        if raw is not None and not isinstance(raw,list):
            return {"schema":"PROJECT_BRAIN_ACCEPTANCE_PROOF_TRANSMUTATION_VERDICT_V1","status":"FAIL_CLOSED","errors":["EVIDENCE_NOT_LIST"],"families":[],"closed_family_count":0,"open_family_count":0,"capability_credit_delta":0,"family_credit_delta":0}
        evidence=raw or []
    by_family={}
    for e in evidence:
        if isinstance(e,Mapping) and isinstance(e.get("family"),str):
            by_family.setdefault(e["family"],[]).append(e)
    out=[]; errors=[]; seen=set()
    for p in rows:
        if not isinstance(p,Mapping) or not isinstance(p.get("family"),str):
            errors.append("MALFORMED_PROTOCOL_ROW"); continue
        family=p["family"]
        if family in seen:
            errors.append(f"DUPLICATE_PROTOCOL_FAMILY:{family}"); continue
        seen.add(family)
        if p.get("status")==PASS:
            out.append({"family":family,"input_status":PASS,"result_status":PASS,"closure_mode":"ALREADY_PASS","witness_id":None,"candidate_transmutations":[],"rejections":[]})
            continue
        witnesses=[]; rejects=[]
        for e in by_family.get(family,[]):
            ok,why=_base(e)
            if not ok:
                rejects.append({"evidence_id":e.get("id"),"mode":e.get("mode"),"reasons":why}); continue
            ok,reason=_mode_pass(e)
            if not ok:
                rejects.append({"evidence_id":e.get("id"),"mode":e.get("mode"),"reasons":[reason]}); continue
            mode=str(e.get("mode"))
            rank=PROOF_PRIORITY.index(mode) if mode in PROOF_PRIORITY else len(PROOF_PRIORITY)
            witnesses.append({"evidence_id":e.get("id"),"mode":mode,"reason":reason,"rank":rank})
        witnesses.sort(key=lambda x:(x["rank"],str(x["evidence_id"])))
        if witnesses:
            w=witnesses[0]
            out.append({"family":family,"input_status":p.get("status"),"result_status":PASS,"closure_mode":w["mode"],"witness_id":w["evidence_id"],"witness_reason":w["reason"],"candidate_transmutations":_candidates(p),"rejections":rejects})
        else:
            out.append({"family":family,"input_status":p.get("status"),"result_status":OPEN,"closure_mode":None,"witness_id":None,"candidate_transmutations":_candidates(p),"rejections":rejects})
    closed=sum(r["result_status"]==PASS for r in out)
    return {
        "schema":"PROJECT_BRAIN_ACCEPTANCE_PROOF_TRANSMUTATION_VERDICT_V1",
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "family_count":len(out),
        "closed_family_count":closed,
        "open_family_count":len(out)-closed,
        "families":out,
        "rule":"NO_ACCEPTANCE_PROMOTION_WITHOUT_FULL_FROZEN_SCOPE_WITNESS__FINITE_SAMPLE_SUCCESS_IS_NOT_A_PROTOCOL_WIDE_BOUND__ABSOLUTE_DOMINANCE_REQUIRES_INDEPENDENT_EXACT_EXHAUSTIVE_OR_UNIVERSAL_SCOPE_COMPLETENESS",
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def _load(path: Path) -> dict[str,Any]:
    v=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(f"{path} must contain a JSON object")
    return v

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("protocols",type=Path)
    ap.add_argument("--evidence",type=Path)
    a=ap.parse_args()
    out=evaluate(_load(a.protocols),_load(a.evidence) if a.evidence else None)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
