from itertools import product
class Q:
 def __init__(s,a=1,b=0,z=1,p=0):s.a,s.b,s.z,s.p=a,b,z,p
 def __neg__(s):return Q(-s.a,-s.b,s.z,s.p)
 def __abs__(s):return s if s.a*s.z>0 else -s
 def __add__(s,x):return Q(s.a,s.b+x,s.z,s.p)
 __radd__=__add__
 def __sub__(s,x):return Q(s.a,s.b-x,s.z,s.p)
 def __rsub__(s,x):return Q(-s.a,x-s.b,s.z,s.p)
 def __mul__(s,x):return Q(s.a*x,s.b*x,s.z,s.p)
 __rmul__=__mul__
 def __gt__(s,x):return s.a*s.z>0
 def __lt__(s,x):return s.a*s.z<0
 def __mod__(s,x):return (s.a*s.p+s.b)%x
def one(K,o,x):
 y=K.f(o.lower(),x)
 return y
def sg(K,w):
 c=[]
 for x in range(-3,3):
  a=1
  for o in w:
   y=one(K,o,x)
   if isinstance(y,bool):
    if not y:a=0;break
   elif y is None:a=0;break
   else:x=y
  c.append(x if a else None)
 for z in(-1,1):
  for p in(0,1):
   x=Q(z=z,p=p);a=1;old=K.math.isfinite;K.math.isfinite=lambda x:True
   try:
    for o in w:
     y=one(K,o,x)
     if isinstance(y,bool):
      if not y:a=0;break
     elif y is None:a=0;break
     else:x=y
    c.append((x.a,x.b) if a else None)
   finally:K.math.isfinite=old
 return tuple(c)
def roles(K):
 A=K.L
 tests=[[3,1,2,0],[2,0,2,1]]
 def r(x):return x[::-1]
 def s(x):return sorted(x)
 def u(x):return list(dict.fromkeys(x))
 def l(x):return x[1:]+x[:1] if x else []
 def h(x):return x[-1:]+x[:-1] if x else []
 fs=[r,s,u,l,h];R={}
 for o in A:
  q=[K.f(o,list(x)) for x in tests]
  for i,g in enumerate(fs):
   if q==[g(list(x)) for x in tests]:R[i]=o
 if len(R)!=5:raise ValueError("STRUCTURAL_ROLE_FAIL")
 T=set(R.values());M=[];F=[]
 x=[-2,-1,0,1,2]
 for o in A:
  if o in T:continue
  y=K.f(o,list(x))
  (M if len(y)==len(x) else F).append(o)
 return A,R,M,F
def props(K,M,F):
 se=lambda a,b:sg(K,a)==sg(K,b);inc=[];dec=[];idem=[];up=[];down=[]
 for m in M:
  v=[one(K,m,x) for x in range(-3,4)];t=sg(K,m)[6:]
  if all(v[i]<v[i+1] for i in range(6)) and all(q and q[0]>0 for q in t):inc.append(m)
  if all(v[i]>v[i+1] for i in range(6)) and all(q and q[0]<0 for q in t):dec.append(m)
  if se(m+m,m):idem.append(m)
 for f in F:
  v=[bool(one(K,f,x)) for x in range(-3,4)];t=sg(K,f)[6:];n=all(q is not None for q in t[:2]);p=all(q is not None for q in t[2:])
  if not n and p and all((not v[i])or v[i+1] for i in range(6)):up.append(f)
  if n and not p and all(v[i]or(not v[i+1]) for i in range(6)):down.append(f)
 return set(inc),set(dec),set(idem),set(up),set(down)
def equations(K):
 A,R,M,F=roles(K);rv,so,uq,le,ri=[R[i] for i in range(5)];P=rv+le+ri;S=set(M+F)
 U=[""]+list(A)+["".join(x) for n in(2,3) for x in product(A,repeat=n)]
 W=[""]+list(S)+["".join(x) for n in(2,3) for x in product(S,repeat=n)]
 g={};E=[];se=lambda a,b:sg(K,a)==sg(K,b)
 for w in W:g.setdefault(sg(K,w),[]).append(w)
 for q in g.values():E += [(w,q[0]) for w in q[1:]]
 inc,dec,idem,up,down=props(K,M,F);inj=inc|dec
 E += [(le+ri,""),(ri+le,""),(rv+rv,""),(rv+le,ri+rv),(rv+ri,le+rv)]
 E += [(p+m,m+p) for p in P for m in M]+[(p+so,so) for p in P]+[(so+so,so)]
 E += [(so+m,m+so) for m in inc]
 E += [x for f in F for x in ((so+f,f+so),(rv+f,f+rv),(uq+f,f+uq))]
 E += [(uq+m,m+uq) for m in inj]+[(uq+so,so+uq),(uq+uq,uq)]
 for n in dec:
  if se(n+n,""):E += [(n+so+n,so+rv),(n+so+rv,so+n),(so+n+rv,n+so),(so+n+so,n+so)]
 E += [(uq+p+uq,uq+p) for p in P]
 for a in idem:E += [(a+so+a,a+so),(so+a+so,a+so),(a+uq+a,a+uq),(uq+a+uq,a+uq)]
 E += [(so+m+so,m+so) for m in M]+[(uq+m+uq,m+uq) for m in M]
 z=None
 for w in U:
  q=sg(K,"".join(c for c in w if c in S))
  if q is not None and all(x is None for x in q):z=w;break
 if z:E += [(w,z) for w in U if w and sg(K,"".join(c for c in w if c in S))==sg(K,z)]
 E += [(f+p+f,f+p) for f in F for p in P]+[(so+uq+rv,so+rv+uq),(so+uq+ri,so+ri+uq)]
 for a in idem:
  for n in dec:
   if se(n+n,"") and se(n+a,a):E += [(so+a+rv,n+so+a)]
 for f in down:E += [(so+le+f,f+so+le)]
 for f in up:E += [(so+ri+f,f+so+ri)]
 return U,list(dict.fromkeys(E))
def check(K):
 U,E=equations(K);ix={w:i for i,w in enumerate(U)};p=list(range(len(U)))
 def f(x):
  while p[x]!=x:p[x]=p[p[x]];x=p[x]
  return x
 def j(a,b):
  a,b=f(a),f(b)
  if a!=b:p[b]=a
 z=1
 while z:
  n=len({f(i) for i in range(len(U))})
  for w in U:
   for a,b in E:
    for x,y in((a,b),(b,a)):
     if not x:continue
     k=0
     while 1:
      k=w.find(x,k)
      if k<0:break
      v=w[:k]+y+w[k+len(x):]
      if len(v)<=3 and v in ix:j(ix[w],ix[v])
      k+=1
  z=len({f(i) for i in range(len(U))})<n
 X=[()]
 for n in range(1,4):X+=list(product(range(-4,5),repeat=n))
 X += [(-4,-4,-4,-3),(-4,-3,-4,-2),(-4,-3,-2,-3)]
 sig={w:[] for w in U};by=[[w for w in U if len(w)==n] for n in range(4)]
 for x in X:
  o={"":list(x)};sig[""].append(tuple(x))
  for n in range(1,4):
   for w in by[n]:o[w]=K.f(w[-1],o[w[:-1]]);sig[w].append(tuple(o[w]))
 sig={w:tuple(v) for w,v in sig.items()};N=len(set(sig.values()));C=len({f(i) for i in range(len(U))})
 d={}
 for w in U:d.setdefault(f(ix[w]),set()).add(sig[w])
 assert C==N and all(len(x)==1 for x in d.values())
 return {"status":"PASS","programs":len(U),"equations":len(E),"classes":N,"witnesses":len(X)}
