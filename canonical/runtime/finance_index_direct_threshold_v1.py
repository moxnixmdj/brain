from __future__ import annotations
from fractions import Fraction
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_INDEX_DIRECT_THRESHOLD_COMPILER_V1"
TARGET=Fraction(61,1)
WEIGHTS={
    "BUSINESS_KNOWLEDGE":Fraction(30,100),
    "AGENTIC_KNOWLEDGE_WORK":Fraction(30,100),
    "REASONING":Fraction(20,100),
    "AGENTIC_TOOL_USE":Fraction(10,100),
    "LONG_CONTEXT":Fraction(5,100),
    "NON_HALLUCINATION":Fraction(5,100),
}

class FinanceThresholdError(ValueError):
    pass

def _frac(x:Any)->Fraction:
    if isinstance(x,bool):
        raise FinanceThresholdError("BOOLEAN_SCORE_INVALID")
    try:
        return x if isinstance(x,Fraction) else Fraction(str(x))
    except Exception as exc:
        raise FinanceThresholdError("SCORE_INVALID") from exc

def compile_verified_lower_bounds(rows:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(rows,Mapping):
        raise FinanceThresholdError("ROWS_MAPPING_REQUIRED")
    missing=sorted(set(WEIGHTS)-set(rows))
    extra=sorted(set(rows)-set(WEIGHTS))
    if missing or extra:
        raise FinanceThresholdError("EXACT_SIX_COMPONENTS_REQUIRED")
    weighted=Fraction(0)
    components=[]
    for name,weight in WEIGHTS.items():
        row=rows[name]
        if not isinstance(row,Mapping):
            raise FinanceThresholdError("COMPONENT_ROW_MAPPING_REQUIRED:"+name)
        if row.get("verified") is not True:
            raise FinanceThresholdError("VERIFIED_LOWER_BOUND_REQUIRED:"+name)
        receipt=str(row.get("receipt") or "").strip()
        if not receipt:
            raise FinanceThresholdError("RECEIPT_REQUIRED:"+name)
        lower=_frac(row.get("lower_bound"))
        weighted += weight*lower
        components.append({
            "component":name,
            "weight":str(weight),
            "lower_bound":str(lower),
            "weighted_lower_bound":str(weight*lower),
            "receipt":receipt,
        })
    sufficient=weighted>=TARGET
    return {
        "schema":SCHEMA,
        "status":"DIRECT_THRESHOLD_MATHEMATICALLY_SUFFICIENT" if sufficient else "DIRECT_THRESHOLD_NOT_YET_SUFFICIENT",
        "weighted_lower_bound":str(weighted),
        "target":str(TARGET),
        "mathematically_sufficient":sufficient,
        "components":components,
        "componentwise_opus_noninferiority_required":False,
        "acceptance_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
