from __future__ import annotations
import itertools, math
from collections import defaultdict
from functools import lru_cache

L="RSu<>NADI2PMEO"
POINT=set("NADI2PMEO")
MAP=set("NADI2")
FIL=set("PMEO")
STRUCT=set("RSu<>")
PERM=set("R<>")
CHARACTERISTIC=(
 (-9,3,-1,-9,9,-10,4,-8,4),
 (6,-10,-6,6,0,1,-10,8,5),
 (5,2,10,2,7,-5,5,-2,-3),
 (-6,-3,0,6,1,4,-2,-5,-3),
 (-1,-9,-10,-10,-9,-8,-2,-2),
 (0,-4,-1,9,7,-7,-3,4,6),
 (4,9,2,1,3,3,4),
 (1,8,-2,5,9,0),
)

def f(o,x):
 if o=="R":return x[::-1]
 if o=="S":return sorted(x)
 if o=="u":return list(dict.fromkeys(x))
 if not x and o in"<>":return []
 if o=="<":return x[1:]+x[:1]
 if o==">":return x[-1:]+x[:-1]
 if o=="N":return [-v for v in x]
 if o=="A":return [abs(v) for v in x]
 if o=="D":return [v-1 for v in x]
 if o=="I":return [v+1 for v in x]
 if o=="2":return [2*v for v in x]
 if o=="P":return [v for v in x if v>0]
 if o=="M":return [v for v in x if v<0]
 if o=="E":return [v for v in x if v%2==0]
 if o=="O":return [v for v in x if v%2!=0]
 raise ValueError(o)

def rp(p,x):
 y=list(x)
 for o in p:y=f(o,y)
 return tuple(y)

def programs(alpha=L,d=3):
 return tuple("".join(p) for n in range(d+1) for p in itertools.product(alpha,repeat=n))

def _inter(lo,hi,nlo=None,nhi=None):
 if nlo is not None:lo=nlo if lo is None else max(lo,nlo)
 if nhi is not None:hi=nhi if hi is None else min(hi,nhi)
 if lo is not None and hi is not None and lo>hi:return None
 return lo,hi

def _restrict(lo,hi,a,b,kind):
 if kind==">0":
  return _inter(lo,hi,nlo=math.floor(-b/a)+1) if a>0 else _inter(lo,hi,nhi=math.ceil(-b/a)-1)
 if kind=="<0":
  return _inter(lo,hi,nhi=math.ceil(-b/a)-1) if a>0 else _inter(lo,hi,nlo=math.floor(-b/a)+1)
 if kind==">=0":
  return _inter(lo,hi,nlo=math.ceil(-b/a)) if a>0 else _inter(lo,hi,nhi=math.floor(-b/a))
 raise ValueError(kind)

def _to_k(lo,hi,p):
 a=None if lo is None else math.ceil((lo-p)/2)
 b=None if hi is None else math.floor((hi-p)/2)
 if a is not None and b is not None and a>b:return None
 return a,b

@lru_cache(maxsize=None)
def scalar_pieces(prog):
 pieces=[(None,None,frozenset((0,1)),1,0)]
 for o in prog:
  q=[]
  for lo,hi,ps,a,b in pieces:
   if o=="N":q.append((lo,hi,ps,-a,-b))
   elif o=="A":
    z=_restrict(lo,hi,a,b,">=0")
    if z:q.append((*z,ps,a,b))
    z=_restrict(lo,hi,a,b,"<0")
    if z:q.append((*z,ps,-a,-b))
   elif o=="D":q.append((lo,hi,ps,a,b-1))
   elif o=="I":q.append((lo,hi,ps,a,b+1))
   elif o=="2":q.append((lo,hi,ps,2*a,2*b))
   elif o in"PM":
    z=_restrict(lo,hi,a,b,">0" if o=="P" else "<0")
    if z:q.append((*z,ps,a,b))
   elif o in"EO":
    want=0 if o=="E" else 1
    nps=set()
    if a%2==0:
     if b%2==want:nps=set(ps)
    else:
     for p in ps:
      if (a*p+b)%2==want:nps.add(p)
    if nps:q.append((lo,hi,frozenset(nps),a,b))
   else:raise ValueError(o)
  pieces=q
 rows=[]
 for lo,hi,ps,a,b in pieces:
  for p in ps:
   z=_to_k(lo,hi,p)
   if z is not None:rows.append((p,z[0],z[1],a,b))
 return tuple(rows)

