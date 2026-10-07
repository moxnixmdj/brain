from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from hashlib import sha256
import json
from canonical.runtime.source_aligned_acceptance_program_v1 import compile_program
from canonical.runtime.typed_acceptance_program_v1 import verify

SCHEMA="PROJECT_BRAIN_SOURCE_ALIGNED_ANALYTIC_GENERATOR_V1"
def _dig(x): return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def _field(fid,meta,rows):
    if not rows: raise ValueError("UNCONSTRAINED:"+fid)
    typ=meta["type"]
    if typ in {"number","integer"}:
        eq=[Decimal(r["literal"]) for r in rows if r["mode"]=="EQ_NUM"]
        lo=[Decimal(r["literal"]) for r in rows if r["mode"]=="GE"]
        hi=[Decimal(r["literal"]) for r in rows if r["mode"]=="LE"]
        if len(eq)>1 and len(set(eq))>1: raise ValueError("CONTRADICTORY_EQ:"+fid)
        low=max(lo) if lo else None; high=min(hi) if hi else None
        if low is not None and high is not None and low>high: raise ValueError("CONTRADICTORY_BOUNDS:"+fid)
        v=eq[0] if eq else (low if low is not None else high)
        if v is None: raise ValueError("NO_EFFECTIVE_CONSTRAINT:"+fid)
        if low is not None and v<low: raise ValueError("BELOW_BOUND:"+fid)
        if high is not None and v>high: raise ValueError("ABOVE_BOUND:"+fid)
        if typ=="integer":
            if eq and v!=v.to_integral_value(): raise ValueError("NONINTEGER_EQ:"+fid)
            if not eq: v=v.to_integral_value(rounding=ROUND_CEILING if low is not None else ROUND_FLOOR)
            if low is not None and v<low: raise ValueError("INTEGER_UNSAT:"+fid)
            if high is not None and v>high: raise ValueError("INTEGER_UNSAT:"+fid)
            return int(v)
        return float(v)
    if typ=="boolean":
        vals=[str(r["literal"]).lower()=="true" for r in rows]
    elif typ=="enum":
        vals=[str(r["literal"]) for r in rows]
    else: raise ValueError("TYPE:"+fid)
    if len(set(vals))!=1: raise ValueError("CONTRADICTORY_EQ:"+fid)
    return vals[0]

def construct(source_text,*,source_id,field_schema):
    a=compile_program(source_text,source_id=source_id,field_schema=field_schema)
    if a.get("status")!="COMPILED":
        return {"schema":SCHEMA,"status":"UNRESOLVED","pass":False,"compiler":a,"terminal_authority":False}
    b=compile_program(source_text,source_id=source_id,field_schema=field_schema)
    if _dig(a)!=_dig(b):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"reason":"COMPILER_NONDETERMINISM","terminal_authority":False}
    grouped={k:[] for k in field_schema}
    for row in a["compiled_requirements"]: grouped[row["field"]].append(row)
    try: candidate={k:_field(k,field_schema[k],grouped[k]) for k in sorted(field_schema)}
    except Exception as exc:
        return {"schema":SCHEMA,"status":"NO_SOUND_ANALYTIC_CANDIDATE","pass":False,"reason":str(exc),"terminal_authority":False}
    v=verify(a["acceptance_program"],trusted_values={},candidate_values=candidate)
    ok=v.get("pass") is True
    return {
      "schema":SCHEMA,"status":"PASS__GENERATED_AND_REVERIFIED" if ok else "FAIL_CLOSED",
      "pass":ok,"candidate_values":candidate if ok else None,"verdict":v,
      "source_sha256":a.get("source_sha256"),"program_sha256":_dig(a["acceptance_program"]),
      "model_dependency_count":0,"external_proposal_dependency":False,
      "terminal_authority":False,"capability_credit_delta":0,
      "boundary":"ADEQUACY_REQUIRES_SEPARATE_PROOF_THAT_COMPLETE_TASK_SUCCESS_EQUALS_THIS_PROGRAM_AND_OUTPUT_IS_THE_FIELD_MAPPING"
    }
