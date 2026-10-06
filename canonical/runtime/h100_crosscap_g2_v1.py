from __future__ import annotations
import heapq,itertools,math
from collections import deque
from fractions import Fraction
from typing import Any,Mapping,Sequence
from canonical.runtime import h100_crosscap_g1_v1 as g1

class G2Error(ValueError): pass

def solve_reasoning(task:Mapping[str,Any]):
 spec=task["spec"]; vs=list(map(str,spec["variables"])); dom=spec["domains"]; cs=list(spec.get("constraints",[]))
 sols=[]
 for vals in itertools.product(*[[int(x) for x in dom[v]] for v in vs]):
  env=dict(zip(vs,vals)); ok=True
  for c in cs:
   xs=[env[v] for v in c.get("vars",[])]
   op=str(c["op"]); val=c.get("value")
   if op=="LT": z=len(xs)==2 and xs[0]<xs[1]
   elif op=="GT": z=len(xs)==2 and xs[0]>xs[1]
   elif op=="EQ": z=len(xs)==2 and xs[0]==xs[1]
   elif op=="NEQ": z=len(xs)==2 and xs[0]!=xs[1]
   elif op=="ALL_DIFF": z=len(xs)==len(set(xs))
   elif op=="SUM_EQ": z=sum(xs)==int(val)
   elif op=="SUM_LT": z=sum(xs)<int(val)
   elif op=="SUM_GT": z=sum(xs)>int(val)
   elif op=="PRODUCT_EQ":
    p=1
    for x in xs:p*=x
    z=p==int(val)
   elif op=="PRODUCT_LT":
    p=1
    for x in xs:p*=x
    z=p<int(val)
   elif op=="PRODUCT_GT":
    p=1
    for x in xs:p*=x
    z=p>int(val)
   else: raise G2Error("CSP_OP_UNSUPPORTED:"+op)
   if not z: ok=False; break
  if ok: sols.append(env)
 return {"status":"UNIQUE" if len(sols)==1 else ("NONE" if not sols else "MULTIPLE"),"solutions":sols}

def _solve_linear(a,b):
 n=len(b); m=[[Fraction(x) for x in a[i]]+[Fraction(b[i])] for i in range(n)]
 for col in range(n):
  p=next((r for r in range(col,n) if m[r][col]!=0),None)
  if p is None:return None
  m[col],m[p]=m[p],m[col]; d=m[col][col]; m[col]=[x/d for x in m[col]]
  for r in range(n):
   if r==col:continue
   f=m[r][col]
   if f:m[r]=[x-f*y for x,y in zip(m[r],m[col])]
 return [m[i][-1] for i in range(n)]

def synthesize_piecewise(examples:Sequence[Mapping[str,int]],max_degree:int=3):
 xs=[int(r["x"]) for r in examples]; ys=[int(r["y"]) for r in examples]
 transforms=[("X",lambda x:Fraction(x)),("ABS",lambda x:Fraction(abs(x)))]
 for tname,tf in transforms:
  for deg in range(max_degree+1):
   if len(xs)<deg+1:continue
   A=[[tf(xs[i])**j for j in range(deg+1)] for i in range(deg+1)]
   c=_solve_linear(A,[ys[i] for i in range(deg+1)])
   if c is None:continue
   def ev(x,c=c,tf=tf):
    z=tf(x); return sum(c[j]*(z**j) for j in range(len(c)))
   if all(ev(x)==y for x,y in zip(xs,ys)):
    return {"status":"PROGRAM_FOUND","transform":tname,"coefficients":[[q.numerator,q.denominator] for q in c],"degree":deg}
 return {"status":"NO_PROGRAM","transform":None,"coefficients":None,"degree":None}

def predict_piecewise(r,x):
 z=Fraction(abs(int(x)) if r["transform"]=="ABS" else int(x))
 c=[Fraction(n,d) for n,d in r["coefficients"]]; q=sum(c[j]*(z**j) for j in range(len(c)))
 return q.numerator if q.denominator==1 else float(q)

def resolve_language(task):
 k=task["knowledge"]; anchors=k["anchors"]; edges=k["edges"]; g={}
 for a,b in edges:g.setdefault(a,set()).add(b);g.setdefault(b,set()).add(a)
 def roles(cue):
  q=deque([cue]);seen={cue};found=set()
  while q:
   x=q.popleft()
   if x==anchors["input"]:found.add("INPUT")
   if x==anchors["target"]:found.add("TARGET")
   for y in g.get(x,()):
    if y not in seen:seen.add(y);q.append(y)
  return found
 ins=[];tar=[]
 for c in task["clauses"]:
  r=roles(c["cue"])
  if len(r)!=1:return {"status":"ABSTAIN_LEXICAL_ROLE_AMBIGUOUS","inputs":[],"target":None}
  (ins if next(iter(r))=="INPUT" else tar).extend(c["fields"])
 if len(tar)!=1:return {"status":"ABSTAIN_ROLE_CARDINALITY","inputs":[],"target":None}
 return {"status":"ROLES_IDENTIFIED","inputs":sorted(ins),"target":tar[0]}

