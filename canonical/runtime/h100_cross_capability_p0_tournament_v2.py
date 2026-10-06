from __future__ import annotations
import ast,itertools,json
from collections import deque
from pathlib import Path

SCHEMA="PROJECT_BRAIN_H100_CROSS_CAPABILITY_P0_TOURNAMENT_V2"
ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_CROSS_CAPABILITY_P0_TOURNAMENT_PRECOMMIT_V2.json"

class P0V2Error(ValueError): pass

def _arith(expr):
    n=ast.parse(expr,mode="eval")
    allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.Constant,ast.Add,ast.Sub,ast.Mult,ast.FloorDiv,ast.Pow,ast.USub,ast.UAdd)
    if any(not isinstance(x,allowed) for x in ast.walk(n)): raise P0V2Error("ARITH_UNSUPPORTED")
    def ev(x):
        if isinstance(x,ast.Expression): return ev(x.body)
        if isinstance(x,ast.Constant) and isinstance(x.value,int): return x.value
        if isinstance(x,ast.UnaryOp): return -ev(x.operand) if isinstance(x.op,ast.USub) else ev(x.operand)
        a,b=ev(x.left),ev(x.right)
        if isinstance(x.op,ast.Add): return a+b
        if isinstance(x.op,ast.Sub): return a-b
        if isinstance(x.op,ast.Mult): return a*b
        if isinstance(x.op,ast.FloorDiv): return a//b
        if isinstance(x.op,ast.Pow):
            if abs(b)>12: raise P0V2Error("EXPONENT_LIMIT")
            return a**b
        raise P0V2Error("ARITH_OP")
    return ev(n)

def _code(inp):
    ops={"<":lambda x,t:x<t,"<=":lambda x,t:x<=t,"==":lambda x,t:x==t,">=":lambda x,t:x>=t,">":lambda x,t:x>t}
    hits=[name for name,f in ops.items() if all(bool(f(x,inp["threshold"]))==bool(y) for x,y in inp["examples"])]
    if len(hits)!=1: return {"status":"ABSTAIN_PROGRAM_AMBIGUOUS","candidate_count":len(hits)}
    op=hits[0]; return {"operator":op,"holdout":[ops[op](x,inp["threshold"]) for x in inp["holdout"]]}

def _roles(inp):
    g={}
    for a,b in inp["edges"]: g.setdefault(a,set()).add(b); g.setdefault(b,set()).add(a)
    def rr(cue):
        q=deque([cue]); seen={cue}; roles=set()
        while q:
            x=q.popleft()
            if x==inp["anchors"]["input"]: roles.add("INPUT")
            if x==inp["anchors"]["target"]: roles.add("TARGET")
            for y in g.get(x,()):
                if y not in seen: seen.add(y); q.append(y)
        return roles
    ins=[]; targets=[]
    for c in inp["clauses"]:
        roles=rr(c["cue"])
        if len(roles)!=1: return {"status":"ABSTAIN_LEXICAL","role_count":len(roles)}
        (ins if next(iter(roles))=="INPUT" else targets).extend(c["fields"])
    if len(targets)!=1: return {"status":"ABSTAIN_ROLE_CARDINALITY"}
    return {"inputs":sorted(ins),"target":targets[0]}

def _raster(inp):
    rows=inp["rows"]; bg=inp["background"]
    if not rows or len({len(r) for r in rows})!=1: raise P0V2Error("RASTER_SHAPE")
    h,w=len(rows),len(rows[0])
    mask=[[rows[y][x]!=bg for x in range(w)] for y in range(h)]
    # Connected nonbackground x-runs define candidate vertical bars.
    col=[sum(mask[y][x] for y in range(h)) for x in range(w)]
    ints=[]; start=None
    for x,v in enumerate(col+[0]):
        if v>0 and start is None: start=x
        if v==0 and start is not None: ints.append((start,x-1)); start=None
    heights=[]
    for lo,hi in ints:
        ys=[y for y in range(h) for x in range(lo,hi+1) if mask[y][x]]
        heights.append(max(ys)-min(ys)+1)
    return {"bar_count":len(ints),"heights":heights}

def _tool(inp):
    r=inp["request"]; hits=[]
    for c in inp["contracts"]:
        if c["effect"]==r["effect"] and c["path"]==r["path"] and all(k in r["payload"] for k in c["required"]): hits.append(c["id"])
    return hits[0] if len(hits)==1 else "ABSTAIN_TOOL_AMBIGUOUS"