def _formula(rows,p,k):
 x=2*k+p
 for pp,lo,hi,a,b in rows:
  if pp==p and (lo is None or k>=lo) and (hi is None or k<=hi):
   return a,b,a*x+b
 return None

def scalar_equal(a,b):
 ra,rb=scalar_pieces(a),scalar_pieces(b)
 for p in (0,1):
  cuts=set()
  for rows in (ra,rb):
   for pp,lo,hi,x,y in rows:
    if pp!=p:continue
    if lo is not None:cuts.add(lo)
    if hi is not None:cuts.add(hi+1)
  bs=sorted(cuts)
  cells=[(None,None)] if not bs else [(None,bs[0]-1)]+[(x,bs[i+1]-1 if i+1<len(bs) else None) for i,x in enumerate(bs)]
  for lo,hi in cells:
   if lo is not None and hi is not None and lo>hi:continue
   if lo is None and hi is None:ks=(0,1)
   elif lo is None:ks=(hi-1,hi)
   elif hi is None:ks=(lo,lo+1)
   elif lo==hi:ks=(lo,)
   else:ks=(lo,lo+1)
   for k in ks:
    x,y=_formula(ra,p,k),_formula(rb,p,k)
    if (x is None)!=(y is None):return False
    if x is not None and x[2]!=y[2]:return False
 return True

@lru_cache(maxsize=1)
def pointwise_partition():
 ps=programs("NADI2PMEO",3)
 classes=[]
 for p in ps:
  for rep,members in classes:
   if scalar_equal(p,rep):
    members.append(p);break
  else:classes.append([p,[p]])
 canon={}
 members=defaultdict(list)
 for rep,ms in classes:
  c=min(ms,key=lambda s:(len(s),s))
  for s in ms:canon[s]=c;members[c].append(s)
 return canon,dict(members),len(classes)

def _base_neighbors(s,maxlen=3):
 canon,members,_=pointwise_partition()
 out=set();n=len(s)
 for i in range(n):
  if s[i] in POINT:
   j=i
   while j<n and s[j] in POINT:j+=1
   for a in range(i,j):
    for b in range(a+1,j+1):
     block=s[a:b];c=canon[block]
     for z in (c,*members[c]):
      q=s[:a]+z+s[b:]
      if q!=s and len(q)<=maxlen:out.add(q)
 pairs=(("RR",""),("<>",""),("><",""),("SS","S"),("uu","u"),("RS","S"),("<S","S"),(">S","S"),("R<",">R"),("R>","<R"),("Su","uS"))
 for a,b in pairs:
  for x,y in ((a,b),(b,a)):
   if not x:continue
   k=0
   while True:
    i=s.find(x,k)
    if i<0:break
    q=s[:i]+y+s[i+len(x):]
    if q!=s and len(q)<=maxlen:out.add(q)
    k=i+1
 for i in range(n-1):
  a,b=s[i:i+2]
  if (a=="R" and b in POINT) or (b=="R" and a in POINT):out.add(s[:i]+b+a+s[i+2:])
  if (a in"<>" and b in MAP) or (b in"<>" and a in MAP):out.add(s[:i]+b+a+s[i+2:])
  X=FIL|set("DI2")
  if (a=="S" and b in X) or (b=="S" and a in X):out.add(s[:i]+b+a+s[i+2:])
  X=FIL|set("NDI2")
  if (a=="u" and b in X) or (b=="u" and a in X):out.add(s[:i]+b+a+s[i+2:])
 if n>=3:
  for i in range(n-2):
   a,b,c=s[i:i+3];rs=[]
   if a in PERM and b in POINT and c=="S":rs.append(b+"S")
   if a in PERM and b=="u" and c=="S":rs.append("uS")
   if a in FIL and b in PERM and c==a:rs.append(a+b)
   if a=="u" and b in PERM and c=="u":rs.append("u"+b)
   if a=="u" and b in MAP and c=="u":rs.append(b+"u")
   if a=="S" and b in POINT and c=="S":rs.append(b+"S")
   for z in rs:
    q=s[:i]+z+s[i+3:]
    if len(q)<=maxlen:out.add(q)
 for x,y in (("SN","NSR"),("NSR","SN")):
  k=0
  while True:
   i=s.find(x,k)
   if i<0:break
   q=s[:i]+y+s[i+len(x):]
   if q!=s and len(q)<=maxlen:out.add(q)
   k=i+1
 return out