def select_tool(task):
 base=g1.g0.select_tool_by_contract(task["tool_packs"],required_effect=str(task["required_effect"]),required_keys=task["required_keys"])
 hits=list(base["matches"])
 if len(hits)<=1:return {"status":"UNIQUE" if len(hits)==1 else "NONE","matches":hits}
 pol=str(task.get("selection_policy") or "")
 if pol.startswith("MIN_") or pol.startswith("MAX_"):
  key=pol[4:].lower(); vals=[x for x in hits if key in x]
  if len(vals)!=len(hits):return {"status":"MULTIPLE","matches":hits}
  best=(min if pol.startswith("MIN_") else max)(float(x[key]) for x in vals)
  hits=[x for x in vals if float(x[key])==best]
 return {"status":"UNIQUE" if len(hits)==1 else "MULTIPLE","matches":hits}

def plan_cost(task):
 start=frozenset(map(str,task["initial_resources"])); req=set(map(str,task.get("required_final_resources") or [task["goal_resource"]]))
 ops=sorted([dict(x) for x in task["operators"]],key=lambda x:str(x["operator_id"])); maxlen=int(task.get("max_length",8))
 pq=[(0,0,tuple(),start)]; best={start:0}
 while pq:
  cost,n,path,state=heapq.heappop(pq)
  if req.issubset(state):return {"status":"PLAN_FOUND","plan":list(path),"cost":cost}
  if n>=maxlen:continue
  for op in ops:
   if not set(map(str,op.get("requires",[]))).issubset(state):continue
   nxt=set(state);nxt.difference_update(map(str,op.get("removes",[])));nxt.update(map(str,op.get("provides",[])));fs=frozenset(nxt)
   nc=cost+float(op.get("cost",1))
   if nc<best.get(fs,float("inf")):
    best[fs]=nc;heapq.heappush(pq,(nc,n+1,path+(str(op["operator_id"]),),fs))
 return {"status":"NO_PLAN","plan":None,"cost":None}

def query_history(events,query):
 vals=[e.get("value") for e in events if e.get("op")=="SET" and str(e.get("key"))==str(query["key"])]
 op=str(query["op"])
 if op=="COUNT_UNIQUE":return len(set(vals))
 if op=="COUNT_SET":return len(vals)
 if op=="MAX_SEEN":return max(vals) if vals else None
 if op=="MIN_SEEN":return min(vals) if vals else None
 if op=="LAST_VALUE":return vals[-1] if vals else None
 if op=="SUM_SEEN":return sum(vals)
 raise G2Error("HISTORY_QUERY_UNSUPPORTED")

def _solve_float(A,b):
 n=len(b);m=[list(map(float,A[i]))+[float(b[i])] for i in range(n)]
 for c in range(n):
  p=max(range(c,n),key=lambda r:abs(m[r][c]))
  if abs(m[p][c])<1e-12:return None
  m[c],m[p]=m[p],m[c];d=m[c][c];m[c]=[v/d for v in m[c]]
  for r in range(n):
   if r==c:continue
   f=m[r][c];m[r]=[x-f*y for x,y in zip(m[r],m[c])]
 return [m[i][-1] for i in range(n)]

def _fit_multi(xs,ys,funcs):
 cols=[[1.0]*len(xs),list(xs)]+[[fn(x) for x in xs] for fn in funcs];n=len(cols)
 xtx=[[sum(cols[i][k]*cols[j][k] for k in range(len(xs))) for j in range(n)] for i in range(n)]
 xty=[sum(cols[i][k]*ys[k] for k in range(len(xs))) for i in range(n)]
 for i in range(n):xtx[i][i]+=1e-14
 c=_solve_float(xtx,xty)
 if c is None:return None
 pred=[sum(c[j]*cols[j][k] for j in range(n)) for k in range(len(xs))]
 mean=sum(ys)/len(ys);spread=math.sqrt(sum((y-mean)**2 for y in ys)/len(ys));scale=max(spread,max(abs(y) for y in ys)*1e-9,1e-12)
 err=math.sqrt(sum((a-b)**2 for a,b in zip(ys,pred))/len(ys))/scale
 return c,err

def resolve_numeric(rows,threshold=1e-8):
 base=g1.resolve_generic_numeric(rows,threshold)
 if base.get("status")=="CAPABILITY_HIT__VERIFY_BEFORE_USE":return base
 xs=[float(r["x"]) for r in rows];ys=[float(r["y"]) for r in rows];names=sorted(g1.BASES)
 hits=[]
 for a,b in itertools.combinations(names,2):
  z=_fit_multi(xs,ys,[g1.BASES[a],g1.BASES[b]])
  if z and z[1]<=threshold:hits.append((z[1],a,b,z[0]))
 if not hits:return {"status":"CAPABILITY_MISS","route":None}
 hits.sort(key=lambda x:(x[0],x[1],x[2]));err,a,b,c=hits[0]
 return {"status":"CAPABILITY_HIT__VERIFY_BEFORE_USE","route":"G2_TWO_BASIS","bases":[a,b],"coefficients":c,"train_nrmse":err}

def predict_numeric(r,x):
 if r.get("route")!="G2_TWO_BASIS":return g1.predict_generic_numeric(r,x)
 c=list(map(float,r["coefficients"]));a,b=r["bases"]
 return c[0]+c[1]*float(x)+c[2]*g1.BASES[a](float(x))+c[3]*g1.BASES[b](float(x))