def _plan(inp):
    q=deque([(frozenset(inp["initial"]),())]); seen={frozenset(inp["initial"])}
    while q:
        res,path=q.popleft()
        if inp["goal"] in res: return list(path)
        for op in sorted(inp["operators"],key=lambda z:z["id"]):
            if op["id"] in path or not set(op["requires"]).issubset(res): continue
            new=frozenset(set(res)|set(op["provides"]))
            if new in seen: continue
            seen.add(new); q.append((new,path+(op["id"],)))
    return None

def _memory(inp):
    s={}
    for op,k,v in inp["events"]:
        if op=="SET": s[k]=v
        elif op=="DELETE": s.pop(k,None)
        else: raise P0V2Error("MEMORY_OP")
    return s.get(inp["query"])

def _prim(op,v): return {"plus1":v+1,"times2":v*2,"square":v*v,"neg":-v}[op]

def _transfer(inp):
    hits=[]
    for seq in itertools.permutations(inp["primitives"],inp["depth"]):
        good=True
        for x,y in inp["examples"]:
            v=x
            for op in seq: v=_prim(op,v)
            if v!=y: good=False; break
        if good: hits.append(seq)
    if len(hits)!=1: return {"status":"ABSTAIN_STRUCTURE_AMBIGUOUS","candidate_count":len(hits)}
    seq=hits[0]; out=[]
    for x in inp["holdout"]:
        v=x
        for op in seq: v=_prim(op,v)
        out.append(v)
    return {"sequence":list(seq),"holdout":out}

def solve(family,public_input):
    if family=="ARITHMETIC_REASONING": return _arith(public_input["expression"])
    if family=="CODE_REPAIR": return _code(public_input)
    if family=="LEXICAL_LANGUAGE": return _roles(public_input)
    if family=="RASTER_VISION": return _raster(public_input)
    if family=="TYPED_TOOL_SELECTION": return _tool(public_input)
    if family=="RESOURCE_PLANNING": return _plan(public_input)
    if family=="EVENT_MEMORY": return _memory(public_input)
    if family=="NOVEL_STRUCTURE_TRANSFER": return _transfer(public_input)
    if family=="SEALED_INFORMATION_CONTROL":
        return {"status":"ABSTAIN_IRREDUCIBLE_INFORMATION_GAP","residual_worlds":int(public_input["hidden_world_count"])}
    raise P0V2Error("FAMILY_UNSUPPORTED")

def run():
    spec=json.loads(PRE.read_text()); rows=[]
    for task in spec["tasks"]:
        got=solve(task["family"],task["public_input"])
        if task["family"]=="SEALED_INFORMATION_CONTROL":
            ok=isinstance(got,dict) and got.get("status")=="ABSTAIN_IRREDUCIBLE_INFORMATION_GAP"
            lb=(int(task["public_input"]["hidden_world_count"])-1).bit_length(); cls="INFORMATION_GAP"
        else:
            ok=got==task["gold"]; lb=0; cls=None if ok else "ALGORITHM_GAP"
        rows.append({"id":task["id"],"family":task["family"],"pass":ok,"output":got,"failure_class":cls,"lower_bound_bits":lb})
    ns=[r for r in rows if r["family"]!="SEALED_INFORMATION_CONTROL"]; seal=[r for r in rows if r["family"]=="SEALED_INFORMATION_CONTROL"][0]
    return {
      "schema":SCHEMA,
      "status":"PASS__STRICT_BOUNDARY_P0_TOURNAMENT" if sum(r["pass"] for r in ns)==8 and seal["pass"] else "FAIL__P0_V2_RESIDUAL",
      "nonsealed_passed":sum(r["pass"] for r in ns),
      "nonsealed_total":8,
      "sealed_control_pass":seal["pass"],
      "max_observed_information_lower_bound_bits":max(r["lower_bound_bits"] for r in rows),
      "target_adapted_persistent_bits":0,
      "generic_frozen_runtime_code_bytes":len(Path(__file__).read_bytes()),
      "task_results":rows,
      "hard_nonclaims":["SYNTHETIC_SUITE_NOT_FRONTIER_EQUIVALENCE","FINITE_PASS_NOT_GENERALIZATION_PROOF"]
    }

if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
