"""Independent information-safe proof population for the compositional normalized-rule AST.

The evaluator intentionally does not import the Brain candidate. It generates
nested typed expressions spanning arithmetic, dimensional composition, predicates,
conditionals, branch selection, requirement applicability, invariants, lineage and
DAG dependencies. Natural-language rule extraction is outside this contract.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math
import random
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_STRUCTURED_METHOD_EXPRESSION_AST_PROOF_V2"


def _dim_parse(raw: str) -> dict[str, int]:
    if raw == "dimensionless":
        return {}
    out: dict[str, int] = {}
    for term in raw.split("*"):
        bits = term.split("^", 1)
        unit = bits[0]
        power = int(bits[1]) if len(bits) == 2 else 1
        out[unit] = out.get(unit, 0) + power
        if out[unit] == 0:
            del out[unit]
    return out


def _dim_string(dim: Mapping[str, int]) -> str:
    if not dim:
        return "dimensionless"
    return "*".join(k if v == 1 else f"{k}^{v}" for k, v in sorted(dim.items()))


def _dim_mul(a: str, b: str, sign: int = 1) -> str:
    out = _dim_parse(a)
    for k, v in _dim_parse(b).items():
        out[k] = out.get(k, 0) + sign * v
        if out[k] == 0:
            del out[k]
    return _dim_string(out)


def _eval(expr: Mapping[str, Any], meta: Mapping[str, Mapping[str, str]], vals: Mapping[str, Any]) -> tuple[str, str, Any]:
    op = expr["op"]
    if op == "ref":
        rid = expr["id"]
        return meta[rid]["type"], meta[rid]["dimension"], vals[rid]
    if op == "const":
        typ = expr["type"]; dim = _dim_string(_dim_parse(expr["dimension"])); value = expr["value"]
        return typ, dim, float(value) if typ == "number" else value

    def one(key: str = "arg"):
        return _eval(expr[key], meta, vals)
    def two():
        return _eval(expr["left"], meta, vals), _eval(expr["right"], meta, vals)

    if op in {"add", "sub", "min", "max"}:
        a, b = two()
        assert a[0] in {"integer","number"} and b[0] in {"integer","number"} and a[1] == b[1]
        av, bv = float(a[2]), float(b[2])
        value = {"add":av+bv,"sub":av-bv,"min":min(av,bv),"max":max(av,bv)}[op]
        return "number", a[1], value
    if op in {"mul", "div"}:
        a, b = two()
        assert a[0] in {"integer","number"} and b[0] in {"integer","number"}
        if op == "div":
            assert float(b[2]) != 0.0
            return "number", _dim_mul(a[1],b[1],-1), float(a[2])/float(b[2])
        return "number", _dim_mul(a[1],b[1]), float(a[2])*float(b[2])
    if op in {"neg","abs"}:
        a=one(); assert a[0] in {"integer","number"}
        return "number",a[1],(-float(a[2]) if op=="neg" else abs(float(a[2])))
    if op == "pow_int":
        a=one(); p=expr["power"]; assert a[0] in {"integer","number"} and isinstance(p,int)
        return "number",_dim_string({k:v*p for k,v in _dim_parse(a[1]).items() if v*p}),float(a[2])**p
    if op in {"exp","log","sqrt"}:
        a=one(); assert a[0] in {"integer","number"} and a[1]=="dimensionless"
        av=float(a[2])
        if op=="log":
            assert av>0.0; value=math.log(av)
        elif op=="sqrt":
            assert av>=0.0; value=math.sqrt(av)
        else:
            value=math.exp(av)
        assert math.isfinite(value)
        return "number","dimensionless",value
    if op in {"gt","ge","lt","le"}:
        a,b=two(); assert a[0] in {"integer","number"} and b[0] in {"integer","number"} and a[1]==b[1]
        av,bv=float(a[2]),float(b[2])
        return "boolean","dimensionless",{"gt":av>bv,"ge":av>=bv,"lt":av<bv,"le":av<=bv}[op]
    if op=="isclose":
        a,b=two(); assert a[0] in {"integer","number"} and b[0] in {"integer","number"} and a[1]==b[1]
        rel=float(expr.get("rel_tol",1e-12)); abs_=float(expr.get("abs_tol",0.0))
        assert rel>=0.0 and abs_>=0.0 and math.isfinite(rel) and math.isfinite(abs_)
        return "boolean","dimensionless",math.isclose(float(a[2]),float(b[2]),rel_tol=rel,abs_tol=abs_)
    if op in {"eq","neq"}:
        a,b=two(); assert a[0]==b[0] and a[1]==b[1]
        v=a[2]==b[2]
        return "boolean","dimensionless",v if op=="eq" else not v
    if op in {"and","or"}:
        rows=[_eval(x,meta,vals) for x in expr["args"]]
        assert all(t=="boolean" and d=="dimensionless" for t,d,_ in rows)
        bs=[bool(v) for _,_,v in rows]
        return "boolean","dimensionless",all(bs) if op=="and" else any(bs)
    if op=="not":
        a=one(); assert a[0]=="boolean" and a[1]=="dimensionless"
        return "boolean","dimensionless",not bool(a[2])
    if op=="if":
        c=one("cond"); t=one("then"); e=one("else")
        assert c[0]=="boolean" and c[1]=="dimensionless" and t[0]==e[0] and t[1]==e[1]
        return t if c[2] else e
    raise ValueError("ORACLE_EXPR_OP:"+op)


def _ref(x: str) -> dict[str, Any]:
    return {"op":"ref","id":x}


def _num(value: float, dimension: str = "dimensionless") -> dict[str, Any]:
    return {"op":"const","type":"number","dimension":dimension,"value":float(value)}


def generate_case(seed: int, ordinal: int) -> dict[str, Any]:
    r=random.Random((seed<<17)^ordinal^0xA57)
    mode=("regulated","standard","stress")[ordinal%3]
    a=float(r.randint(40,120)); b=float(r.randint(10,35)); q=float(r.randint(2,9))
    adj=float(r.randint(1,8)); cap=float(r.randint(55,140)); threshold=float(r.uniform(1.2,5.5))
    schema_fields=[
        {"id":"amount_a","type":"number","dimension":"currency","value":a},
        {"id":"amount_b","type":"number","dimension":"currency","value":b},
        {"id":"quantity","type":"number","dimension":"count","value":q},
        {"id":"adjustment","type":"number","dimension":"currency","value":adj},
        {"id":"cap","type":"number","dimension":"currency","value":cap},
        {"id":"review_threshold","type":"number","dimension":"dimensionless","value":threshold},
        {"id":"mode","type":"enum","dimension":"dimensionless","value":mode},
    ]
    is_reg={"op":"eq","left":_ref("mode"),"right":{"op":"const","type":"enum","dimension":"dimensionless","value":"regulated"}}
    is_std={"op":"eq","left":_ref("mode"),"right":{"op":"const","type":"enum","dimension":"dimensionless","value":"standard"}}
    is_stress={"op":"eq","left":_ref("mode"),"right":{"op":"const","type":"enum","dimension":"dimensionless","value":"stress"}}
    positive_a={"op":"gt","left":_ref("amount_a"),"right":_num(0,"currency")}
    requirements=[
        {"id":"REQ_SCHEMA","source_kind":"schema"},
        {"id":"REQ_FORMULA","source_kind":"formula"},
        {"id":"REQ_CALLOUT","source_kind":"feature_callout"},
        {"id":"REQ_CONSTRAINT","source_kind":"constraint","applies_when":positive_a},
        {"id":"REQ_NEQ","source_kind":"constraint","applies_when":{"op":"neq","left":_ref("mode"),"right":{"op":"const","type":"enum","dimension":"dimensionless","value":"impossible"}}},
        {"id":"REQ_REG","source_kind":"standard","applies_when":is_reg},
        {"id":"REQ_STD","source_kind":"standard","applies_when":is_std},
        {"id":"REQ_STRESS","source_kind":"standard","applies_when":is_stress},
        {"id":"REQ_NEVER","source_kind":"constraint","applies_when":{"op":"lt","left":_ref("amount_a"),"right":_num(0,"currency")}},
    ]
    common_rules=[
        {
            "id":"R_SUBTOTAL",
            "expr":{"op":"add","left":_ref("amount_a"),"right":_ref("amount_b")},
            "output":"subtotal","output_type":"number","output_dimension":"currency",
            "consumes_requirements":["REQ_SCHEMA","REQ_FORMULA"],
            "invariants":[{"op":"ge","left":_ref("subtotal"),"right":_num(0,"currency")}],
        },
        {
            "id":"R_UNIT_PRICE",
            "expr":{"op":"div","left":_ref("subtotal"),"right":_ref("quantity")},
            "output":"unit_price","output_type":"number","output_dimension":"count^-1*currency",
            "consumes_requirements":["REQ_FORMULA"],
            "invariants":[{"op":"gt","left":_ref("unit_price"),"right":_num(0,"count^-1*currency")}],
        },
        {
            "id":"R_REBUILT_TOTAL",
            "expr":{"op":"mul","left":_ref("unit_price"),"right":_ref("quantity")},
            "output":"rebuilt_total","output_type":"number","output_dimension":"currency",
            "consumes_requirements":["REQ_SCHEMA"],
            "invariants":[{"op":"isclose","left":_ref("rebuilt_total"),"right":_ref("subtotal"),"rel_tol":1e-12,"abs_tol":1e-12}],
        },
        {
            "id":"R_DELTA",
            "expr":{"op":"sub","left":_ref("amount_a"),"right":_ref("amount_b")},
            "output":"delta","output_type":"number","output_dimension":"currency",
            "consumes_requirements":["REQ_CALLOUT"],
            "invariants":[],
        },
        {
            "id":"R_ABS_DELTA",
            "expr":{"op":"abs","arg":_ref("delta")},
            "output":"abs_delta","output_type":"number","output_dimension":"currency",
            "consumes_requirements":["REQ_CALLOUT"],
            "invariants":[{"op":"ge","left":_ref("abs_delta"),"right":_num(0,"currency")}],
        },
        {
            "id":"R_RATIO",
            "expr":{"op":"div","left":_ref("amount_a"),"right":_ref("amount_b")},
            "output":"ratio","output_type":"number","output_dimension":"dimensionless",
            "consumes_requirements":["REQ_CONSTRAINT"],
            "invariants":[{"op":"gt","left":_ref("ratio"),"right":_num(0)}],
        },
        {
            "id":"R_RATIO_SQ",
            "expr":{"op":"pow_int","arg":_ref("ratio"),"power":2},
            "output":"ratio_sq","output_type":"number","output_dimension":"dimensionless",
            "consumes_requirements":["REQ_CONSTRAINT"],
            "invariants":[{"op":"ge","left":_ref("ratio_sq"),"right":_num(0)}],
        },
        {
            "id":"R_LOG_RATIO",
            "expr":{"op":"log","arg":_ref("ratio")},
            "output":"log_ratio","output_type":"number","output_dimension":"dimensionless",
            "consumes_requirements":["REQ_FORMULA"],
            "invariants":[],
        },
        {
            "id":"R_EXP_LOG_RATIO",
            "expr":{"op":"exp","arg":_ref("log_ratio")},
            "output":"exp_log_ratio","output_type":"number","output_dimension":"dimensionless",
            "consumes_requirements":["REQ_FORMULA"],
            "invariants":[],
        },
        {
            "id":"R_SQRT_RATIO_SQ",
            "expr":{"op":"sqrt","arg":_ref("ratio_sq")},
            "output":"sqrt_ratio_sq","output_type":"number","output_dimension":"dimensionless",
            "consumes_requirements":["REQ_FORMULA"],
            "invariants":[{"op":"ge","left":_ref("sqrt_ratio_sq"),"right":_num(0)}],
        },
        {
            "id":"R_CAPPED",
            "expr":{"op":"min","left":{"op":"max","left":_ref("subtotal"),"right":_num(0,"currency")},"right":_ref("cap")},
            "output":"capped","output_type":"number","output_dimension":"currency",
            "consumes_requirements":["REQ_CONSTRAINT"],
            "invariants":[{"op":"le","left":_ref("capped"),"right":_ref("cap")}],
        },
        {
            "id":"R_REVIEW",
            "expr":{
                "op":"and",
                "args":[
                    {"op":"gt","left":_ref("ratio"),"right":_ref("review_threshold")},
                    {"op":"not","arg":{"op":"eq","left":_ref("mode"),"right":{"op":"const","type":"enum","dimension":"dimensionless","value":"standard"}}},
                ],
            },
            "output":"needs_review","output_type":"boolean","output_dimension":"dimensionless",
            "consumes_requirements":["REQ_CALLOUT","REQ_NEQ"],
            "invariants":[],
        },
    ]
    branches=[
        {
            "id":"REGULATED_BRANCH","when":is_reg,
            "rules":[{
                "id":"R_FINAL_REG",
                "expr":{"op":"sub","left":_ref("capped"),"right":_ref("adjustment")},
                "output":"final_amount","output_type":"number","output_dimension":"currency",
                "consumes_requirements":["REQ_REG"],
                "invariants":[{"op":"ge","left":_ref("final_amount"),"right":{"op":"neg","arg":_ref("adjustment")}}],
            }],
        },
        {
            "id":"STANDARD_BRANCH","when":is_std,
            "rules":[{
                "id":"R_FINAL_STD",
                "expr":{"op":"add","left":_ref("capped"),"right":_ref("adjustment")},
                "output":"final_amount","output_type":"number","output_dimension":"currency",
                "consumes_requirements":["REQ_STD"],
                "invariants":[],
            }],
        },
        {
            "id":"STRESS_BRANCH","when":is_stress,
            "rules":[{
                "id":"R_FINAL_STRESS",
                "expr":{
                    "op":"if",
                    "cond":{"op":"or","args":[_ref("needs_review"),{"op":"gt","left":_ref("ratio_sq"),"right":_num(4)}]},
                    "then":{"op":"sub","left":_ref("capped"),"right":{"op":"mul","left":_ref("adjustment"),"right":_num(2)}},
                    "else":{"op":"add","left":_ref("capped"),"right":_ref("adjustment")},
                },
                "output":"final_amount","output_type":"number","output_dimension":"currency",
                "consumes_requirements":["REQ_STRESS"],
                "invariants":[],
            }],
        },
    ]
    return {
        "schema":SCHEMA,
        "case_id":f"STRUCTURED-AST-{seed}-{ordinal}",
        "schema_fields":schema_fields,
        "requirements":requirements,
        "common_rules":common_rules,
        "branches":branches,
        "required_outputs":["final_amount","needs_review","unit_price","ratio_sq"],
    }


def public_case(case: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(case))


def _expected(case: Mapping[str, Any]) -> dict[str, Any]:
    meta={x["id"]:{"type":x["type"],"dimension":_dim_string(_dim_parse(x["dimension"]))} for x in case["schema_fields"]}
    vals={x["id"]:x["value"] for x in case["schema_fields"]}
    applicable: dict[str,str]={}; exclusions=[]
    for req in case["requirements"]:
        cond=req.get("applies_when")
        applies=True if cond is None else bool(_eval(cond,meta,vals)[2])
        if applies:
            applicable[req["id"]]=req["source_kind"]
        else:
            exclusions.append({"requirement_id":req["id"],"source_kind":req["source_kind"],"reason":"APPLICABILITY_CONDITION_FALSE"})
    matches=[]
    for branch in case["branches"]:
        t,d,v=_eval(branch["when"],meta,vals)
        assert t=="boolean" and d=="dimensionless"
        if v: matches.append(branch)
    assert len(matches)==1
    selected=matches[0]
    pending=list(case.get("common_rules",[]))+list(selected["rules"])
    nodes=[]; consumers={x:[] for x in applicable}
    while pending:
        progressed=False; rest=[]
        for rule in pending:
            # Oracle dependency resolution by catching missing references.
            try:
                typ,dim,value=_eval(rule["expr"],meta,vals)
            except KeyError:
                rest.append(rule); continue
            assert typ==rule["output_type"] and dim==_dim_string(_dim_parse(rule["output_dimension"]))
            vals[rule["output"]]=value
            meta[rule["output"]]={"type":typ,"dimension":dim}
            invariants=deepcopy(rule.get("invariants",[]))
            for inv in invariants:
                it,idim,iv=_eval(inv,meta,vals)
                assert it=="boolean" and idim=="dimensionless" and iv is True
            consumes=sorted(rule.get("consumes_requirements",[]))
            for rid in consumes:
                assert rid in consumers
                consumers[rid].append(rule["id"])
            nodes.append({
                "rule_id":rule["id"],"expression":deepcopy(rule["expr"]),"output":rule["output"],
                "output_type":typ,"output_dimension":dim,"consumes_requirements":consumes,
                "invariants":invariants,"evaluated_value":value,
            })
            progressed=True
        if not progressed:
            raise ValueError("ORACLE_DAG_UNRESOLVED")
        pending=rest
    assert all(consumers.values())
    lineage=[{"requirement_id":rid,"source_kind":applicable[rid],"consumer_rule_ids":sorted(consumers[rid])} for rid in sorted(applicable)]
    outputs=[{"id":oid,"type":meta[oid]["type"],"dimension":meta[oid]["dimension"],"value":vals[oid]} for oid in case["required_outputs"]]
    return {
        "selected_branch_id":selected["id"],"nodes":nodes,"requirement_lineage":lineage,
        "justified_exclusions":sorted(exclusions,key=lambda x:x["requirement_id"]),"outputs":outputs,
    }


def score(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate,Mapping) or candidate.get("status")!="COMPILED":
        return {"pass":False,"reason":"CANDIDATE_NOT_COMPILED"}
    expected=_expected(case)
    for key in ("selected_branch_id","nodes","requirement_lineage","justified_exclusions","outputs"):
        if candidate.get(key)!=expected[key]:
            return {"pass":False,"reason":"MISMATCH:"+key}
    return {"pass":True,"reason":"PASS"}


def run_batch(seed: int, count: int, solver) -> dict[str, Any]:
    by_branch=defaultdict(lambda:{"pass":0,"total":0}); failures=[]; op_coverage=set()
    for i in range(count):
        case=generate_case(seed,i)
        def walk(expr):
            if not isinstance(expr,Mapping): return
            op_coverage.add(str(expr.get("op")))
            for k in ("arg","left","right","cond","then","else"):
                if k in expr: walk(expr[k])
            for x in expr.get("args",[]) if isinstance(expr.get("args",[]),list) else []: walk(x)
        for req in case["requirements"]:
            if req.get("applies_when"): walk(req["applies_when"])
        for branch in case["branches"]:
            walk(branch["when"])
            for rule in branch["rules"]:
                walk(rule["expr"])
                for inv in rule.get("invariants",[]): walk(inv)
        for rule in case["common_rules"]:
            walk(rule["expr"])
            for inv in rule.get("invariants",[]): walk(inv)
        try:
            out=solver(public_case(case)); verdict=score(case,out)
        except Exception as exc:
            verdict={"pass":False,"reason":type(exc).__name__+":"+str(exc)}
        branch=("REGULATED","STANDARD","STRESS")[i%3]
        by_branch[branch]["total"]+=1; by_branch[branch]["pass"]+=int(bool(verdict["pass"]))
        if not verdict["pass"]: failures.append({"case_id":case["case_id"],"reason":verdict["reason"]})
    return {
        "schema":"PROJECT_BRAIN_STRUCTURED_METHOD_EXPRESSION_AST_PREFLIGHT_RESULT_V2",
        "case_count":count,"passed":count-len(failures),"failed":len(failures),"all_pass":not failures,
        "by_branch":dict(by_branch),"operation_coverage":sorted(op_coverage),"failures":failures,
        "terminal_authority":False,"capability_credit_delta":0,
    }
