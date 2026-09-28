#!/usr/bin/env python3
import argparse, hashlib, json, platform, time
from pathlib import Path
import sympy as sp

def symbols_for(names):
    return {name: sp.Symbol(name) for name in names}

def parse_expr(text, env):
    safe = dict(env)
    safe.update({"sin":sp.sin,"cos":sp.cos,"exp":sp.exp,"log":sp.log,"sqrt":sp.sqrt,"pi":sp.pi})
    return sp.sympify(text, locals=safe)

def exact_equal(a,b):
    try:
        return sp.simplify(a-b) == 0
    except Exception:
        return a == b

def run_task(task):
    op=task["operation"]; args=task["args"]
    names=set(args.get("vars",[]))
    if "var" in args: names.add(args["var"])
    names.update(["x","y","k"])
    env=symbols_for(sorted(names))
    if op=="rational_sum":
        result=sp.Rational(int(args["a_num"]),int(args["a_den"])) + sp.Rational(int(args["b_num"]),int(args["b_den"]))
        expected=parse_expr(task["expected"],env)
        return str(result), bool(exact_equal(result,expected))
    if op=="factor":
        expr=parse_expr(args["expr"],env)
        result=sp.factor(expr)
        expected=parse_expr(task["expected"],env)
        ok=bool(exact_equal(result,expected) and sp.expand(result-expr)==0 and isinstance(result,sp.Mul))
        return str(result),ok
    if op=="coefficient":
        expr=sp.expand(parse_expr(args["expr"],env))
        result=expr.coeff(env[args["var"]],int(args["power"]))
        expected=parse_expr(task["expected"],env)
        return str(result),bool(exact_equal(result,expected))
    if op=="roots":
        expr=parse_expr(args["expr"],env); var=env[args["var"]]
        result=sorted(sp.solve(expr,var),key=sp.default_sort_key)
        expected=sorted([parse_expr(v,env) for v in task["expected"]],key=sp.default_sort_key)
        ok=len(result)==len(expected) and all(exact_equal(a,b) for a,b in zip(result,expected))
        return [str(v) for v in result],bool(ok)
    if op=="differentiate":
        result=sp.diff(parse_expr(args["expr"],env),env[args["var"]])
        expected=parse_expr(task["expected"],env)
        return str(result),bool(exact_equal(result,expected))
    if op=="integrate_definite":
        var=env[args["var"]]
        result=sp.integrate(parse_expr(args["expr"],env),(var,parse_expr(args["lower"],env),parse_expr(args["upper"],env)))
        expected=parse_expr(task["expected"],env)
        return str(result),bool(exact_equal(result,expected))
    if op=="hilbert_determinant":
        n=int(args["n"])
        mat=sp.Matrix([[sp.Rational(1,i+j-1) for j in range(1,n+1)] for i in range(1,n+1)])
        result=mat.det(); expected=parse_expr(task["expected"],env)
        return str(result),bool(exact_equal(result,expected))
    if op=="binomial_square_sum":
        n=int(args["n"])
        result=sum(sp.binomial(n,k)**2 for k in range(n+1))
        expected=sp.Integer(task["expected"])
        return str(result),bool(result==expected)
    if op=="limit":
        result=sp.limit(parse_expr(args["expr"],env),env[args["var"]],parse_expr(args["point"],env))
        expected=parse_expr(task["expected"],env)
        return str(result),bool(exact_equal(result,expected))
    if op=="linear_system":
        vars_=[env[n] for n in args["vars"]]
        eqs=[parse_expr(v,env) for v in args["equations"]]
        sols=sp.solve(eqs,vars_,dict=True)
        if len(sols)!=1: return [{"unexpected_solution_count":len(sols)}],False
        got={str(v):str(sols[0][v]) for v in vars_}
        return got,got==task["expected"]
    if op=="series_coefficient":
        var=env[args["var"]]; power=int(args["power"])
        expr=parse_expr(args["expr"],env)
        result=sp.expand(sp.series(expr,var,0,power+1).removeO()).coeff(var,power)
        expected=parse_expr(task["expected"],env)
        return str(result),bool(exact_equal(result,expected))
    raise ValueError("unknown operation: "+op)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--suite",required=True)
    ap.add_argument("--report",required=True)
    ns=ap.parse_args()
    suite_path=Path(ns.suite)
    raw=suite_path.read_bytes()
    suite=json.loads(raw)
    t_all=time.perf_counter()
    results=[]
    for task in suite["tasks"]:
        t0=time.perf_counter()
        try:
            output,ok=run_task(task)
            error=None
        except Exception as e:
            output=None; ok=False; error=type(e).__name__+":"+str(e)
        results.append({
            "id":task["id"],
            "operation":task["operation"],
            "pass":bool(ok),
            "output":output,
            "expected":task["expected"],
            "elapsed_s":round(time.perf_counter()-t0,9),
            "error":error
        })
    total=round(time.perf_counter()-t_all,9)
    passes=sum(1 for r in results if r["pass"])
    report={
      "schema":"PROJECT_BRAIN_CAPABILITY_OBSOLESCENCE_EXECUTION_REPORT_V1",
      "suite_id":suite["suite_id"],
      "capability_id":suite["capability_id"],
      "suite_sha256":hashlib.sha256(raw).hexdigest(),
      "producer":"SymPy",
      "producer_version":sp.__version__,
      "python_version":platform.python_version(),
      "platform":platform.platform(),
      "pass_count":passes,
      "fail_count":len(results)-passes,
      "exact_correctness":passes/len(results),
      "total_eval_s":total,
      "incremental_spend_usd":0,
      "results":results,
      "candidate_obsolescence_status":"CANDIDATE_MATCH" if passes==len(results) else "RESIDUAL_GAP_VERIFIED"
    }
    Path(ns.report).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))
    if passes != suite["acceptance"]["pass_count_required"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
