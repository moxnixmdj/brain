"""Generic scorer for frozen fresh cross-capability suite."""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any, Mapping


def _eq(a:Any,b:Any)->bool:
    if isinstance(a,float) or isinstance(b,float):
        try: return math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-9)
        except Exception: return False
    if isinstance(a,list) and isinstance(b,list):
        return len(a)==len(b) and all(_eq(x,y) for x,y in zip(a,b))
    if isinstance(a,dict) and isinstance(b,dict):
        return set(a)==set(b) and all(_eq(a[k],b[k]) for k in a)
    return a==b


def score(outputs:Mapping[str,Any],answers:Mapping[str,Any])->dict[str,Any]:
    expected={str(x["id"]):x for x in answers["answers"]}
    rows=[]
    for row in outputs["rows"]:
        tid=str(row["id"]); exp=expected[tid]
        fields=exp["compare_fields"]; got=row["output"]
        checks={f:_eq(got.get(f),exp["expected"].get(f)) for f in fields}
        rows.append({"id":tid,"kind":row["kind"],"pass":all(checks.values()),"checks":checks})
    by_kind={}
    for r in rows:
        by_kind.setdefault(r["kind"],[]).append(r["pass"])
    return {
        "schema":"PROJECT_BRAIN_H100_CROSSCAP_G0_SCORE_V1",
        "passed":sum(r["pass"] for r in rows),
        "total":len(rows),
        "all_pass":all(r["pass"] for r in rows),
        "by_kind":{k:{"passed":sum(v),"total":len(v)} for k,v in sorted(by_kind.items())},
        "rows":rows,
    }


def main()->None:
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--outputs",required=True); ap.add_argument("--answers",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args()
    result=score(json.loads(Path(a.outputs).read_text()),json.loads(Path(a.answers).read_text()))
    Path(a.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:result[k] for k in ("passed","total","all_pass","by_kind")},sort_keys=True))


if __name__=="__main__":
    main()