def neighbors(s,maxlen=3):
 out=set(_base_neighbors(s,maxlen))
 pairs=(("SR","NSN"),("SNR","NS"),("ASA","AS"),("AuA","Au"),("SuR","SRu"),("SAR","NSA"),("Su>","S>u"),("MS<","S<M"),("PS>","S>P"))
 for a,b in pairs:
  for x,y in ((a,b),(b,a)):
   k=0
   while True:
    i=s.find(x,k)
    if i<0:break
    q=s[:i]+y+s[i+len(x):]
    if q!=s and len(q)<=maxlen:out.add(q)
    k=i+1
 if s.startswith("2O") and len(s)==3 and s[2] in STRUCT:out.add("2O")
 if len(s)==3 and s[0]=="2" and s[1] in STRUCT and s[2]=="O":out.add("2O")
 dis={("P","M"),("M","P"),("E","O"),("O","E")}
 if len(s)==3 and s[1] in PERM and (s[0],s[2]) in dis:out.add("2O")
 return out

@lru_cache(maxsize=1)
def sequence_components():
 ps=programs()
 aset=set(ps);adj={s:set() for s in ps}
 for s in ps:
  for q in neighbors(s,3):
   if q in aset:adj[s].add(q);adj[q].add(s)
 seen=set();cc=[]
 for s in ps:
  if s in seen:continue
  stack=[s];seen.add(s);c=[]
  while stack:
   x=stack.pop();c.append(x)
   for q in adj[x]:
    if q not in seen:seen.add(q);stack.append(q)
  cc.append(tuple(sorted(c,key=lambda z:(len(z),z))))
 return tuple(cc)

def signature(p):
 return tuple(rp(p,x) for x in CHARACTERISTIC)

def evaluate():
 canon,members,pc=pointwise_partition()
 cc=sequence_components()
 member_agreement=True
 seen={}
 collision=[]
 for c in cc:
  sig=signature(c[0])
  if any(signature(p)!=sig for p in c):member_agreement=False
  if sig in seen:collision.append((seen[sig],c[0]))
  else:seen[sig]=c[0]
 return {
  "schema":"PROJECT_BRAIN_BYTES_SEQUENCE_CHARACTERISTIC_SET_V1",
  "program_count":len(programs()),
  "pointwise_program_count":len(programs("NADI2PMEO",3)),
  "pointwise_exact_classes":pc,
  "sequence_global_equivalence_components":len(cc),
  "characteristic_set_size":len(CHARACTERISTIC),
  "distinct_characteristic_signatures":len(seen),
  "component_members_agree_on_characteristic_set":member_agreement,
  "cross_component_signature_collisions":collision,
  "pass":len(programs())==2955 and pc==200 and len(cc)==809 and member_agreement and len(seen)==809 and not collision,
 }

if __name__=="__main__":
 import json
 out=evaluate();print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
